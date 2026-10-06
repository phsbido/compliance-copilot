"""
Conferência 1a (pós-v6): tamanho dos prompts do benchmark v5 contra a
janela de 4.096 tokens.

O protótipo não grava o prompt_eval_count; o server.log do Ollama registra
os tokens de cada requisição. Este script seleciona, no log copiado para
logs/ollama_server_v5.log (fora do git; SHA-256 db848dfa…), as requisições
da janela de horário da rodada e as casa em ordem com as execuções do JSON:
cada execução faz uma classificação e, se o desfecho foi "resposta", uma
síntese. Ver docs/evidencias_empiricas.md (2026-10-05, Conferência 1).

Uso:
    python scripts/conferencia_tokens_v5.py                  # produção
    python scripts/conferencia_tokens_v5.py --modo sensibilidade
"""
import argparse
import json
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from log_ollama import ler_requisicoes

RAIZ = Path(__file__).resolve().parent.parent
LOG = RAIZ / "logs" / "ollama_server_v5.log"
JSONS = {
    "producao": RAIZ / "docs" / "resultados" / "resultados_benchmark.json",
    "sensibilidade": RAIZ / "docs" / "resultados" / "resultados_benchmark_sensibilidade.json",
}
JANELA = 4096
FUSO = timedelta(hours=-3)  # o log está em horário local (UTC-3); o JSON, em UTC


def janela_da_rodada(execucoes: list[dict]) -> tuple[str, str]:
    """Do início da primeira execução (timestamp menos latência) ao fim da última, em horário local."""
    def local(e, menos_latencia):
        t = datetime.fromisoformat(e["timestamp"]) + FUSO
        if menos_latencia:
            t -= timedelta(milliseconds=float(e["latencia_ms"]) + 1000)
        return t.strftime("%Y/%m/%d %H:%M:%S")
    return local(execucoes[0], True), local(execucoes[-1], False)


def main(modo: str) -> None:
    execucoes = json.load(JSONS[modo].open(encoding="utf-8"))
    inicio, fim = janela_da_rodada(execucoes)
    reqs = [r for r in ler_requisicoes(LOG) if inicio <= r.get("t", "") <= fim]
    print(f"modo {modo}: janela {inicio} – {fim}; {len(reqs)} requisições, {len(execucoes)} execuções")

    i, linhas = 0, []
    for e in execucoes:
        classif = reqs[i]
        i += 1
        sintese = None
        if e["desfecho"] == "resposta":
            sintese = reqs[i]
            i += 1
        linhas.append((e, classif, sintese))
    assert i == len(reqs), f"casamento consumiu {i} de {len(reqs)} requisições"

    cl = [c["n_prompt"] for _, c, _ in linhas]
    sp = [s["n_prompt"] for _, _, s in linhas if s]
    tot = [s["n_total"] for _, _, s in linhas if s]
    print(f"classificação: n={len(cl)}, máx {max(cl)} ({100 * max(cl) / JANELA:.1f}%), mediana {st.median(cl)}")
    print(f"síntese: n={len(sp)}, máx {max(sp)} ({100 * max(sp) / JANELA:.1f}%), "
          f"mediana {st.median(sp)} ({100 * st.median(sp) / JANELA:.1f}%), p95 {sorted(sp)[int(.95 * len(sp))]}")
    print(f"síntese, prompt + geração: máx {max(tot)} ({100 * max(tot) / JANELA:.1f}%)")
    maior = max((s["n_prompt"], e["caso_id"]) for e, _, s in linhas if s)
    print(f"maior prompt: {maior[1]} ({maior[0]})")
    geracao = max(s["n_total"] - s["n_prompt"] for _, _, s in linhas if s)
    print(f"pior caso combinado (maior prompt + maior geração de síntese): {max(sp)} + {geracao} = {max(sp) + geracao}")
    g_cl = max(c["n_total"] - c["n_prompt"] for _, c, _ in linhas)
    print(f"maior geração de classificação: {g_cl} tokens")
    print(f"requisições com truncated = 1: {sum(r.get('trunc', 0) for r in reqs)}; "
          f"com linhas de context shift/truncamento: {sum(1 for r in reqs if 'obs' in r)}")

    por_caso = defaultdict(set)
    for e, _, s in linhas:
        if s:
            por_caso[e["caso_id"]].add(s["n_prompt"])
    divergentes = [k for k, v in por_caso.items() if len(v) > 1]
    print(f"casos com síntese em que o prompt tem o mesmo tamanho nas 3 repetições: "
          f"{len(por_caso) - len(divergentes)} de {len(por_caso)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=list(JSONS), default="producao")
    main(ap.parse_args().modo)
