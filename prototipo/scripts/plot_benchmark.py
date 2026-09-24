"""
Gera os gráficos de publicação (Capítulo 3) a partir dos dados agregados do
benchmark empírico (docs/tabela_resultados_empiricos.csv), produzido por
run_benchmark.py.

Lê a tabela agregada por cenário (4 linhas, uma por caso de
tests/casos_teste.json) e gera dois gráficos em docs/figuras/, 300 DPI,
rótulos em português, estilo acadêmico limpo (seaborn "whitegrid", sem
elementos decorativos supérfluos):

  - grafico_latencia_cenarios.png: latência média por cenário, com barra de
    erro (desvio padrão) e anotação do fator de aceleração entre o caminho
    de recusa (Camada 7) e o caminho normativo completo (Camadas 2-7).
  - grafico_taxas_governanca.png: taxa de recusa e taxa de aviso de citação
    não verificada por cenário, com destaque textual no comportamento de
    borda (cenário de norma ausente).

Uso:
    python scripts/plot_benchmark.py
"""
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

RAIZ = Path(__file__).resolve().parent.parent
CSV_ENTRADA = RAIZ / "docs" / "tabela_resultados_empiricos.csv"
DIR_FIGURAS = RAIZ / "docs" / "figuras"

# Cenários cujo tipo esperado desvia o fluxo para uma recusa direta da
# Camada 7 (ver orchestrator.py, _RECUSAS) — não fazem síntese via LLM.
TIPOS_RECUSA = {"parecer_juridico", "fora_de_escopo"}

COR_RECUSA = "#4C72B0"
COR_NORMATIVO = "#DD8452"
COR_TAXA_RECUSA = "#4C72B0"
COR_TAXA_AVISO = "#C44E52"

LARGURA_QUEBRA_ROTULO = 18


def _quebrar_rotulo(texto: str) -> str:
    return "\n".join(textwrap.wrap(texto, LARGURA_QUEBRA_ROTULO))


def _configurar_estilo() -> None:
    sns.set_theme(style="whitegrid", context="talk")
    plt.rcParams.update(
        {
            "font.size": 12,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "axes.labelsize": 13,
            "figure.dpi": 300,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
        }
    )


def carregar_dados() -> pd.DataFrame:
    df = pd.read_csv(CSV_ENTRADA)
    df["caminho"] = df["tipo_esperado"].apply(
        lambda t: "Recusa direta (Camada 7)" if t in TIPOS_RECUSA else "Fluxo normativo completo (Camadas 2-7)"
    )
    df["rotulo"] = df["categoria"].apply(_quebrar_rotulo)
    return df


def grafico_latencia(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 7))

    cores = df["caminho"].map(
        {"Recusa direta (Camada 7)": COR_RECUSA, "Fluxo normativo completo (Camadas 2-7)": COR_NORMATIVO}
    )
    barras = ax.bar(
        df["rotulo"],
        df["latencia_media_ms"],
        yerr=df["latencia_desvio_padrao_ms"],
        color=cores,
        capsize=6,
        edgecolor="white",
        linewidth=0.8,
    )

    for barra, media in zip(barras, df["latencia_media_ms"]):
        ax.annotate(
            f"{media:,.0f} ms".replace(",", "."),
            xy=(barra.get_x() + barra.get_width() / 2, barra.get_height()),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=11,
            fontweight="bold",
        )

    media_recusa = df.loc[df["caminho"] == "Recusa direta (Camada 7)", "latencia_media_ms"].mean()
    media_normativo = df.loc[df["caminho"] == "Fluxo normativo completo (Camadas 2-7)", "latencia_media_ms"].mean()
    fator = media_normativo / media_recusa

    ax.annotate(
        f"~{fator:.0f}x mais rápido\n(recusa vs. fluxo normativo)",
        xy=(0.5, max(df["latencia_media_ms"]) * 0.55),
        ha="center",
        fontsize=13,
        fontweight="bold",
        color="#333333",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF3CD", edgecolor="#B8860B"),
    )

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=COR_RECUSA),
        plt.Rectangle((0, 0), 1, 1, color=COR_NORMATIVO),
    ]
    ax.legend(
        handles,
        ["Recusa direta (Camada 7) — só classificação", "Fluxo normativo completo (Camadas 2-7) — classificação + síntese"],
        loc="upper left",
        frameon=True,
        fontsize=10,
    )

    ax.set_title("Latência média por cenário de teste (n=5 execuções cada)")
    ax.set_xlabel("Cenário")
    ax.set_ylabel("Latência média (ms)")
    ax.set_ylim(0, max(df["latencia_media_ms"] + df["latencia_desvio_padrao_ms"]) * 1.25)
    sns.despine(ax=ax)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_latencia_cenarios.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


def grafico_taxas_governanca(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 7))

    x = range(len(df))
    largura = 0.35

    barras_recusa = ax.bar(
        [i - largura / 2 for i in x],
        df["taxa_recusa"] * 100,
        width=largura,
        label="Taxa de recusa (Camada 7)",
        color=COR_TAXA_RECUSA,
        edgecolor="white",
        linewidth=0.8,
    )
    barras_aviso = ax.bar(
        [i + largura / 2 for i in x],
        df["taxa_aviso_citacao_nao_verificada"] * 100,
        width=largura,
        label="Taxa de aviso de citação não verificada (Camada 7)",
        color=COR_TAXA_AVISO,
        edgecolor="white",
        linewidth=0.8,
    )

    for grupo in (barras_recusa, barras_aviso):
        for barra in grupo:
            altura = barra.get_height()
            if altura > 0:
                ax.annotate(
                    f"{altura:.0f}%",
                    xy=(barra.get_x() + barra.get_width() / 2, altura),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                    fontsize=11,
                    fontweight="bold",
                )

    # Destaque no comportamento de borda: cenário de norma ausente. Ancorado
    # à direita do último grupo de barras para não sobrepor os rótulos "100%"
    # dos cenários de governança nem a legenda (que fica no canto superior
    # esquerdo, sobre a área vazia do cenário "Caminho Feliz").
    idx_fronteira = df.index[df["caso_id"] == "norma_ausente_fronteira"]
    if len(idx_fronteira):
        i = df.index.get_loc(idx_fronteira[0])
        taxa = df.loc[idx_fronteira[0], "taxa_aviso_citacao_nao_verificada"] * 100
        ax.annotate(
            "Comportamento de borda:\nnorma citada pelo usuário não está\nno corpus indexado",
            xy=(i + largura / 2, taxa),
            xytext=(len(df) - 0.85, taxa - 8),
            fontsize=10.5,
            ha="left",
            va="center",
            color="#333333",
            arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2),
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#FDEDEC", edgecolor=COR_TAXA_AVISO),
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["rotulo"])
    ax.set_ylim(0, 115)
    ax.set_title("Taxa de recusa e de aviso de citação não verificada por cenário (n=5 execuções cada)")
    ax.set_xlabel("Cenário")
    ax.set_ylabel("Taxa (%)")
    ax.legend(loc="upper left", frameon=True, fontsize=10)
    sns.despine(ax=ax)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_taxas_governanca.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


if __name__ == "__main__":
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    _configurar_estilo()

    df = carregar_dados()
    print(f"Dados carregados de {CSV_ENTRADA} ({len(df)} cenários).")

    caminho1 = grafico_latencia(df)
    print(f"Gráfico salvo: {caminho1}")

    caminho2 = grafico_taxas_governanca(df)
    print(f"Gráfico salvo: {caminho2}")
