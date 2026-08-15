"""
Script de validação — Camada 6 (Contexto e Memória).

Testa a classe Memoria isoladamente: adiciona interações e confirma que o
contexto formatado reflete o histórico, respeitando o limite configurado.

Uso:
    python run_check_memory.py
"""
from src.layer6_memory.memory import Memoria


if __name__ == "__main__":
    print("Testando a Memoria (Camada 6)...")

    memoria = Memoria(limite=2)
    print("\nContexto antes de qualquer interação:")
    print(repr(memoria.contexto_formatado()))

    memoria.adicionar("O que é Open Finance?", "É o compartilhamento padronizado de dados e serviços financeiros.")
    memoria.adicionar("Quem participa obrigatoriamente?", "Instituições S1/S2 e com mais de 5 milhões de clientes.")
    memoria.adicionar("E qual o prazo?", "Seis meses após se enquadrar no critério.")

    print("\nContexto após 3 interações (limite=2, deve manter só as 2 últimas):")
    print(memoria.contexto_formatado())

    assert "O que é Open Finance?" not in memoria.contexto_formatado(), "limite não respeitado"
    assert "E qual o prazo?" in memoria.contexto_formatado()

    print("\nMemória validada.")
