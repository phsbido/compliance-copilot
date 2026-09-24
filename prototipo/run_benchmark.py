"""
Benchmark empírico do protótipo completo (Camadas 1-8 ligadas via Orchestrator).

Roda cada cenário de tests/casos_teste.json N_REPETICOES vezes, contra o
Ollama local, medindo latência (Camada 2, dominante no tempo total) e
capturando o que a Camada 7 (Governança) e a Camada 8 (Observabilidade)
registraram para cada execução: se a pergunta foi recusada (desvio de fluxo
para parecer_juridico/fora_de_escopo — ver src/layer3_orchestration/
orchestrator.py, _RECUSAS) e se a resposta carregou aviso de citação não
verificada (validar_citacao).

Cada repetição usa uma nova instância de Orchestrator (memória de sessão
vazia), para que os cenários sejam comparáveis entre si e entre repetições —
o objetivo aqui é medir o comportamento por pergunta isolada, não o efeito de
histórico de conversa (esse já foi exercitado separadamente, ver Caso 2 de
tests/casos_teste.md).

Dois modos de execução (ver docs/decisoes_arquitetura.md,
"Reprodutibilidade"):

  - livre (padrão): parâmetros de amostragem default do modelo — o mesmo
    comportamento de main.py; mede o protótipo como um usuário o usaria.
  - deterministico: temperature=0 e seed fixa (OPCOES_DETERMINISTICAS),
    repassados à Camada 2 — mede o quanto a variação observada no modo livre
    vem da amostragem do LLM, e permite a terceiros reproduzir as respostas.

Gera dois artefatos por modo (sufixo "_deterministico" no modo determinístico):
  - docs/resultados/resultados_benchmark[_deterministico].json: um registro
    por execução (dado bruto, versionado).
  - docs/tabela_resultados_empiricos[_deterministico].csv: estatísticas
    agregadas por cenário (via pandas), para uso direto na monografia.

Uso:
    python run_benchmark.py                        # modo livre
    python run_benchmark.py --modo deterministico  # temperature=0, seed fixa
    python run_benchmark.py --somente-tabela [--modo ...]
        # não chama o LLM: regera o CSV a partir do JSON bruto já salvo
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.layer2_llm_core.core import LLMCore
from src.layer3_orchestration.orchestrator import Orchestrator

RAIZ = Path(__file__).resolve().parent
CASOS_FILE = RAIZ / "tests" / "casos_teste.json"
RESULTADOS_DIR = RAIZ / "docs" / "resultados"

N_REPETICOES = 5

OPCOES_DETERMINISTICAS = {"temperature": 0, "seed": 42}


def caminhos_saida(modo: str) -> tuple[Path, Path]:
    sufixo = "" if modo == "livre" else f"_{modo}"
    return (
        RESULTADOS_DIR / f"resultados_benchmark{sufixo}.json",
        RAIZ / "docs" / f"tabela_resultados_empiricos{sufixo}.csv",
    )

# Classificações que a Camada 3 desvia para uma recusa direta da Camada 7
# (ver orchestrator.py, _RECUSAS) — não buscam nem sintetizam resposta.
TIPOS_RECUSA = {"parecer_juridico", "fora_de_escopo"}


def carregar_casos() -> list[dict]:
    with CASOS_FILE.open(encoding="utf-8") as f:
        return json.load(f)["casos"]


def rodar_caso(caso: dict, repeticao: int, modo: str) -> dict:
    opcoes = OPCOES_DETERMINISTICAS if modo == "deterministico" else None
    orchestrator = Orchestrator(llm=LLMCore(options=opcoes))

    inicio = time.perf_counter()
    resposta = orchestrator.responder(caso["pergunta"])
    latencia_ms = (time.perf_counter() - inicio) * 1000

    registro = orchestrator.ultimo_registro
    tipo_obtido = registro.tipo_classificacao if registro else None

    return {
        "caso_id": caso["id"],
        "modo": modo,
        "categoria": caso["categoria"],
        "repeticao": repeticao,
        "tipo_esperado": caso["tipo_esperado"],
        "tipo_obtido": tipo_obtido,
        "classificacao_correta": tipo_obtido == caso["tipo_esperado"],
        "recusou": tipo_obtido in TIPOS_RECUSA,
        "aviso_citacao_nao_verificada": bool(registro.aviso_citacao_nao_verificada) if registro else False,
        "num_fontes_normativas": len(registro.fontes_normativas) if registro else 0,
        "latencia_ms": round(latencia_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resposta": resposta,
    }


def salvar_resultados_json(resultados: list[dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


def exportar_tabela_csv(resultados: list[dict], destino: Path) -> pd.DataFrame:
    df = pd.DataFrame(resultados)

    agregado = df.groupby(["caso_id", "categoria", "tipo_esperado"], sort=False).agg(
        n_execucoes=("repeticao", "count"),
        taxa_classificacao_correta=("classificacao_correta", "mean"),
        taxa_recusa=("recusou", "mean"),
        taxa_aviso_citacao_nao_verificada=("aviso_citacao_nao_verificada", "mean"),
        latencia_media_ms=("latencia_ms", "mean"),
        latencia_mediana_ms=("latencia_ms", "median"),
        latencia_desvio_padrao_ms=("latencia_ms", "std"),
        latencia_min_ms=("latencia_ms", "min"),
        latencia_max_ms=("latencia_ms", "max"),
        # Quantas respostas textualmente diferentes o cenário produziu nas
        # N repetições: 1 = saída idêntica em todas (reprodutível).
        n_respostas_distintas=("resposta", "nunique"),
    ).reset_index()

    colunas_arredondar = [
        "taxa_classificacao_correta",
        "taxa_recusa",
        "taxa_aviso_citacao_nao_verificada",
        "latencia_media_ms",
        "latencia_mediana_ms",
        "latencia_desvio_padrao_ms",
        "latencia_min_ms",
        "latencia_max_ms",
    ]
    agregado[colunas_arredondar] = agregado[colunas_arredondar].round(2)

    destino.parent.mkdir(parents=True, exist_ok=True)
    agregado.to_csv(destino, index=False, encoding="utf-8")
    return agregado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark empírico do protótipo.")
    parser.add_argument("--modo", choices=["livre", "deterministico"], default="livre")
    parser.add_argument(
        "--somente-tabela",
        action="store_true",
        help="não chama o LLM; regera o CSV a partir do JSON bruto já salvo",
    )
    args = parser.parse_args()
    resultados_json, tabela_csv = caminhos_saida(args.modo)

    if args.somente_tabela:
        with resultados_json.open(encoding="utf-8") as f:
            resultados = json.load(f)
        print(f"Lidos {len(resultados)} registros de {resultados_json} (sem chamar o LLM).")
    else:
        casos = carregar_casos()
        opcoes = OPCOES_DETERMINISTICAS if args.modo == "deterministico" else "default do modelo"
        print(f"Modo: {args.modo} (opções do LLM: {opcoes})")
        print(f"Carregados {len(casos)} cenários de {CASOS_FILE}, {N_REPETICOES} repetições cada "
              f"({len(casos) * N_REPETICOES} execuções no total).\n")

        resultados = []
        for caso in casos:
            for repeticao in range(1, N_REPETICOES + 1):
                print(f"[{caso['id']}] repetição {repeticao}/{N_REPETICOES}...", end=" ", flush=True)
                resultado = rodar_caso(caso, repeticao, args.modo)
                resultados.append(resultado)
                print(
                    f"tipo={resultado['tipo_obtido']} "
                    f"(esperado={resultado['tipo_esperado']}, "
                    f"{'OK' if resultado['classificacao_correta'] else 'DIVERGIU'}) "
                    f"recusou={resultado['recusou']} "
                    f"aviso_citacao={resultado['aviso_citacao_nao_verificada']} "
                    f"latencia={resultado['latencia_ms']:.0f}ms"
                )

        salvar_resultados_json(resultados, resultados_json)
        print(f"\nDado bruto salvo em {resultados_json}")

    tabela = exportar_tabela_csv(resultados, tabela_csv)
    print(f"Tabela agregada salva em {tabela_csv}\n")
    print(tabela.to_string(index=False))
