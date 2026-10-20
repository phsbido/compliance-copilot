"""
Rodadas v7 do benchmark: os três modos de recuperação da Camada 5 (bm25,
embeddings, hybrid), com o protocolo da v6 (docs/decisoes_arquitetura.md,
"Camada 5: embeddings e busca híbrida").

Para cada modo: encerra os processos do Ollama (inclusive o app, cujo
atualizador instalaria outra versão), sobe um `ollama serve` próprio, roda
`run_benchmark.py --saida docs/resultados/v7/<modo>[_sensibilidade]` com
RECUPERACAO_MODO=<modo> e grava, na pasta da rodada, a hora de início e fim,
a versão do Ollama, a saída de `ollama ps` e o resumo do `nvidia-smi` (sem a
tabela de processos da máquina) logo depois da
rodada (com os modelos ainda carregados).

ATENÇÃO: encerra ollama.exe, "ollama app.exe" e llama-server.exe (Windows).

Uso (dentro de prototipo/):
    python scripts/rodar_v7.py                          # produção, os três modos
    python scripts/rodar_v7.py --modo sensibilidade
    python scripts/rodar_v7.py --recuperacao hybrid
    python scripts/rodar_v7.py --host http://127.0.0.1:11434 --pasta host_127
        # medição de latência sem o atraso de ~2 s do Windows ao resolver
        # "localhost" (IPv6 primeiro) a cada conexão nova; saída em
        # docs/resultados/v7/host_127/<modo>
"""
import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import ollama

PROTO = Path(__file__).resolve().parent.parent
SAIDA = PROTO / "docs" / "resultados" / "v7"
LOG_SERVIDOR = PROTO / "logs" / "ollama_serve_v7.log"


def reiniciar_ollama() -> None:
    for imagem in ("ollama app.exe", "ollama.exe", "llama-server.exe"):
        subprocess.run(["taskkill", "/F", "/T", "/IM", imagem], capture_output=True)
    time.sleep(3)
    LOG_SERVIDOR.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(["ollama", "serve"], stdout=LOG_SERVIDOR.open("a", encoding="utf-8"),
                     stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    for _ in range(60):
        try:
            ollama.list()
            return
        except Exception:
            time.sleep(1)
    raise SystemExit("ollama serve não respondeu em 60 s")


def _saida_de(comando: list[str]) -> str:
    return subprocess.run(comando, capture_output=True, text=True, encoding="utf-8").stdout


# Só o resumo da GPU: a saída completa do nvidia-smi lista os processos
# abertos na máquina, que não interessam à rodada e não devem ser publicados.
NVIDIA_SMI_RESUMO = ["nvidia-smi", "--query-gpu=name,driver_version,memory.used,memory.total,utilization.gpu",
                     "--format=csv"]


def _sem_caminho_local(caminho: Path) -> None:
    """Troca, no log da rodada, os caminhos absolutos (que trazem o usuário
    da máquina) por caminhos relativos a prototipo/."""
    padrao = re.compile(re.escape(str(PROTO)) + r"[\\/]", re.IGNORECASE)
    caminho.write_text(padrao.sub("", caminho.read_text(encoding="utf-8")), encoding="utf-8")


def rodar(recuperacao: str, modo: str, host: str | None = None, subpasta: str | None = None) -> None:
    base = SAIDA / subpasta if subpasta else SAIDA
    pasta = base / (recuperacao if modo == "producao" else f"{recuperacao}_{modo}")
    pasta.mkdir(parents=True, exist_ok=True)
    reiniciar_ollama()
    inicio = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"\n=== {recuperacao} / {modo} — início {inicio}", flush=True)
    env = {**os.environ, "RECUPERACAO_MODO": recuperacao, "PYTHONUTF8": "1"}
    if host:
        env["OLLAMA_HOST"] = host  # tem precedência sobre o .env (load_dotenv não sobrescreve)
    with (pasta / "execucao.log").open("w", encoding="utf-8") as log:
        retorno = subprocess.run([sys.executable, "run_benchmark.py", "--modo", modo, "--saida", str(pasta)],
                                 cwd=PROTO, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    _sem_caminho_local(pasta / "execucao.log")
    fim = datetime.now().astimezone().isoformat(timespec="seconds")
    (pasta / "ambiente.txt").write_text(
        f"recuperacao: {recuperacao}\nmodo: {modo}\nOLLAMA_HOST: {env.get('OLLAMA_HOST', '(do .env)')}\n"
        f"inicio: {inicio}\nfim: {fim}\n"
        f"retorno: {retorno}\n\n$ ollama --version\n{_saida_de(['ollama', '--version'])}\n"
        f"$ ollama ps\n{_saida_de(['ollama', 'ps'])}\n"
        f"$ {' '.join(NVIDIA_SMI_RESUMO)}\n{_saida_de(NVIDIA_SMI_RESUMO)}",
        encoding="utf-8")
    print(f"=== {recuperacao} / {modo} — fim {fim}, retorno {retorno}", flush=True)
    if retorno:
        raise SystemExit(f"run_benchmark.py falhou ({pasta / 'execucao.log'})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rodadas v7 (três modos de recuperação).")
    parser.add_argument("--modo", choices=["producao", "sensibilidade"], default="producao")
    parser.add_argument("--recuperacao", choices=["bm25", "embeddings", "hybrid"], action="append")
    parser.add_argument("--host", help="OLLAMA_HOST da rodada (padrão: o do .env)")
    parser.add_argument("--pasta", help="subpasta de docs/resultados/v7 (padrão: a própria v7)")
    args = parser.parse_args()
    print(f"Hora UTC: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    for recuperacao in args.recuperacao or ["bm25", "embeddings", "hybrid"]:
        rodar(recuperacao, args.modo, args.host, args.pasta)
