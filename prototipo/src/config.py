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


def _seed_do_ambiente() -> int | None:
    valor = os.getenv("OLLAMA_SEED", "42").strip()
    return int(valor) if valor else None  # vazio = seed aleatória


@dataclass(frozen=True)
class ParametrosAmostragem:
    temperatura_classificacao: float
    temperatura_sintese: float
    seed: int | None

    def opcoes(self, temperatura: float) -> dict:
        """Opções repassadas ao Ollama para uma chamada."""
        opcoes = {"temperature": temperatura}
        if self.seed is not None:
            opcoes["seed"] = self.seed
        return opcoes

    def como_dict(self) -> dict:
        return {
            "temperatura_classificacao": self.temperatura_classificacao,
            "temperatura_sintese": self.temperatura_sintese,
            "seed": self.seed,
        }


@dataclass
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    amostragem: ParametrosAmostragem = ParametrosAmostragem(
        temperatura_classificacao=float(os.getenv("OLLAMA_TEMPERATURA_CLASSIFICACAO", "0")),
        temperatura_sintese=float(os.getenv("OLLAMA_TEMPERATURA_SINTESE", "0.1")),
        seed=_seed_do_ambiente(),
    )


settings = Settings()
