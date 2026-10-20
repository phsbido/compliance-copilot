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
sem embeddings e sem biblioteca de vector DB (até a v6; embeddings na v7,
ver abaixo).

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

Embeddings e busca híbrida (v7, 2026-10-20; ver docs/decisoes_arquitetura.md,
"Camada 5: embeddings e busca híbrida"): `modo` escolhe a recuperação —
"bm25" (o padrão, como até a v6), "embeddings" (cosseno entre o vetor da
pergunta e o de cada trecho, de `indice_embeddings.json`) ou "hybrid" (os
dois rankings completos combinados por Reciprocal Rank Fusion, k = 60). A
interface não muda. `limiar` continua sendo a pontuação BM25 do melhor
trecho em qualquer modo; o cosseno mínimo do melhor trecho é outro limiar,
`limiar_cosseno` (só nos modos com embeddings; `None` desliga, o padrão).
A identificação da recuperação (modo, modelo e digest de embeddings,
versão dos índices) é registrada pela Camada 8 via
`identificacao_recuperacao()`.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from src.config import settings
from src.layer5_knowledge.embeddings import (
    INDICE_EMBEDDINGS_NOME,
    MODOS,
    ClienteEmbeddings,
    cosseno,
    decodificar_vetor,
    validar_indice,
    versao_arquivo,
)
from src.layer5_knowledge.texto import tokenizar

GOLD_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos" / "3_gold_indexed"
INDICE_FILE = GOLD_DIR / "indice_bm25.json"
INDICE_EMBEDDINGS_FILE = GOLD_DIR / INDICE_EMBEDDINGS_NOME

# Constante da Reciprocal Rank Fusion (Cormack, Clarke & Büttcher, 2009).
RRF_K = 60

# Identificação da base construída com a configuração padrão do processo —
# a mesma que a Camada 4 usa —, lida pela Camada 8.
_identificacao_padrao: dict | None = None


def identificacao_recuperacao() -> dict:
    """Modo, modelo e digest de embeddings e versão dos índices da base
    configurada neste processo; vazio se nenhuma foi carregada (ex: só
    recusas, sem a Camada 4 importada)."""
    return dict(_identificacao_padrao or {})


@dataclass
class Documento:
    titulo: str
    ementa: str
    url_oficial: str
    trecho: str
    identificador: str = ""
    id_trecho: str = ""
    frequencia_tokens: dict[str, int] = field(default_factory=dict, repr=False)
    n_tokens: int = 0


class KnowledgeBase:
    def __init__(
        self,
        diretorio_gold: Path | None = None,
        modo: str | None = None,
        cliente_embeddings: ClienteEmbeddings | None = None,
        limiar_cosseno: float | None = None,
    ):
        padrao = diretorio_gold is None and modo is None and cliente_embeddings is None and limiar_cosseno is None
        self.diretorio_gold = diretorio_gold or GOLD_DIR
        self.modo = modo or settings.recuperacao_modo
        if self.modo not in MODOS:
            raise ValueError(f"modo de recuperação deve ser um de {MODOS}, não {self.modo!r}")
        self.limiar_cosseno = limiar_cosseno if limiar_cosseno is not None else settings.limiar_cosseno
        self.documentos: list[Documento] = []
        self._vetores: list[list[float]] = []
        self._cliente: ClienteEmbeddings | None = None
        self._indice_embeddings: dict = {}
        self._carregar()
        if self.modo != "bm25":
            self._cliente = cliente_embeddings or ClienteEmbeddings(
                settings.modelo_embeddings, settings.ollama_host, settings.embeddings_na_gpu)
            self._carregar_embeddings()
        if padrao:
            global _identificacao_padrao
            _identificacao_padrao = self.identificacao()

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
                        id_trecho=trecho["id"],
                        frequencia_tokens=trecho["frequencia_tokens"],
                        n_tokens=trecho["n_tokens"],
                    )
                )

    def _carregar_embeddings(self) -> None:
        indice_path = self.diretorio_gold / INDICE_EMBEDDINGS_NOME
        if not indice_path.exists():
            raise FileNotFoundError(
                f"Índice de embeddings não encontrado em {indice_path} (modo {self.modo!r}). Gere-o com "
                "`python -m src.layer5_knowledge.ingest_normativos --somente-embeddings`."
            )
        indice = json.loads(indice_path.read_text(encoding="utf-8"))
        validar_indice(indice, [(d.id_trecho, d.trecho) for d in self.documentos],
                       self._cliente.modelo, self._cliente.digest())
        self._vetores = [decodificar_vetor(t["vetor"]) for t in indice["vetores"]]
        self._indice_embeddings = indice

    def identificacao(self) -> dict:
        """Proveniência da recuperação (Camada 8)."""
        versao_bm25 = versao_arquivo(self.diretorio_gold / INDICE_FILE.name)
        if self.modo == "bm25":
            return {"modo": "bm25", "modelo_embeddings": None, "digest_embeddings": None,
                    "versao_indice": f"bm25:{versao_bm25}"}
        versao_emb = versao_arquivo(self.diretorio_gold / INDICE_EMBEDDINGS_NOME)
        versao = f"emb:{versao_emb}" if self.modo == "embeddings" else f"bm25:{versao_bm25}+emb:{versao_emb}"
        return {
            "modo": self.modo,
            "modelo_embeddings": self._indice_embeddings["modelo"],
            "digest_embeddings": self._indice_embeddings["digest"][:12],
            "versao_indice": versao,
            "limiar_cosseno": self.limiar_cosseno,
        }

    def _pontuar(self, tokens_pergunta: set[str], doc: Documento) -> float:
        normalizacao = self._k1 * (1 - self._b + self._b * doc.n_tokens / self._tamanho_medio)
        pontuacao = 0.0
        for token in tokens_pergunta:
            tf = doc.frequencia_tokens.get(token, 0)
            if tf:
                pontuacao += self._idf.get(token, 0.0) * tf * (self._k1 + 1) / (tf + normalizacao)
        return pontuacao

    def _ranking_bm25(self, pergunta: str) -> list[tuple[float, int]]:
        """(pontuação, posição do trecho), só os trechos com pontuação > 0,
        do maior para o menor (empate: ordem do índice)."""
        tokens_pergunta = set(tokenizar(pergunta))
        pontuados = []
        for i, doc in enumerate(self.documentos):
            pontuacao = self._pontuar(tokens_pergunta, doc)
            if pontuacao > 0:
                pontuados.append((pontuacao, i))
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return pontuados

    def _ranking_embeddings(self, pergunta: str) -> list[tuple[float, int]]:
        """(cosseno, posição do trecho), todos os trechos, do maior para o menor."""
        vetor = self._cliente.gerar([pergunta])[0]
        pontuados = [(cosseno(vetor, v), i) for i, v in enumerate(self._vetores)]
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return pontuados

    def _ranking_hibrido(self, pergunta: str) -> tuple[list[tuple[float, int]], float]:
        """RRF dos dois rankings completos; devolve também o cosseno do melhor
        trecho (para `limiar_cosseno`)."""
        por_embeddings = self._ranking_embeddings(pergunta)
        fusao = [0.0] * len(self.documentos)
        for ranking in (self._ranking_bm25(pergunta), por_embeddings):
            for posicao, (_, i) in enumerate(ranking, start=1):
                fusao[i] += 1 / (RRF_K + posicao)
        pontuados = [(p, i) for i, p in enumerate(fusao) if p > 0]
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return pontuados, por_embeddings[0][0] if por_embeddings else 0.0

    def _ranking(self, pergunta: str) -> tuple[list[tuple[float, int]], float | None]:
        """Ranking do modo configurado e cosseno do melhor trecho (None no bm25)."""
        if self.modo == "bm25":
            return self._ranking_bm25(pergunta), None
        if self.modo == "embeddings":
            ranking = self._ranking_embeddings(pergunta)
            return ranking, ranking[0][0] if ranking else 0.0
        return self._ranking_hibrido(pergunta)

    def buscar_pontuado(self, pergunta: str, top_k: int = 3) -> list[tuple[float, Documento]]:
        """Os k melhores trechos com a pontuação do modo (BM25, cosseno ou
        RRF), sem limiar (usado na calibração do limiar e por `buscar`)."""
        ranking, _ = self._ranking(pergunta)
        return [(p, self.documentos[i]) for p, i in ranking[:top_k]]

    def cosseno_melhor_trecho(self, pergunta: str) -> float:
        """Cosseno do melhor trecho do corpus (calibração de `limiar_cosseno`)."""
        if self.modo == "bm25":
            raise ValueError("cosseno_melhor_trecho exige o modo 'embeddings' ou 'hybrid'")
        ranking = self._ranking_embeddings(pergunta)
        return ranking[0][0] if ranking else 0.0

    def buscar(self, pergunta: str, top_k: int = 3, limiar: float | None = None) -> list[Documento]:
        ranking, melhor_cosseno = self._ranking(pergunta)
        if limiar is not None:
            # Limiar BM25 (v6): no bm25 o próprio ranking já é o BM25.
            melhor_bm25 = ranking[:1] if self.modo == "bm25" else self._ranking_bm25(pergunta)[:1]
            if not melhor_bm25 or melhor_bm25[0][0] < limiar:
                return []
        if self.limiar_cosseno is not None and melhor_cosseno is not None and melhor_cosseno < self.limiar_cosseno:
            return []
        return [self.documentos[i] for _, i in ranking[:top_k]]
