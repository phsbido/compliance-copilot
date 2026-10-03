"""
Calibração do limiar BM25 da Camada 5 (v6, Tarefa A) — sem LLM.

Lê o conjunto de calibração (tests/calibracao_limiar.json, independente dos
66 casos), calcula a pontuação BM25 do melhor trecho de cada pergunta e
aplica o critério pré-registrado no próprio arquivo e em
docs/decisoes_arquitetura.md ("Tarefa A"):

    limiar = pontuação da (k+1)-ésima menor pergunta respondível,
    k = floor(0,05 × n_respondiveis)

isto é, o maior limiar que recusa no máximo 5% das respondíveis. Também
informa, só como referência, o limiar de Youden (não usado).

Saída: docs/resultados/v6/calibracao_limiar.csv (uma linha por pergunta),
docs/figuras/grafico_calibracao_limiar.png (distribuição das pontuações nos
dois grupos, com o limiar) e o resumo no terminal.

Uso (dentro de prototipo/):
    python scripts/calibrar_limiar.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from run_benchmark import TOP_K, metricas_recuperacao  # noqa: E402
from scripts.plot_benchmark import (  # noqa: E402
    AZUL, DIR_FIGURAS, LARANJA, TINTA, TINTA_SECUNDARIA, _configurar_estilo,
)
from src.layer5_knowledge.knowledge_base import KnowledgeBase  # noqa: E402

CONJUNTO = RAIZ / "tests" / "calibracao_limiar.json"
SAIDA = RAIZ / "docs" / "resultados" / "v6" / "calibracao_limiar.csv"
FIGURA = DIR_FIGURAS / "grafico_calibracao_limiar.png"
TAXA_MAXIMA_RECUSA_INDEVIDA = 0.05


def pontuar(perguntas: list[dict]) -> pd.DataFrame:
    kb = KnowledgeBase()
    linhas = []
    for p in perguntas:
        pontuados = kb.buscar_pontuado(p["pergunta"], top_k=TOP_K)
        recuperados = [{"norma": d.titulo, "trecho": d.identificador} for _, d in pontuados]
        linhas.append({
            "id": p["id"],
            "grupo": p["grupo"],
            "subgrupo": p.get("subgrupo", ""),
            "pergunta": p["pergunta"],
            "pontuacao_melhor_trecho": round(pontuados[0][0], 4) if pontuados else 0.0,
            "melhor_trecho": f"{recuperados[0]['norma'].split(',')[0]} {recuperados[0]['trecho']}" if pontuados else "",
            "relevante_entre_os_3": metricas_recuperacao(recuperados, p.get("relevantes") or [])["acerto_recuperacao"],
        })
    return pd.DataFrame(linhas)


def limiar_pelo_criterio(pontuacoes_respondiveis: list[float]) -> tuple[float, int]:
    ordenadas = sorted(pontuacoes_respondiveis)
    k = math.floor(TAXA_MAXIMA_RECUSA_INDEVIDA * len(ordenadas))
    return ordenadas[k], k


def limiar_youden(df: pd.DataFrame) -> tuple[float, float]:
    """Referência apenas: limiar que maximiza sensibilidade + especificidade − 1,
    com 'positivo' = pergunta sem resposta recusada."""
    melhor = (-1.0, math.nan)
    for t in sorted(df["pontuacao_melhor_trecho"].unique()):
        recusa = df["pontuacao_melhor_trecho"] < t
        sens = recusa[df["grupo"] == "sem_resposta"].mean()
        espec = (~recusa)[df["grupo"] == "respondivel"].mean()
        if sens + espec - 1 > melhor[0]:
            melhor = (sens + espec - 1, t)
    return melhor[1], melhor[0]


def grafico(df: pd.DataFrame, limiar: float) -> None:
    """Pontuação do melhor trecho por pergunta, um ponto por pergunta, com
    o limiar escolhido. Grupo identificado por posição, rótulo, cor e
    marcador (não só pela cor)."""
    _configurar_estilo()
    fig, ax = plt.subplots(figsize=(8, 3.2))
    grupos = [("respondivel", "Respondível pela Gold\n(n = 20)", AZUL, "o"),
              ("sem_resposta", "Sem resposta no corpus\n(n = 20)", LARANJA, "^")]
    for y, (grupo, _, cor, marcador) in enumerate(grupos):
        valores = df.loc[df["grupo"] == grupo, "pontuacao_melhor_trecho"].sort_values().tolist()
        # Deslocamento vertical determinístico para separar pontos próximos.
        desloc = [((i % 3) - 1) * 0.12 for i in range(len(valores))]
        ax.scatter(valores, [y + d for d in desloc], s=42, color=cor, marker=marcador,
                   edgecolor="white", linewidth=0.8, zorder=3)
    ax.axvline(limiar, color=TINTA_SECUNDARIA, linestyle="--", linewidth=1.2, zorder=2)
    ax.text(limiar, 1.55, f"  limiar = {limiar:.2f}".replace(".", ","), color=TINTA,
            va="center", ha="left", fontsize=10)
    ax.text(limiar, 1.55, "recusa  ", color=TINTA_SECUNDARIA, va="center", ha="right", fontsize=10)
    ax.set_yticks([0, 1], [g[1] for g in grupos])
    ax.set_ylim(-0.5, 1.8)
    ax.set_xlabel("Pontuação BM25 do melhor trecho")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title("Calibração do limiar da Camada 5 (conjunto independente, 40 perguntas)")
    FIGURA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURA)
    plt.close(fig)


if __name__ == "__main__":
    conjunto = json.loads(CONJUNTO.read_text(encoding="utf-8"))
    df = pontuar(conjunto["perguntas"])
    resp = df[df["grupo"] == "respondivel"]
    sem = df[df["grupo"] == "sem_resposta"]

    limiar, k = limiar_pelo_criterio(resp["pontuacao_melhor_trecho"].tolist())
    df["recusada_no_limiar"] = df["pontuacao_melhor_trecho"] < limiar
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values(["grupo", "pontuacao_melhor_trecho"]).to_csv(SAIDA, index=False, encoding="utf-8")

    print(f"Conjunto {conjunto['versao']}: {len(resp)} respondíveis, {len(sem)} sem resposta")
    print("\nPontuação do melhor trecho (BM25):")
    print(df.groupby("grupo")["pontuacao_melhor_trecho"].describe().round(2).to_string())
    print(f"\nCritério pré-registrado: k = floor({TAXA_MAXIMA_RECUSA_INDEVIDA} x {len(resp)}) = {k}; "
          f"limiar = {k + 1}ª menor pontuação respondível = {limiar:.4f}")
    print(f"  respondíveis recusadas: {int((resp['pontuacao_melhor_trecho'] < limiar).sum())}/{len(resp)}")
    print(f"  sem resposta recusadas: {int((sem['pontuacao_melhor_trecho'] < limiar).sum())}/{len(sem)}")
    for sub, g in sem.groupby("subgrupo"):
        print(f"    {sub}: {int((g['pontuacao_melhor_trecho'] < limiar).sum())}/{len(g)}")
    t_y, j = limiar_youden(df)
    print(f"\nReferência (não usada): limiar de Youden = {t_y:.4f} (J = {j:.2f})")
    print(f"Respondíveis com o trecho rotulado entre os 3: {int(resp['relevante_entre_os_3'].sum())}/{len(resp)}")
    grafico(df, limiar)
    print(f"\nTabela salva em {SAIDA}; figura em {FIGURA}")
