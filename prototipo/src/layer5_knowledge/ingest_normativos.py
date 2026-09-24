"""
Pipeline de ingestão em camadas (Bronze/Silver/Gold) — Camada 5.

Alimenta a base de conhecimento consultada em runtime: `KnowledgeBase`
(`knowledge_base.py`) lê **somente** a camada Gold gerada aqui (ver
docs/decisoes_arquitetura.md, Camada 5, "Ingestão por URL e consumo da
Gold", 2026-09-24).

**Entrada**: `data/normativos/fontes_url.json` — URLs oficiais das páginas
de normativos do BCB (`.../exibenormativo?tipo=...&numero=...`) e, para
cada uma, se entra no corpus de runtime (`corpus_runtime`).

**Bronze** (`1_bronze_raw/`, dado bruto, sem alteração):
- `<arquivo>.json`: resposta do endpoint JSON que a própria página consome
  (`_API_NORMATIVO`), com metadados oficiais e o campo `Texto` (HTML).
- `<arquivo>.pdf`: quando a página lista versões consolidadas em PDF
  (campo `Documentos`), a mais recente na versão "limpa" (`_vN_L.pdf`).
  Motivo: para normas anteriores a 2021, o `Texto` da API é a **redação
  original** (ex.: Resolução Conjunta nº 1/2020 ainda diz "Open Banking"),
  e o texto vigente só existe nesses PDFs. Sem PDF consolidado (normas
  recentes, ou que o BCB mantém consolidadas no próprio HTML), o texto vem
  do HTML.

**Silver** (`2_silver_cleaned/<arquivo>.json`, texto vigente estruturado):
- remove texto tachado do HTML (redações revogadas), rodapés de página e
  artefatos de espaçamento do PDF;
- reconstrói parágrafos (HTML e PDF quebram linhas no meio da frase);
- separa as anotações de alteração ("(Redação dada pela...)", "(Incluído
  pela...)", "(Revogado pela...)") do texto e as guarda como metadado —
  no texto, elas citam outras normas e confundiriam a busca e a validação
  de citação da Camada 7;
- estrutura em unidades: artigo (com capítulo/seção como contexto) ou,
  em anexos sem artigos, seção numerada; marca unidades revogadas.

**Gold** (`3_gold_indexed/`, pronto para a busca):
- `<arquivo>.json`: trechos de até `TAMANHO_MAXIMO_TRECHO` caracteres, cada
  um com um cabeçalho de contexto no próprio texto (norma, capítulo/seção,
  artigo) e a frequência de tokens pré-calculada; unidades revogadas não
  entram;
- `indice_bm25.json`: estatísticas do corpus (N, tamanho médio, frequência
  de documento por token) só dos normativos com `corpus_runtime: true`.

Uso:
    python -m src.layer5_knowledge.ingest_normativos
        # baixa tudo (precisa de internet) e regera Bronze, Silver e Gold
    python -m src.layer5_knowledge.ingest_normativos --a-partir-da-bronze
        # não acessa a internet: regera Silver e Gold a partir da Bronze
        # versionada no repositório
"""
import argparse
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import pypdf

from src.layer5_knowledge.texto import tokenizar
from src.layer7_governance.governance import validar_fonte_publica

FONTE_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos"
FONTES_URL_FILE = FONTE_DIR / "fontes_url.json"
BRONZE_DIR = FONTE_DIR / "1_bronze_raw"
SILVER_DIR = FONTE_DIR / "2_silver_cleaned"
GOLD_DIR = FONTE_DIR / "3_gold_indexed"
INDICE_FILE = GOLD_DIR / "indice_bm25.json"

# Endpoint JSON consumido pela página pública exibenormativo do BCB, e local
# dos anexos (PDFs) listados no campo `Documentos` da mesma resposta.
_API_NORMATIVO = "https://www.bcb.gov.br/api/conteudo/app/normativos/exibenormativo"
_ANEXO_PDF = "https://normativos.bcb.gov.br/Lists/Normativos/Attachments/{id}/{arquivo}"
_TIMEOUT_S = 60
_USER_AGENT = "prototipo-compliance-monografia/1.0"

# Tamanho máximo de um trecho da Gold (caracteres, sem o cabeçalho). Menor
# que os 8000 da KnowledgeBase anterior: com top_k=3, o contexto enviado ao
# LLM cai de até ~24 mil para ~7,5 mil caracteres, e trechos menores dão ao
# BM25 unidades mais homogêneas para comparar.
TAMANHO_MAXIMO_TRECHO = 2500

# Parâmetros usuais do BM25 (Robertson & Zaragoza, 2009).
BM25_K1 = 1.5
BM25_B = 0.75

_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


# --------------------------------------------------------------------------
# Bronze
# --------------------------------------------------------------------------

def _http_get(url: str, accept: str) -> bytes:
    requisicao = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_S) as resposta:
        return resposta.read()


def _url_api(url_oficial: str) -> str:
    """URL pública (.../exibenormativo?tipo=X&numero=N) -> URL do endpoint
    JSON que a página consome (...?p1=X&p2=N)."""
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url_oficial).query)
    try:
        tipo, numero = params["tipo"][0], params["numero"][0]
    except KeyError as e:
        raise ValueError(f"URL sem parâmetro {e} (esperado ?tipo=...&numero=...): {url_oficial}") from None
    return f"{_API_NORMATIVO}?{urllib.parse.urlencode({'p1': tipo, 'p2': numero}, quote_via=urllib.parse.quote)}"


def _pdf_consolidado_mais_recente(documentos: str | None) -> tuple[str, int] | None:
    """Campo `Documentos` ("Res_Conj_0001_v1_O.pdf;718#;..._v9_L.pdf;414#;")
    -> (nome do PDF "limpo" de maior versão, versão). "_O" é o original e
    "_P" a versão com marcações; "_L" é o texto consolidado limpo."""
    if not documentos:
        return None
    candidatos = []
    for nome in re.findall(r"([^;#]+\.pdf)", documentos):
        m = re.search(r"_v(\d+)_L\.pdf$", nome.strip())
        if m:
            candidatos.append((int(m.group(1)), nome.strip()))
    if not candidatos:
        return None
    versao, nome = max(candidatos)
    return nome, versao


def etapa_bronze(fontes: list[dict]) -> None:
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    for antigo in BRONZE_DIR.iterdir():
        antigo.unlink()

    for fonte in fontes:
        nome, url_oficial = fonte["arquivo"], fonte["url_oficial"]
        # Constraint "usar apenas fontes públicas" (Camada 7), garantida em
        # código: URL fora dos domínios do BCB interrompe a ingestão.
        validar_fonte_publica(url_oficial)
        print(f"    baixando {nome} ...", flush=True)
        dados = json.loads(_http_get(_url_api(url_oficial), "application/json").decode("utf-8"))
        conteudo = dados.get("conteudo") or []
        if not conteudo:
            raise ValueError(f"API do BCB não retornou o normativo de {url_oficial}")
        registro = conteudo[0]

        pdf = _pdf_consolidado_mais_recente(registro.get("Documentos"))
        pdf_info = None
        if pdf:
            arquivo_pdf, versao_pdf = pdf
            url_pdf = _ANEXO_PDF.format(id=registro["Id"], arquivo=arquivo_pdf)
            validar_fonte_publica(url_pdf)
            print(f"      + PDF consolidado {arquivo_pdf}", flush=True)
            (BRONZE_DIR / f"{nome}.pdf").write_bytes(_http_get(url_pdf, "application/pdf"))
            pdf_info = {"arquivo": arquivo_pdf, "versao": versao_pdf, "url": url_pdf}
        elif not registro.get("Texto"):
            raise ValueError(f"Normativo sem texto HTML nem PDF consolidado: {url_oficial}")

        bruto = {
            "arquivo": nome,
            "url_oficial": url_oficial,
            "corpus_runtime": bool(fonte.get("corpus_runtime", False)),
            "obtido_em": datetime.now(timezone.utc).isoformat(),
            "pdf_consolidado": pdf_info,
            "resposta_api": dados,
        }
        (BRONZE_DIR / f"{nome}.json").write_text(json.dumps(bruto, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Silver
# --------------------------------------------------------------------------

class _ExtratorTextoHTML(HTMLParser):
    """HTML do campo `Texto` -> texto puro. Uma quebra de linha por elemento
    de bloco; linha de tabela vira "| célula | célula"; texto tachado
    (`<s>`, `<strike>`, `<del>` ou `text-decoration: line-through`), que o
    BCB usa para redações revogadas, é descartado."""

    _BLOCOS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"}
    _VAZIAS = {"br", "img", "hr", "meta", "input", "col", "wbr"}
    _CELULAS = {"td", "th"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []
        self._pilha: list[tuple[str, bool]] = []  # (tag, tachado)

    def _em_celula(self) -> bool:
        return any(tag in self._CELULAS for tag, _ in self._pilha)

    def _quebra(self) -> str:
        return " " if self._em_celula() else "\n"

    def handle_starttag(self, tag, attrs):
        estilo = (dict(attrs).get("style") or "").replace("&#58;", ":")
        tachado = tag in ("s", "strike", "del") or "line-through" in estilo
        if tag == "tr":
            self.partes.append("\n")
        elif tag in self._CELULAS:
            self.partes.append(" | ")
        elif tag == "br" or tag in self._BLOCOS:
            self.partes.append(self._quebra())
        if tag not in self._VAZIAS:
            self._pilha.append((tag, tachado))

    def handle_endtag(self, tag):
        if any(t == tag for t, _ in self._pilha):
            while self._pilha:
                if self._pilha.pop()[0] == tag:
                    break
        if tag == "tr":
            self.partes.append("\n")
        elif tag in self._BLOCOS:
            self.partes.append(self._quebra())

    def handle_data(self, data):
        if not any(tachado for _, tachado in self._pilha):
            self.partes.append(data)


def _texto_do_html(html: str) -> str:
    extrator = _ExtratorTextoHTML()
    extrator.feed(html)
    return "".join(extrator.partes)


def _texto_do_pdf(caminho: Path) -> str:
    leitor = pypdf.PdfReader(io.BytesIO(caminho.read_bytes()))
    return "\n".join(pagina.extract_text() or "" for pagina in leitor.pages)


_RODAPE_PAGINA = re.compile(r"^.*\bPágina\s+\d+\s+de\s+\d+\s*$", re.MULTILINE)

# Linha que começa um novo dispositivo/estrutura — nunca é continuação da
# linha anterior na reconstrução de parágrafos.
_INICIO_ESTRUTURAL = re.compile(
    r"^(Art\.\s*\d|§\s*\d|Parágrafo único|[IVXLC]+\s*[-–—]\s|[a-z]\)\s|\d+[.)]\s|\d+(?:\.\d+)+\.?\s|\|"
    r"|CAP[IÍ]TULO\b|T[IÍ]TULO\b|Se[çc][ãa]o\b|SE[ÇC][ÃA]O\b|Subse[çc][ãa]o\b|ANEXO\b|REGULAMENTO\b|\()"
)


def _limpar_artefatos(texto: str) -> str:
    texto = texto.replace(" ", " ")
    texto = _RODAPE_PAGINA.sub("", texto)
    # PDF: "Art. 3 1." -> "Art. 31."; "dados :" -> "dados:".
    texto = re.sub(r"Art\.\s*(\d)\s+(\d)", r"Art. \1\2", texto)
    texto = re.sub(r"[ \t]+([,.;:])", r"\1", texto)
    # "Art." ou "§" separados do número por quebra de linha.
    texto = re.sub(r"(Art\.|§)\s*\n\s*(?=\d)", r"\1 ", texto)
    return texto


def _reconstruir_paragrafos(texto: str) -> list[str]:
    """Junta linhas quebradas no meio da frase. Uma linha continua a anterior
    se não começa um dispositivo (ver `_INICIO_ESTRUTURAL`) e a anterior não
    termina frase — ou se começa com minúscula."""
    paragrafos: list[str] = []
    for linha in texto.splitlines():
        linha = re.sub(r"[ \t]+", " ", linha).strip()
        if not linha or linha == "|":
            continue
        if paragrafos and re.fullmatch(r"\d+(?:\.\d+)*\.?", paragrafos[-1]):
            # Número de seção sozinho na linha ("2.") + título na seguinte.
            paragrafos[-1] += " " + linha
        elif paragrafos and not _INICIO_ESTRUTURAL.match(linha) and (
            not re.search(r"[.;:!?]$", paragrafos[-1]) or linha[0].islower()
        ):
            paragrafos[-1] += " " + linha
        else:
            paragrafos.append(linha)
    return paragrafos


_ARTIGO_INICIO = re.compile(r"^Art\.\s*(\d+)\s*[º°o]?\s*(-\s*[A-Z]\b)?\.?")
_ESTRUTURA = re.compile(r"^(CAP[IÍ]TULO|T[IÍ]TULO|Se[çc][ãa]o|SE[ÇC][ÃA]O|Subse[çc][ãa]o)\b")
_NIVEIS = ["titulo", "capitulo", "secao", "subsecao"]
_ANEXO_INICIO = re.compile(r"^(ANEXO|REGULAMENTO ANEXO)\b")
# Seção numerada de anexo: "2.1 Título..." ou "3. Título..." (número simples
# exige ponto, para não confundir com "90 (noventa) dias"). O título pode vir
# colado ao conteúdo, porque o HTML não o separa em linha própria.
_SECAO_ANEXO = re.compile(r"^(\d+(?:\.\d+)+|\d+)\.?\s+[A-ZÀ-Ú]")
_SECAO_ANEXO_SIMPLES = re.compile(r"^\d+\.\s")
# Seção que é só título (ex: "2.4 Outros canais disponíveis", seguida direto
# da subseção 2.4.1): vira contexto das subseções, não trecho próprio.
_TAMANHO_MAXIMO_SO_TITULO = 120
# A página de algumas normas traz, depois do texto normativo, a nota técnica
# ou o voto que fundamentou o ato ("NOTA 599/2026-BCB/DENOR, DE ...") — é
# justificativa, não norma, e não é indexada.
_FIM_TEXTO_NORMATIVO = re.compile(r"^(NOTA|VOTO)\s+\d+/\d{4}-BCB", re.IGNORECASE)

_ANOTACAO = re.compile(
    r"\s*\((?:Redação dada|Incluíd[oa]s?|Revogad[oa]s?|Acrescid[oa]s?|Renumerad[oa]s?"
    r"|Alterad[oa]s?|Vide\b|Vigência|Produzindo efeitos)[^()]*(?:\([^()]*\)[^()]*)*\)",
    re.IGNORECASE,
)
# Dispositivo que ficou vazio depois de retirada a anotação de revogação
# (ex: "V - (Revogado pela ...)" -> "V -").
_DISPOSITIVO_VAZIO = re.compile(r"^([IVXLC]+\s*[-–—]|§\s*\d+\s*[º°]?|[a-z]\)|\d+[.)])\s*[.;]?$")


@dataclass
class Unidade:
    tipo: str  # "artigo" | "secao_anexo"
    identificador: str
    contexto: list[str]
    paragrafos: list[str] = field(default_factory=list)
    anotacoes: list[str] = field(default_factory=list)
    revogado: bool = False


def _nivel_estrutura(linha: str) -> str:
    palavra = linha.split()[0].lower()
    if palavra.startswith("t"):
        return "titulo"
    if palavra.startswith("cap"):
        return "capitulo"
    if palavra.startswith("sub"):
        return "subsecao"
    return "secao"


def _identificador_artigo(m: re.Match) -> str:
    numero = int(m.group(1))
    sufixo = (m.group(2) or "").replace(" ", "")
    return f"Art. {numero}{'º' if numero < 10 else ''}{sufixo}"


def _finalizar(unidade: Unidade) -> Unidade:
    paragrafos = []
    for p in unidade.paragrafos:
        unidade.anotacoes.extend(a.strip(" ()") for a in _ANOTACAO.findall(p))
        p = _ANOTACAO.sub("", p).strip()
        if p and not _DISPOSITIVO_VAZIO.match(p):
            paragrafos.append(p)
    unidade.paragrafos = paragrafos
    if unidade.tipo == "artigo":
        corpo = _ARTIGO_INICIO.sub("", paragrafos[0]).strip(" .-") if paragrafos else ""
        unidade.revogado = not corpo and len(paragrafos) <= 1
    else:
        unidade.revogado = not paragrafos
    return unidade


def _estruturar(paragrafos: list[str]) -> list[Unidade]:
    unidades: list[Unidade] = []
    estrutura: dict[str, str] = {}
    atual: Unidade | None = None
    em_anexo = False
    secao_topo: int | None = None  # número de 1º nível da última seção do anexo

    def contexto() -> list[str]:
        return [estrutura[n] for n in ["anexo", *_NIVEIS] if n in estrutura]

    def secao_plausivel(numero: str) -> bool:
        # Seções do manual seguem em ordem (mesmo nível de topo ou o
        # seguinte); "3. NIF, 4. RNE" dentro de uma tabela da seção 4, ou
        # "90. Formato numérico", quebram a sequência e não são seção.
        topo = int(numero.split(".")[0])
        return secao_topo is None or topo in (secao_topo, secao_topo + 1)

    for p in paragrafos:
        if _FIM_TEXTO_NORMATIVO.match(p):
            break
        if _ANEXO_INICIO.match(p):
            em_anexo = True
            # Rótulo curto: o título completo do anexo ("ANEXO À INSTRUÇÃO
            # NORMATIVA ... Manual de Escopo ... do Open Finance") repetido em
            # todo trecho inflaria a frequência desses termos no BM25.
            estrutura = {"anexo": "Regulamento anexo" if p.startswith("REGULAMENTO") else "Anexo"}
            atual = None
        elif _ESTRUTURA.match(p) and len(p) < 200:
            nivel = _nivel_estrutura(p)
            estrutura[nivel] = p
            for inferior in _NIVEIS[_NIVEIS.index(nivel) + 1:]:
                estrutura.pop(inferior, None)
            atual = None
        elif m := _ARTIGO_INICIO.match(p):
            atual = Unidade("artigo", _identificador_artigo(m), contexto(), [p])
            unidades.append(atual)
        elif em_anexo and (m := _SECAO_ANEXO.match(p)) and (
            "." in m.group(1) or _SECAO_ANEXO_SIMPLES.match(p)
        ) and secao_plausivel(m.group(1)):
            secao_topo = int(m.group(1).split(".")[0])
            atual = Unidade("secao_anexo", f"seção {m.group(1)}", contexto(), [p])
            unidades.append(atual)
        elif em_anexo and atual is None:
            # Texto do anexo antes da primeira seção numerada (ex: termos de uso).
            atual = Unidade("secao_anexo", "introdução", contexto(), [p])
            unidades.append(atual)
        elif atual is not None:
            atual.paragrafos.append(p)
        # else: preâmbulo antes do primeiro artigo — não indexado.

    return _titulos_como_contexto([_finalizar(u) for u in unidades])


def _titulos_como_contexto(unidades: list[Unidade]) -> list[Unidade]:
    resultado: list[Unidade] = []
    titulos: list[tuple[str, str]] = []  # (número da seção, título)
    for u in unidades:
        if u.tipo != "secao_anexo" or u.identificador == "introdução":
            resultado.append(u)
            continue
        numero = u.identificador.removeprefix("seção ")
        titulos = [(n, t) for n, t in titulos if numero.startswith(n + ".")]
        texto = " ".join(u.paragrafos)
        if len(texto) <= _TAMANHO_MAXIMO_SO_TITULO:
            titulos.append((numero, texto))
            continue
        u.contexto = u.contexto + [t for _, t in titulos]
        resultado.append(u)
    return resultado


def _titulo(registro: dict) -> tuple[str, str]:
    """("Resolução Conjunta nº 1, de 4 de maio de 2020", "Resolução Conjunta nº 1/2020")."""
    base = re.sub(r"\bN\s*[º°]\.?\s*", "nº ", registro.get("Titulo", "")).strip()
    data = (registro.get("Data") or "")[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}", data):
        return base, base
    ano, mes, dia = (int(x) for x in data.split("-"))
    return f"{base}, de {dia} de {_MESES[mes - 1]} de {ano}", f"{base}/{ano}"


def etapa_silver() -> list[Path]:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    for antigo in SILVER_DIR.iterdir():
        antigo.unlink()

    gerados = []
    for bronze_json in sorted(BRONZE_DIR.glob("*.json")):
        bruto = json.loads(bronze_json.read_text(encoding="utf-8"))
        registro = bruto["resposta_api"]["conteudo"][0]
        titulo, titulo_curto = _titulo(registro)
        data_coleta = bruto["obtido_em"][:10]

        pdf = bruto.get("pdf_consolidado")
        if pdf:
            texto = _texto_do_pdf(BRONZE_DIR / f"{bruto['arquivo']}.pdf")
            fonte_texto = f"PDF consolidado {pdf['arquivo']}"
            versao = f"consolidada v{pdf['versao']}, obtida em {data_coleta}"
        else:
            texto = _texto_do_html(registro["Texto"])
            fonte_texto = "HTML da página (texto tachado removido)"
            v = registro.get("VersaoNormativo")
            versao = f"versão {int(v)} da página, obtida em {data_coleta}" if isinstance(v, (int, float)) else f"obtida em {data_coleta}"

        unidades = _estruturar(_reconstruir_paragrafos(_limpar_artefatos(texto)))
        silver = {
            "arquivo": bruto["arquivo"],
            "titulo": titulo,
            "titulo_curto": titulo_curto,
            "orgao": "Banco Central do Brasil (BCB)",
            "ementa": registro.get("Assunto", ""),
            "url_oficial": bruto["url_oficial"],
            "data_publicacao": (registro.get("Data") or "")[:10],
            "versao": versao,
            "fonte_texto": fonte_texto,
            "corpus_runtime": bruto["corpus_runtime"],
            "unidades": [asdict(u) for u in unidades],
        }
        destino = SILVER_DIR / f"{bruto['arquivo']}.json"
        destino.write_text(json.dumps(silver, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(destino)
    return gerados


# --------------------------------------------------------------------------
# Gold
# --------------------------------------------------------------------------

def _dividir(paragrafos: list[str], limite: int) -> list[list[str]]:
    """Agrupa parágrafos em partes de até `limite` caracteres, sem quebrar
    parágrafo; um parágrafo sozinho maior que o limite (ex: tabela longa) é
    cortado em espaço."""
    partes: list[list[str]] = [[]]
    tamanho = 0
    for p in paragrafos:
        pedacos = [p]
        if len(p) > limite:
            pedacos, resto = [], p
            while len(resto) > limite:
                corte = resto.rfind(" ", 0, limite)
                corte = corte if corte > 0 else limite
                pedacos.append(resto[:corte])
                resto = resto[corte:].strip()
            pedacos.append(resto)
        for pedaco in pedacos:
            if partes[-1] and tamanho + len(pedaco) > limite:
                partes.append([])
                tamanho = 0
            partes[-1].append(pedaco)
            tamanho += len(pedaco) + 1
    return [p for p in partes if p]


def etapa_gold(arquivos_silver: list[Path]) -> list[Path]:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    for antigo in GOLD_DIR.iterdir():
        antigo.unlink()

    gerados = []
    for silver_path in arquivos_silver:
        silver = json.loads(silver_path.read_text(encoding="utf-8"))
        trechos = []
        for u in silver["unidades"]:
            if u["revogado"]:
                continue
            cabecalho_base = " — ".join([silver["titulo_curto"], *u["contexto"], u["identificador"]])
            partes = _dividir(u["paragrafos"], TAMANHO_MAXIMO_TRECHO)
            for i, parte in enumerate(partes, start=1):
                sufixo = f" (parte {i}/{len(partes)})" if len(partes) > 1 else ""
                texto = f"[{cabecalho_base}{sufixo}]\n" + "\n".join(parte)
                tokens = tokenizar(texto)
                trechos.append({
                    "id": f"{silver['arquivo']}#{len(trechos) + 1}",
                    "identificador": u["identificador"],
                    "contexto": u["contexto"],
                    "anotacoes": u["anotacoes"],
                    "texto": texto,
                    "n_tokens": len(tokens),
                    "frequencia_tokens": dict(Counter(tokens)),
                })

        gold = {k: v for k, v in silver.items() if k != "unidades"}
        gold["trechos"] = trechos
        destino = GOLD_DIR / f"{silver['arquivo']}.json"
        destino.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(destino)
    return gerados


def gerar_indice_bm25(arquivos_gold: list[Path]) -> dict:
    """Estatísticas de corpus do BM25, só dos normativos de runtime."""
    arquivos, n_trechos, soma_tokens = [], 0, 0
    frequencia_documento: Counter = Counter()
    for gold_path in arquivos_gold:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        if not gold["corpus_runtime"]:
            continue
        arquivos.append(gold_path.name)
        for trecho in gold["trechos"]:
            n_trechos += 1
            soma_tokens += trecho["n_tokens"]
            frequencia_documento.update(trecho["frequencia_tokens"].keys())

    indice = {
        "arquivos": arquivos,
        "k1": BM25_K1,
        "b": BM25_B,
        "n_trechos": n_trechos,
        "tamanho_medio": soma_tokens / n_trechos if n_trechos else 0.0,
        "frequencia_documento": dict(sorted(frequencia_documento.items())),
    }
    INDICE_FILE.write_text(json.dumps(indice, ensure_ascii=False, indent=2), encoding="utf-8")
    return indice


# --------------------------------------------------------------------------

def executar(a_partir_da_bronze: bool = False) -> None:
    if a_partir_da_bronze:
        if not any(BRONZE_DIR.glob("*.json")):
            print(f"Bronze vazia em {BRONZE_DIR} — rode sem --a-partir-da-bronze.", file=sys.stderr)
            sys.exit(1)
        print(f"Usando a Bronze existente em {BRONZE_DIR} (sem acesso à internet).")
    else:
        fontes = json.loads(FONTES_URL_FILE.read_text(encoding="utf-8"))["fontes"]
        print(f"Bronze: baixando {len(fontes)} normativo(s) de {FONTES_URL_FILE.name}...")
        etapa_bronze(fontes)

    arquivos_silver = etapa_silver()
    for p in arquivos_silver:
        silver = json.loads(p.read_text(encoding="utf-8"))
        unidades = silver["unidades"]
        revogadas = sum(u["revogado"] for u in unidades)
        print(f"  Silver: {silver['titulo_curto']} — {len(unidades)} unidades "
              f"({revogadas} revogadas), fonte: {silver['fonte_texto']}")

    arquivos_gold = etapa_gold(arquivos_silver)
    indice = gerar_indice_bm25(arquivos_gold)
    print(f"  Gold: {len(arquivos_gold)} normativo(s) em {GOLD_DIR}")
    print(f"  Índice BM25 (runtime): {indice['n_trechos']} trechos de "
          f"{len(indice['arquivos'])} normativo(s): {', '.join(indice['arquivos'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão Bronze/Silver/Gold dos normativos do BCB.")
    parser.add_argument("--a-partir-da-bronze", action="store_true",
                        help="não acessa a internet; regera Silver e Gold a partir da Bronze existente")
    executar(parser.parse_args().a_partir_da_bronze)
