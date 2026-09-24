"""
Camada 5 — normalização e tokenização compartilhadas entre a ingestão
(`ingest_normativos.py`, que pré-calcula os tokens de cada trecho na camada
Gold) e a busca em runtime (`knowledge_base.py`, que tokeniza a pergunta).

As duas pontas precisam usar exatamente a mesma função — um token gerado de
um jeito na indexação e de outro na consulta simplesmente não casa. Por isso
a tokenização vive aqui, e não duplicada em cada módulo.
"""
import re
import unicodedata

_STOPWORDS_BRUTAS = {
    "a", "as", "o", "os", "de", "da", "do", "das", "dos", "e", "ou", "em",
    "no", "na", "nos", "nas", "um", "uma", "uns", "umas", "para", "por",
    "com", "que", "se", "é", "são", "ao", "aos", "à", "às", "sobre", "como",
    "quais", "qual", "quando", "onde", "pelo", "pela", "pelos", "pelas",
    "seu", "sua", "seus", "suas", "este", "esta", "esse", "essa", "isso",
    "ser", "sem", "mais", "nao", "deve", "devem",
    # Verbos que só emolduram a pergunta ("Como funciona X?", "O que
    # significa X?"). Sem isso, "funciona" vira o radical "funcion" e casa
    # com "autorizadas a funcionar", termo raro no corpus e portanto de peso
    # alto no BM25 (achado do teste de recuperação, ver
    # docs/evidencias_empiricas.md, 2026-09-24).
    "funciona", "funcionam", "existe", "existem", "significa", "significam",
    "posso", "podemos", "devo", "devemos", "preciso", "precisa", "precisam",
}


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


# Comparadas depois de `normalizar` (sem acento), então a lista é
# normalizada uma vez aqui.
STOPWORDS = {normalizar(p) for p in _STOPWORDS_BRUTAS}


# Sufixos removidos por `radical`, do mais longo para o mais curto (o
# primeiro que casar vence). Inspirado nas etapas de plural, nominal e verbal
# do RSLP (Orengo & Huyck, 2001), reduzido às terminações frequentes no
# corpus normativo, para a regra caber numa tabela explicável.
_SUFIXOS = (
    "amentos", "imentos", "amento", "imento", "acoes", "icoes", "ucoes",
    "acao", "icao", "ucao", "antes", "entes", "idades", "idade", "ante",
    "ente", "ativos", "ativas", "ativo", "ativa", "ivos", "ivas", "ivo", "iva",
    "ados", "adas", "idos", "idas", "ado", "ada", "ido", "ida",
    "ar", "er", "ir", "oes", "aes", "ais", "eis", "es", "os", "as", "o", "a", "s",
)
_TAMANHO_MINIMO_RADICAL = 4


def radical(palavra: str) -> str:
    """Reduz a palavra (já normalizada) a um radical, para que variações da
    mesma raiz casem na busca: "participar", "participação" e
    "participantes" -> "particip"; "instituição"/"instituições" ->
    "institu". Não remove sufixo se o radical ficaria com menos de
    `_TAMANHO_MINIMO_RADICAL` letras (ver docs/decisoes_arquitetura.md,
    Camada 5, Gold/BM25)."""
    for sufixo in _SUFIXOS:
        if palavra.endswith(sufixo) and len(palavra) - len(sufixo) >= _TAMANHO_MINIMO_RADICAL:
            return palavra[: -len(sufixo)]
    return palavra


def tokenizar(texto: str) -> list[str]:
    """Lista de tokens (com repetição, para contar frequência no BM25)."""
    # "4.015" -> "4015": número de norma com separador de milhar vira um
    # token só, igual ao que o usuário digita sem o ponto.
    texto = re.sub(r"(\d)\.(\d{3})\b", r"\1\2", texto)
    palavras = re.findall(r"\w+", normalizar(texto))
    return [
        radical(p)
        for p in palavras
        if p not in STOPWORDS and len(p) > 2
    ]
