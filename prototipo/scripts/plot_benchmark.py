"""
Gera os gráficos de publicação (Capítulo 3) a partir do benchmark empírico
v5 (66 casos em cinco grupos), produzido por run_benchmark.py:

  - docs/resultados/resultados_benchmark.json: um registro por execução do
    modo produção (cada ponto dos gráficos de latência);
  - docs/tabela_resultados_por_grupo.csv e
    docs/tabela_resultados_por_grupo_sensibilidade.csv: taxas por grupo, com
    IC 95% de Wilson sobre os casos.

Até a v4.1 os gráficos eram por cenário (4 cenários); com 66 casos, um
gráfico por caso fica ilegível, e a unidade de análise passou a ser o grupo.

Gera quatro gráficos em docs/figuras/, 300 DPI, rótulos em português:

  - grafico_latencia_cenarios.png: latência de cada execução por grupo
    (pontos), colorida pelo desfecho (resposta sintetizada x recusa), com a
    mediana do grupo; escala logarítmica, porque recusas (~200 ms) e
    respostas (~10 s) diferem em duas ordens de grandeza. A anotação traz a
    razão entre as medianas, calculada dos dados.
  - grafico_taxas_governanca.png: por grupo, taxa de sucesso (comportamento
    esperado observado), taxa de recusa e taxa de aviso da Camada 7 (norma,
    artigo ou valor não verificado), sobre as execuções do modo produção.
  - grafico_sucesso_grupos.png: proporção de casos com sucesso automático em
    todas as repetições, com IC 95% de Wilson, nos modos produção e
    sensibilidade;
  - grafico_auditoria_recuperacao.png: veredito da auditoria manual
    (docs/auditoria_respostas_v5.csv) das execuções com resposta esperada no
    corpus, separado pelo acerto da recuperação (docs/tabela_recuperacao.csv).
    O sucesso automático mede segurança (sem citação não verificada); este
    gráfico mostra a correção.

Os números exibidos vêm todos dos dados; nada é fixo no código.

Uso:
    python scripts/plot_benchmark.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

RAIZ = Path(__file__).resolve().parent.parent
JSON_ENTRADA = RAIZ / "docs" / "resultados" / "resultados_benchmark.json"
CSV_GRUPOS = {
    "producao": RAIZ / "docs" / "tabela_resultados_por_grupo.csv",
    "sensibilidade": RAIZ / "docs" / "tabela_resultados_por_grupo_sensibilidade.csv",
}
CSV_AUDITORIA = RAIZ / "docs" / "auditoria_respostas_v5.csv"
CSV_RECUPERACAO = RAIZ / "docs" / "tabela_recuperacao.csv"
DIR_FIGURAS = RAIZ / "docs" / "figuras"

ROTULOS_GRUPO = {
    "normativo_corpus": "Normativo\nno corpus",
    "norma_ausente": "Norma\nausente",
    "parecer_juridico": "Parecer\njurídico",
    "fora_de_escopo": "Fora de\nescopo",
    "robustez": "Robustez",
}

# Paleta categórica (slots 1-3 da paleta de referência, validados em todos
# os pares no modo claro); texto sempre em tinta neutra.
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE_AGUA = "#1baf7a"
CINZA = "#9a9893"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e4e3df"
SUPERFICIE = "#ffffff"


def _ms(valor: float) -> str:
    """Formata milissegundos com separador de milhar brasileiro."""
    return f"{valor:,.0f}".replace(",", ".") + " ms"


def _pct(valor: float) -> str:
    return f"{valor * 100:.0f}%"


def _configurar_estilo() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.labelsize": 11,
            "axes.edgecolor": TINTA_SECUNDARIA,
            "axes.labelcolor": TINTA,
            "axes.facecolor": SUPERFICIE,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "grid.color": GRADE,
            "grid.linewidth": 0.8,
            "axes.axisbelow": True,
            "xtick.color": TINTA_SECUNDARIA,
            "ytick.color": TINTA_SECUNDARIA,
            "xtick.labelcolor": TINTA,
            "legend.frameon": False,
            "figure.facecolor": SUPERFICIE,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def carregar_dados() -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    with JSON_ENTRADA.open(encoding="utf-8") as f:
        execucoes = pd.DataFrame(json.load(f))
    execucoes = execucoes[execucoes["modo"] == "producao"]
    grupos = {modo: pd.read_csv(csv) for modo, csv in CSV_GRUPOS.items()}

    # O CSV e o JSON têm de descrever a mesma rodada.
    prod = grupos["producao"].set_index("grupo")
    for grupo, df in execucoes.groupby("grupo"):
        assert len(df) == prod.loc[grupo, "n_execucoes"], f"{grupo}: n diverge entre CSV e JSON"
        assert abs(df["sucesso"].mean() - prod.loc[grupo, "taxa_sucesso_execucoes"]) < 0.001, grupo
    return execucoes, grupos


def _ordem(grupos_presentes) -> list[str]:
    return [g for g in ROTULOS_GRUPO if g in set(grupos_presentes)]


def grafico_latencia(execucoes: pd.DataFrame) -> tuple[Path, float]:
    fig, ax = plt.subplots(figsize=(9, 6))
    ordem = _ordem(execucoes["grupo"])
    recusa = execucoes["desfecho"] != "resposta"

    for i, grupo in enumerate(ordem):
        df = execucoes[execucoes["grupo"] == grupo].reset_index(drop=True)
        # Deslocamento horizontal fixo (sem aleatoriedade: figura reprodutível).
        desloc = [-0.3 + 0.6 * k / max(len(df) - 1, 1) for k in range(len(df))]
        cores = [AZUL if d != "resposta" else LARANJA for d in df["desfecho"]]
        ax.scatter([i + d for d in desloc], df["latencia_ms"], s=16, color=cores,
                   edgecolor=SUPERFICIE, linewidth=0.6, zorder=3)
        mediana = df["latencia_ms"].median()
        ax.hlines(mediana, i - 0.36, i + 0.36, color=TINTA, linewidth=2, zorder=4)
        ax.annotate(f"mediana {_ms(mediana)}", xy=(i, df["latencia_ms"].max()), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=9.5, fontweight="bold", color=TINTA)

    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _ms(v)))
    ax.set_ylim(execucoes["latencia_ms"].min() / 2, execucoes["latencia_ms"].max() * 4)
    ax.set_xticks(range(len(ordem)))
    ax.set_xticklabels([ROTULOS_GRUPO[g] for g in ordem])
    ax.set_ylabel("Latência (ms, escala logarítmica)")
    n_rep = execucoes.groupby("caso_id")["repeticao"].count().max()
    ax.set_title(f"Latência por grupo de casos ({len(execucoes)} execuções, {n_rep} por caso)", pad=14)

    med_resposta = execucoes.loc[~recusa, "latencia_ms"].median()
    med_recusa = execucoes.loc[recusa, "latencia_ms"].median()
    razao = med_resposta / med_recusa
    ax.text(0.98, 0.97,
            f"Mediana com síntese: {_ms(med_resposta)}\n"
            f"Mediana da recusa: {_ms(med_recusa)}\n"
            f"Razão: {f'{razao:.1f}'.replace('.', ',')}x",
            transform=ax.transAxes, ha="right", va="top", fontsize=10, color=TINTA,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=SUPERFICIE, edgecolor=GRADE))

    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=LARANJA, markersize=6),
        plt.Line2D([], [], marker="o", linestyle="", color=AZUL, markersize=6),
        plt.Line2D([], [], color=TINTA, linewidth=2),
    ]
    ax.legend(handles,
              ["Resposta sintetizada (classificação + busca + síntese)",
               "Recusa (Camada 7; sem síntese)",
               "Mediana do grupo"],
              loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=10)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_latencia_cenarios.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino, razao


def grafico_taxas_governanca(execucoes: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 6))
    ordem = _ordem(execucoes["grupo"])
    taxas = execucoes.groupby("grupo")[["sucesso", "recusou", "aviso_camada7"]].mean().loc[ordem]
    series = [
        ("sucesso", "Sucesso automático: comportamento esperado, sem aviso (não mede correção)", VERDE_AGUA),
        ("recusou", "Recusa (Camada 7)", AZUL),
        ("aviso_camada7", "Aviso de norma, artigo ou valor não verificado (Camada 7)", LARANJA),
    ]
    largura = 0.26
    for j, (coluna, rotulo, cor) in enumerate(series):
        posicoes = [i + (j - 1) * largura for i in range(len(ordem))]
        valores = taxas[coluna] * 100
        ax.bar(posicoes, valores, width=largura, label=rotulo, color=cor,
               edgecolor=SUPERFICIE, linewidth=2, zorder=2)
        # Rótulo em toda barra, inclusive 0%: zero é resultado, não dado ausente.
        for p, v in zip(posicoes, valores):
            ax.annotate(f"{v:.0f}%", xy=(p, v), xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=9, fontweight="bold", color=TINTA)

    ax.set_xticks(range(len(ordem)))
    ax.set_xticklabels([ROTULOS_GRUPO[g] for g in ordem])
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel("Proporção das execuções (modo produção)")
    ax.set_title(f"Desfechos por grupo de casos ({len(execucoes)} execuções)", pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=10)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_taxas_governanca.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


def grafico_sucesso_grupos(grupos: dict[str, pd.DataFrame]) -> Path:
    fig, ax = plt.subplots(figsize=(9, 6))
    ordem = _ordem(grupos["producao"]["grupo"]) + ["total"]
    rotulos = {**ROTULOS_GRUPO, "total": "Total"}
    modos = [("producao", "Produção (temperatura 0,1, seed 42)", VERDE_AGUA),
             ("sensibilidade", "Sensibilidade (temperatura 0,8, seed aleatória)", LARANJA)]

    for j, (modo, rotulo, cor) in enumerate(modos):
        df = grupos[modo].set_index("grupo").loc[ordem]
        x = [i + (j - 0.5) * 0.3 for i in range(len(ordem))]
        y = df["taxa_casos_sucesso_total"]
        erro = [y - df["ic95_casos_sucesso_inf"], df["ic95_casos_sucesso_sup"] - y]
        ax.errorbar(x, y * 100, yerr=[e * 100 for e in erro], fmt="o", color=cor, markersize=8,
                    markeredgecolor=SUPERFICIE, markeredgewidth=1.5, ecolor=cor, elinewidth=2,
                    capsize=4, label=rotulo, zorder=3)
        # Produção rotulada à esquerda do ponto e sensibilidade à direita,
        # para os rótulos dos dois modos não se sobreporem.
        lado, alinhamento = (-9, "right") if j == 0 else (9, "left")
        for xi, (_, linha) in zip(x, df.iterrows()):
            ax.annotate(f"{int(linha['casos_sucesso_total'])}/{int(linha['n_casos'])}",
                        xy=(xi, linha["taxa_casos_sucesso_total"] * 100), xytext=(lado, -3),
                        textcoords="offset points", ha=alinhamento, fontsize=8.5, color=TINTA)

    ax.axvline(len(ordem) - 1.5, color=GRADE, linewidth=1)
    ax.set_xlim(-0.8, len(ordem) - 0.4)  # espaço para os rótulos à esquerda
    ax.set_xticks(range(len(ordem)))
    ax.set_xticklabels([rotulos[g] for g in ordem])
    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel("Casos com sucesso em todas as repetições")
    ax.set_title("Sucesso automático por grupo, com IC 95% de Wilson (sobre os casos)", pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=1, fontsize=10)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_sucesso_grupos.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


def grafico_auditoria() -> Path:
    """Veredito manual das execuções com resposta esperada no corpus, separado
    por acerto da recuperação (algum trecho rotulado entre os 3)."""
    auditoria = pd.read_csv(CSV_AUDITORIA)
    recuperacao = pd.read_csv(CSV_RECUPERACAO)[["caso_id", "acerto_recuperacao"]]
    df = auditoria.merge(recuperacao, on="caso_id")
    contagem = df.pivot_table(index="acerto_recuperacao", columns="veredito", values="n_repeticoes",
                              aggfunc="sum", fill_value=0)
    categorias = [("correta", "Correta", VERDE_AGUA), ("parcial", "Parcial", AZUL),
                  ("abstencao", "Abstenção (declara que o contexto não tem a informação)", CINZA),
                  ("incorreta", "Incorreta, sem aviso da Camada 7", LARANJA)]
    linhas = [(True, "Trecho relevante\nentre os 3 recuperados"), (False, "Nenhum trecho\nrelevante recuperado")]

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, (acerto, _) in enumerate(linhas):
        total = contagem.loc[acerto].sum()
        inicio = 0.0
        for chave, _, cor in categorias:
            n = contagem.loc[acerto].get(chave, 0)
            largura = n / total * 100
            ax.barh(i, largura, left=inicio, color=cor, edgecolor=SUPERFICIE, linewidth=2, height=0.6, zorder=2)
            if n:
                ax.text(inicio + largura / 2, i, f"{n}", ha="center", va="center", fontsize=10,
                        fontweight="bold", color=SUPERFICIE if chave != "abstencao" else TINTA)
            inicio += largura
        ax.text(101, i, f"n={total}", va="center", fontsize=10, color=TINTA_SECUNDARIA)

    ax.set_yticks(range(len(linhas)))
    ax.set_yticklabels([rotulo for _, rotulo in linhas])
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xticks(range(0, 101, 20))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlabel("Proporção das execuções (modo produção; números = execuções)")
    ax.set_title("Auditoria manual das respostas, pelo acerto da recuperação", pad=14)
    handles = [plt.Rectangle((0, 0), 1, 1, color=cor) for _, _, cor in categorias]
    ax.legend(handles, [rotulo for _, rotulo, _ in categorias], loc="upper center",
              bbox_to_anchor=(0.5, -0.25), ncol=2, fontsize=9.5)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_auditoria_recuperacao.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


if __name__ == "__main__":
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    _configurar_estilo()

    execucoes, grupos = carregar_dados()
    print(f"Dados carregados de {JSON_ENTRADA} ({len(execucoes)} execuções) e das tabelas por grupo; "
          "CSV e JSON conferem.")

    caminho1, razao = grafico_latencia(execucoes)
    print(f"Gráfico salvo: {caminho1} (razão das medianas resposta/recusa = {razao:.1f}x)")
    print(f"Gráfico salvo: {grafico_taxas_governanca(execucoes)}")
    print(f"Gráfico salvo: {grafico_sucesso_grupos(grupos)}")
    print(f"Gráfico salvo: {grafico_auditoria()}")
