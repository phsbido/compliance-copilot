"""
Comparação dos três modos de recuperação da rodada v7 — sem LLM, sem Ollama.

Lê docs/resultados/v7/<modo>/resultados_benchmark.json (bm25, embeddings,
hybrid; modo produção) e gera, em docs/resultados/v7/:

  - comparacao_modos.csv: por modo e grupo (e total), Acerto@3, Recall@3,
    MRR, sucesso automático (execuções e casos) e latências medianas (busca e
    resposta completa); `norma_ausente_3_validos` repete o grupo só com os 3
    casos cuja norma continua fora do corpus (decisão do usuário,
    2026-10-20);
  - casos_mudaram_recuperacao.csv: casos normativos cujo Acerto@3 difere
    entre os modos, com o top-3 de cada modo;
  - mcnemar.csv: teste de McNemar exato do Acerto@3 por caso nos casos
    normativos, para os três pares de modos, com p bruto e ajustado por Holm
    (pré-registrado);
  - limiar_cosseno_execucoes.csv: execuções que o limiar de cosseno
    (scripts/calibrar_limiar_cosseno.py) recusaria, por grupo — só as que
    passaram da classificação e chegaram à busca;
  - auditoria_respostas_v7.csv: respostas sintetizadas distintas de cada
    modo, no formato de docs/auditoria_respostas_v5.csv, com veredito, padrão
    e nota em branco (os vereditos são do usuário) e a sugestão do
    assistente numa coluna separada.

Uso (dentro de prototipo/):
    python scripts/comparar_v7.py
"""
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from run_benchmark import ORDEM_GRUPOS, carregar_casos, tabela_por_caso, wilson  # noqa: E402

V7 = RAIZ / "docs" / "resultados" / "v7"
MODOS = ["bm25", "embeddings", "hybrid"]
PREMISSA_VENCIDA = {"ausente_res_cmn_4893", "ausente_circ_3978_pld", "ausente_res_bcb_96_contas"}
SUGESTOES_FILE = V7 / "sugestoes_veredito_assistente.json"


def carregar(modo: str, amostragem: str = "producao", base: Path = V7) -> pd.DataFrame:
    """JSON bruto de uma rodada: `base/<modo>/resultados_benchmark.json` na
    produção, `base/<modo>_sensibilidade/resultados_benchmark_sensibilidade.json`
    na sensibilidade (nomes de scripts/rodar_v7.py e run_benchmark.py)."""
    if amostragem == "producao":
        caminho = base / modo / "resultados_benchmark.json"
    else:
        caminho = base / f"{modo}_{amostragem}" / f"resultados_benchmark_{amostragem}.json"
    with caminho.open(encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))


def _linha(modo: str, nome: str, df: pd.DataFrame) -> dict:
    por_caso = tabela_por_caso(df)
    casos_ok = int((por_caso["taxa_sucesso"] == 1).sum())
    rot = por_caso.dropna(subset=["acerto_recuperacao_3"])
    ic = wilson(casos_ok, len(por_caso))
    return {
        "modo": modo, "grupo": nome, "n_casos": len(por_caso), "n_execucoes": len(df),
        "n_casos_rotulados": len(rot),
        "acerto_3": rot["acerto_recuperacao_3"].astype(float).mean(),
        "recall_3": rot["recall_recuperacao_3"].mean(),
        "mrr_3": rot["rr_recuperacao_3"].mean(),
        "taxa_sucesso_execucoes": df["sucesso"].mean(),
        "casos_sucesso_total": casos_ok,
        "ic95_inf": ic[0], "ic95_sup": ic[1],
        "latencia_busca_mediana_ms": df["latencia_busca_ms"].median(),
        "latencia_resposta_mediana_ms": df["latencia_ms"].median(),
        "latencia_resposta_media_ms": df["latencia_ms"].mean(),
    }


def comparacao(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    linhas = []
    for modo, df in dados.items():
        for g in ORDEM_GRUPOS:
            linhas.append(_linha(modo, g, df[df["grupo"] == g]))
            if g == "norma_ausente":
                sub = df[(df["grupo"] == g) & ~df["caso_id"].isin(PREMISSA_VENCIDA)]
                linhas.append(_linha(modo, "norma_ausente_3_validos", sub))
        linhas.append(_linha(modo, "total", df))
    return pd.DataFrame(linhas).round(3)


def _top3(r: dict) -> str:
    return "; ".join(f"{t['norma'].split(',')[0]} {t['trecho']}" for t in r["trechos_recuperados"])


def casos_mudaram(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    linhas = []
    base = dados["bm25"]
    for caso_id in base.loc[(base["grupo"] == "normativo_corpus"), "caso_id"].unique():
        primeira = {m: d[d["caso_id"] == caso_id].iloc[0] for m, d in dados.items()}
        acertos = {m: bool(primeira[m]["acerto_recuperacao"]) for m in MODOS}
        if len(set(acertos.values())) > 1:
            linhas.append({
                "caso_id": caso_id,
                **{f"acerto_{m}": acertos[m] for m in MODOS},
                **{f"rr_{m}": primeira[m]["rr_recuperacao"] for m in MODOS},
                **{f"top3_{m}": _top3(primeira[m]) for m in MODOS},
            })
    return pd.DataFrame(linhas)


def mcnemar_exato(b: int, c: int) -> float:
    """p bilateral: binomial(n = b + c, 0,5) sobre os pares discordantes."""
    n = b + c
    if n == 0:
        return 1.0
    cauda = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * cauda)


def mcnemar(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    acerto = {}
    for m, d in dados.items():
        n = d[d["grupo"] == "normativo_corpus"].groupby("caso_id")["acerto_recuperacao"].first()
        acerto[m] = n.astype(bool)
    linhas = []
    for a, b in combinations(MODOS, 2):
        x, y = acerto[a], acerto[b].reindex(acerto[a].index)
        so_a, so_b = int((x & ~y).sum()), int((~x & y).sum())
        linhas.append({"comparacao": f"{a} x {b}", "n_casos": len(x), f"acertos_a": int(x.sum()),
                       "acertos_b": int(y.sum()), "so_a_acerta": so_a, "so_b_acerta": so_b,
                       "p_exato": mcnemar_exato(so_a, so_b)})
    df = pd.DataFrame(linhas)
    # Holm: ordena os p, multiplica pelo número de hipóteses restantes, mantém monotônico.
    ordem = df["p_exato"].sort_values().index
    ajustado, maximo = {}, 0.0
    for i, idx in enumerate(ordem):
        maximo = max(maximo, min(1.0, (len(df) - i) * df.loc[idx, "p_exato"]))
        ajustado[idx] = maximo
    df["p_holm"] = pd.Series(ajustado)
    df["distinguivel_de_ruido"] = df["p_holm"] < 0.05
    return df.round(4)


def limiar_execucoes(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    limiar = json.loads((V7 / "limiar_cosseno.json").read_text(encoding="utf-8"))["limiar_cosseno"]
    cossenos = pd.read_csv(V7 / "cosseno_casos.csv").set_index("id")["cosseno_melhor_trecho"]
    linhas = []
    for m in ("embeddings", "hybrid"):
        d = dados[m]
        # Só chega à busca o que a Camada 3 classificou como normativo.
        chegou = d[d["desfecho"].isin(["resposta", "recusa_sem_base"])]
        recusaria = chegou[chegou["caso_id"].map(cossenos) < limiar]
        for g in ORDEM_GRUPOS + ["norma_ausente_3_validos"]:
            if g == "norma_ausente_3_validos":
                sel = lambda x: x[(x["grupo"] == "norma_ausente") & ~x["caso_id"].isin(PREMISSA_VENCIDA)]  # noqa: E731
            else:
                sel = lambda x, g=g: x[x["grupo"] == g]  # noqa: E731
            linhas.append({"modo": m, "grupo": g, "limiar_cosseno": round(limiar, 6),
                           "execucoes": len(sel(d)), "chegaram_a_busca": len(sel(chegou)),
                           "recusaria": len(sel(recusaria)),
                           "casos_recusados": ", ".join(sorted(sel(recusaria)["caso_id"].unique()))})
    return pd.DataFrame(linhas)


def auditoria(dados: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sugestoes = json.loads(SUGESTOES_FILE.read_text(encoding="utf-8")) if SUGESTOES_FILE.exists() else {}
    respostas_bm25 = {}
    linhas = []
    for m in MODOS:
        d = dados[m]
        for caso_id in d["caso_id"].unique():
            execucoes = d[(d["caso_id"] == caso_id) & (d["resposta_sintetizada"].fillna("") != "")]
            distintas: list[str] = []
            for texto in execucoes["resposta_sintetizada"]:
                if texto not in distintas:
                    distintas.append(texto)
            if m == "bm25":
                respostas_bm25[caso_id] = set(distintas)
            for i, texto in enumerate(distintas, start=1):
                reps = execucoes[execucoes["resposta_sintetizada"] == texto]
                linhas.append({
                    "modo": m,
                    "caso_id": caso_id,
                    "grupo": reps.iloc[0]["grupo"],
                    "repeticoes": ",".join(map(str, reps["repeticao"])),
                    "n_repeticoes": len(reps),
                    "sucesso_automatico": bool(reps["sucesso"].all()),
                    "veredito": "",
                    "padrao": "",
                    "nota": "",
                    "igual_a_bm25": texto in respostas_bm25.get(caso_id, set()),
                    "trechos_recuperados": _top3(reps.iloc[0]),
                    "resposta_sintetizada": texto,
                    "sugestao_veredito_assistente": sugestoes.get(f"{m}|{caso_id}|{i}", ""),
                })
    return pd.DataFrame(linhas)


def _so_comparacao(amostragem: str, base: Path, sufixo: str) -> None:
    """Rodadas extras (sensibilidade, host_127): tabela comparativa e McNemar;
    auditoria e limiar ficam com a rodada de produção."""
    dados = {m: carregar(m, amostragem, base) for m in MODOS}
    comp = comparacao(dados)
    comp.to_csv(V7 / f"comparacao_modos{sufixo}.csv", index=False, encoding="utf-8")
    mc = mcnemar(dados)
    mc.to_csv(V7 / f"mcnemar{sufixo}.csv", index=False, encoding="utf-8")
    colunas = ["modo", "grupo", "acerto_3", "taxa_sucesso_execucoes", "casos_sucesso_total", "n_casos",
               "latencia_busca_mediana_ms", "latencia_resposta_mediana_ms", "latencia_resposta_media_ms"]
    print(comp[colunas].to_string(index=False))
    print(mc.to_string(index=False))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Comparação dos três modos de recuperação (v7).")
    parser.add_argument("--modo", choices=["producao", "sensibilidade"], default="producao")
    parser.add_argument("--pasta", help="subpasta de docs/resultados/v7 (ex: host_127)")
    args = parser.parse_args()
    if args.modo != "producao" or args.pasta:
        sufixo = "".join(f"_{s}" for s in (args.pasta, None if args.modo == "producao" else args.modo) if s)
        _so_comparacao(args.modo, V7 / args.pasta if args.pasta else V7, sufixo)
        raise SystemExit(0)

    dados = {m: carregar(m) for m in MODOS}
    for m, d in dados.items():
        modos_registrados = {r.get("modo") for r in d["recuperacao"] if r}
        assert modos_registrados == {m}, f"{m}: a Camada 8 registrou {modos_registrados}"
    comp = comparacao(dados)
    comp.to_csv(V7 / "comparacao_modos.csv", index=False, encoding="utf-8")
    colunas = ["modo", "grupo", "acerto_3", "recall_3", "mrr_3", "taxa_sucesso_execucoes",
               "casos_sucesso_total", "n_casos", "latencia_busca_mediana_ms", "latencia_resposta_mediana_ms"]
    print(comp[colunas].to_string(index=False))

    mud = casos_mudaram(dados)
    mud.to_csv(V7 / "casos_mudaram_recuperacao.csv", index=False, encoding="utf-8")
    print(f"\n{len(mud)} casos normativos com Acerto@3 diferente entre os modos:")
    print(mud[["caso_id"] + [f"acerto_{m}" for m in MODOS]].to_string(index=False))

    mc = mcnemar(dados)
    mc.to_csv(V7 / "mcnemar.csv", index=False, encoding="utf-8")
    print("\nMcNemar exato (Acerto@3 por caso, normativo_corpus):")
    print(mc.to_string(index=False))

    lim = limiar_execucoes(dados)
    lim.to_csv(V7 / "limiar_cosseno_execucoes.csv", index=False, encoding="utf-8")
    print("\nLimiar de cosseno, execuções que recusaria:")
    print(lim.drop(columns="casos_recusados").to_string(index=False))

    aud = auditoria(dados)
    aud.to_csv(V7 / "auditoria_respostas_v7.csv", index=False, encoding="utf-8")
    print(f"\nAuditoria: {len(aud)} respostas distintas "
          f"({aud.groupby('modo').size().to_dict()}; iguais a uma do bm25: "
          f"{int(aud[aud['modo'] != 'bm25']['igual_a_bm25'].sum())})")
