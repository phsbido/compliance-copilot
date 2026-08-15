"""
Script de validação — Camada 4 (Ferramentas e Serviços).

Testa a ferramenta `buscar_normativo` isoladamente (sem passar pela
Orquestração), confirmando que ela embrulha corretamente a Camada 5 e
retorna texto citável.

Uso:
    python run_check_tools.py
"""
from src.layer4_tools.tools import buscar_normativo


if __name__ == "__main__":
    print("Testando a ferramenta buscar_normativo (Camada 4)...")

    resultado = buscar_normativo(
        "Quais instituições devem participar do Open Finance de forma obrigatória?"
    )

    print("\nResultado:")
    print(resultado)
    print("\nFerramenta validada.")
