"""
Camada 1 — Interação com o Usuário (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: interface pela qual o
usuário interage com o sistema. Aspectos multimodais explicitamente fora de
escopo (ver README.md) — aqui, um loop de CLI em texto puro.

Decisão de projeto (ver docs/decisoes_arquitetura.md): um único
`Orchestrator` é instanciado uma vez por sessão (não por pergunta), para que
a Camada 6 (memória) acumule as interações da sessão inteira. Após cada
resposta, um destaque é impresso a partir de `orchestrator.ultimo_registro`
(Camada 8) se a Camada 7 sinalizou algo não verificado. As fontes
consultadas vêm na própria resposta desde a Camada 7 v2 (antes eram
impressas aqui).

Falhas (2026-10-20): se o Ollama estiver fora do ar ou der timeout, a CLI
mostra uma mensagem (como a interface web) e continua o loop com a sessão
intacta; a falha já foi registrada pela Camada 3/8.
"""
from src.config import settings
from src.layer3_orchestration.orchestrator import Orchestrator

COMANDOS_SAIDA = {"sair", "exit", "quit"}


def _formatar_proveniencia(registro) -> str:
    if registro is None:
        return ""
    # As fontes já vêm na própria resposta ("Fontes consultadas", anexadas
    # pela Camada 7 v2); aqui fica só o destaque quando a validação
    # encontrou algo não verificado.
    if registro.validacao.get("possui_aviso"):
        return "[Atenção: a Camada 7 encontrou citação ou valor não verificado — ver avisos acima]"
    return ""


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

        try:
            resposta = orchestrator.responder(pergunta)
        except Exception as erro:  # em geral, Ollama fora do ar ou modelo ausente
            print(
                f"\nNão foi possível gerar a resposta: o Ollama ({settings.ollama_host}) "
                f"está rodando e com o modelo {settings.ollama_model} baixado? "
                f"Detalhe técnico: {erro}\n"
            )
            continue
        print(f"\n{resposta}")
        proveniencia = _formatar_proveniencia(orchestrator.ultimo_registro)
        if proveniencia:
            print(f"\n{proveniencia}")
        print()


if __name__ == "__main__":
    main()
