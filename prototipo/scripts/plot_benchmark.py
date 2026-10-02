"""
Gera os gráficos de publicação (Capítulo 3) a partir do benchmark empírico
do modo produção, produzido por run_benchmark.py:

  - docs/tabela_resultados_empiricos.csv: estatísticas agregadas por cenário
    (4 linhas, uma por caso de tests/casos_teste.json);
  - docs/resultados/resultados_benchmark.json: um registro por execução,
    usado para plotar cada execução individual sobre a média.

Gera dois gráficos em docs/figuras/, 300 DPI, rótulos em português:

  - grafico_latencia_cenarios.png: latência média por cenário (barra) com
    cada uma das n execuções (pontos), em escala logarítmica — em escala
    linear as barras de recusa (~150 ms) ficam invisíveis ao lado do
    caminho feliz (~14 s). A anotação traz a razão entre a latência média
    do fluxo normativo e a da recusa direta, calculada dos dados.
  - grafico_taxas_governanca.png: por cenário, taxa de recusa, taxa de
    aviso da Camada 7 (régua atual, v2: norma, artigo ou valor não
    verificado) e taxa de ausência declarada (o modelo diz que a norma não
    está no corpus — comportamento correto, não um aviso). A métrica legada
    `aviso_citacao_nao_verificada` (régua v1/v2) não é plotada: ela marca
    como "citação não verificada" a menção à norma ausente, que a Camada 7
    atual classifica como ausência declarada.

Os números exibidos (taxas, latências, n, razão) vêm todos dos dados; nada é
fixo no código.

Uso:
    python scripts/plot_benchmark.py
"""
import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

RAIZ = Path(__file__).resolve().parent.parent
CSV_ENTRADA = RAIZ / "docs" / "tabela_resultados_empiricos.csv"
JSON_ENTRADA = RAIZ / "docs" / "resultados" / "resultados_benchmark.json"
DIR_FIGURAS = RAIZ / "docs" / "figuras"

# Cenários cujo tipo esperado desvia o fluxo para uma recusa direta da
# Camada 7 (ver orchestrator.py, _RECUSAS) — não fazem síntese via LLM.
TIPOS_RECUSA = {"parecer_juridico", "fora_de_escopo"}
CAMINHO_RECUSA = "Recusa direta (Camada 7)"
CAMINHO_NORMATIVO = "Fluxo normativo completo (Camadas 2-7)"

# Paleta categórica (slots 1-3 da paleta de referência, validados em todos
# os pares no modo claro); texto sempre em tinta neutra.
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE_AGUA = "#1baf7a"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
GRADE = "#e4e3df"
SUPERFICIE = "#ffffff"

LARGURA_QUEBRA_ROTULO = 18


def _quebrar_rotulo(texto: str) -> str:
    return "\n".join(textwrap.wrap(texto, LARGURA_QUEBRA_ROTULO))


def _ms(valor: float) -> str:
    """Formata milissegundos com separador de milhar brasileiro."""
    return f"{valor:,.0f}".replace(",", ".") + " ms"


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


def _caminho(tipo_esperado: str) -> str:
    return CAMINHO_RECUSA if tipo_esperado in TIPOS_RECUSA else CAMINHO_NORMATIVO


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    agregado = pd.read_csv(CSV_ENTRADA)
    agregado["caminho"] = agregado["tipo_esperado"].apply(_caminho)
    agregado["rotulo"] = agregado["categoria"].apply(_quebrar_rotulo)

    with JSON_ENTRADA.open(encoding="utf-8") as f:
        execucoes = pd.DataFrame(json.load(f))
    execucoes = execucoes[execucoes["modo"] == "producao"]

    # O CSV e o JSON têm de descrever a mesma rodada.
    conferencia = execucoes.groupby("caso_id")["latencia_ms"].agg(["count", "mean"])
    for _, linha in agregado.iterrows():
        n, media = conferencia.loc[linha["caso_id"]]
        assert n == linha["n_execucoes"], f"{linha['caso_id']}: n diverge entre CSV e JSON"
        assert abs(media - linha["latencia_media_ms"]) < 0.01, f"{linha['caso_id']}: média diverge"
    return agregado, execucoes


def _n_por_cenario(df: pd.DataFrame) -> str:
    valores = df["n_execucoes"].unique()
    return f"n={valores[0]} execuções por cenário" if len(valores) == 1 else "n variável por cenário"


def grafico_latencia(df: pd.DataFrame, execucoes: pd.DataFrame) -> tuple[Path, float]:
    fig, ax = plt.subplots(figsize=(9, 6))
    cores = {CAMINHO_RECUSA: AZUL, CAMINHO_NORMATIVO: LARANJA}
    x = list(range(len(df)))

    ax.bar(x, df["latencia_media_ms"], width=0.6, color=df["caminho"].map(cores),
           edgecolor=SUPERFICIE, linewidth=2, zorder=2)

    # Cada execução individual, com deslocamento horizontal fixo (sem
    # aleatoriedade, para a figura ser reprodutível).
    for i, caso_id in enumerate(df["caso_id"]):
        lat = execucoes.loc[execucoes["caso_id"] == caso_id, "latencia_ms"].to_list()
        desloc = [(-0.16 + 0.32 * k / max(len(lat) - 1, 1)) for k in range(len(lat))]
        ax.scatter([i + d for d in desloc], lat, s=22, color=SUPERFICIE,
                   edgecolor=TINTA, linewidth=1, zorder=3)

    for i, (media, maximo) in enumerate(zip(df["latencia_media_ms"], df["latencia_max_ms"])):
        ax.annotate(f"média {_ms(media)}", xy=(i, max(media, maximo)), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=10,
                    fontweight="bold", color=TINTA)

    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _ms(v)))
    ax.set_ylim(df["latencia_min_ms"].min() / 2, df["latencia_max_ms"].max() * 4)
    ax.set_xticks(x)
    ax.set_xticklabels(df["rotulo"])
    ax.set_ylabel("Latência (ms, escala logarítmica)")
    ax.set_title(f"Latência por cenário de teste ({_n_por_cenario(df)})", pad=14)

    media_recusa = execucoes.loc[execucoes["tipo_esperado"].isin(TIPOS_RECUSA), "latencia_ms"].mean()
    media_normativo = execucoes.loc[~execucoes["tipo_esperado"].isin(TIPOS_RECUSA), "latencia_ms"].mean()
    razao = media_normativo / media_recusa
    ax.text(0.98, 0.97,
            f"Média do fluxo normativo: {_ms(media_normativo)}\n"
            f"Média da recusa direta: {_ms(media_recusa)}\n"
            f"Razão: {f'{razao:.1f}'.replace('.', ',')}x",
            transform=ax.transAxes, ha="right", va="top", fontsize=10, color=TINTA,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=SUPERFICIE, edgecolor=GRADE))

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=LARANJA),
        plt.Rectangle((0, 0), 1, 1, color=AZUL),
        plt.Line2D([], [], marker="o", linestyle="", markerfacecolor=SUPERFICIE,
                   markeredgecolor=TINTA, markersize=5),
    ]
    ax.legend(handles,
              [f"{CAMINHO_NORMATIVO}: classificação + síntese",
               f"{CAMINHO_RECUSA}: só classificação",
               "Execução individual"],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, fontsize=10)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_latencia_cenarios.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino, razao


def grafico_taxas_governanca(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 6))
    series = [
        ("taxa_recusa", "Recusa (Camada 7)", AZUL),
        ("taxa_aviso_camada7", "Aviso de norma, artigo ou valor não verificado (Camada 7)", LARANJA),
        ("taxa_ausencia_declarada", "Ausência declarada: o modelo informa que a norma não está no corpus",
         VERDE_AGUA),
    ]
    x = list(range(len(df)))
    largura = 0.26

    for j, (coluna, rotulo, cor) in enumerate(series):
        posicoes = [i + (j - 1) * largura for i in x]
        valores = df[coluna] * 100
        ax.bar(posicoes, valores, width=largura, label=rotulo, color=cor,
               edgecolor=SUPERFICIE, linewidth=2, zorder=2)
        # Rótulo em toda barra, inclusive 0%: zero é resultado, não dado ausente.
        for p, v in zip(posicoes, valores):
            ax.annotate(f"{v:.0f}%", xy=(p, v), xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=9.5, fontweight="bold", color=TINTA)

    ax.set_xticks(x)
    ax.set_xticklabels(df["rotulo"])
    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel("Proporção das execuções")
    ax.set_title(f"Desfechos de governança por cenário ({_n_por_cenario(df)})", pad=14)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1, fontsize=10)
    fig.tight_layout()

    destino = DIR_FIGURAS / "grafico_taxas_governanca.png"
    fig.savefig(destino)
    plt.close(fig)
    return destino


if __name__ == "__main__":
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    _configurar_estilo()

    df, execucoes = carregar_dados()
    print(f"Dados carregados de {CSV_ENTRADA} ({len(df)} cenários) e {JSON_ENTRADA} "
          f"({len(execucoes)} execuções); CSV e JSON conferem.")

    caminho1, razao = grafico_latencia(df, execucoes)
    print(f"Gráfico salvo: {caminho1} (razão normativo/recusa = {razao:.1f}x)")

    caminho2 = grafico_taxas_governanca(df)
    print(f"Gráfico salvo: {caminho2}")
