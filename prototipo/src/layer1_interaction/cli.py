"""
Camada 1 — Interação com o Usuário (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: interface pela qual o
usuário interage com o sistema. Aspectos multimodais explicitamente fora de
escopo (ver README.md) — aqui, um loop de CLI em texto puro.

Decisão de projeto (ver docs/decisoes_arquitetura.md): um único
`Orchestrator` é instanciado uma vez por sessão (não por pergunta), para que
a Camada 6 (memória) acumule as interações da sessão inteira. Após cada
resposta, um rodapé de proveniência é impresso a partir de
`orchestrator.ultimo_registro` (Camada 8) — títulos das fontes normativas
usadas e um aviso se a Camada 7 sinalizou citação não verificada — em vez do
log JSON bruto, para que o usuário veja de forma legível o que fundamentou
a resposta.
"""
from src.layer3_orchestration.orchestrator import Orchestrator

COMANDOS_SAIDA = {"sair", "exit", "quit"}


def _formatar_proveniencia(registro) -> str:
    if registro is None:
        return ""
    linhas = []
    if registro.fontes_normativas:
        titulos = ", ".join(f["titulo"] for f in registro.fontes_normativas)
        linhas.append(f"[Fontes: {titulos}]")
    if registro.aviso_citacao_nao_verificada:
        linhas.append("[Atenção: citação não verificada no corpus indexado — ver aviso acima]")
    return "\n".join(linhas)


def main() -> None:
    print("Copiloto de Compliance Regulatório (Open Finance / Contas PJ)")
    print(f"Digite sua pergunta, ou {'/'.join(COMANDOS_SAIDA)} para encerrar.\n")

    orchestrator = Orchestrator()

    while True:
        try:
            pergunta = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando.")
            break

        if not pergunta:
            continue
        if pergunta.lower() in COMANDOS_SAIDA:
            print("Encerrando.")
            break

        resposta = orchestrator.responder(pergunta)
        print(f"\n{resposta}")
        proveniencia = _formatar_proveniencia(orchestrator.ultimo_registro)
        if proveniencia:
            print(f"\n{proveniencia}")
        print()


if __name__ == "__main__":
    main()
