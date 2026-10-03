"""
Comparação v5 x v6 (Tarefa A: limiar BM25 na Camada 5) — sem LLM.

Lê os JSONs brutos das duas rodadas (modo produção) e compara, por grupo:
recusas sem base (corretas no grupo norma ausente, indevidas no grupo
normativo), sucesso automático, Acerto@3 e latência. Para os casos
normativos recusados na v6, mostra o veredito majoritário da auditoria v5,
isto é, o que se perdeu com a recusa.

Saída: docs/resultados/v6/comparacao_v5_v6.csv e
docs/resultados/v6/casos_recusados_v6.csv.

Uso (dentro de prototipo/):
    python scripts/comparar_v5_v6.py
"""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "docs" / "resultados"
V5 = RES / "resultados_benchmark.json"
V6 = RES / "v6" / "resultados_benchmark.json"
AUDITORIA = RAIZ / "docs" / "auditoria_respostas_v5.csv"
SAIDA = RES / "v6" / "comparacao_v5_v6.csv"
SAIDA_CASOS = RES / "v6" / "casos_recusados_v6.csv"
ORDEM = ["normativo_corpus", "norma_ausente", "parecer_juridico", "fora_de_escopo", "robustez"]


def carregar(caminho: Path) -> pd.DataFrame:
    return pd.DataFrame(json.loads(caminho.read_text(encoding="utf-8")))


def linha(versao: str, df: pd.DataFrame, grupo: str) -> dict:
    rot = df.dropna(subset=["acerto_recuperacao"]).drop_duplicates("caso_id")
    return {
        "versao": versao, "grupo": grupo, "execucoes": len(df),
        "recusa_sem_base": int((df["desfecho"] == "recusa_sem_base").sum()),
        "taxa_recusa_sem_base": round((df["desfecho"] == "recusa_sem_base").mean(), 3),
        "sucesso_execucoes": round(df["sucesso"].mean(), 3),
        "casos_sucesso_total": int(df.groupby("caso_id")["sucesso"].all().sum()),
        "n_casos": df["caso_id"].nunique(),
        "acerto_recuperacao_3": round(rot["acerto_recuperacao"].astype(float).mean(), 3) if len(rot) else None,
        "latencia_mediana_ms": round(df["latencia_ms"].median(), 1),
        "latencia_p95_ms": round(df["latencia_ms"].quantile(0.95), 1),
    }


if __name__ == "__main__":
    v5, v6 = carregar(V5), carregar(V6)
    linhas = []
    for grupo in ORDEM + ["total"]:
        for versao, df in (("v5", v5), ("v6", v6)):
            sel = df if grupo == "total" else df[df["grupo"] == grupo]
            linhas.append(linha(versao, sel, grupo))
    tabela = pd.DataFrame(linhas)
    tabela.to_csv(SAIDA, index=False, encoding="utf-8")

    aud = pd.read_csv(AUDITORIA)
    majoritario = (aud.assign(n=aud["n_repeticoes"]).groupby(["caso_id", "veredito"])["n"].sum()
                   .reset_index().sort_values("n", ascending=False).drop_duplicates("caso_id")
                   .set_index("caso_id")["veredito"])
    recusados = (v6[v6["desfecho"] == "recusa_sem_base"].groupby(["caso_id", "grupo"])
                 .agg(execucoes_recusadas=("repeticao", "count"),
                      pontuacao_melhor_trecho=("pontuacao_melhor_trecho", "first")).reset_index())
    recusados["veredito_v5_majoritario"] = recusados["caso_id"].map(majoritario).fillna("(sem auditoria)")
    recusados.sort_values(["grupo", "pontuacao_melhor_trecho"]).to_csv(SAIDA_CASOS, index=False, encoding="utf-8")

    print(tabela.to_string(index=False))
    print("\nCasos com recusa sem base na v6, por veredito majoritário da auditoria v5:")
    print(recusados.groupby(["grupo", "veredito_v5_majoritario"])["caso_id"].count().to_string())
    print(f"\nSalvos: {SAIDA}, {SAIDA_CASOS}")
