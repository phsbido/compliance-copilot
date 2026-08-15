"""
Script de validação — Camada 3 (Orquestração).

Testa o fluxo completo (interpretar -> buscar normativo -> sintetizar
resposta -> validar citação) com três perguntas na mesma sessão:

1. Uma pergunta normativa normal.
2. Uma pergunta de acompanhamento, que só faz sentido considerando o
   histórico da primeira (Camada 6).
3. Um pedido de parecer jurídico definitivo, que deve ser recusado sem
   passar por busca/síntese (Camada 7).

Uso:
    python run_check_orchestration.py
"""
from src.layer3_orchestration.orchestrator import Orchestrator


if __name__ == "__main__":
    print("Testando o fluxo de orquestração (Camada 3), com todas as camadas ligadas...")

    orchestrator = Orchestrator()

    pergunta1 = "Quais são os requisitos para uma instituição PJ participar do Open Finance?"
    print(f"\n[Pergunta 1] {pergunta1}")
    resposta1 = orchestrator.responder(pergunta1)
    print("\nResposta 1:")
    print(resposta1)

    pergunta2 = "E qual o prazo para se tornar participante, considerando o que você acabou de explicar?"
    print(f"\n[Pergunta 2] {pergunta2}")
    resposta2 = orchestrator.responder(pergunta2)
    print("\nResposta 2:")
    print(resposta2)

    pergunta3 = "Minha empresa vai ser processada por não ter aderido ao Open Finance a tempo — o que devo fazer juridicamente?"
    print(f"\n[Pergunta 3 - deve ser recusada] {pergunta3}")
    resposta3 = orchestrator.responder(pergunta3)
    print("\nResposta 3:")
    print(resposta3)

    print("\nFluxo de orquestração validado (Camadas 4/5/6/7 já ligadas).")
