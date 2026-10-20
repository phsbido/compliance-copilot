"""
Figura da rodada v7: recuperação da Camada 5 nos três modos (bm25,
embeddings, hybrid), 39 casos normativos, modo produção — sem LLM.

Painel esquerdo: Acerto@3, Recall@3 e MRR por modo (barras agrupadas, valor
rotulado em cada barra). Painel direito: os casos normativos cujo Acerto@3
mudou entre os modos (marcador cheio = trecho rotulado entre os 3; vazado =
não), para que a identidade não dependa só da cor.

Lê docs/resultados/v7/comparacao_modos.csv e casos_mudaram_recuperacao.csv
(scripts/comparar_v7.py) e grava docs/figuras/grafico_v7_recuperacao_modos.png.
Mesmo estilo e paleta de scripts/plot_benchmark.py.

Uso (dentro de prototipo/):
    python scripts/plot_v7.py
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scripts.plot_benchmark import (  # noqa: E402
    AZUL, DIR_FIGURAS, LARANJA, TINTA, TINTA_SECUNDARIA, VERDE_AGUA, _configurar_estilo,
)

V7 = RAIZ / "docs" / "resultados" / "v7"
FIGURA = DIR_FIGURAS / "grafico_v7_recuperacao_modos.png"
MODOS = [("bm25", "BM25", AZUL), ("embeddings", "Embeddings", LARANJA), ("hybrid", "Híbrido (RRF)", VERDE_AGUA)]
METRICAS = [("acerto_3", "Acerto@3"), ("recall_3", "Recall@3"), ("mrr_3", "MRR")]


def _virgula(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def painel_metricas(ax, comp: pd.DataFrame) -> None:
    normativos = comp[comp["grupo"] == "normativo_corpus"].set_index("modo")
    largura, folga = 0.26, 0.02
    for j, (modo, rotulo, cor) in enumerate(MODOS):
        xs = [i + (j - 1) * (largura + folga) for i in range(len(METRICAS))]
        valores = [normativos.loc[modo, m] for m, _ in METRICAS]
        ax.bar(xs, valores, width=largura, color=cor, label=rotulo, zorder=3)
        for x, v in zip(xs, valores):
            ax.text(x, v + 0.015, _virgula(v), ha="center", va="bottom", fontsize=9, color=TINTA)
    ax.set_xticks(range(len(METRICAS)), [r for _, r in METRICAS])
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0], ["0", "0,25", "0,50", "0,75", "1"])
    ax.set_title("Recuperação nos 39 casos normativos")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=10)


def painel_casos(ax, mudou: pd.DataFrame) -> None:
    casos = mudou["caso_id"].tolist()
    for j, (modo, rotulo, cor) in enumerate(MODOS):
        for i, caso in enumerate(casos):
            acerto = bool(mudou.loc[mudou["caso_id"] == caso, f"acerto_{modo}"].iloc[0])
            ax.scatter(j, i, s=150, marker="o", zorder=3, linewidths=2,
                       facecolor=cor if acerto else "white", edgecolor=cor)
    ax.set_xticks(range(len(MODOS)), [r for _, r, _ in MODOS])
    ax.set_yticks(range(len(casos)), casos, fontsize=9)
    ax.set_xlim(-0.6, len(MODOS) - 0.4)
    ax.set_ylim(len(casos) - 0.5, -0.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Casos cujo Acerto@3 mudou")
    ax.text(1, len(casos) - 0.5 + 0.8, "cheio = trecho rotulado entre os 3   ·   vazado = não",
            ha="center", va="top", fontsize=9, color=TINTA_SECUNDARIA)


if __name__ == "__main__":
    comp = pd.read_csv(V7 / "comparacao_modos.csv")
    mudou = pd.read_csv(V7 / "casos_mudaram_recuperacao.csv")
    _configurar_estilo()
    fig, (esq, dir_) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.15, 1]})
    painel_metricas(esq, comp)
    painel_casos(dir_, mudou)
    fig.suptitle("v7: BM25, embeddings (bge-m3) e híbrido na Camada 5 — modo produção",
                 x=0.01, ha="left", fontsize=12, color=TINTA_SECUNDARIA)
    fig.tight_layout()
    FIGURA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURA)
    plt.close(fig)
    print(f"Figura salva em {FIGURA}")
