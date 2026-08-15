"""
Camada 5 — Integração de Conhecimento / RAG (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: manter e disponibilizar
a base de conhecimento externa (aqui, o corpus de atos normativos do BACEN
sobre Open Finance/PJ) para fundamentar as respostas do Núcleo de Raciocínio.

Decisão de projeto (ver docs/decisoes_arquitetura.md): indexação e busca
lexical simples (contagem de sobreposição de palavras), sem embeddings e sem
biblioteca de vector DB — cada normativo é um arquivo Markdown com
cabeçalho de metadados (título, ementa, URL oficial, data) seguido do texto
integral, dividido em trechos por artigo para a busca.
"""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos"

_STOPWORDS = {
    "a", "as", "o", "os", "de", "da", "do", "das", "dos", "e", "ou", "em",
    "no", "na", "nos", "nas", "um", "uma", "uns", "umas", "para", "por",
    "com", "que", "se", "é", "são", "ao", "aos", "à", "às", "sobre", "como",
    "quais", "qual", "quando", "onde",
}


@dataclass
class Documento:
    titulo: str
    ementa: str
    url_oficial: str
    trecho: str


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def _tokenizar(texto: str) -> set[str]:
    palavras = re.findall(r"\w+", _normalizar(texto))
    return {p for p in palavras if p not in _STOPWORDS and len(p) > 2}


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


def _dividir_em_trechos(corpo: str) -> list[str]:
    # Divide por artigo (ex: "Art. 5º"), que é a unidade natural de citação
    # em atos normativos brasileiros. Divisão é aproximada: a extração de
    # texto de PDF pode introduzir quebras/espaçamento irregulares em
    # "Art. N" (ver docs/decisoes_arquitetura.md, Camada 5).
    partes = re.split(r"\n(?=Art\.\s*\d)", corpo)
    return [p.strip() for p in partes if p.strip()]


class KnowledgeBase:
    def __init__(self, diretorio: Path | None = None):
        self.diretorio = diretorio or DATA_DIR
        self.documentos: list[Documento] = []
        self._carregar()

    def _carregar(self) -> None:
        for arquivo in sorted(self.diretorio.glob("*.md")):
            conteudo = arquivo.read_text(encoding="utf-8")
            metadados, corpo = _parse_frontmatter(conteudo)
            if not metadados:
                continue  # sem cabeçalho de metadados -> não é normativo indexável (ex: PENDENTES.md)
            for trecho in _dividir_em_trechos(corpo):
                self.documentos.append(
                    Documento(
                        titulo=metadados.get("titulo", arquivo.stem),
                        ementa=metadados.get("ementa", ""),
                        url_oficial=metadados.get("url_oficial", ""),
                        trecho=trecho,
                    )
                )

    def buscar(self, pergunta: str, top_k: int = 3) -> list[Documento]:
        tokens_pergunta = _tokenizar(pergunta)
        pontuados = []
        for doc in self.documentos:
            tokens_trecho = _tokenizar(doc.trecho)
            pontuacao = len(tokens_pergunta & tokens_trecho)
            if pontuacao > 0:
                pontuados.append((pontuacao, doc))
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return [doc for _, doc in pontuados[:top_k]]
