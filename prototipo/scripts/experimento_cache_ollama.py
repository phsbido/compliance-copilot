"""
Diagnóstico v5 (Fase 1), item 2: divergência da repetição 1 no modo produção.

Hipótese: a repetição 1 difere porque o prompt de síntese é calculado do zero
(em lotes de 512 tokens), enquanto nas repetições 2 e 3 o llama-server o
recupera do cache de prompts e reavalia só o último token. Análise em
docs/diagnostico_falhas_v5.md, Seção 3.

Condições (4 casos, mesmo caminho do benchmark: run_benchmark.rodar_caso):
  E0 reprodução: servidor reiniciado uma vez; 3 repetições seguidas por caso.
  E1 ordem alterada: servidor reiniciado uma vez; casos em ordem inversa e
     intercalados (rep 1 de todos, depois rep 2 de todos, depois rep 3).
  E2 aquecimento: servidor reiniciado uma vez; por caso, uma execução de
     aquecimento descartada e depois 3 repetições.
  E3 reinício entre chamadas: servidor reiniciado antes de cada execução.

ATENÇÃO: encerra os processos ollama.exe e llama-server.exe (Windows) e sobe
um `ollama serve` próprio, para poder reiniciá-lo entre chamadas. O log do
servidor vai para logs/ e é lido no fim para registrar, por chamada, quantos
tokens do prompt vieram do cache.

Uso (dentro de prototipo/, com o venv ativado; ~15 min):
    python scripts/experimento_cache_ollama.py
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROTO))
os.chdir(PROTO)

import ollama  # noqa: E402
import run_benchmark as rb  # noqa: E402
import src.layer8_observability.observability as obs  # noqa: E402
from src.layer7_governance.governance import POLITICA_SINTESE  # noqa: E402

obs.LOG_FILE = PROTO / "logs" / "interacoes_experimento_cache.jsonl"  # fora do log normal
LOG_SERVIDOR = PROTO / "logs" / "ollama_serve_experimento_cache.log"
SAIDA = PROTO / "docs" / "resultados" / "diagnostico_v5_experimento_cache.json"

CASOS = ["rc1_prazo_revogacao", "in759_vigencia", "ausente_circ_3978_pld", "rc1_prazo_adesao"]
with (PROTO / "tests" / "casos_teste.json").open(encoding="utf-8") as f:
    casos = {c["id"]: c for c in json.load(f)["casos"]}
with (PROTO / "docs" / "resultados" / "resultados_benchmark.json").open(encoding="utf-8") as f:
    bench = {(r["caso_id"], r["repeticao"]): r["resposta_sintetizada"] for r in json.load(f)}


def parar():
    subprocess.run(["taskkill", "/F", "/T", "/IM", "ollama.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/T", "/IM", "llama-server.exe"], capture_output=True)
    time.sleep(2)


def iniciar():
    subprocess.Popen(["ollama", "serve"], stdout=LOG_SERVIDOR.open("a", encoding="utf-8"),
                     stderr=subprocess.STDOUT)
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/version", timeout=1)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Ollama não subiu")


def reiniciar():
    parar()
    iniciar()


# Captura a chamada de síntese (opções enviadas e contagens do servidor).
_chat_original = ollama.chat
ultima_sintese = {}


def chat_instrumentado(*args, **kwargs):
    resp = _chat_original(*args, **kwargs)
    msgs = kwargs.get("messages") or []
    if msgs and msgs[0].get("content") == POLITICA_SINTESE:
        ultima_sintese.clear()
        # prompt_eval_count do Ollama é o total do prompt, não os tokens
        # avaliados; estes vêm do log do servidor (anotar_cache).
        ultima_sintese.update(options=kwargs.get("options"), eval_count=resp.eval_count,
                              prompt_eval_ms=round(resp.prompt_eval_duration / 1e6, 1))
    return resp


ollama.chat = chat_instrumentado


def executar(cond, caso_id, rotulo):
    ultima_sintese.clear()
    r = rb.rodar_caso(casos[caso_id], 0, "producao")
    s = r["resposta_sintetizada"]
    igual = "rep1" if s == bench[(caso_id, 1)] else "rep2/3" if s == bench[(caso_id, 2)] else "nova"
    print(f"{cond} {caso_id:28} {rotulo:12} -> {igual}", flush=True)
    return {"condicao": cond, "caso_id": caso_id, "execucao": rotulo, "igual_a_benchmark": igual,
            **ultima_sintese, "latencia_ms": r["latencia_ms"], "resposta": s}


def anotar_cache(resultados):
    """Casa cada síntese com o registro do llama-server: tamanho do prefixo
    reaproveitado do cache de prompts e tokens efetivamente avaliados."""
    tarefas, atual = [], None
    for linha in LOG_SERVIDOR.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"task (\d+) \| new prompt, .*task.n_tokens = (\d+)", linha)
        if m:
            atual = {"n_tokens": int(m.group(2)), "cached": [], "avaliados": None}
            tarefas.append(atual)
            continue
        if atual is None:
            continue
        m = re.search(r"cached n_tokens = (\d+)", linha)
        if m:
            atual["cached"].append(int(m.group(1)))
        m = re.search(r"prompt eval time =\s+[\d.]+ ms /\s+(\d+) tokens", linha)
        if m:
            atual["avaliados"] = int(m.group(1))
    sinteses = [t for t in tarefas if t["n_tokens"] > 400]  # a classificação tem ~130 tokens
    assert len(sinteses) == len(resultados), (len(sinteses), len(resultados))
    for r, t in zip(resultados, sinteses):
        r.update(n_tokens_prompt=t["n_tokens"], prefixo_do_cache=t["cached"][0] if t["cached"] else 0,
                 fronteiras_lote=t["cached"], tokens_avaliados=t["avaliados"])


def main():
    LOG_SERVIDOR.parent.mkdir(exist_ok=True)
    LOG_SERVIDOR.write_text("", encoding="utf-8")
    resultados = []
    reiniciar()  # E0
    for c in CASOS:
        for rep in (1, 2, 3):
            resultados.append(executar("E0", c, f"rep{rep}"))
    reiniciar()  # E1
    for rep in (1, 2, 3):
        for c in reversed(CASOS):
            resultados.append(executar("E1", c, f"rep{rep}"))
    reiniciar()  # E2
    for c in CASOS:
        resultados.append(executar("E2", c, "aquecimento"))
        for rep in (1, 2, 3):
            resultados.append(executar("E2", c, f"rep{rep}"))
    for c in CASOS:  # E3
        for rep in (1, 2, 3):
            reiniciar()
            resultados.append(executar("E3", c, f"rep{rep}"))
    parar()
    anotar_cache(resultados)
    with SAIDA.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
