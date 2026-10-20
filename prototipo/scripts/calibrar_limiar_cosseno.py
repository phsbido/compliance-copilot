"""
Calibração do limiar de cosseno da Camada 5 (v7) — sem LLM.

Mesmo conjunto (tests/calibracao_limiar.json) e mesmo critério da v6, agora
sobre o cosseno do melhor trecho do corpus no índice de embeddings,
pré-registrados em docs/decisoes_arquitetura.md ("Camada 5: embeddings e
busca híbrida", commit anterior a este cálculo):

    limiar = cosseno da (k+1)-ésima menor pergunta respondível,
    k = floor(0,05 × n_respondiveis); recusa = cosseno < limiar

A taxa de recusa das perguntas sem resposta é consequência, não critério, e
sai em três versões declaradas antes do cálculo: as 20; sem as 3 cuja norma
entrou no corpus em 2026-10-12; e sem essas 3 mais as 2 que talvez tenham
resposta nas normas novas. O mesmo limiar é aplicado, offline, aos 66 casos
de tests/casos_teste.json (cosseno do melhor trecho por caso; a contagem por
execução, que depende da classificação da Camada 3, sai em
scripts/comparar_v7.py). O limiar não é ativado (LIMIAR_COSSENO vazio).

Saídas: docs/resultados/v7/calibracao_limiar_cosseno.csv (40 perguntas) e
docs/resultados/v7/cosseno_casos.csv (66 casos), e o resumo no terminal.

Uso (dentro de prototipo/):
    python scripts/calibrar_limiar_cosseno.py
"""
import json
import math
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from run_benchmark import TOP_K, carregar_casos, metricas_recuperacao  # noqa: E402
from src.layer5_knowledge.knowledge_base import KnowledgeBase  # noqa: E402

CONJUNTO = RAIZ / "tests" / "calibracao_limiar.json"
SAIDA_DIR = RAIZ / "docs" / "resultados" / "v7"
TAXA_MAXIMA_RECUSA_INDEVIDA = 0.05
# Declaradas no pré-registro, antes do cálculo.
NORMA_ENTROU_NO_CORPUS = {"cal_s04", "cal_s09", "cal_s12"}
TALVEZ_COM_RESPOSTA = {"cal_s15", "cal_s17"}


def pontuar(kb: KnowledgeBase, perguntas: list[dict], campos: tuple[str, ...]) -> pd.DataFrame:
    linhas = []
    for p in perguntas:
        pontuados = kb.buscar_pontuado(p["pergunta"], top_k=TOP_K)
        recuperados = [{"norma": d.titulo, "trecho": d.identificador} for _, d in pontuados]
        linhas.append({
            **{c: p.get(c, "") for c in campos},
            "pergunta": p["pergunta"],
            "cosseno_melhor_trecho": round(pontuados[0][0], 6),
            "melhor_trecho": f"{recuperados[0]['norma'].split(',')[0]} {recuperados[0]['trecho']}",
            "relevante_entre_os_3": metricas_recuperacao(recuperados, p.get("relevantes") or [])["acerto_recuperacao"],
        })
    return pd.DataFrame(linhas)


def limiar_pelo_criterio(cossenos_respondiveis: list[float]) -> tuple[float, int]:
    ordenados = sorted(cossenos_respondiveis)
    k = math.floor(TAXA_MAXIMA_RECUSA_INDEVIDA * len(ordenados))
    return ordenados[k], k


if __name__ == "__main__":
    kb = KnowledgeBase(modo="embeddings")
    conjunto = json.loads(CONJUNTO.read_text(encoding="utf-8"))
    df = pontuar(kb, conjunto["perguntas"], ("id", "grupo", "subgrupo"))
    resp = df[df["grupo"] == "respondivel"]
    sem = df[df["grupo"] == "sem_resposta"]

    limiar, k = limiar_pelo_criterio(resp["cosseno_melhor_trecho"].tolist())
    df["recusada_no_limiar"] = df["cosseno_melhor_trecho"] < limiar
    df["premissa"] = df["id"].map(lambda i: "norma_entrou_no_corpus" if i in NORMA_ENTROU_NO_CORPUS
                                  else "talvez_com_resposta" if i in TALVEZ_COM_RESPOSTA else "")
    SAIDA_DIR.mkdir(parents=True, exist_ok=True)
    df.sort_values(["grupo", "cosseno_melhor_trecho"]).to_csv(
        SAIDA_DIR / "calibracao_limiar_cosseno.csv", index=False, encoding="utf-8")

    print(f"Modelo: {kb.identificacao()}")
    print(f"Conjunto {conjunto['versao']}: {len(resp)} respondíveis, {len(sem)} sem resposta\n")
    print(df.groupby("grupo")["cosseno_melhor_trecho"].describe().round(4).to_string())
    print(f"\nCritério pré-registrado: k = floor({TAXA_MAXIMA_RECUSA_INDEVIDA} x {len(resp)}) = {k}; "
          f"limiar = {k + 1}ª menor respondível = {limiar:.6f}")
    print(f"  respondíveis recusadas: {int((resp['cosseno_melhor_trecho'] < limiar).sum())}/{len(resp)}")
    for nome, excluir in (("as 20", set()), ("sem as 3 cuja norma entrou", NORMA_ENTROU_NO_CORPUS),
                          ("sem as 3 + 2 talvez com resposta", NORMA_ENTROU_NO_CORPUS | TALVEZ_COM_RESPOSTA)):
        g = sem[~sem["id"].isin(excluir)]
        print(f"  sem resposta recusadas ({nome}): {int((g['cosseno_melhor_trecho'] < limiar).sum())}/{len(g)}")

    casos = carregar_casos()
    dc = pontuar(kb, casos, ("id", "grupo"))
    dc["recusado_no_limiar"] = dc["cosseno_melhor_trecho"] < limiar
    dc.to_csv(SAIDA_DIR / "cosseno_casos.csv", index=False, encoding="utf-8")
    print("\nNos 66 casos (por caso; cada caso = 3 execuções, se classificado como normativo):")
    print(dc.groupby("grupo")["recusado_no_limiar"].agg(["sum", "count"]).to_string())
    json.dump({"limiar_cosseno": limiar, "k": k, "modelo": kb.identificacao()},
              (SAIDA_DIR / "limiar_cosseno.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=2)
