"""
Script de validação — Camada 2 (Núcleo de Raciocínio).

Faz uma chamada direta ao modelo, sem nenhuma das demais camadas: sem base
de normas (Camada 5), sem governança (Camada 7) e com a amostragem padrão do
Ollama (temperatura 0,8, seed aleatória), não a configuração de produção do
`.env`. Serve para dois fins:

1. confirmar que Python + Ollama + modelo local estão funcionando (foi o
   Estágio 1 do plano de construção);
2. servir de linha de base: a resposta tende a ser genérica, sem fonte e
   muda a cada execução. Compare com a mesma pergunta feita em `main.py`.

Uso:
    python run_check.py
"""
from src.layer2_llm_core.core import LLMCore


if __name__ == "__main__":
    print("Testando conexão com o Ollama (modelo puro, sem as demais camadas)...")

    core = LLMCore()
    resposta = core.generate(
        prompt="Explique em uma frase o que é Open Finance no contexto do sistema financeiro brasileiro.",
        system="Você é um assistente que responde de forma objetiva e concisa, em português.",
    )

    print("\nResposta do modelo puro:")
    print(resposta)
    print(
        f"\nConexão com o modelo validada ({core.model}).\n"
        "Observe: sem a base de normas e a governança, a resposta não cita fonte,\n"
        "não traz aviso e pode mudar a cada execução. Compare com main.py."
    )
