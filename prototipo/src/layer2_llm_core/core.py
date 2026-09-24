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
    def __init__(self, model: str | None = None, options: dict | None = None):
        """`options` é repassado ao Ollama sem alteração (ex:
        {"temperature": 0, "seed": 42}). Padrão None = parâmetros de
        amostragem default do modelo — é o modo usado por main.py e pelo
        benchmark "livre". O modo "deterministico" do run_benchmark.py fixa
        temperatura e seed para avaliar reprodutibilidade (ver
        docs/decisoes_arquitetura.md, "Reprodutibilidade")."""
        self.model = model or settings.ollama_model
        self.options = options

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

        response = ollama.chat(model=self.model, messages=messages, options=self.options)
        return response["message"]["content"]
