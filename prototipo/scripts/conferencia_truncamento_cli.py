"""
Conferência 1b (pós-v6): o que o Ollama descarta numa conversa de 5 turnos
pela CLI quando o prompt passa da janela de 4.096 tokens.

Reconstrói o prompt de síntese de cada turno da conversa de 2026-10-05
(memória com a resposta sintetizada, buscar_normativo determinístico e
template do llama3.1), tokeniza no próprio llama-server e compara com o
task.n_tokens do log. Nos turnos truncados, mostra o trecho mantido e o
descartado, como o Ollama 0.33.2 faz:
  - prompt acima da janela: mantém os 4 primeiros tokens e os últimos
    2.046 (limit=2050) e descarta o meio, antes da inferência;
  - prompt abaixo, mas prompt + geração acima: context shift na geração
    (n_keep = 5, n_discard = 2045).
Ver docs/evidencias_empiricas.md (2026-10-05, Conferência 1).

Entradas (fora do git, em logs/): interacoes.jsonl, filtrado pelo horário
da conversa, e ollama_server_conferencia_contexto.log. Saída: os textos
mantido e descartado de cada turno truncado em
logs/conferencia_truncamento/turno{N}.json.

Precisa do Ollama 0.33.2 rodando com o llama3.1. Sem --porta, o script
carrega o modelo (POST /api/generate sem prompt, que não gera nada) e lê a
porta do llama-server no server.log do Ollama.

Uso:
    python scripts/conferencia_truncamento_cli.py [--porta N]
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from src.layer4_tools.tools import buscar_normativo  # noqa: E402
from src.layer6_memory.memory import Memoria  # noqa: E402
from src.layer7_governance.governance import POLITICA_SINTESE  # noqa: E402

from log_ollama import ler_requisicoes, truncamentos_de_entrada  # noqa: E402

INTERACOES = RAIZ / "logs" / "interacoes.jsonl"
LOG_CONVERSA = RAIZ / "logs" / "ollama_server_conferencia_contexto.log"
SAIDA = RAIZ / "logs" / "conferencia_truncamento"
INICIO, FIM = "2026-10-05T23:52", "2026-10-05T23:55"  # UTC (20:52–20:55 local)
LIMITE_ENTRADA, MANTIDOS_INICIO = 2050, 4  # "truncating input prompt limit=2050 ... keep=4"
SHIFT_KEEP, SHIFT_DISCARD = 5, 2045  # context shift da geração no turno 3
SERVER_LOG = Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama" / "server.log"


def porta_do_llama_server() -> int:
    req = urllib.request.Request("http://localhost:11434/api/generate",
                                 json.dumps({"model": "llama3.1"}).encode(),
                                 {"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
    portas = re.findall(r"starting llama-server.*?--port (\d+)", SERVER_LOG.read_text(encoding="utf-8", errors="replace"))
    return int(portas[-1])


def main(porta: int) -> None:
    def post(ep, d):
        req = urllib.request.Request(f"http://127.0.0.1:{porta}/{ep}", json.dumps(d).encode(),
                                     {"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req).read())

    def tok(s, especiais=True):
        return post("tokenize", {"content": s, "add_special": especiais, "parse_special": True})["tokens"]

    def detok(t):
        return post("detokenize", {"tokens": t})["content"]

    def sintetizada(final):
        cortes = [final.find(m) for m in ("\n\nAviso:", "\n\nFontes consultadas:") if final.find(m) >= 0]
        return final[:min(cortes)] if cortes else final

    turnos = [json.loads(l) for l in INTERACOES.open(encoding="utf-8")]
    turnos = [t for t in turnos if INICIO <= t["timestamp"] < FIM]
    assert len(turnos) == 5, f"{len(turnos)} interações na janela da conversa"
    sinteses = [r for r in ler_requisicoes(LOG_CONVERSA) if r["n_prompt"] >= 400]  # classificações têm < 200
    assert len(sinteses) == 5, f"{len(sinteses)} sínteses no log"
    truncados = truncamentos_de_entrada(LOG_CONVERSA)
    print("truncamentos de entrada no log:")
    for l in truncados:
        print("  ", l[l.find("msg="):][:120])
    # nos turnos truncados, o task.n_tokens já é o prompt cortado; o tamanho original está no "prompt="
    originais = [int(re.search(r"prompt=(\d+)", l)[1]) for l in truncados]
    SAIDA.mkdir(parents=True, exist_ok=True)

    mem = Memoria()
    for i, r in enumerate(turnos, start=1):
        hist = mem.contexto_formatado()
        normativo = buscar_normativo(r["pergunta"])
        partes = ([f"Histórico da conversa nesta sessão:\n{hist}"] if hist else []) + \
                 [f"Contexto normativo: {normativo}", f"Pergunta: {r['pergunta']}"]
        sistema = "<|start_header_id|>system<|end_header_id|>\n\n" + POLITICA_SINTESE + "<|eot_id|>"
        prompt = (sistema + "<|start_header_id|>user<|end_header_id|>\n\n" + "\n\n".join(partes)
                  + "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n")
        T = tok(prompt)
        n = len(T)
        s = sinteses[i - 1]
        n_sis = len(tok(sistema))
        n_hist = len(tok(partes[0], False)) if hist else 0
        n_ctx, n_perg = len(tok(partes[-2], False)), len(tok(partes[-1], False))
        ini_hist = len(tok(prompt[:prompt.find("Histórico da conversa")])) if hist else None
        ini_ctx = len(tok(prompt[:prompt.find("Contexto normativo:")]))
        n_log = originais.pop(0) if s["n_prompt"] == LIMITE_ENTRADA and originais else s["n_prompt"]
        geracao = s["n_gerados"]
        print(f"\nturno {i}: reconstruído {n}, log {n_log} | sistema ~{n_sis}, histórico ~{n_hist}, "
              f"contexto ~{n_ctx}, pergunta ~{n_perg} | geração ~{geracao}, truncated = {s.get('trunc')}")
        if n > LIMITE_ENTRADA + 1 and n > 4096:
            fim_desc = n - (LIMITE_ENTRADA - MANTIDOS_INICIO)
            mantido, descartado = detok(T[fim_desc:]), detok(T[MANTIDOS_INICIO:fim_desc])
            print(f"  prompt truncado na entrada: descartados {fim_desc - MANTIDOS_INICIO} tokens "
                  f"[{MANTIDOS_INICIO}:{fim_desc}); histórico mantido = {ini_ctx - fim_desc} de {ini_ctx - ini_hist}")
            print(f"  sistema sobrevive? {'Regras obrigatórias' in mantido} | contexto normativo inteiro? "
                  f"{'Contexto normativo:' in mantido}")
        elif s.get("trunc"):
            fim_desc = SHIFT_KEEP + SHIFT_DISCARD
            mantido, descartado = detok(T[fim_desc:]), detok(T[SHIFT_KEEP:fim_desc])
            print(f"  context shift na geração: descartadas as posições {SHIFT_KEEP}–{fim_desc - 1}; "
                  f"o contexto normativo começa no token {ini_ctx}")
            print(f"  descartado termina com: {descartado[-160:]!r}")
            print(f"  mantido começa com: {mantido[:160]!r}")
        else:
            mantido = descartado = None
        if mantido is not None:
            with (SAIDA / f"turno{i}.json").open("w", encoding="utf-8") as f:
                json.dump({"turno": i, "mantido": mantido, "descartado": descartado}, f, ensure_ascii=False)
        mem.adicionar(r["pergunta"], sintetizada(r["resposta_final"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, help="porta do llama-server (padrão: carrega o modelo e lê do server.log)")
    a = ap.parse_args()
    main(a.porta or porta_do_llama_server())
