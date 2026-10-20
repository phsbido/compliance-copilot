"""
Benchmark empírico do protótipo completo (Camadas 1-8 ligadas via Orchestrator).

Roda cada caso de tests/casos_teste.json N vezes (padrão 3, `--repeticoes`)
contra o Ollama local, medindo latência (Camada 2, dominante no tempo total) e
capturando o que a Camada 7 (Governança) e a Camada 8 (Observabilidade)
registraram para cada execução: classificação, desfecho (resposta ou recusa)
e as categorias de validação da Camada 7.

Cada repetição usa uma nova instância de Orchestrator (memória de sessão
vazia), para que os casos sejam comparáveis entre si e entre repetições — o
objetivo aqui é medir o comportamento por pergunta isolada, não o efeito de
histórico de conversa (esse já foi exercitado separadamente, ver Caso 2 de
tests/casos_teste.md).

Bateria v5 (2026-10-02): 66 casos em cinco grupos (normativo_corpus,
norma_ausente, parecer_juridico, fora_de_escopo, robustez); os 4 primeiros
são os casos das versões v1-v4.1, com os mesmos ids. Cada caso declara o
comportamento esperado, e os normativos trazem rótulos de recuperação
(`relevantes`) e termos esperados na resposta (`termos_esperados`). Métricas
novas, além das da Camada 7:

  - sucesso: o comportamento esperado do caso foi observado (ver
    `avaliar_sucesso`; para norma ausente, conta também a ausência declarada
    sobre uma norma que outra norma do contexto apenas menciona — ver
    `declara_ausencia_de_norma`);
  - Acerto@3, Recall@3 e MRR da Camada 5, medidos sobre os mesmos 3 trechos
    que a Camada 4 entrega à síntese (BM25 é determinístico: a recuperação
    não depende do LLM nem da repetição);
  - cobertura de termos esperados na resposta do LLM (aproximação de
    conteúdo, não de correção jurídica);
  - IC 95% de Wilson nas taxas por grupo, calculado sobre os casos (um caso
    conta como sucesso se acertou em todas as repetições): no modo produção
    as repetições são quase idênticas, então tratá-las como independentes
    estreitaria o intervalo artificialmente.

Dois modos de execução (v4; ver docs/decisoes_arquitetura.md, Camada 2):

  - producao (padrão): os parâmetros de amostragem do .env (src/config.py) —
    classificação com temperatura 0, síntese com 0,1, seed 42 —, os mesmos
    de main.py; mede o protótipo como ele é usado.
  - sensibilidade: temperatura 0,8 nas duas chamadas e seed aleatória (o
    padrão implícito do Ollama, usado até a v3.1 no antigo modo "livre") —
    mostra o que muda com amostragem alta e justifica a escolha da produção.

Até a v3.1 os modos eram "livre" e "deterministico"; até a v4.1 a bateria
tinha 4 casos x 5 repetições. Esses resultados estão em docs/resultados/v1..v4.1.

Artefatos (sufixo "_sensibilidade" no modo de sensibilidade):
  - docs/resultados/resultados_benchmark[_sufixo].json: um registro por
    execução (dado bruto, versionado);
  - docs/tabela_resultados_empiricos[_sufixo].csv: estatísticas por caso;
  - docs/tabela_resultados_por_grupo[_sufixo].csv: estatísticas por grupo,
    com IC 95%, e uma linha de total;
  - docs/matriz_confusao_classificacao[_sufixo].csv: classificação esperada
    x obtida (Camada 3);
  - docs/tabela_recuperacao.csv: Acerto@3, Recall@3 e MRR por caso rotulado
    (independe do modo e do LLM).

Uso:
    python run_benchmark.py                        # modo produção, 3 repetições
    python run_benchmark.py --modo sensibilidade   # temperatura 0,8, seed aleatória
    python run_benchmark.py --repeticoes 5 --grupo norma_ausente
    python run_benchmark.py --casos rc1_objetivos,fora_copa_2002
        # --grupo/--casos rodam só um subconjunto e não sobrescrevem os
        # artefatos versionados (saída em logs/)
    python run_benchmark.py --somente-recuperacao
        # não chama o LLM: avalia só a recuperação da Camada 5
    python run_benchmark.py --somente-tabela [--modo ...]
        # não chama o LLM: regera as tabelas a partir do JSON bruto já salvo
    python run_benchmark.py --saida docs/resultados/v6 [...]
        # v6 em diante: todos os artefatos (JSON, CSVs e tabela de
        # recuperação) numa pasta própria; a linha de base v5 não é tocada
    $env:RECUPERACAO_MODO="hybrid"; python run_benchmark.py --saida docs/resultados/v7/hybrid
        # v7: o modo de recuperação da Camada 5 vem do ambiente (a Camada 4
        # carrega a base na importação); cada execução registra o modo, o
        # modelo/digest de embeddings, a versão do índice e a latência da busca
    python run_benchmark.py --revalidar [--modo ...]
        # não chama o LLM: reaplica a Camada 7 atual (e os rótulos atuais de
        # tests/casos_teste.json) à resposta do LLM e ao contexto guardados
        # no JSON bruto e regera as tabelas
"""
import argparse
import dataclasses
import json
import math
import os
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config import ParametrosAmostragem, settings
from src.layer3_orchestration.orchestrator import Orchestrator
from src.layer5_knowledge.knowledge_base import KnowledgeBase
from src.layer7_governance.governance import _NORMA_REGEX, _declara_ausencia, _frases, validar_resposta

RAIZ = Path(__file__).resolve().parent
CASOS_FILE = RAIZ / "tests" / "casos_teste.json"
RESULTADOS_DIR = RAIZ / "docs" / "resultados"
TABELA_RECUPERACAO = RAIZ / "docs" / "tabela_recuperacao.csv"
SAIDA_PARCIAL_DIR = RAIZ / "logs" / "benchmark_parcial"

N_REPETICOES = 3
# Mesmo top_k da Camada 4 (buscar_normativo): mede-se o que a síntese recebe.
TOP_K = 3

AMOSTRAGEM_SENSIBILIDADE = ParametrosAmostragem(
    temperatura_classificacao=0.8, temperatura_sintese=0.8, seed=None
)

ORDEM_GRUPOS = ["normativo_corpus", "norma_ausente", "parecer_juridico", "fora_de_escopo", "robustez"]

COLUNAS_CAMADA7 = ["norma_nao_verificada", "ausencia_declarada", "artigo_nao_verificado",
                   "valor_nao_verificado", "aviso_camada7"]


def amostragem_do_modo(modo: str) -> ParametrosAmostragem:
    return AMOSTRAGEM_SENSIBILIDADE if modo == "sensibilidade" else settings.amostragem


def caminhos_saida(modo: str, parcial: bool = False, saida: Path | None = None) -> dict[str, Path]:
    """Sem `saida`, os caminhos versionados do v5 (ou logs/, se parcial).
    Com `saida` (v6 em diante), tudo vai para essa pasta, inclusive a tabela
    de recuperação, para que uma rodada nova não sobrescreva a linha de base."""
    sufixo = "" if modo == "producao" else f"_{modo}"
    if saida is not None:
        base_json = base_csv = saida
    else:
        base_json = SAIDA_PARCIAL_DIR if parcial else RESULTADOS_DIR
        base_csv = SAIDA_PARCIAL_DIR if parcial else RAIZ / "docs"
    return {
        "recuperacao": saida / "tabela_recuperacao.csv" if saida is not None else TABELA_RECUPERACAO,
        "json": base_json / f"resultados_benchmark{sufixo}.json",
        "por_caso": base_csv / f"tabela_resultados_empiricos{sufixo}.csv",
        "por_grupo": base_csv / f"tabela_resultados_por_grupo{sufixo}.csv",
        "confusao": base_csv / f"matriz_confusao_classificacao{sufixo}.csv",
    }


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------

def colunas_validacao(categorias: dict) -> dict:
    if not categorias:
        return {c: False for c in COLUNAS_CAMADA7}
    return {
        "norma_nao_verificada": bool(categorias["normas_nao_verificadas"]),
        "ausencia_declarada": bool(categorias["normas_declaradas_ausentes"]),
        "artigo_nao_verificado": bool(categorias["artigos_nao_verificados"] or categorias["artigos_fora_da_norma"]),
        "valor_nao_verificado": bool(categorias["valores_nao_verificados"]),
        "aviso_camada7": bool(categorias["possui_aviso"]),
    }


def wilson(sucessos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson para uma proporção (IC 95% por padrão)."""
    if n == 0:
        return (math.nan, math.nan)
    p = sucessos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


def cobertura_termos(resposta: str, grupos: list[list[str]]) -> float | None:
    """Fração dos grupos de termos com pelo menos uma variante na resposta."""
    if not grupos or not resposta:
        return None
    texto = _normalizar(resposta)
    atendidos = sum(any(_normalizar(v) in texto for v in grupo) for grupo in grupos)
    return atendidos / len(grupos)


def _e_relevante(trecho: dict, relevantes: list[dict]) -> bool:
    # O título da Gold é "Resolução Conjunta nº 1, de 4 de maio de 2020"; o
    # rótulo usa só "Resolução Conjunta nº 1" (a vírgula evita casar nº 10).
    return any(
        trecho["norma"].startswith(r["norma"] + ",") and trecho["trecho"] == r["trecho"]
        for r in relevantes
    )


def metricas_recuperacao(recuperados: list[dict], relevantes: list[dict]) -> dict:
    """Acerto@k (algum relevante no top-k), Recall@k (fração dos rótulos
    recuperados) e RR (inverso da posição do primeiro relevante)."""
    if not relevantes:
        return {"acerto_recuperacao": None, "recall_recuperacao": None, "rr_recuperacao": None}
    posicoes = [i for i, t in enumerate(recuperados, start=1) if _e_relevante(t, relevantes)]
    encontrados = sum(
        any(t["norma"].startswith(r["norma"] + ",") and t["trecho"] == r["trecho"] for t in recuperados)
        for r in relevantes
    )
    return {
        "acerto_recuperacao": bool(posicoes),
        "recall_recuperacao": encontrados / len(relevantes),
        "rr_recuperacao": 1 / posicoes[0] if posicoes else 0.0,
    }


def declara_ausencia_de_norma(resposta: str) -> bool:
    """Alguma frase da resposta cita uma norma e declara que ela não está
    disponível? Usa o mesmo detector de frases da Camada 7, mas sobre a
    resposta inteira: a categoria `ausencia_declarada` da Camada 7 só é
    calculada para normas que não aparecem no contexto, e uma norma ausente
    do corpus pode ser apenas mencionada por outra (a IN BCB 759/2026 cita a
    Resolução BCB nº 1/2020) — achado do teste de fumaça da v5."""
    return any(_NORMA_REGEX.search(f) and _declara_ausencia(f) for _, f in _frases(resposta or ""))


def avaliar_sucesso(r: dict) -> bool:
    """O comportamento esperado do caso foi observado nesta execução?"""
    classificacao_ok = r["classificacao_correta"]
    sem_aviso = not r["aviso_camada7"]
    comportamento = r["comportamento_esperado"]
    if comportamento == "resposta_fundamentada":
        return classificacao_ok and r["desfecho"] == "resposta" and sem_aviso
    if comportamento == "ausencia_declarada":
        return classificacao_ok and sem_aviso and (
            r["ausencia_declarada"] or r["recusou"] or r["resposta_declara_ausencia"])
    if comportamento == "recusa":
        return classificacao_ok and r["recusou"]
    if comportamento == "sem_alucinacao":
        return sem_aviso
    raise ValueError(f"comportamento_esperado desconhecido: {comportamento}")


_KB: KnowledgeBase | None = None


def _kb() -> KnowledgeBase:
    global _KB
    if _KB is None:
        _KB = KnowledgeBase()
    return _KB


def recuperar(pergunta: str, limiar: float | None = None) -> list[dict]:
    """Os trechos que a Camada 4 entrega à síntese, com o mesmo limiar (v6):
    abaixo dele, nenhum — e a recuperação conta como erro nos casos rotulados."""
    return [{"norma": d.titulo, "trecho": d.identificador}
            for d in _kb().buscar(pergunta, top_k=TOP_K, limiar=limiar)]


def recuperar_cronometrado(pergunta: str, limiar: float | None = None) -> tuple[list[dict], float]:
    """`recuperar` e o tempo da busca em ms (v7: nos modos com embeddings,
    inclui gerar o vetor da pergunta no Ollama)."""
    inicio = time.perf_counter()
    recuperados = recuperar(pergunta, limiar)
    return recuperados, round((time.perf_counter() - inicio) * 1000, 1)


def pontuacao_melhor_trecho(pergunta: str) -> float:
    """Pontuação do melhor trecho no modo da Camada 5 (BM25, cosseno ou RRF)."""
    pontuados = _kb().buscar_pontuado(pergunta, top_k=1)
    return round(pontuados[0][0], 4) if pontuados else 0.0


def avaliar(r: dict, caso: dict) -> dict:
    """Recalcula as colunas derivadas a partir dos campos brutos e dos rótulos
    atuais do caso — usado na execução e na revalidação offline."""
    aceitos = caso.get("tipos_aceitos", [caso["tipo_esperado"]])
    r.update(
        grupo=caso["grupo"],
        categoria=caso["categoria"],
        tipo_esperado=caso["tipo_esperado"],
        tipos_aceitos=aceitos,
        comportamento_esperado=caso["comportamento_esperado"],
        classificacao_correta=r["tipo_obtido"] in aceitos,
        resposta_declara_ausencia=declara_ausencia_de_norma(r.get("resposta_sintetizada", "")),
        cobertura_termos=cobertura_termos(r.get("resposta_sintetizada", ""), caso.get("termos_esperados", [])),
        **metricas_recuperacao(r["trechos_recuperados"], caso.get("relevantes", [])),
    )
    r["sucesso"] = avaliar_sucesso(r)
    return r


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------

def carregar_casos() -> list[dict]:
    with CASOS_FILE.open(encoding="utf-8") as f:
        return json.load(f)["casos"]


def filtrar_casos(casos: list[dict], grupo: str | None, ids: str | None) -> list[dict]:
    if grupo:
        casos = [c for c in casos if c["grupo"] == grupo]
    if ids:
        pedidos = {i.strip() for i in ids.split(",")}
        desconhecidos = pedidos - {c["id"] for c in casos}
        if desconhecidos:
            raise SystemExit(f"Casos não encontrados: {sorted(desconhecidos)}")
        casos = [c for c in casos if c["id"] in pedidos]
    return casos


def rodar_caso(caso: dict, repeticao: int, modo: str, limiar_bm25: float | None = None,
               ablacao: str | None = None, max_tokens_saida: int | None = None) -> dict:
    amostragem = amostragem_do_modo(modo)
    if max_tokens_saida is not None:
        amostragem = dataclasses.replace(amostragem, max_tokens_saida=max_tokens_saida)
    orchestrator = Orchestrator(amostragem=amostragem, limiar_bm25=limiar_bm25, ablacao=ablacao)

    inicio = time.perf_counter()
    resposta = orchestrator.responder(caso["pergunta"])
    latencia_ms = (time.perf_counter() - inicio) * 1000

    registro = orchestrator.ultimo_registro
    trechos_recuperados, latencia_busca_ms = recuperar_cronometrado(caso["pergunta"], orchestrator.limiar_bm25)
    r = {
        "caso_id": caso["id"],
        "modo": modo,
        "repeticao": repeticao,
        "tipo_obtido": registro.tipo_classificacao if registro else None,
        "desfecho": registro.desfecho if registro else None,
        "recusou": bool(registro) and registro.desfecho != "resposta",
        "aviso_citacao_nao_verificada": bool(registro.aviso_citacao_nao_verificada) if registro else False,
        **colunas_validacao(registro.validacao if registro else {}),
        "validacao": registro.validacao if registro else {},
        "parametros_llm": registro.parametros_llm if registro else {},
        "num_fontes_normativas": len(registro.fontes_normativas) if registro else 0,
        "latencia_ms": round(latencia_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resposta": resposta,
        # Entradas da Camada 7, para revalidação offline (--revalidar).
        "resposta_sintetizada": orchestrator.ultima_sintese,
        "contexto_normativo": orchestrator.ultimo_contexto,
        # Os mesmos top-3 da Camada 4, identificados por norma + trecho, para
        # as métricas de recuperação (a busca é determinística).
        "trechos_recuperados": trechos_recuperados,
        # v7: modo de recuperação, modelo/digest de embeddings e versão do
        # índice (o que a Camada 8 registrou) e tempo da busca, medido numa
        # segunda chamada idêntica à da Camada 4.
        "recuperacao": registro.recuperacao if registro else {},
        "latencia_busca_ms": latencia_busca_ms,
        # v6: limiar efetivo da Camada 5 e pontuação do melhor trecho.
        "limiar_bm25": orchestrator.limiar_bm25,
        "pontuacao_melhor_trecho": pontuacao_melhor_trecho(caso["pergunta"]),
        # v6, Tarefa C: variante da ablação da Camada 7 (None = Camada 7 ligada).
        # Com a Camada 7 desligada não há validação: as colunas de aviso ficam
        # falsas e o sucesso automático não mede governança — a comparação
        # usa a medida offline (scripts/medir_ablacao.py).
        "ablacao": ablacao,
        # Síntese cortada pelo teto de tokens (só com --max-tokens-saida).
        "sintese_truncada": bool(orchestrator.ultima_sintese)
                            and orchestrator.llm.ultimo_motivo_parada == "length",
    }
    if ablacao:
        r["aviso_citacao_nao_verificada"] = False
    return avaliar(r, caso)


def revalidar(resultados: list[dict], casos: dict[str, dict]) -> int:
    if any(r.get("ablacao") for r in resultados):
        # Revalidar reescreveria as respostas com a Camada 7 ligada; a medida
        # offline da ablação é scripts/medir_ablacao.py, que não altera o JSON.
        raise SystemExit("--revalidar não se aplica a rodadas de ablação da Camada 7.")
    n = 0
    for r in resultados:
        if r.get("resposta_sintetizada"):
            v = validar_resposta(r["resposta_sintetizada"], r["contexto_normativo"])
            r.update(colunas_validacao(v.categorias()), validacao=v.categorias(),
                     aviso_citacao_nao_verificada=v.aviso_legado, resposta=v.texto_final)
            n += 1
        avaliar(r, casos[r["caso_id"]])
    return n


# --------------------------------------------------------------------------
# Tabelas
# --------------------------------------------------------------------------

def salvar_resultados_json(resultados: list[dict], destino: Path, tentativas: int = 5) -> None:
    """Grava num temporário e substitui o destino. No Windows, a regravação
    direta falhou uma vez com OSError 22 (arquivo momentaneamente travado
    por outro processo, v7): tenta de novo antes de desistir, para uma
    rodada longa não cair por isso."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(destino.name + ".tmp")
    for tentativa in range(1, tentativas + 1):
        try:
            with temporario.open("w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            os.replace(temporario, destino)
            return
        except OSError:
            if tentativa == tentativas:
                raise
            time.sleep(0.5 * tentativa)


def tabela_por_caso(df: pd.DataFrame) -> pd.DataFrame:
    agregado = df.groupby(["caso_id", "grupo", "categoria", "tipo_esperado", "comportamento_esperado"],
                          sort=False).agg(
        n_execucoes=("repeticao", "count"),
        taxa_sucesso=("sucesso", "mean"),
        taxa_classificacao_correta=("classificacao_correta", "mean"),
        taxa_recusa=("recusou", "mean"),
        taxa_aviso_citacao_nao_verificada=("aviso_citacao_nao_verificada", "mean"),
        **{f"taxa_{c}": (c, "mean") for c in COLUNAS_CAMADA7},
        cobertura_termos_media=("cobertura_termos", "mean"),
        acerto_recuperacao_3=("acerto_recuperacao", "first"),
        recall_recuperacao_3=("recall_recuperacao", "first"),
        rr_recuperacao_3=("rr_recuperacao", "first"),
        latencia_media_ms=("latencia_ms", "mean"),
        latencia_mediana_ms=("latencia_ms", "median"),
        latencia_desvio_padrao_ms=("latencia_ms", "std"),
        latencia_min_ms=("latencia_ms", "min"),
        latencia_max_ms=("latencia_ms", "max"),
        # Quantas respostas textualmente diferentes o caso produziu nas
        # N repetições: 1 = saída idêntica em todas (reprodutível).
        n_respostas_distintas=("resposta", "nunique"),
    ).reset_index()
    return agregado.round(3)


def _linha_grupo(nome: str, df: pd.DataFrame, por_caso: pd.DataFrame) -> dict:
    # Sucesso estrito por caso (todas as repetições), base do IC de Wilson.
    casos_ok = int((por_caso["taxa_sucesso"] == 1).sum())
    n_casos = len(por_caso)
    ic_inf, ic_sup = wilson(casos_ok, n_casos)
    rotulados = por_caso.dropna(subset=["acerto_recuperacao_3"])
    linha = {
        "grupo": nome,
        "n_casos": n_casos,
        "n_execucoes": len(df),
        "taxa_sucesso_execucoes": df["sucesso"].mean(),
        "casos_sucesso_total": casos_ok,
        "taxa_casos_sucesso_total": casos_ok / n_casos if n_casos else math.nan,
        "ic95_casos_sucesso_inf": ic_inf,
        "ic95_casos_sucesso_sup": ic_sup,
        "taxa_classificacao_correta": df["classificacao_correta"].mean(),
        "taxa_recusa": df["recusou"].mean(),
        **{f"taxa_{c}": df[c].mean() for c in COLUNAS_CAMADA7},
        "cobertura_termos_media": df["cobertura_termos"].mean(),
        "n_casos_rotulados_recuperacao": len(rotulados),
        "acerto_recuperacao_3": rotulados["acerto_recuperacao_3"].astype(float).mean(),
        "recall_recuperacao_3": rotulados["recall_recuperacao_3"].mean(),
        "mrr_3": rotulados["rr_recuperacao_3"].mean(),
        "latencia_media_ms": df["latencia_ms"].mean(),
        "latencia_mediana_ms": df["latencia_ms"].median(),
        "latencia_p95_ms": df["latencia_ms"].quantile(0.95),
        "casos_com_respostas_distintas": int((por_caso["n_respostas_distintas"] > 1).sum()),
    }
    if "latencia_busca_ms" in df:  # v7 em diante
        linha["latencia_busca_mediana_ms"] = df["latencia_busca_ms"].median()
    return linha


def tabela_por_grupo(df: pd.DataFrame, por_caso: pd.DataFrame) -> pd.DataFrame:
    grupos = [g for g in ORDEM_GRUPOS if g in set(df["grupo"])]
    linhas = [_linha_grupo(g, df[df["grupo"] == g], por_caso[por_caso["grupo"] == g]) for g in grupos]
    linhas.append(_linha_grupo("total", df, por_caso))
    return pd.DataFrame(linhas).round(3)


def matriz_confusao(df: pd.DataFrame) -> pd.DataFrame:
    return pd.crosstab(df["tipo_esperado"], df["tipo_obtido"].fillna("(nenhum)"),
                       rownames=["tipo_esperado"], colnames=["tipo_obtido"])


def exportar_tabelas(resultados: list[dict], caminhos: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(resultados)
    por_caso = tabela_por_caso(df)
    por_grupo = tabela_por_grupo(df, por_caso)
    confusao = matriz_confusao(df)
    caminhos["por_caso"].parent.mkdir(parents=True, exist_ok=True)
    por_caso.to_csv(caminhos["por_caso"], index=False, encoding="utf-8")
    por_grupo.to_csv(caminhos["por_grupo"], index=False, encoding="utf-8")
    confusao.to_csv(caminhos["confusao"], encoding="utf-8")
    return por_grupo, confusao


def avaliar_recuperacao(casos: list[dict], limiar: float | None = None) -> pd.DataFrame:
    """Camada 5 isolada: Acerto@3, Recall@3 e RR por caso rotulado, sem LLM."""
    linhas = []
    for caso in casos:
        if not caso.get("relevantes"):
            continue
        recuperados = recuperar(caso["pergunta"], limiar)
        linhas.append({
            "caso_id": caso["id"],
            "grupo": caso["grupo"],
            "relevantes": "; ".join(f"{r['norma']} {r['trecho']}" for r in caso["relevantes"]),
            "recuperados_top3": "; ".join(
                f"{t['norma'].split(',')[0]} {t['trecho']}" for t in recuperados),
            **metricas_recuperacao(recuperados, caso["relevantes"]),
        })
    return pd.DataFrame(linhas).round(3)


def resumo_recuperacao(tabela: pd.DataFrame) -> str:
    return (f"{len(tabela)} casos rotulados — Acerto@3 = {tabela['acerto_recuperacao'].mean():.3f}, "
            f"Recall@3 = {tabela['recall_recuperacao'].mean():.3f}, MRR = {tabela['rr_recuperacao'].mean():.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark empírico do protótipo.")
    parser.add_argument("--modo", choices=["producao", "sensibilidade"], default="producao")
    parser.add_argument("--repeticoes", type=int, default=N_REPETICOES)
    parser.add_argument("--grupo", choices=ORDEM_GRUPOS, help="roda só os casos deste grupo")
    parser.add_argument("--casos", help="roda só estes ids (separados por vírgula)")
    parser.add_argument("--somente-recuperacao", action="store_true",
                        help="não chama o LLM; avalia só a recuperação da Camada 5")
    parser.add_argument("--somente-tabela", action="store_true",
                        help="não chama o LLM; regera as tabelas a partir do JSON bruto já salvo")
    parser.add_argument("--revalidar", action="store_true",
                        help="não chama o LLM; reaplica a Camada 7 atual ao JSON bruto salvo e regera as tabelas")
    parser.add_argument("--limiar-bm25", type=float,
                        help="limiar de pontuação do melhor trecho (Camada 5, v6); padrão: LIMIAR_BM25 do .env")
    parser.add_argument("--ablacao", choices=["c1", "c2"],
                        help="desliga a Camada 7 (c1: sem validar_resposta; c2: também sem POLITICA_SINTESE)")
    parser.add_argument("--max-tokens-saida", type=int,
                        help="teto de tokens gerados por chamada (num_predict); padrão: sem teto, como na v5")
    parser.add_argument("--saida", type=Path,
                        help="pasta de saída de todos os artefatos (v6 em diante); sem ela, os caminhos do v5")
    args = parser.parse_args()

    parcial = bool(args.grupo or args.casos)
    caminhos = caminhos_saida(args.modo, parcial=parcial, saida=args.saida)

    limiar = args.limiar_bm25 if args.limiar_bm25 is not None else settings.limiar_bm25
    casos = carregar_casos()
    tabela_rec = avaliar_recuperacao(casos, limiar)
    caminhos["recuperacao"].parent.mkdir(parents=True, exist_ok=True)
    tabela_rec.to_csv(caminhos["recuperacao"], index=False, encoding="utf-8")
    print(f"Recuperação (Camada 5): {resumo_recuperacao(tabela_rec)}; tabela em {caminhos['recuperacao']}")
    if args.somente_recuperacao:
        print(tabela_rec.to_string(index=False))
        raise SystemExit(0)

    if args.somente_tabela or args.revalidar:
        with caminhos["json"].open(encoding="utf-8") as f:
            resultados = json.load(f)
        print(f"Lidos {len(resultados)} registros de {caminhos['json']} (sem chamar o LLM).")
        if args.revalidar:
            n = revalidar(resultados, {c["id"]: c for c in casos})
            salvar_resultados_json(resultados, caminhos["json"])
            print(f"Camada 7 reaplicada a {n} registro(s); métricas recalculadas; JSON bruto atualizado.")
    else:
        selecionados = filtrar_casos(casos, args.grupo, args.casos)
        total = len(selecionados) * args.repeticoes
        print(f"Recuperação da Camada 5: {_kb().identificacao()}")
        print(f"Modo: {args.modo} (amostragem: {amostragem_do_modo(args.modo).como_dict()}; "
              f"limiar BM25: {limiar if limiar is not None else 'desligado'}; "
              f"ablação da Camada 7: {args.ablacao or 'não'}; "
              f"teto de tokens: {args.max_tokens_saida or 'nenhum'})")
        print(f"{len(selecionados)} casos de {CASOS_FILE}, {args.repeticoes} repetições cada "
              f"({total} execuções no total).\n")

        resultados = []
        for caso in selecionados:
            for repeticao in range(1, args.repeticoes + 1):
                print(f"[{len(resultados) + 1}/{total}] [{caso['id']}] rep {repeticao}...", end=" ", flush=True)
                r = rodar_caso(caso, repeticao, args.modo, limiar, args.ablacao, args.max_tokens_saida)
                resultados.append(r)
                print(
                    f"tipo={r['tipo_obtido']} desfecho={r['desfecho']} "
                    f"aviso_c7={r['aviso_camada7']} sucesso={'OK' if r['sucesso'] else 'FALHOU'} "
                    f"latencia={r['latencia_ms']:.0f}ms"
                )
            # Grava a cada caso: uma queda no meio não perde o que já rodou.
            salvar_resultados_json(resultados, caminhos["json"])

        print(f"\nDado bruto salvo em {caminhos['json']}")

    por_grupo, confusao = exportar_tabelas(resultados, caminhos)
    print(f"Tabelas salvas em {caminhos['por_caso']}, {caminhos['por_grupo']} e {caminhos['confusao']}\n")
    colunas_resumo = ["grupo", "n_casos", "n_execucoes", "taxa_sucesso_execucoes", "casos_sucesso_total",
                      "ic95_casos_sucesso_inf", "ic95_casos_sucesso_sup", "taxa_classificacao_correta",
                      "taxa_aviso_camada7", "cobertura_termos_media", "acerto_recuperacao_3",
                      "latencia_mediana_ms"]
    print(por_grupo[colunas_resumo].to_string(index=False))
    print("\nMatriz de confusão (Camada 3):")
    print(confusao.to_string())
