"""
Conferências 2 e 3 (pós-v6), recalculadas em memória, sem regravar nenhum
resultado do v5 nem do v6.

Conferência 2 — os 4 casos de desenvolvimento (CT01–CT04): sucesso
automático por grupo (v5 produção, v5 sensibilidade e v6), Acerto@3 e
auditoria, com e sem esses casos. Usa tabela_por_caso e tabela_por_grupo do
run_benchmark.py, que reproduzem os valores publicados.

Conferência 3 — vereditos da auditoria (docs/auditoria_respostas_v5.csv)
contados por execução e por resposta distinta, e a tabela "a recuperação
decide" nas duas contagens.

Ver docs/evidencias_empiricas.md (2026-10-05, Conferências 2 e 3).

Uso:
    python scripts/conferencias_pos_v6.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from run_benchmark import tabela_por_caso, tabela_por_grupo  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)

DEV = ["caminho_feliz_rag_bacen", "norma_ausente_fronteira", "solicitacao_parecer_governanca",
       "fora_de_escopo_governanca"]
CATS = ["correta", "parcial", "abstencao", "incorreta", "recusa_modelo"]
RODADAS = [
    ("v5 produção", RAIZ / "docs" / "resultados" / "resultados_benchmark.json"),
    ("v5 sensibilidade", RAIZ / "docs" / "resultados" / "resultados_benchmark_sensibilidade.json"),
    ("v6", RAIZ / "docs" / "resultados" / "v6" / "resultados_benchmark.json"),
]


def grupos(arq: Path, excluir=()) -> pd.DataFrame:
    df = pd.DataFrame(json.load(arq.open(encoding="utf-8")))
    df = df[~df.caso_id.isin(excluir)]
    return tabela_por_grupo(df, tabela_por_caso(df))[
        ["grupo", "n_casos", "casos_sucesso_total", "ic95_casos_sucesso_inf", "ic95_casos_sucesso_sup",
         "n_casos_rotulados_recuperacao", "acerto_recuperacao_3"]]


def tab(d: pd.DataFrame, peso: str) -> pd.DataFrame:
    return (d.pivot_table(index="g", columns="veredito", values=peso, aggfunc="sum", fill_value=0)
            .reindex(columns=CATS, fill_value=0).assign(total=lambda x: x.sum(axis=1)))


def main() -> None:
    print("##### Conferência 2 — sucesso automático por grupo, com e sem os 4 casos de desenvolvimento")
    for nome, arq in RODADAS:
        print("=====", nome)
        print(grupos(arq).merge(grupos(arq, DEV), on="grupo", suffixes=("", "_sem4")).to_string(index=False))

    rec = pd.read_csv(RAIZ / "docs" / "tabela_recuperacao.csv")
    for nome, t in [("com os 4", rec), ("sem os 4", rec[~rec.caso_id.isin(DEV)])]:
        n = t[t.grupo == "normativo_corpus"]
        print(f"Acerto@3 (tabela_recuperacao.csv), {nome}: {len(t)} rotulados, {t.acerto_recuperacao.mean():.3f}"
              f" | normativos {len(n)}, {n.acerto_recuperacao.mean():.3f}")

    print("\n##### Conferências 2 e 3 — auditoria v5 (produção)")
    au = pd.read_csv(RAIZ / "docs" / "auditoria_respostas_v5.csv")
    au["g"] = au.grupo.map({"normativo_corpus": "normativo_corpus", "robustez": "robustez",
                            "norma_ausente": "norma_ausente"}).fillna("parecer/fora mal classif.")
    au["um"] = 1
    for nome, d in [("com os 4", au), ("sem os 4", au[~au.caso_id.isin(DEV)])]:
        print(f"===== {nome} | respostas distintas {len(d)}, execuções {d.n_repeticoes.sum()}")
        print("por execução\n", tab(d, "n_repeticoes"))
        print("por resposta distinta\n", tab(d, "um"))
        n = d[d.grupo == "normativo_corpus"]
        maj = n.sort_values("n_repeticoes", ascending=False).groupby("caso_id").veredito.first()
        print("normativos por caso (resposta majoritária):", maj.value_counts().to_dict(), "de", len(maj))
        r = d.merge(rec[["caso_id", "acerto_recuperacao"]], on="caso_id")
        print("a recuperação decide (por execução):\n",
              r.pivot_table(index="acerto_recuperacao", columns="veredito", values="n_repeticoes",
                            aggfunc="sum", fill_value=0))
        print("a recuperação decide (por resposta distinta):\n",
              r.pivot_table(index="acerto_recuperacao", columns="veredito", values="um", aggfunc="sum",
                            fill_value=0))
    print("\nCasos de desenvolvimento na auditoria:")
    print(au[au.caso_id.isin(DEV)][["caso_id", "grupo", "repeticoes", "veredito", "padrao"]].to_string(index=False))


if __name__ == "__main__":
    main()
