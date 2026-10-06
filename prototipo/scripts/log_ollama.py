"""
Leitura do server.log do Ollama (0.33.2): uma entrada por requisição ao
llama-server, com os tokens do prompt, o total no fim da geração e os sinais
de truncamento.

Campos de cada requisição:
  task      — id da tarefa no llama-server;
  ctx       — n_ctx_slot (janela de contexto);
  n_prompt  — task.n_tokens (tokens do prompt);
  n_total   — n_tokens no fim da geração (no cache: prompt + gerados − 1,
              porque o último token amostrado não entra no cache);
  n_gerados — tokens gerados ("eval time = ... / N tokens");
  trunc     — "truncated" no fim da geração (1 = houve context shift);
  obs       — linhas da tarefa que mencionam context shift ou truncamento;
  t         — horário local do POST /api/chat|generate correspondente;
  line      — linha do log onde a requisição começa.

O Ollama também registra "truncating input prompt" (prompt maior que a
janela, cortado antes da inferência) fora das linhas da tarefa; essas
linhas são contadas à parte em `truncamentos_de_entrada`.

Uso (resumo de um log):
    python scripts/log_ollama.py logs/ollama_server_v5.log
"""
import re
import sys


def ler_requisicoes(caminho) -> list[dict]:
    linhas = open(caminho, encoding="utf-8", errors="replace").read().splitlines()
    reqs, vivas, pendentes = [], {}, []
    for i, l in enumerate(linhas):
        if "starting llama-server" in l:
            vivas = {}
        m = re.search(r"task (\d+) \| new prompt, n_ctx_slot = (\d+).*task.n_tokens = (\d+)", l)
        if m:
            r = dict(task=int(m[1]), ctx=int(m[2]), n_prompt=int(m[3]), line=i + 1)
            reqs.append(r)
            vivas[r["task"]] = r
            pendentes.append(r)
            continue
        m = re.search(r"task (\d+) \|\s+eval time =.*/\s*(\d+) tokens", l)
        if m and int(m[1]) in vivas:
            vivas[int(m[1])]["n_gerados"] = int(m[2])
            continue
        m = re.search(r"task (\d+) \| stop processing: n_tokens = (\d+), truncated = (\d+)", l)
        if m and int(m[1]) in vivas:
            vivas[int(m[1])].update(n_total=int(m[2]), trunc=int(m[3]))
            continue
        m = re.search(r"task (\d+) \|.*(context shift|truncat)", l, re.I)
        if m and int(m[1]) in vivas:
            vivas[int(m[1])].setdefault("obs", []).append(l.strip()[:200])
        m = re.search(r"\[GIN\] (\S+) - (\S+) \|.*POST\s+\"/api/(chat|generate)\"", l)
        if m and pendentes:
            pendentes.pop(0)["t"] = m[1] + " " + m[2]
    return reqs


def truncamentos_de_entrada(caminho) -> list[str]:
    return [l.strip() for l in open(caminho, encoding="utf-8", errors="replace")
            if "truncating input prompt" in l]


if __name__ == "__main__":
    caminho = sys.argv[1]
    reqs = ler_requisicoes(caminho)
    print(f"{len(reqs)} requisições; sem n_total: {sum(1 for r in reqs if 'n_total' not in r)}; "
          f"sem horário: {sum(1 for r in reqs if 't' not in r)}")
    print(f"maior prompt: {max(r['n_prompt'] for r in reqs)}; "
          f"maior prompt + geração: {max(r.get('n_total', 0) for r in reqs)}")
    print(f"com truncated = 1 (context shift): {sum(r.get('trunc', 0) for r in reqs)}; "
          f"com linhas de context shift/truncamento: {sum(1 for r in reqs if 'obs' in r)}")
    print(f"prompts truncados na entrada: {len(truncamentos_de_entrada(caminho))}")
