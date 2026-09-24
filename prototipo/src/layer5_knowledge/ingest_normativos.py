"""
Pipeline de ingestão em camadas (Bronze/Silver/Gold) — Camada 5, artefato
ILUSTRATIVO/PARALELO, não ligado ao runtime do protótipo.

**Status (ver docs/decisoes_arquitetura.md, seção "Benchmark Empírico" e
docs/estado_atual.md)**: `KnowledgeBase` (`knowledge_base.py`) continua
sendo a implementação real da Camada 5, validada nos 4 casos de teste
(`tests/casos_teste.md`) e nas 20 execuções do benchmark
(`docs/tabela_resultados_empiricos.csv`) — ela lê `*.md` diretamente de
`data/normativos/` (glob não-recursivo) e **não** consome nada gerado por
este script. Este pipeline foi construído a pedido do usuário como um
artefato paralelo, ilustrando como uma arquitetura de dados em camadas
(medalhão) poderia organizar a ingestão do corpus, sem substituir a
implementação já validada nem reorganizar os arquivos-fonte curados. Decisão
deliberada: menor risco para os resultados empíricos já obtidos, em troca de
não estar de fato "ligado" à Camada 5 em runtime.

**Duas fontes de entrada**:

- `data/normativos/*.md`: o corpus já curado manualmente (metadados
  conferidos, URL oficial confirmada — ver `docs/decisoes_arquitetura.md`,
  Camada 5). Copiado verbatim para o Bronze.
- `data/normativos/fontes_url.json`: lista de URLs oficiais de normativos no
  site do BCB (`.../exibenormativo?tipo=...&numero=...`). A página é
  renderizada via JavaScript; o texto integral e os metadados oficiais
  (título, ementa/assunto, data, versão vigente) vêm do endpoint JSON que a
  própria página consome (`_API_NORMATIVO`), derivado dos parâmetros `tipo`
  e `numero` da URL. Substitui a versão anterior deste pipeline, que lia
  PDFs baixados manualmente e ignorados pelo git — com URLs, qualquer pessoa
  que clone o repositório refaz a ingestão (ver docs/decisoes_arquitetura.md,
  "Reprodutibilidade"). Os metadados vêm da fonte oficial, não de heurística,
  por isso esses registros saem com `fonte_confirmada: true`. Ressalva: a API
  devolve sempre a **versão vigente** do normativo; o JSON bruto salvo no
  Bronze (`versao_bcb`, `obtido_em`) é o registro de qual versão foi usada.

**Três camadas geradas em `data/normativos/`** (a árvore anterior —
`data/normativos/*.md`, `PENDENTES.md`, `README.md` — não é alterada por
este módulo):

- `1_bronze_raw/`: para os `.md` já curados, cópia verbatim (frontmatter +
  texto integral). Para as URLs, **dois arquivos por normativo**: a resposta
  JSON da API do BCB sem alteração (o artefato "bronze" de fato bruto) e um
  `.md` irmão com o texto convertido de HTML e o frontmatter com os
  metadados oficiais — necessário para que as etapas Silver/Gold, que só
  sabem ler `.md`, processem os dois tipos de entrada de forma uniforme.
- `2_silver_cleaned/`: o conteúdo textual (de ambas as origens), limpo
  (espaços/quebras de linha normalizados) e estruturado por Artigo e
  Parágrafo/Inciso único, em JSON.
- `3_gold_indexed/`: um JSON por normativo, com metadados regulatórios
  (título, órgão, ementa, URL oficial, data, versão, `fonte_confirmada`) e
  os trechos já estruturados da camada Silver — formato que uma futura
  reimplementação de `KnowledgeBase` poderia consumir, caso a migração para
  esta arquitetura seja decidida (não decidida nesta sessão).

Requer acesso à internet (www.bcb.gov.br). Só usa a biblioteca padrão.

Uso:
    python -m src.layer5_knowledge.ingest_normativos
"""
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

FONTE_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos"
FONTES_URL_FILE = FONTE_DIR / "fontes_url.json"
BRONZE_DIR = FONTE_DIR / "1_bronze_raw"
SILVER_DIR = FONTE_DIR / "2_silver_cleaned"
GOLD_DIR = FONTE_DIR / "3_gold_indexed"

# Endpoint JSON consumido pela página pública exibenormativo do BCB.
_API_NORMATIVO = "https://www.bcb.gov.br/api/conteudo/app/normativos/exibenormativo"
_TIMEOUT_S = 60

_ARTIGO_SPLIT_REGEX = re.compile(r"\n(?=Art\.\s*\d)")
_PARAGRAFO_SPLIT_REGEX = re.compile(r"\n(?=§\s*\d|Parágrafo único)")
_ARTIGO_ID_REGEX = re.compile(r"Art\.\s*\d+[º°]?", re.IGNORECASE)
_PARAGRAFO_ID_REGEX = re.compile(r"§\s*\d+[º°]?|Parágrafo único", re.IGNORECASE)


@dataclass
class Paragrafo:
    identificador: str
    texto: str


@dataclass
class Artigo:
    identificador: str
    texto: str
    paragrafos: list[Paragrafo] = field(default_factory=list)


def _parse_frontmatter(conteudo: str) -> tuple[dict, str]:
    if not conteudo.startswith("---"):
        return {}, conteudo
    fim = conteudo.find("\n---", 3)
    if fim == -1:
        return {}, conteudo
    bloco_cabecalho = conteudo[3:fim].strip()
    corpo = conteudo[fim + 4:].lstrip("\n")
    metadados = {}
    for linha in bloco_cabecalho.splitlines():
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        metadados[chave.strip()] = valor.strip().strip('"')
    return metadados, corpo


def _normalizar_espacos(texto: str) -> str:
    # Limpeza mínima e determinística (Camada "Silver"): colapsa espaços e
    # tabs repetidos, remove espaços no fim de linha. Não corrige artefatos
    # de extração que exigiriam correção semântica — mesma limitação já
    # documentada para a divisão em trechos de knowledge_base.py.
    linhas = [re.sub(r"[ \t ]+", " ", linha).strip() for linha in texto.splitlines()]
    texto = "\n".join(linha for linha in linhas if linha)
    # O HTML do BCB às vezes põe "Art." / "§" e o número em elementos
    # distintos, o que vira quebra de linha na conversão — reúne-os para que
    # o identificador do artigo/parágrafo fique em uma linha só.
    return re.sub(r"(Art\.|§)\s*\n\s*(?=\d)", r"\1 ", texto)


def _dividir_paragrafos(texto_artigo: str) -> tuple[str, list[Paragrafo]]:
    partes = _PARAGRAFO_SPLIT_REGEX.split(texto_artigo)
    caput = partes[0].strip()
    paragrafos = []
    for parte in partes[1:]:
        parte = parte.strip()
        if not parte:
            continue
        match = _PARAGRAFO_ID_REGEX.match(parte)
        identificador = match.group(0) if match else "parágrafo"
        paragrafos.append(Paragrafo(identificador=identificador, texto=parte))
    return caput, paragrafos


class _ExtratorTextoHTML(HTMLParser):
    """HTML do campo `Texto` da API -> texto puro, com uma quebra de linha
    por elemento de bloco (necessário para que `_ARTIGO_SPLIT_REGEX`, que
    procura "Art." no início de linha, funcione) e células de tabela
    separadas por " | "."""

    _BLOCOS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._BLOCOS:
            self.partes.append("\n")
        elif tag in ("td", "th"):
            self.partes.append(" | ")

    def handle_endtag(self, tag):
        if tag in self._BLOCOS:
            self.partes.append("\n")

    def handle_data(self, data):
        self.partes.append(data)


def _html_para_texto(html: str) -> str:
    extrator = _ExtratorTextoHTML()
    extrator.feed(html)
    return "".join(extrator.partes)


def _url_api(url_oficial: str) -> str:
    """URL pública (.../exibenormativo?tipo=X&numero=N) -> URL do endpoint
    JSON que a página consome (...?p1=X&p2=N)."""
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url_oficial).query)
    try:
        tipo, numero = params["tipo"][0], params["numero"][0]
    except KeyError as e:
        raise ValueError(f"URL sem parâmetro {e} (esperado ?tipo=...&numero=...): {url_oficial}") from None
    return f"{_API_NORMATIVO}?{urllib.parse.urlencode({'p1': tipo, 'p2': numero}, quote_via=urllib.parse.quote)}"


def _baixar_normativo(url_oficial: str) -> dict:
    requisicao = urllib.request.Request(
        _url_api(url_oficial),
        headers={"User-Agent": "prototipo-compliance-monografia/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(requisicao, timeout=_TIMEOUT_S) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    conteudo = dados.get("conteudo") or []
    if not conteudo or not conteudo[0].get("Texto"):
        raise ValueError(f"API do BCB não retornou texto para {url_oficial}")
    return dados


def _metadados_da_api(registro: dict, url_oficial: str, obtido_em: str) -> dict:
    """Metadados oficiais (campos da própria API do BCB), não heurística."""
    versao = registro.get("VersaoNormativo")
    versao_txt = f"versão {int(versao)}" if isinstance(versao, (int, float)) else "versão não informada"
    return {
        "titulo": registro.get("Titulo", ""),
        "orgao": "Banco Central do Brasil (BCB)",
        "ementa": registro.get("Assunto", ""),
        "url_oficial": url_oficial,
        "data_publicacao": (registro.get("Data") or "")[:10],
        "versao": f"{versao_txt} vigente no site do BCB, obtida via API em {obtido_em[:10]}",
        "fonte_confirmada": "true",
    }


def _dividir_artigos(corpo_limpo: str) -> list[Artigo]:
    artigos = []
    for trecho in _ARTIGO_SPLIT_REGEX.split(corpo_limpo):
        trecho = trecho.strip()
        if not trecho or not _ARTIGO_ID_REGEX.match(trecho):
            continue  # preâmbulo/cabeçalho antes do primeiro "Art." — fora do escopo de indexação por artigo
        match = _ARTIGO_ID_REGEX.match(trecho)
        identificador = match.group(0)
        caput, paragrafos = _dividir_paragrafos(trecho)
        artigos.append(Artigo(identificador=identificador, texto=caput, paragrafos=paragrafos))
    return artigos


def _escrever_frontmatter(metadados: dict, corpo: str) -> str:
    linhas_cabecalho = "\n".join(f'{chave}: "{valor}"' for chave, valor in metadados.items())
    return f"---\n{linhas_cabecalho}\n---\n\n{corpo}"


def _carregar_fontes_url() -> list[dict]:
    if not FONTES_URL_FILE.exists():
        return []
    return json.loads(FONTES_URL_FILE.read_text(encoding="utf-8"))["fontes"]


def etapa_bronze() -> list[Path]:
    """Duas fontes, tratadas de forma diferente (ver docstring do módulo):

    - `data/normativos/*.md` (corpus já curado manualmente): cópia verbatim
      para 1_bronze_raw/, sem reprocessamento.
    - `data/normativos/fontes_url.json` (URLs oficiais do BCB): salva a
      resposta JSON da API sem alteração em 1_bronze_raw/<arquivo>.json e
      gera um `.md` irmão com o texto convertido de HTML e os metadados
      oficiais no frontmatter.

    Não escreve nada em `data/normativos/` fora de 1_bronze_raw/.
    """
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    gerados = []

    for arquivo in sorted(FONTE_DIR.glob("*.md")):
        conteudo = arquivo.read_text(encoding="utf-8")
        metadados, _ = _parse_frontmatter(conteudo)
        if not metadados:
            continue  # sem cabeçalho -> não é um normativo indexável (ex: PENDENTES.md, README.md)
        destino = BRONZE_DIR / arquivo.name
        destino.write_text(conteudo, encoding="utf-8")
        gerados.append(destino)

    for fonte in _carregar_fontes_url():
        nome, url_oficial = fonte["arquivo"], fonte["url_oficial"]
        print(f"    baixando {nome} de {url_oficial} ...", flush=True)
        dados = _baixar_normativo(url_oficial)
        obtido_em = datetime.now(timezone.utc).isoformat()

        destino_json = BRONZE_DIR / f"{nome}.json"
        bruto = {"url_oficial": url_oficial, "obtido_em": obtido_em, "resposta_api": dados}
        destino_json.write_text(json.dumps(bruto, ensure_ascii=False, indent=2), encoding="utf-8")

        registro = dados["conteudo"][0]
        metadados = _metadados_da_api(registro, url_oficial, obtido_em)
        texto = _html_para_texto(registro["Texto"])
        destino_md = BRONZE_DIR / f"{nome}.md"
        destino_md.write_text(_escrever_frontmatter(metadados, texto), encoding="utf-8")
        gerados.append(destino_md)

    return gerados


def etapa_silver(arquivos_bronze: list[Path]) -> list[Path]:
    """Lê cada arquivo em 1_bronze_raw/, limpa espaçamento e estrutura o
    corpo em Artigos/Parágrafos, salvando um JSON por normativo em
    2_silver_cleaned/."""
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    gerados = []
    for arquivo in arquivos_bronze:
        conteudo = arquivo.read_text(encoding="utf-8")
        metadados, corpo = _parse_frontmatter(conteudo)
        corpo_limpo = _normalizar_espacos(corpo)
        artigos = _dividir_artigos(corpo_limpo)

        estrutura = {
            "titulo": metadados.get("titulo", arquivo.stem),
            "artigos": [asdict(a) for a in artigos],
        }

        destino = SILVER_DIR / f"{arquivo.stem}.json"
        destino.write_text(json.dumps(estrutura, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(destino)
    return gerados


def etapa_gold(arquivos_bronze: list[Path], arquivos_silver: list[Path]) -> list[Path]:
    """Combina os metadados regulatórios completos (lidos do Bronze) com a
    estrutura por Artigo/Parágrafo (lida do Silver) em um único JSON
    "pronto para indexação" por normativo, em 3_gold_indexed/."""
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    silver_por_stem = {p.stem: p for p in arquivos_silver}
    gerados = []
    for bronze_path in arquivos_bronze:
        conteudo = bronze_path.read_text(encoding="utf-8")
        metadados, _ = _parse_frontmatter(conteudo)

        silver_path = silver_por_stem.get(bronze_path.stem)
        estrutura_silver = json.loads(silver_path.read_text(encoding="utf-8")) if silver_path else {"artigos": []}

        registro_gold = {
            "titulo": metadados.get("titulo", bronze_path.stem),
            "orgao": metadados.get("orgao", ""),
            "ementa": metadados.get("ementa", ""),
            "url_oficial": metadados.get("url_oficial", ""),
            "data_publicacao": metadados.get("data_publicacao", ""),
            "versao": metadados.get("versao", ""),
            # Ausente no frontmatter (corpus já curado manualmente) -> True:
            # esses normativos já passaram por verificação humana da URL
            # oficial (ver docs/decisoes_arquitetura.md, Camada 5). Normativos
            # vindos de fontes_url.json também saem "true": URL oficial
            # informada manualmente e metadados lidos da API do próprio BCB.
            "fonte_confirmada": metadados.get("fonte_confirmada", "true") == "true",
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "artigos": estrutura_silver["artigos"],
        }

        destino = GOLD_DIR / f"{bronze_path.stem}.json"
        destino.write_text(json.dumps(registro_gold, ensure_ascii=False, indent=2), encoding="utf-8")
        gerados.append(destino)
    return gerados


def executar() -> None:
    if not FONTE_DIR.exists():
        print(f"Diretório de origem não encontrado: {FONTE_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Lendo entrada de {FONTE_DIR} (.md curados + URLs de {FONTES_URL_FILE.name}) — nenhum arquivo-fonte é movido ou alterado...")

    arquivos_bronze = etapa_bronze()
    print(f"  Bronze: {len(arquivos_bronze)} normativo(s) em {BRONZE_DIR}")

    arquivos_silver = etapa_silver(arquivos_bronze)
    total_artigos = sum(
        len(json.loads(p.read_text(encoding="utf-8"))["artigos"]) for p in arquivos_silver
    )
    print(f"  Silver: {len(arquivos_silver)} normativo(s) estruturado(s) ({total_artigos} artigos) em {SILVER_DIR}")

    arquivos_gold = etapa_gold(arquivos_bronze, arquivos_silver)
    print(f"  Gold: {len(arquivos_gold)} normativo(s) indexado(s) com metadados em {GOLD_DIR}")

    print(
        "\nPipeline ilustrativo concluído. Lembrete: knowledge_base.py (Camada 5 em "
        "runtime) NÃO consome estes arquivos — continua lendo data/normativos/*.md "
        "diretamente. Ver docstring deste módulo e docs/decisoes_arquitetura.md."
    )


if __name__ == "__main__":
    executar()
