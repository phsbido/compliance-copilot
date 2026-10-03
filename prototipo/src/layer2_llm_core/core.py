"""
Camada 2 — Núcleo de Raciocínio do LLM (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: interpretar a intenção do
usuário, sintetizar artefatos intermediários de raciocínio e produzir saídas
estruturadas (respostas, planos, chamadas de ferramenta).

Implementação: wrapper fino sobre o cliente Python do Ollama. Faz geração de
texto (sem tool calling — a busca normativa é acionada pela Camada 3, não
pelo modelo). Cada chamada pode receber seus próprios parâmetros de
amostragem, porque a Camada 3 usa temperaturas diferentes para classificar
a pergunta e para sintetizar a resposta (ver `src/config.py`). Também expõe
a identificação exata do modelo (nome e ID/digest), que a Camada 8 registra
em cada interação.

Decisões registradas em docs/decisoes_arquitetura.md, Camada 2.
"""
import ollama
from src.config import settings


class LLMCore:
    def __init__(self, model: str | None = None, options: dict | None = None):
        """`options` são opções padrão repassadas ao Ollama em toda chamada
        (ex: {"temperature": 0, "seed": 42}); as opções passadas a
        `generate` têm precedência sobre elas."""
        self.model = model or settings.ollama_model
        self.options = options
        self._identificacao: dict | None = None
        # Motivo de parada da última chamada ("stop", "length"...): "length"
        # indica que a geração foi cortada pelo teto de tokens (v6).
        self.ultimo_motivo_parada: str | None = None

    def generate(self, prompt: str, system: str | None = None, options: dict | None = None) -> str:
        """Envia uma única mensagem ao modelo e retorna a resposta em texto."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        opcoes = {**(self.options or {}), **(options or {})} or None
        response = ollama.chat(model=self.model, messages=messages, options=opcoes)
        self.ultimo_motivo_parada = response.get("done_reason")
        return response["message"]["content"]

    def identificacao(self) -> dict:
        """{"modelo": nome, "id_modelo": digest de 12 caracteres} — o ID
        muda quando a tag (ex: "latest") passa a apontar para outro modelo,
        então é o que permite saber com que modelo cada resposta foi gerada.
        Consultado uma vez por instância."""
        if self._identificacao is None:
            id_modelo = "desconhecido"
            nomes = {self.model, f"{self.model}:latest"}
            try:
                for m in ollama.list().models:
                    if m.model in nomes:
                        id_modelo = m.digest[:12]
                        break
            except Exception:  # Ollama indisponível: a geração falhará de qualquer forma
                pass
            self._identificacao = {"modelo": self.model, "id_modelo": id_modelo}
        return self._identificacao
