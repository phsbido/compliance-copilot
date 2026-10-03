"""
Camada 5 — Integração de Conhecimento / RAG (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: manter e disponibilizar
a base de conhecimento externa (aqui, o corpus de atos normativos do BACEN
sobre Open Finance/PJ) para fundamentar as respostas do Núcleo de Raciocínio.

Decisão de projeto (ver docs/decisoes_arquitetura.md, Camada 5, "Ingestão
por URL e consumo da Gold", 2026-09-24): a base lê **somente** a camada Gold
gerada por `ingest_normativos.py` (`data/normativos/3_gold_indexed/`) —
trechos já limpos, com cabeçalho de contexto (norma, capítulo/seção,
artigo) e frequência de tokens pré-calculada — e ranqueia com BM25 usando as
estatísticas de corpus de `indice_bm25.json`. Continua sendo busca lexical,
sem embeddings e sem biblioteca de vector DB.

A interface (`buscar()` -> `list[Documento]` com título, ementa, URL oficial
e trecho) é a mesma da versão anterior, que lia os `.md` curados e contava
palavras em comum — as Camadas 4, 7 e 8 não mudam.

Limiar de pontuação (v6, 2026-10-02; ver docs/decisoes_arquitetura.md,
"Tarefa A"): o BM25 sempre devolve os k melhores trechos, por pior que seja
o casamento, então a recusa sem base da Camada 7 quase nunca disparava. Com
`limiar`, se o **melhor** trecho pontuar abaixo dele, a busca não devolve
nada; acima, devolve os k melhores como antes (o limiar não filtra trecho a
trecho, para não mudar o contexto das perguntas respondíveis). `None`
desliga o limiar — o padrão, que mantém a v5 reprodutível.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from src.layer5_knowledge.texto import tokenizar

GOLD_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos" / "3_gold_indexed"
INDICE_FILE = GOLD_DIR / "indice_bm25.json"


@dataclass
class Documento:
    titulo: str
    ementa: str
    url_oficial: str
    trecho: str
    identificador: str = ""
    frequencia_tokens: dict[str, int] = field(default_factory=dict, repr=False)
    n_tokens: int = 0


class KnowledgeBase:
    def __init__(self, diretorio_gold: Path | None = None):
        self.diretorio_gold = diretorio_gold or GOLD_DIR
        self.documentos: list[Documento] = []
        self._carregar()

    def _carregar(self) -> None:
        indice_path = self.diretorio_gold / INDICE_FILE.name
        if not indice_path.exists():
            raise FileNotFoundError(
                f"Índice da camada Gold não encontrado em {indice_path}. Gere-o com "
                "`python -m src.layer5_knowledge.ingest_normativos --a-partir-da-bronze` "
                "(ou sem a flag, para baixar os normativos do BCB)."
            )
        indice = json.loads(indice_path.read_text(encoding="utf-8"))
        self._k1 = indice["k1"]
        self._b = indice["b"]
        self._tamanho_medio = indice["tamanho_medio"] or 1.0
        n = indice["n_trechos"]
        # IDF do BM25 na forma com +1 (sempre positivo), pré-calculado por token.
        self._idf = {
            token: math.log((n - df + 0.5) / (df + 0.5) + 1)
            for token, df in indice["frequencia_documento"].items()
        }

        for arquivo in indice["arquivos"]:
            gold = json.loads((self.diretorio_gold / arquivo).read_text(encoding="utf-8"))
            for trecho in gold["trechos"]:
                self.documentos.append(
                    Documento(
                        titulo=gold["titulo"],
                        ementa=gold["ementa"],
                        url_oficial=gold["url_oficial"],
                        trecho=trecho["texto"],
                        identificador=trecho["identificador"],
                        frequencia_tokens=trecho["frequencia_tokens"],
                        n_tokens=trecho["n_tokens"],
                    )
                )

    def _pontuar(self, tokens_pergunta: set[str], doc: Documento) -> float:
        normalizacao = self._k1 * (1 - self._b + self._b * doc.n_tokens / self._tamanho_medio)
        pontuacao = 0.0
        for token in tokens_pergunta:
            tf = doc.frequencia_tokens.get(token, 0)
            if tf:
                pontuacao += self._idf.get(token, 0.0) * tf * (self._k1 + 1) / (tf + normalizacao)
        return pontuacao

    def buscar_pontuado(self, pergunta: str, top_k: int = 3) -> list[tuple[float, Documento]]:
        """Os k melhores trechos com a pontuação BM25 de cada um, sem limiar
        (usado na calibração do limiar e por `buscar`)."""
        tokens_pergunta = set(tokenizar(pergunta))
        pontuados = []
        for doc in self.documentos:
            pontuacao = self._pontuar(tokens_pergunta, doc)
            if pontuacao > 0:
                pontuados.append((pontuacao, doc))
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return pontuados[:top_k]

    def buscar(self, pergunta: str, top_k: int = 3, limiar: float | None = None) -> list[Documento]:
        pontuados = self.buscar_pontuado(pergunta, top_k)
        if limiar is not None and (not pontuados or pontuados[0][0] < limiar):
            return []
        return [doc for _, doc in pontuados]
