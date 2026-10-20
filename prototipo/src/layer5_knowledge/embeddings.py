"""
Camada 5 — vetores de embeddings dos trechos da Gold e da pergunta (v7).

Compartilhado entre a ingestão (`ingest_normativos.py`, que gera
`indice_embeddings.json` ao lado de `indice_bm25.json`) e a busca em runtime
(`knowledge_base.py`, que embeda a pergunta) — pelo mesmo motivo de
`texto.py`: as duas pontas precisam usar o mesmo modelo, e um vetor gerado
por um modelo não é comparável com o de outro.

Decisão de projeto (ver docs/decisoes_arquitetura.md, "Camada 5: embeddings
e busca híbrida", 2026-10-20): o modelo (`bge-m3` por padrão) é servido pelo
próprio Ollama local, sem API paga nem biblioteca nova. Na GPU de 8 GB ele
não cabe junto com o llama3.1, então roda na CPU (`num_gpu: 0`), a menos
que `OLLAMA_EMBEDDINGS_GPU=1`.

O índice guarda modelo, digest, dimensão, data e o sha256 do texto de cada
trecho. A `KnowledgeBase` recusa um índice cujo modelo, digest ou textos não
batam com o que está instalado e com a Gold atual (`validar_indice`): o
índice é regerado inteiro, nunca misturado. Os vetores ficam em float32
codificado em base64 (o que o Ollama devolve, sem arredondamento), para o
arquivo não passar de alguns MB.
"""
import base64
import hashlib
import math
from array import array
from datetime import datetime, timezone
from pathlib import Path

import ollama

MODOS = ("bm25", "embeddings", "hybrid")
INDICE_EMBEDDINGS_NOME = "indice_embeddings.json"
# Trechos por chamada ao Ollama na ingestão.
TAMANHO_LOTE = 16


class IndiceEmbeddingsInvalido(RuntimeError):
    """O índice de embeddings não corresponde à Gold atual ou ao modelo instalado."""


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def versao_arquivo(caminho: Path) -> str:
    """Identificador curto da versão de um arquivo de índice (sha256 do conteúdo)."""
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:12]


def _nome_completo(modelo: str) -> str:
    return modelo if ":" in modelo else f"{modelo}:latest"


def _normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(x * x for x in vetor)) or 1.0
    return [x / norma for x in vetor]


def codificar_vetor(vetor: list[float]) -> str:
    return base64.b64encode(array("f", vetor).tobytes()).decode("ascii")


def decodificar_vetor(texto: str) -> list[float]:
    vetor = array("f")
    vetor.frombytes(base64.b64decode(texto))
    return vetor.tolist()


def cosseno(a: list[float], b: list[float]) -> float:
    """Produto interno; os vetores já são normalizados (norma 1)."""
    return math.fsum(x * y for x, y in zip(a, b))


class ClienteEmbeddings:
    """Gera vetores com um modelo de embeddings do Ollama local."""

    def __init__(self, modelo: str, host: str | None = None, na_gpu: bool = False):
        self.modelo = modelo
        self._cliente = ollama.Client(host=host) if host else ollama.Client()
        self._opcoes = {} if na_gpu else {"num_gpu": 0}
        self._digest: str | None = None

    def digest(self) -> str:
        """Digest completo do modelo instalado (muda se a tag passar a
        apontar para outro modelo)."""
        if self._digest is None:
            alvo = _nome_completo(self.modelo)
            for m in self._cliente.list().models:
                if m.model == alvo:
                    self._digest = m.digest
                    break
            else:
                raise IndiceEmbeddingsInvalido(
                    f"Modelo de embeddings {alvo} não está instalado no Ollama "
                    f"(`ollama pull {self.modelo}`).")
        return self._digest

    def gerar(self, textos: list[str]) -> list[list[float]]:
        """Vetores normalizados, na ordem dos textos. `truncate=False`: um
        texto maior que o contexto do modelo dá erro, em vez de ser cortado
        sem aviso."""
        vetores = []
        for inicio in range(0, len(textos), TAMANHO_LOTE):
            resposta = self._cliente.embed(model=self.modelo, input=textos[inicio:inicio + TAMANHO_LOTE],
                                           truncate=False, options=self._opcoes)
            vetores.extend(_normalizar(list(v)) for v in resposta.embeddings)
        return vetores


def gerar_indice(trechos: list[tuple[str, str]], cliente: ClienteEmbeddings) -> dict:
    """`trechos`: (id, texto) na ordem em que a `KnowledgeBase` os carrega."""
    vetores = cliente.gerar([texto for _, texto in trechos])
    return {
        "modelo": cliente.modelo,
        "digest": cliente.digest(),
        "dimensao": len(vetores[0]) if vetores else 0,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "n_trechos": len(trechos),
        "codificacao_vetor": "float32 little-endian, base64, norma 1",
        # "vetores", não "trechos": quem percorre os JSON da Gold procurando
        # trechos (ex: tests/test_benchmark.py) não deve confundir os dois.
        "vetores": [
            {"id": id_trecho, "sha256": hash_texto(texto), "vetor": codificar_vetor(v)}
            for (id_trecho, texto), v in zip(trechos, vetores)
        ],
    }


def validar_indice(indice: dict, trechos: list[tuple[str, str]], modelo: str, digest_instalado: str) -> None:
    """Levanta `IndiceEmbeddingsInvalido` se o índice não foi gerado com o
    modelo instalado ou sobre os textos atuais da Gold."""
    regerar = ("Regere-o com `python -m src.layer5_knowledge.ingest_normativos --somente-embeddings`.")
    if _nome_completo(indice["modelo"]) != _nome_completo(modelo):
        raise IndiceEmbeddingsInvalido(
            f"Índice de embeddings gerado com {indice['modelo']}, mas o configurado é {modelo}. {regerar}")
    if indice["digest"] != digest_instalado:
        raise IndiceEmbeddingsInvalido(
            f"Digest do modelo {modelo} mudou ({indice['digest'][:12]} no índice, "
            f"{digest_instalado[:12]} instalado). {regerar}")
    esperado = [(id_trecho, hash_texto(texto)) for id_trecho, texto in trechos]
    no_indice = [(t["id"], t["sha256"]) for t in indice["vetores"]]
    if esperado != no_indice:
        diferentes = sum(a != b for a, b in zip(esperado, no_indice)) + abs(len(esperado) - len(no_indice))
        raise IndiceEmbeddingsInvalido(
            f"O índice de embeddings não corresponde à Gold atual ({diferentes} trecho(s) diferentes "
            f"ou ausentes). {regerar}")
