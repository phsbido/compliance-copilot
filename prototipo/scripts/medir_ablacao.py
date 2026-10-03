"""
Medida offline da ablação da Camada 7 (v6, Tarefa C) — sem LLM.

Aplica `validar_resposta` (a mesma função que as variantes C1 e C2 desligam)
à resposta crua do LLM (`resposta_sintetizada`) e ao contexto guardados no
JSON bruto de cada variante, **só para medir**: nada é gravado de volta nos
JSONs. A medida usa o mesmo validador que foi desligado, então herda os
mesmos limites (verificação lexical; falsos positivos conhecidos, como o
valor citado para ser refutado). A contagem de fontes não oficiais não faz
parte do validador: é uma medida nova, sobre URLs e domínios citados na
resposta que não são do BCB.

Variantes: v5 (Camada 7 ligada, linha de base), C1 (sem validar_resposta),
C2 (sem validar_resposta e sem POLITICA_SINTESE).

Saídas:
  docs/resultados/ablacao_medida_offline.csv          — variante x métrica
  docs/resultados/ablacao_medida_offline_por_grupo.csv
  docs/resultados/ablacao_amostra_auditoria.csv        — respostas que mudaram
      em relação ao v5, para auditoria manual (amostra com seed registrada)

Uso (dentro de prototipo/):
    python scripts/medir_ablacao.py
"""
import json
import random
import re
import sys
import urllib.parse
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.layer7_governance.governance import DOMINIOS_FONTES_PUBLICAS, validar_resposta  # noqa: E402

RESULTADOS = RAIZ / "docs" / "resultados"
VARIANTES = {
    "v5": RESULTADOS / "resultados_benchmark.json",
    "C1": RESULTADOS / "ablacao_c1" / "resultados_benchmark.json",
    "C2": RESULTADOS / "ablacao_c2" / "resultados_benchmark.json",
}
AUDITORIA_V5 = RAIZ / "docs" / "auditoria_respostas_v5.csv"
SAIDA = RESULTADOS / "ablacao_medida_offline.csv"
SAIDA_GRUPO = RESULTADOS / "ablacao_medida_offline_por_grupo.csv"
SAIDA_AMOSTRA = RESULTADOS / "ablacao_amostra_auditoria.csv"
SEED_AMOSTRA = 20261002
MAX_AMOSTRA_POR_VARIANTE = 40

_URL = re.compile(r"\b(?:https?://|www\.)[^\s)\]>\"']+", re.IGNORECASE)


def fontes_nao_oficiais(texto: str) -> list[str]:
    """URLs citadas na resposta cujo domínio não é do BCB."""
    fora = []
    for url in _URL.findall(texto or ""):
        host = urllib.parse.urlparse(url if "://" in url else f"https://{url}").hostname or ""
        if host.lower().rstrip(".") not in DOMINIOS_FONTES_PUBLICAS:
            fora.append(url)
    return fora


def medir(execucoes: list[dict]) -> pd.DataFrame:
    linhas = []
    for r in execucoes:
        sintese = r.get("resposta_sintetizada") or ""
        linha = {"caso_id": r["caso_id"], "grupo": r["grupo"], "repeticao": r["repeticao"],
                 "com_sintese": bool(sintese), "recusou": r["recusou"], "desfecho": r["desfecho"]}
        if sintese:
            c = validar_resposta(sintese, r["contexto_normativo"]).categorias()
            fontes = fontes_nao_oficiais(sintese)
            linha.update(
                normas_nao_verificadas=len(c["normas_nao_verificadas"]),
                artigos_divergentes=len(c["artigos_nao_verificados"]) + len(c["artigos_fora_da_norma"]),
                valores_divergentes=len(c["valores_nao_verificados"]),
                fontes_nao_oficiais=len(fontes),
                possui_aviso=c["possui_aviso"],
                ausencia_declarada=bool(c["normas_declaradas_ausentes"]),
            )
        linhas.append(linha)
    return pd.DataFrame(linhas)


def resumir(df: pd.DataFrame) -> dict:
    s = df[df["com_sintese"]]
    return {
        "execucoes": len(df),
        "execucoes_com_sintese": len(s),
        "recusas": int(df["recusou"].sum()),
        "exec_com_norma_nao_verificada": int((s["normas_nao_verificadas"] > 0).sum()),
        "normas_nao_verificadas": int(s["normas_nao_verificadas"].sum()),
        "exec_com_artigo_divergente": int((s["artigos_divergentes"] > 0).sum()),
        "artigos_divergentes": int(s["artigos_divergentes"].sum()),
        "exec_com_valor_divergente": int((s["valores_divergentes"] > 0).sum()),
        "valores_divergentes": int(s["valores_divergentes"].sum()),
        "exec_com_fonte_nao_oficial": int((s["fontes_nao_oficiais"] > 0).sum()),
        "exec_com_algum_aviso": int(s["possui_aviso"].sum()),
        "taxa_exec_com_algum_aviso": round(float(s["possui_aviso"].mean()), 3) if len(s) else None,
    }


def amostra_auditoria(dados: dict[str, list[dict]]) -> pd.DataFrame:
    """Respostas distintas de C1 e C2 que não aparecem entre as respostas do
    v5 para o mesmo caso; até MAX_AMOSTRA_POR_VARIANTE por variante,
    estratificadas por grupo, com seed fixa."""
    v5_por_caso: dict[str, set[str]] = {}
    for r in dados["v5"]:
        v5_por_caso.setdefault(r["caso_id"], set()).add(r.get("resposta_sintetizada") or "")
    vereditos_v5 = pd.read_csv(AUDITORIA_V5).groupby("caso_id")["veredito"].apply(
        lambda v: ", ".join(sorted(set(v)))).to_dict()
    rng = random.Random(SEED_AMOSTRA)
    linhas = []
    for variante in ("C1", "C2"):
        distintas: dict[tuple[str, str], dict] = {}
        for r in dados[variante]:
            s = r.get("resposta_sintetizada") or ""
            if not s or s in v5_por_caso.get(r["caso_id"], set()):
                continue
            chave = (r["caso_id"], s)
            if chave not in distintas:
                distintas[chave] = {**r, "repeticoes": []}
            distintas[chave]["repeticoes"].append(r["repeticao"])
        candidatas = list(distintas.values())
        if len(candidatas) > MAX_AMOSTRA_POR_VARIANTE:
            por_grupo: dict[str, list[dict]] = {}
            for c in candidatas:
                por_grupo.setdefault(c["grupo"], []).append(c)
            escolhidas = []
            for grupo in sorted(por_grupo):
                cota = round(MAX_AMOSTRA_POR_VARIANTE * len(por_grupo[grupo]) / len(candidatas))
                escolhidas += rng.sample(por_grupo[grupo], min(cota, len(por_grupo[grupo])))
            candidatas = escolhidas
        for c in candidatas:
            fontes = fontes_nao_oficiais(c["resposta_sintetizada"])
            cat = validar_resposta(c["resposta_sintetizada"], c["contexto_normativo"]).categorias()
            linhas.append({
                "variante": variante, "caso_id": c["caso_id"], "grupo": c["grupo"],
                "repeticoes": ",".join(map(str, c["repeticoes"])),
                "n_candidatas_da_variante": len(distintas),
                "vereditos_v5_do_caso": vereditos_v5.get(c["caso_id"], "(sem síntese no v5)"),
                "trechos_no_contexto": "\n".join(re.findall(r"^\[(.+)\]$", c["contexto_normativo"] or "", re.M)),
                "resposta_sintetizada": c["resposta_sintetizada"],
                "medida_offline_aviso": cat["possui_aviso"],
                "medida_offline_detalhe": json.dumps({k: v for k, v in cat.items() if v and k != "possui_aviso"},
                                                     ensure_ascii=False),
                "fontes_nao_oficiais": "; ".join(fontes),
                "AUDITOR_veredito": "", "AUDITOR_comentario": "",
                "contexto_normativo_completo": c["contexto_normativo"],
            })
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    dados = {v: json.loads(p.read_text(encoding="utf-8")) for v, p in VARIANTES.items()}
    medidas = {v: medir(execs) for v, execs in dados.items()}

    # Sanidade: no v5, a medida offline reproduz o que a Camada 7 registrou.
    v5 = medidas["v5"]
    registrado = sum(bool(r["validacao"].get("possui_aviso")) for r in dados["v5"] if r.get("resposta_sintetizada"))
    assert int(v5[v5["com_sintese"]]["possui_aviso"].sum()) == registrado, "medida offline diverge do v5 registrado"

    resumo = pd.DataFrame([{"variante": v, **resumir(m)} for v, m in medidas.items()])
    resumo.to_csv(SAIDA, index=False, encoding="utf-8")
    por_grupo = pd.DataFrame([{"variante": v, "grupo": g, **resumir(m[m["grupo"] == g])}
                              for v, m in medidas.items() for g in m["grupo"].unique()])
    por_grupo.to_csv(SAIDA_GRUPO, index=False, encoding="utf-8")
    amostra = amostra_auditoria(dados)
    amostra.to_csv(SAIDA_AMOSTRA, index=False, encoding="utf-8")

    print("Medida offline (validar_resposta aplicado à resposta crua; o mesmo validador desligado em C1/C2):\n")
    print(resumo.set_index("variante").T.to_string())
    print(f"\nAmostra para auditoria: {len(amostra)} respostas "
          f"({amostra.groupby('variante').size().to_dict()}); seed {SEED_AMOSTRA}")
    print(f"Salvos: {SAIDA}, {SAIDA_GRUPO}, {SAIDA_AMOSTRA}")
