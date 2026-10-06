"""
Planilha de conferência, pelo autor, dos vereditos da auditoria v5.

Junta, para cada resposta distinta de docs/auditoria_respostas_v5.csv
(gerado por scripts/auditoria_v5.py), a pergunta, o rótulo de recuperação,
os trechos e o contexto recuperados e a resposta sintetizada do benchmark
v5 em modo produção. As colunas AUTOR_* saem vazias, para o autor
preencher. Linhas ordenadas por veredito do assistente (incorreta, parcial,
abstenção, recusa, correta) e, dentro de cada um, pela linha da auditoria.

Saída: docs/conferencia_vereditos_v5.csv (UTF-8 com BOM, separador ";",
para abrir no Excel em português).

ATENÇÃO: rodar de novo sobrescreve as colunas AUTOR_* já preenchidas.

Uso:
    python scripts/conferencia_vereditos_v5.py
"""
import csv
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JSON_ENTRADA = RAIZ / "docs" / "resultados" / "resultados_benchmark.json"
CASOS = RAIZ / "tests" / "casos_teste.json"
AUDITORIA = RAIZ / "docs" / "auditoria_respostas_v5.csv"
CSV_SAIDA = RAIZ / "docs" / "conferencia_vereditos_v5.csv"

ORDEM_VEREDITOS = ["incorreta", "parcial", "abstencao", "recusa_modelo", "correta"]
COLUNAS = [
    "ordem", "linha_csv_auditoria", "caso_id", "grupo", "repeticoes", "n_execucoes", "pergunta",
    "trechos_relevantes_rotulo", "trechos_no_contexto", "relevante_recuperado", "sucesso_automatico",
    "aviso_camada7", "veredito_assistente", "padrao_assistente", "nota_assistente", "resposta_sintetizada",
    "AUTOR_concorda (S/N)", "AUTOR_veredito", "AUTOR_padrao", "AUTOR_comentario", "contexto_normativo_completo",
]
RECUPERADO = {"True": "sim", "False": "não", "None": "n/a"}


def gerar() -> list[dict]:
    with JSON_ENTRADA.open(encoding="utf-8") as f:
        resultados = [r for r in json.load(f) if r["modo"] == "producao"]
    with CASOS.open(encoding="utf-8") as f:
        casos = {c["id"]: c for c in json.load(f)["casos"]}
    with AUDITORIA.open(encoding="utf-8", newline="") as f:
        auditoria = list(csv.DictReader(f))

    linhas = []
    for n, a in enumerate(auditoria, start=2):  # linha 1 do CSV é o cabeçalho
        reps = a["repeticoes"].split(",")
        execucoes = [r for r in resultados if r["caso_id"] == a["caso_id"] and str(r["repeticao"]) in reps]
        e = execucoes[0]
        caso = casos[a["caso_id"]]
        rotulo = "; ".join(f"{t['norma']} {t['trecho']}" for t in caso.get("relevantes") or [])
        linhas.append({
            "linha_csv_auditoria": n,
            "caso_id": a["caso_id"],
            "grupo": a["grupo"],
            "repeticoes": a["repeticoes"],
            "n_execucoes": a["n_repeticoes"],
            "pergunta": caso["pergunta"],
            "trechos_relevantes_rotulo": rotulo or "(sem rótulo)",
            "trechos_no_contexto": "\n".join(re.findall(r"^\[(.+)\]$", e["contexto_normativo"], re.M)),
            "relevante_recuperado": RECUPERADO[str(e["acerto_recuperacao"])],
            "sucesso_automatico": a["sucesso_automatico"],
            "aviso_camada7": "sim" if any(str(r["aviso_camada7"]) == "True" for r in execucoes) else "não",
            "veredito_assistente": a["veredito"],
            "padrao_assistente": a["padrao"],
            "nota_assistente": a["nota"],
            "resposta_sintetizada": e["resposta_sintetizada"],
            "AUTOR_concorda (S/N)": "", "AUTOR_veredito": "", "AUTOR_padrao": "", "AUTOR_comentario": "",
            "contexto_normativo_completo": e["contexto_normativo"],
        })
    linhas.sort(key=lambda l: (ORDEM_VEREDITOS.index(l["veredito_assistente"]), l["linha_csv_auditoria"]))
    for i, l in enumerate(linhas, start=1):
        l["ordem"] = i
    return linhas


if __name__ == "__main__":
    linhas = gerar()
    with CSV_SAIDA.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} respostas distintas; salvo em {CSV_SAIDA}")
