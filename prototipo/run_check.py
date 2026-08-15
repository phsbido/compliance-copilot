"""
Script de validação — Estágio 1 do plano de construção.

Faz apenas uma chamada simples ao Núcleo de Raciocínio (Camada 2), sem
nenhuma das demais camadas, para confirmar que a base (Python + Ollama +
modelo local) está funcionando antes de acrescentar orquestração, ferramentas,
RAG, memória, governança e observabilidade.

Uso:
    python run_check.py
"""
from src.layer2_llm_core.core import LLMCore


if __name__ == "__main__":
    print(f"Testando conexão com o Ollama...")

    core = LLMCore()
    resposta = core.generate(
        prompt="Explique em uma frase o que é Open Finance no contexto do sistema financeiro brasileiro.",
        system="Você é um assistente que responde de forma objetiva e concisa, em português.",
    )

    print("\nResposta do modelo:")
    print(resposta)
    print("\nBase validada. Pronto para construir as demais camadas.")
