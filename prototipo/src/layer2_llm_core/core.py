"""
Camada 2 — Núcleo de Raciocínio do LLM (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: interpretar a intenção do
usuário, sintetizar artefatos intermediários de raciocínio e produzir saídas
estruturadas (respostas, planos, chamadas de ferramenta).

Estágio atual: implementação mínima — apenas geração de texto simples, sem
tool calling e sem integração com as demais camadas. Serve para validar a
base (Estágio 1 do plano de construção) antes de acrescentar complexidade.

Decisão de projeto registrada em docs/decisoes_arquitetura.md.
"""
import ollama
from src.config import settings


class LLMCore:
    def __init__(self, model: str | None = None):
        self.model = model or settings.ollama_model

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Envia uma única mensagem ao modelo e retorna a resposta em texto.

        Esta é a operação mínima da camada — ainda sem decomposição de
        tarefas, sem chamadas de ferramenta e sem uso de contexto/memória
        (essas responsabilidades pertencem às Camadas 3, 4 e 6,
        respectivamente, e serão integradas nos próximos estágios).
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(model=self.model, messages=messages)
        return response["message"]["content"]
