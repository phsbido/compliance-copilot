"""
Camada 7 — Governança e Segurança (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: aplicar constraints sobre
o comportamento do sistema. Neste protótipo, as constraints são:

1. nunca citar norma, artigo ou valor que não esteja na fonte consultada;
2. sempre indicar a fonte;
3. recusar parecer jurídico definitivo e perguntas fora de escopo;
4. usar apenas fontes públicas do BCB.

A camada atua em três momentos (ver docs/decisoes_arquitetura.md, Camada 7,
"Camada 7 v2", 2026-09-24):

- **antes da geração**: `POLITICA_SINTESE` (regras injetadas pela Camada 3 no
  prompt de síntese) e as recusas diretas (`recusar_*`), que desviam o fluxo
  sem chamar o LLM para sintetizar — incluindo quando a Camada 5 não achou
  base normativa;
- **depois da geração**: `validar_resposta` confere, de forma determinística
  (padrões de texto, não semântica), as normas, os artigos e os valores
  numéricos citados contra os trechos normativos usados como contexto, e
  anexa avisos, as fontes consultadas e o aviso de validação humana;
- **na ingestão**: `validar_fonte_publica` impede que a Camada 5 ingira
  fonte fora dos domínios do BCB.

Limites declarados: a verificação é lexical. Não detecta afirmação falsa que
não cite norma, artigo nem valor, e confere só o contexto do turno atual,
não o histórico da conversa (Camada 6).
"""
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Políticas e recusas (antes da geração)
# --------------------------------------------------------------------------

POLITICA_SINTESE = (
    "Você é um copiloto de compliance regulatório de Open Finance e contas PJ "
    "no Brasil. Regras obrigatórias:\n"
    "1. Responda somente com base no contexto normativo fornecido. Não use "
    "conhecimento externo sobre normas.\n"
    "2. Se a pergunta mencionar uma norma que não aparece no contexto, diga "
    "explicitamente que ela não está disponível no corpus consultado e não "
    "descreva o conteúdo dela.\n"
    "3. Ao afirmar um requisito, indique entre parênteses a norma e o artigo "
    "(ou a seção do anexo) de onde ele vem, usando as informações do cabeçalho "
    "do trecho. Não copie os cabeçalhos entre colchetes e não mencione artigos "
    "que não aparecem no contexto.\n"
    "4. Reproduza valores numéricos (prazos, limites, quantidades, "
    "percentuais) exatamente como estão no texto, sem arredondar nem converter.\n"
    "5. Se o contexto não for suficiente para responder, diga isso.\n"
    "6. Nunca dê parecer jurídico definitivo sobre um caso concreto."
)

AVISO_VALIDACAO_HUMANA = (
    "\n\n---\nEsta resposta é apoiada em atos normativos públicos do BCB, mas "
    "não constitui parecer jurídico definitivo. Valide com a área jurídica/"
    "compliance antes de qualquer decisão final."
)

RECUSA_PARECER_JURIDICO = (
    "Não posso emitir parecer jurídico definitivo sobre casos concretos. "
    "Posso indicar o que os atos normativos públicos do BACEN dizem sobre o "
    "tema em geral — se for útil, reformule a pergunta nesses termos. A "
    "decisão final sobre o seu caso deve ser validada por um profissional "
    "jurídico/compliance qualificado."
)

RECUSA_FORA_DE_ESCOPO = (
    "Este copiloto responde apenas perguntas sobre requisitos regulatórios "
    "de Open Finance e contas PJ no Brasil, com base em atos normativos "
    "públicos do BACEN. Sua pergunta parece estar fora desse escopo — se "
    "for sobre esse tema, reformule para eu poder ajudar."
)

RECUSA_SEM_BASE = (
    "Não encontrei, no corpus de atos normativos consultado, nenhum trecho "
    "relacionado à sua pergunta — por isso não vou responder, para não "
    "apresentar informação sem fonte. Reformule com outros termos ou "
    "consulte diretamente o site do BCB (https://www.bcb.gov.br)."
)

# Domínios aceitos como fonte pública oficial pela ingestão (Camada 5).
DOMINIOS_FONTES_PUBLICAS = {"www.bcb.gov.br", "bcb.gov.br", "normativos.bcb.gov.br"}


def recusar_parecer_juridico() -> str:
    return RECUSA_PARECER_JURIDICO


def recusar_fora_de_escopo() -> str:
    return RECUSA_FORA_DE_ESCOPO


def recusar_sem_base() -> str:
    return RECUSA_SEM_BASE


def validar_fonte_publica(url: str) -> None:
    """Levanta ValueError se `url` não for HTTPS num domínio do BCB."""
    partes = urllib.parse.urlparse(url)
    if partes.scheme != "https" or partes.hostname not in DOMINIOS_FONTES_PUBLICAS:
        raise ValueError(
            f"Fonte recusada pela Camada 7: {url} não é uma URL HTTPS de "
            f"{', '.join(sorted(DOMINIOS_FONTES_PUBLICAS))}."
        )


# --------------------------------------------------------------------------
# Extração de citações
# --------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


_NORMA_REGEX = re.compile(
    r"\b(?P<tipo>Lei\s+Complementar|Lei|Decreto"
    r"|Resolu[çc][ãa]o\s+Conjunta(?:\s+BCB/CMN)?"
    r"|Resolu[çc][ãa]o\s+(?:BCB|CMN|CNSP)|Resolu[çc][ãa]o"
    r"|Circular\s+Susep|Circular"
    r"|Instru[çc][ãa]o\s+Normativa(?:\s+BCB)?)"
    r"\s+n[º°o]\.?\s*(?P<numero>\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

# "art. 6º", "Art. 13-A", "artigo 51", "arts. 5º e 6º", "artigos 13 e 14".
_ID_ARTIGO = r"\d+(?:\s*[º°])?(?:-[A-Z]\b)?"
_ARTIGO_REGEX = re.compile(
    rf"\b(?:arts?\.?|artigos?)\s*(?P<lista>{_ID_ARTIGO}(?:\s*(?:,|\be\b)\s*{_ID_ARTIGO})*)",
    re.IGNORECASE,
)

# Frase que declara uma norma indisponível, em vez de usá-la como fonte
# ("Não encontrei a Resolução BCB nº 32/2020 no contexto"): marcador
# explícito de ausência, ou negação + termo de disponibilidade/localização.
# A primeira versão era uma lista fechada de expressões e deixou passar
# "Não foi encontrado…", "Não estou com… disponíveis" e "não é possível
# determinar…" no benchmark v3 (ver docs/evidencias_empiricas.md). Negar
# algo sobre o conteúdo ("a norma X não exige Y") continua sendo citação.
# "forneça (mais informações)" = pedido ao usuário, frase não afirmativa
# (benchmark v4); "por favor" sozinho não basta ("Por favor, note que a norma
# X exige…" é afirmação).
_AUSENCIA_EXPLICITA = re.compile(
    r"aus[êe]ncia|ausente|indispon[ií]ve|fora\s+do\s+(?:corpus|contexto)|\bforne[çc]a\b", re.IGNORECASE
)
_NEGACAO = re.compile(r"\b(?:n[ãa]o|nenhum|nenhuma)\b", re.IGNORECASE)
_DISPONIBILIDADE = re.compile(
    r"encontr|localiz|identific|dispon[ií]ve|\bconsta|men[çc][ãa]o|mencion|contexto|corpus"
    r"|fornecid|acesso|poss[ií]vel|\bposso\b|informa[çc][ãõ]|exist[êe]ncia",
    re.IGNORECASE,
)


def _declara_ausencia(frase: str) -> bool:
    return bool(_AUSENCIA_EXPLICITA.search(frase)
                or (_NEGACAO.search(frase) and _DISPONIBILIDADE.search(frase)))


# Abreviações após as quais um ponto não termina a frase ("Art. 6º").
_ABREVIACOES = {"art", "arts", "n", "nº", "no", "inc", "res", "al", "p", "pag", "sr", "sra", "dr"}


def _chave_norma(tipo: str, numero: str) -> tuple[str, str]:
    tipo = re.sub(r"\s+", " ", _normalizar(tipo)).replace(" bcb/cmn", "")
    if tipo == "instrucao normativa":
        tipo = "instrucao normativa bcb"
    return tipo, numero.replace(".", "").lstrip("0") or "0"


def _mesma_norma(a: tuple[str, str], b: tuple[str, str]) -> bool:
    if a[1] != b[1]:
        return False
    if a[0] == b[0]:
        return True
    # "Resolução nº 4.553" (sem qualificador) casa com qualquer resolução de
    # mesmo número — o modelo nem sempre repete o órgão emissor.
    genericas = {a[0], b[0]} & {"resolucao"}
    return bool(genericas) and a[0].startswith("resolucao") and b[0].startswith("resolucao")


def _ids_artigo(lista: str) -> list[str]:
    return [re.sub(r"\s*[º°]", "", i).replace(" ", "").upper() for i in re.findall(_ID_ARTIGO, lista)]


def _frases(texto: str) -> list[tuple[int, str]]:
    """(posição inicial, frase). Quebra em linha e em [.!?] seguido de
    maiúscula, exceto depois de abreviação ("Art. 6º" não quebra)."""
    frases = []
    for m_linha in re.finditer(r"[^\n]+", texto):
        linha, base, inicio = m_linha.group(0), m_linha.start(), 0
        for m in re.finditer(r"[.!?]\s+(?=[A-ZÀ-Ú\"(*-])", linha):
            anterior = re.findall(r"[\wº]+$", linha[inicio:m.start()])
            if anterior and _normalizar(anterior[0]) in _ABREVIACOES:
                continue
            frases.append((base + inicio, linha[inicio:m.end()]))
            inicio = m.end()
        frases.append((base + inicio, linha[inicio:]))
    return [(p, f) for p, f in frases if f.strip()]


@dataclass
class _Mencoes:
    normas: list[tuple[tuple[str, str], str, bool]]      # (chave, texto original, frase declara ausência)
    artigos: list[tuple[str, tuple[str, str] | None, bool]]  # (id, norma associada, frase declara ausência)


def _mencoes(texto: str) -> _Mencoes:
    """Normas e artigos citados, frase a frase. Cada artigo é associado à
    norma mais próxima na mesma frase (ou a nenhuma)."""
    normas, artigos = [], []
    for _, frase in _frases(texto):
        ausencia = _declara_ausencia(frase)
        normas_frase = []
        for m in _NORMA_REGEX.finditer(frase):
            chave = _chave_norma(m.group("tipo"), m.group("numero"))
            normas.append((chave, f"{m.group('tipo')} nº {m.group('numero')}", ausencia))
            normas_frase.append((m.start(), m.end(), chave))
        for m in _ARTIGO_REGEX.finditer(frase):
            associada = None
            if normas_frase:
                meio = (m.start() + m.end()) / 2
                associada = min(normas_frase, key=lambda n: abs((n[0] + n[1]) / 2 - meio))[2]
            for id_artigo in _ids_artigo(m.group("lista")):
                artigos.append((id_artigo, associada, ausencia))
    return _Mencoes(normas, artigos)


# --------------------------------------------------------------------------
# Valores numéricos
# --------------------------------------------------------------------------

_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15, "dezesseis": 16,
    "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
    "noventa": 90, "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200,
    "trezentos": 300, "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600,
    "setecentos": 700, "oitocentos": 800, "novecentos": 900,
}
_MULTIPLICADORES = {"mil": 1e3, "milhao": 1e6, "milhoes": 1e6, "bilhao": 1e9, "bilhoes": 1e9}
_UNIDADES = {
    "%": "percentual", "por cento": "percentual",
    "dia": "dia", "dias": "dia", "mes": "mes", "meses": "mes", "ano": "ano", "anos": "ano",
    "hora": "hora", "horas": "hora", "minuto": "minuto", "minutos": "minuto",
    "segundo": "segundo", "segundos": "segundo", "semana": "semana", "semanas": "semana",
    "trimestre": "trimestre", "trimestres": "trimestre", "semestre": "semestre", "semestres": "semestre",
}
_PALAVRA_NUM = "|".join(sorted(_EXTENSO, key=len, reverse=True))
_VALOR_REGEX = re.compile(
    rf"(?P<reais>r\$\s*)?\b(?P<num>\d{{1,3}}(?:\.\d{{3}})+(?:,\d+)?|\d+(?:,\d+)?"
    rf"|(?:{_PALAVRA_NUM})(?:\s+e\s+(?:{_PALAVRA_NUM}))*)\b"
    rf"(?:\s*\([^)]{{1,40}}\))?"
    rf"(?:\s*(?P<mult>milhoes|milhao|bilhoes|bilhao|mil)\b)?"
    rf"(?:\s*(?:de\s+)?(?P<unid>%|por cento|dias?\b|meses\b|mes\b|anos?\b|horas?\b|minutos?\b|segundos?\b|semanas?\b|trimestres?\b|semestres?\b))?"
)


def _valores(texto: str) -> dict[tuple[float, str], str]:
    """{(valor, unidade): trecho original} — só números com unidade,
    multiplicador (mil/milhões) ou R$; anos, artigos e incisos ficam de fora."""
    normalizado = _normalizar(texto)
    encontrados = {}
    for m in _VALOR_REGEX.finditer(normalizado):
        if not (m.group("mult") or m.group("unid") or m.group("reais")):
            continue
        num = m.group("num")
        if num[0].isdigit():
            valor = float(num.replace(".", "").replace(",", "."))
        else:
            valor = float(sum(_EXTENSO[p] for p in re.findall(r"\w+", num) if p in _EXTENSO))
        valor *= _MULTIPLICADORES.get(m.group("mult") or "", 1)
        unidade = "real" if m.group("reais") else _UNIDADES.get(m.group("unid") or "", "quantidade")
        # A normalização remove acentos sem mudar o tamanho do texto em
        # português, então a mesma posição recupera o trecho original.
        original = texto[m.start():m.end()] if len(normalizado) == len(texto) else m.group(0)
        encontrados.setdefault((round(valor, 6), unidade), original.strip())
    return encontrados


# --------------------------------------------------------------------------
# Contexto normativo (formato da Camada 4: "Fonte: título (url)\ntrecho")
# --------------------------------------------------------------------------

_FONTE_REGEX = re.compile(r"^Fonte:\s*(.+?)\s*\((https?://[^\s)]+)\)\s*$", re.MULTILINE)


@dataclass
class _Contexto:
    fontes: list[tuple[str, str]]
    normas: set[tuple[str, str]]
    artigos: set[str]
    pares: set[tuple[tuple[str, str], str]]  # (norma, artigo) atestados no contexto
    valores: set[tuple[float, str]]


def _analisar_contexto(contexto: str) -> _Contexto:
    fontes, normas, artigos, pares = [], set(), set(), set()
    marcas = list(_FONTE_REGEX.finditer(contexto))
    blocos = []
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(contexto)
        blocos.append((m.group(1), m.group(2), contexto[m.end():fim]))
        if (m.group(1), m.group(2)) not in fontes:
            fontes.append((m.group(1), m.group(2)))
    if not blocos and contexto.strip():
        blocos.append(("", "", contexto))

    for titulo, _, texto in blocos:
        m_titulo = _NORMA_REGEX.search(titulo)
        norma_bloco = _chave_norma(m_titulo.group("tipo"), m_titulo.group("numero")) if m_titulo else None
        if norma_bloco:
            normas.add(norma_bloco)
        mencoes = _mencoes(texto)
        normas.update(chave for chave, _, _ in mencoes.normas)
        for id_artigo, associada, _ in mencoes.artigos:
            artigos.add(id_artigo)
            # Artigo sem norma na mesma frase pertence à norma do bloco;
            # remissão explícita ("art. 44 da Resolução Conjunta nº 1")
            # pertence à norma citada.
            dona = associada or norma_bloco
            if dona:
                pares.add((dona, id_artigo))
    return _Contexto(fontes, normas, artigos, pares, set(_valores(contexto)))


# --------------------------------------------------------------------------
# Validação (depois da geração)
# --------------------------------------------------------------------------

@dataclass
class ResultadoValidacao:
    texto_final: str
    normas_nao_verificadas: list[str] = field(default_factory=list)
    normas_declaradas_ausentes: list[str] = field(default_factory=list)
    artigos_nao_verificados: list[str] = field(default_factory=list)
    artigos_fora_da_norma: list[str] = field(default_factory=list)
    valores_nao_verificados: list[str] = field(default_factory=list)
    fontes: list[tuple[str, str]] = field(default_factory=list)
    # Aviso calculado com o validador da v1/v2 (só regex de artigo e norma),
    # mantido para comparar versões com a mesma régua.
    aviso_legado: bool = False

    @property
    def possui_aviso(self) -> bool:
        return bool(self.normas_nao_verificadas or self.artigos_nao_verificados
                    or self.artigos_fora_da_norma or self.valores_nao_verificados)

    def categorias(self) -> dict:
        return {
            "normas_nao_verificadas": self.normas_nao_verificadas,
            "normas_declaradas_ausentes": self.normas_declaradas_ausentes,
            "artigos_nao_verificados": self.artigos_nao_verificados,
            "artigos_fora_da_norma": self.artigos_fora_da_norma,
            "valores_nao_verificados": self.valores_nao_verificados,
            "possui_aviso": self.possui_aviso,
            "aviso_legado": self.aviso_legado,
        }


def _rotulo_norma(chave: tuple[str, str]) -> str:
    tipo = (chave[0].title().replace("Bcb", "BCB").replace("Cmn", "CMN")
            .replace("Resolucao", "Resolução").replace("Instrucao", "Instrução"))
    return f"{tipo} nº {chave[1]}"


def validar_resposta(resposta: str, contexto_normativo: str) -> ResultadoValidacao:
    ctx = _analisar_contexto(contexto_normativo)
    mencoes = _mencoes(resposta)

    def norma_no_contexto(chave):
        return any(_mesma_norma(chave, c) for c in ctx.normas)

    citadas, ausentes = {}, {}
    for chave, original, ausencia in mencoes.normas:
        if norma_no_contexto(chave):
            continue
        (ausentes if ausencia else citadas).setdefault(chave, original)
    normas_nao_verificadas = sorted(citadas.values())
    normas_declaradas_ausentes = sorted(v for k, v in ausentes.items() if k not in citadas)

    nao_verificados, fora_da_norma = set(), set()
    for id_artigo, associada, ausencia in mencoes.artigos:
        if ausencia:
            continue
        if associada is not None:
            if not norma_no_contexto(associada):
                continue  # a própria norma já foi avaliada acima
            if any(_mesma_norma(associada, n) and a == id_artigo for n, a in ctx.pares):
                continue
            if id_artigo in ctx.artigos:
                fora_da_norma.add(f"art. {id_artigo} ({_rotulo_norma(associada)})")
            else:
                nao_verificados.add(id_artigo)
        elif id_artigo not in ctx.artigos:
            nao_verificados.add(id_artigo)

    valores = [texto for chave, texto in _valores(resposta).items() if chave not in ctx.valores]

    resultado = ResultadoValidacao(
        texto_final="",
        normas_nao_verificadas=normas_nao_verificadas,
        normas_declaradas_ausentes=normas_declaradas_ausentes,
        artigos_nao_verificados=sorted(nao_verificados, key=lambda a: (int(re.match(r"\d+", a).group(0)), a)),
        artigos_fora_da_norma=sorted(fora_da_norma),
        valores_nao_verificados=valores,
        fontes=ctx.fontes,
        aviso_legado=_aviso_legado(resposta, contexto_normativo),
    )
    resultado.texto_final = _montar_texto(resposta, resultado)
    return resultado


def _montar_texto(resposta: str, r: ResultadoValidacao) -> str:
    avisos = []
    if r.normas_nao_verificadas:
        avisos.append(
            f"Aviso: a resposta cita {'; '.join(r.normas_nao_verificadas)}, que não consta nos "
            f"trechos normativos consultados — não foi possível verificar essa citação no corpus indexado."
        )
    if r.artigos_nao_verificados:
        avisos.append(
            f"Aviso: a resposta cita art. {', '.join(r.artigos_nao_verificados)}, que não aparece nos "
            f"trechos normativos consultados — confirme essa referência na fonte oficial antes de usá-la."
        )
    if r.artigos_fora_da_norma:
        avisos.append(
            f"Aviso: a resposta atribui {'; '.join(r.artigos_fora_da_norma)}, mas nos trechos "
            f"consultados esse artigo pertence a outra norma — confirme a atribuição na fonte oficial."
        )
    if r.valores_nao_verificados:
        avisos.append(
            f"Aviso: os valores {'; '.join(repr(v) for v in r.valores_nao_verificados)} não aparecem nos "
            f"trechos normativos consultados — confira prazos, limites e quantidades na fonte oficial."
        )
    texto = resposta
    if avisos:
        texto += "\n\n" + "\n".join(avisos)
    if r.fontes:
        texto += "\n\nFontes consultadas:\n" + "\n".join(f"- {t} ({u})" for t, u in r.fontes)
    return texto + AVISO_VALIDACAO_HUMANA


def validar_citacao(resposta: str, contexto_normativo: str) -> str:
    """Compatibilidade com a interface da v1: só o texto final."""
    return validar_resposta(resposta, contexto_normativo).texto_final


# --------------------------------------------------------------------------
# Validador da v1/v2 (inalterado), para a métrica legada
# --------------------------------------------------------------------------

_ARTIGO_REGEX_V1 = re.compile(r"art(?:igo)?\.?\s*(\d+)", re.IGNORECASE)
_NORMA_REGEX_V1 = re.compile(
    r"(Resolução(?:\s+Conjunta|\s+BCB)?|Circular|Instrução Normativa)\s+n[ºo°]\.?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)


def _aviso_legado(resposta: str, contexto: str) -> bool:
    artigos = {m.group(1) for m in _ARTIGO_REGEX_V1.finditer(resposta)}
    artigos_ctx = {m.group(1) for m in _ARTIGO_REGEX_V1.finditer(contexto)}
    normas = {f"{m.group(1).strip()} nº {m.group(2)}" for m in _NORMA_REGEX_V1.finditer(resposta)}
    normas_ctx = {f"{m.group(1).strip()} nº {m.group(2)}" for m in _NORMA_REGEX_V1.finditer(contexto)}
    return bool(artigos - artigos_ctx or normas - normas_ctx)
