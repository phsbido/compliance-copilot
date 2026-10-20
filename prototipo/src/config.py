"""
Configurações centrais do protótipo.

Camada: transversal — usada pela Camada 2 (Núcleo de Raciocínio) e por
qualquer outra camada que precise saber qual provedor de LLM está ativo.

Decisão de projeto (ver docs/decisoes_arquitetura.md): as configurações são
lidas de variáveis de ambiente (.env), não hardcoded, para permitir trocar de
modelo/provedor sem alterar código-fonte.

Parâmetros de amostragem (v4, 2026-09-24): explícitos, em vez dos padrões
implícitos do Ollama (temperatura 0,8 e seed aleatória), que eram o que o
protótipo usava até a v3.1 sem que isso tivesse sido decidido. Classificação
com temperatura 0 (decisão de governança — a mesma pergunta não pode ser
recusada numa vez e respondida em outra); síntese com temperatura 0,1 (quase
determinística, com margem mínima contra laços de repetição do modo
guloso); seed fixa para reprodutibilidade e auditoria. Ver
docs/decisoes_arquitetura.md, Camada 2.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _limiar_do_ambiente() -> float | None:
    """LIMIAR_BM25 (v6): pontuação mínima do melhor trecho da Camada 5;
    vazio ou ausente = desligado (comportamento da v5)."""
    valor = os.getenv("LIMIAR_BM25", "").strip()
    return float(valor) if valor else None


def _limiar_cosseno_do_ambiente() -> float | None:
    """LIMIAR_COSSENO (v7): cosseno mínimo do melhor trecho nos modos
    `embeddings` e `hybrid` da Camada 5; vazio ou ausente = desligado."""
    valor = os.getenv("LIMIAR_COSSENO", "").strip()
    return float(valor) if valor else None


def _seed_do_ambiente() -> int | None:
    valor = os.getenv("OLLAMA_SEED", "42").strip()
    return int(valor) if valor else None  # vazio = seed aleatória


@dataclass(frozen=True)
class ParametrosAmostragem:
    temperatura_classificacao: float
    temperatura_sintese: float
    seed: int | None
    # Teto de tokens gerados por chamada (num_predict do Ollama). None = sem
    # teto, o padrão do Ollama e a configuração da v5. Usado só na ablação C2
    # da v6, em que uma síntese sem política não terminava (ver
    # docs/decisoes_arquitetura.md, "Tarefa C").
    max_tokens_saida: int | None = None

    def opcoes(self, temperatura: float) -> dict:
        """Opções repassadas ao Ollama para uma chamada."""
        opcoes = {"temperature": temperatura}
        if self.seed is not None:
            opcoes["seed"] = self.seed
        if self.max_tokens_saida is not None:
            opcoes["num_predict"] = self.max_tokens_saida
        return opcoes

    def como_dict(self) -> dict:
        d = {
            "temperatura_classificacao": self.temperatura_classificacao,
            "temperatura_sintese": self.temperatura_sintese,
            "seed": self.seed,
        }
        if self.max_tokens_saida is not None:
            d["max_tokens_saida"] = self.max_tokens_saida
        return d


@dataclass
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    amostragem: ParametrosAmostragem = ParametrosAmostragem(
        temperatura_classificacao=float(os.getenv("OLLAMA_TEMPERATURA_CLASSIFICACAO", "0")),
        temperatura_sintese=float(os.getenv("OLLAMA_TEMPERATURA_SINTESE", "0.1")),
        seed=_seed_do_ambiente(),
    )
    limiar_bm25: float | None = _limiar_do_ambiente()
    # Recuperação da Camada 5 (v7, ver docs/decisoes_arquitetura.md, "Camada
    # 5: embeddings e busca híbrida"): "bm25" (padrão), "embeddings" ou
    # "hybrid". O modelo de embeddings roda no mesmo Ollama, na CPU por
    # padrão (OLLAMA_EMBEDDINGS_GPU=1 para tentar a GPU): na GPU de 8 GB ele
    # não cabe junto com o llama3.1.
    recuperacao_modo: str = os.getenv("RECUPERACAO_MODO", "bm25").strip() or "bm25"
    modelo_embeddings: str = os.getenv("OLLAMA_MODELO_EMBEDDINGS", "bge-m3").strip() or "bge-m3"
    embeddings_na_gpu: bool = os.getenv("OLLAMA_EMBEDDINGS_GPU", "").strip() == "1"
    limiar_cosseno: float | None = _limiar_cosseno_do_ambiente()


settings = Settings()
