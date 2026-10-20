# Mapa do Projeto

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Estrutura de diretórios (sem `venv/`, `__pycache__/`, `.git/`)

```
prototipo/
├── .env / .env.example          # config runtime (2 variáveis)
├── .gitignore
├── README.md                    # instalação, uso, reprodução de experimentos
├── _openfinance_limpo.md        # arquivo órfão — ver 07_riscos.md
├── requirements.txt              # 6 dependências, sem pin exato
├── main.py                       # ponto de entrada único (Camada 1)
├── run_benchmark.py              # benchmark quantitativo
├── run_check.py                  # valida Camada 2 isolada
├── run_check_governance.py       # valida Camada 7 isolada
├── run_check_knowledge.py        # valida Camada 5 isolada
├── run_check_memory.py           # valida Camada 6 isolada
├── run_check_observability.py    # valida Camada 8 isolada
├── run_check_orchestration.py    # valida Camada 3 (fluxo completo)
├── run_check_tools.py            # valida Camada 4 isolada
│
├── scripts/
│   └── plot_benchmark.py         # gera gráficos a partir do CSV do benchmark
│
├── src/
│   ├── __init__.py                        # vazio
│   ├── config.py                          # Settings via .env
│   ├── layer1_interaction/cli.py          # Camada 1 — loop de conversa
│   ├── layer2_llm_core/core.py            # Camada 2 — wrapper do Ollama
│   ├── layer3_orchestration/orchestrator.py  # Camada 3 — coordenação do fluxo
│   ├── layer4_tools/tools.py              # Camada 4 — ferramenta buscar_normativo
│   ├── layer5_knowledge/
│   │   ├── knowledge_base.py              # Camada 5 real — RAG lexical
│   │   └── ingest_normativos.py           # pipeline Bronze/Silver/Gold — PARALELO, não usado em runtime
│   ├── layer6_memory/memory.py            # Camada 6 — histórico de sessão
│   ├── layer7_governance/governance.py    # Camada 7 — validação de citação e recusas
│   └── layer8_observability/observability.py  # Camada 8 — log de proveniência
│
├── data/normativos/
│   ├── *.md                     # corpus curado manualmente (2 normas), lido por KnowledgeBase
│   ├── *.pdf                    # 2 PDFs brutos (git-ignorados), entrada de teste do pipeline ilustrativo
│   ├── 1_bronze_raw/            # saída do pipeline ilustrativo (não lida por KnowledgeBase)
│   ├── 2_silver_cleaned/        # idem
│   ├── 3_gold_indexed/          # idem
│   ├── README.md, PENDENTES.md  # proveniência e normas ainda não incluídas
│
├── tests/
│   ├── casos_teste.md            # 4 casos qualitativos, execuções reais documentadas
│   └── casos_teste.json          # os mesmos 4 cenários, estruturados para o benchmark
│
├── docs/
│   ├── decisoes_arquitetura.md   # evidência primária — decisões por camada
│   ├── evidencias_empiricas.md   # log de observações ao testar o sistema
│   ├── estado_atual.md           # handoff de sessão
│   ├── diagrama_arquitetura.md   # diagrama Mermaid
│   ├── apendice_casos_teste.md   # Apêndice A da monografia
│   ├── tabela_resultados_empiricos.csv
│   └── figuras/*.png
│
└── logs/                         # git-ignorado, gerado em runtime
    ├── interacoes.jsonl          # 1 linha por interação real de main.py
    └── resultados_benchmark.json # saída bruta de run_benchmark.py
```

**[FATO]** Não existem `pyproject.toml`, `setup.py/cfg`, `Pipfile`,
`Dockerfile`, `docker-compose.yml`, `Makefile` nem `.github/workflows` no
repositório (confirmado por busca no diretório completo). O projeto não é
empacotado, não tem CI, não é containerizado — execução é sempre `python
<script>.py` dentro de um venv local.

## Arquivos de projeto

| Arquivo | Papel |
|---|---|
| `requirements.txt` (6 linhas) | `ollama>=0.4.0`, `python-dotenv>=1.0.0`, `pandas>=2.0.0`, `matplotlib>=3.8.0`, `seaborn>=0.13.0`, `pypdf>=4.0.0` — sem hash/versão travada |
| `.env.example` | `OLLAMA_MODEL=llama3.1`, `OLLAMA_HOST=http://localhost:11434` |
| `.gitignore` | ignora `venv/`, `__pycache__/`, `*.pyc`, `.env`, `data/normativos/*.pdf`, `data/normativos/*.html`, `data/normativos/1_bronze_raw/*.pdf`, `logs/`, `.DS_Store` |
| `README.md` (244 linhas) | guia de reprodutibilidade científica completo |

## Versão do Python e dependências (uso real confirmado por leitura)

**[FATO]** Python 3.10+ é o requisito declarado (`README.md:46`) — condizente
com o uso de `str | None` como anotação de tipo (sintaxe de union types sem
`Optional`, disponível desde 3.10) em `src/layer2_llm_core/core.py:19` e
`src/layer3_orchestration/orchestrator.py:49`.

| Dependência | Onde é importada | Usada por |
|---|---|---|
| `ollama` | `src/layer2_llm_core/core.py:14` | Runtime do protótipo — única chamada de rede externa (para `localhost:11434`, servidor Ollama) |
| `python-dotenv` | `src/config.py:13` (`load_dotenv`) | Runtime — lê `.env` |
| `pypdf` | `src/layer5_knowledge/ingest_normativos.py:70` | **Só** o pipeline ilustrativo Bronze/Silver/Gold — `knowledge_base.py` (Camada 5 real) não depende dela |
| `pandas` | `run_benchmark.py:31` | Só o script de benchmark, para agregar resultados em CSV |
| `matplotlib`, `seaborn` | `scripts/plot_benchmark.py:24,26` | Só o script de geração de gráficos |

Confirma exatamente o que o README afirma (`README.md:68-71`): `main.py` e
`Orchestrator` (o runtime do protótipo em si) dependem apenas de `ollama` e
`python-dotenv`; as demais 4 bibliotecas são ferramentas de análise/extração
usadas só nos scripts auxiliares (benchmark, gráficos, ingestão ilustrativa).

Nenhuma chave de API, nenhum serviço pago — todo o pipeline roda localmente
via Ollama (`README.md:240-243`).

## Tamanho dos módulos (código próprio, sem `venv/`)

| Arquivo | Linhas |
|---|---:|
| `src/layer5_knowledge/ingest_normativos.py` | 358 |
| `scripts/plot_benchmark.py` | 224 |
| `src/layer3_orchestration/orchestrator.py` | 115 |
| `run_benchmark.py` | 141 |
| `src/layer5_knowledge/knowledge_base.py` | 105 |
| `src/layer7_governance/governance.py` | 93 |
| `src/layer8_observability/observability.py` | 75 |
| `run_check_observability.py` | 78 |
| `src/layer1_interaction/cli.py` | 62 |
| `run_check_orchestration.py` | 42 |
| `src/layer6_memory/memory.py` | 38 |
| `src/layer2_llm_core/core.py` | 36 |
| `src/layer4_tools/tools.py` | 34 |
| `run_check_knowledge.py` | 33 |
| `run_check_memory.py` | 30 |
| `run_check.py` | 26 |
| `src/config.py` | 24 |
| `run_check_tools.py` | 23 |
| `main.py` | 10 |
| **Total (código próprio)** | **≈1.639** |

Todo esse código foi lido integralmente, linha a linha, para esta análise —
não há amostragem. Além destes, existem 9 arquivos `__init__.py`
(`src/__init__.py` e um por `src/layerN_*/`) — todos **vazios** (0 bytes de
código, confirmado por `wc -l`), servindo só para marcar cada pasta como
pacote Python importável; não têm entrada própria em `03_modulos/` por não
terem nenhum conteúdo a documentar.

## Pontos de entrada (todas as formas de executar o código)

| Comando | Dispara | O que faz |
|---|---|---|
| `python main.py` | `main.py:9-10` → `src/layer1_interaction/cli.py:34` `main()` | Loop de conversa interativo (REPL). Único ponto de entrada "de produto". |
| `python run_check.py` | `run_check.py:15-26` | Valida só a Camada 2 (uma chamada ao LLM). |
| `python run_check_orchestration.py` | `run_check_orchestration.py:19-42` | Valida o fluxo completo (Camadas 2-8) com 3 perguntas fixas em uma sessão. |
| `python run_check_tools.py` | `run_check_tools.py:14-23` | Valida `buscar_normativo` isolada. |
| `python run_check_knowledge.py` | `run_check_knowledge.py:13-33` | Valida `KnowledgeBase` isolada. |
| `python run_check_memory.py` | `run_check_memory.py:13-30` | Valida `Memoria` isolada, com asserts. |
| `python run_check_governance.py` | `run_check_governance.py:26-53` | Valida `validar_citacao`/recusas isoladas, com asserts. |
| `python run_check_observability.py` | `run_check_observability.py:25-78` | Valida `registrar_interacao` isolada, com asserts, em arquivo temporário. |
| `python run_benchmark.py` | `run_benchmark.py:116-141` | Roda 4 cenários x 5 repetições contra o Ollama real, grava JSON bruto + CSV agregado. |
| `python scripts/plot_benchmark.py` | `scripts/plot_benchmark.py:213-224` | Lê o CSV do benchmark, gera 2 PNGs — não depende do Ollama. |
| `python -m src.layer5_knowledge.ingest_normativos` (ou caminho direto) | `ingest_normativos.py:357-358` | Pipeline ilustrativo Bronze/Silver/Gold — não conectado ao runtime. |

Não há CLI com `argparse`/`click`/`typer` (nenhum desses pacotes está em
`requirements.txt` ou é importado), não há servidor web, não há workers,
tarefas agendadas nem notebooks. Todos os pontos de entrada são scripts
executados diretamente com `if __name__ == "__main__":` — confirmado em
todos os arquivos acima.

## Grafo de dependências entre módulos internos

```
main.py
  └─ layer1_interaction/cli.py
       └─ layer3_orchestration/orchestrator.py     (Orchestrator)
            ├─ layer2_llm_core/core.py              (LLMCore)
            │    └─ config.py                        (settings)
            ├─ layer4_tools/tools.py                (buscar_normativo)
            │    └─ layer5_knowledge/knowledge_base.py  (KnowledgeBase)
            ├─ layer6_memory/memory.py              (Memoria)
            ├─ layer7_governance/governance.py      (validar_citacao, recusar_*)
            └─ layer8_observability/observability.py (registrar_interacao)

layer5_knowledge/ingest_normativos.py   — autocontido (json/re/shutil/pathlib/dataclasses/datetime + pypdf),
                                           não importado por nenhum outro módulo do projeto

run_benchmark.py       → layer3_orchestration/orchestrator.py (mesmo grafo acima) + pandas
scripts/plot_benchmark.py → só lê o CSV gerado por run_benchmark.py, sem dependência de código-fonte do projeto
run_check_*.py          → cada um importa só a camada que testa
```

**[FATO]** `orchestrator.py` é o único módulo que importa de todas as outras
7 camadas (`src/layer3_orchestration/orchestrator.py:22-30`) — é literalmente
o "hub" do sistema, condizente com seu papel de Camada 3 (Orquestração).
