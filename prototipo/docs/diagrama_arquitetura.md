# Diagrama de Arquitetura

Diagrama de componentes do protótipo, mapeando 1:1 as 8 camadas conceituais
de Maia et al. (2026, Seção 8) às pastas/módulos concretos do repositório, e
o fluxo de dados de uma interação completa (`Orchestrator.responder()`, ver
`src/layer3_orchestration/orchestrator.py`).

Gerado a partir da inspeção do código-fonte real em `src/layerN_*/`
(2026-10-20, estado da v7) — nomes de classes, funções e arquivos abaixo
correspondem literalmente à implementação, não a uma versão idealizada da
arquitetura. Ver `docs/decisoes_arquitetura.md` para a justificativa de cada
decisão de projeto por trás de cada camada. A versão em figura (Capítulo 3)
é `docs/figuras/diagrama_arquitetura.png`, gerada por
`scripts/plot_arquitetura.py` com os números lidos do código e dos dados.

**Nota sobre a Camada 5**: a `KnowledgeBase` lê apenas a camada Gold do
medalhão (`data/normativos/3_gold_indexed/`): um JSON por norma, mais
`indice_bm25.json` e `indice_embeddings.json`. A esteira de ingestão
(offline, `ingest_normativos.py`) vai da URL oficial do BCB (`fontes_url.json`)
à Bronze (bruto), à Silver (limpo e estruturado) e à Gold (trechos e índices);
em tempo de execução só a Gold é consultada. A recuperação tem três modos,
escolhidos por `RECUPERACAO_MODO`: `bm25` (o padrão), `embeddings` (`bge-m3`
no Ollama, similaridade de cosseno) e `hybrid` (os dois rankings combinados
por Reciprocal Rank Fusion, `RRF_K = 60`). Os limiares `LIMIAR_BM25` e
`LIMIAR_COSSENO` existem e estão desligados por padrão. O corpus de execução
tem 17 normas e 440 trechos.

```mermaid
graph TD
    Usuario(["Usuário"])

    subgraph C1["Camada 1 — Interação — src/layer1_interaction/"]
        CLI["cli.py: main() — loop CLI"]
        WEB["web.py: interface web local\n(http.server, 127.0.0.1)"]
    end

    subgraph C3["Camada 3 — Orquestração — src/layer3_orchestration/orchestrator.py"]
        ORC["Orchestrator.responder()"]
        INTERP["_interpretar()"]
        RECUSAS{"tipo em _RECUSAS?"}
        BUSCA["_buscar_normativo()"]
        SEMBASE{"NENHUM_TRECHO_ENCONTRADO?"}
        SINT["_sintetizar_resposta()"]
        VALID["_validar_resposta()"]
    end

    subgraph C2["Camada 2 — Núcleo de Raciocínio LLM — src/layer2_llm_core/core.py"]
        LLM["LLMCore.generate()\n(Ollama, llama3.1)"]
    end

    subgraph C4["Camada 4 — Ferramentas — src/layer4_tools/tools.py"]
        TOOL["buscar_normativo()"]
    end

    subgraph C5["Camada 5 — Conhecimento / RAG — src/layer5_knowledge/"]
        KB["KnowledgeBase.buscar()\nRECUPERACAO_MODO: bm25 (padrão) /\nembeddings (bge-m3, cosseno) /\nhybrid (RRF, RRF_K = 60)"]
        GOLD[("data/normativos/3_gold_indexed/\n17 normas, 440 trechos\nindice_bm25.json +\nindice_embeddings.json")]
        INGEST["ingest_normativos.py (offline)\nBCB → Bronze → Silver → Gold"]
    end

    subgraph C6["Camada 6 — Memória — src/layer6_memory/memory.py"]
        MEM["Memoria\n(buffer das últimas 5 interações\nem processo, sem persistência)"]
    end

    subgraph C7["Camada 7 — Governança — src/layer7_governance/governance.py"]
        POLITICA["POLITICA_SINTESE\n(regras da síntese)"]
        GOVVALID["validar_resposta()\n(normas, artigos e valores citados\nvs. trechos do turno)"]
        GOVREC1["recusar_parecer_juridico()"]
        GOVREC2["recusar_fora_de_escopo()"]
        GOVREC3["recusar_sem_base()"]
        GOVFONTE["validar_fonte_publica()\n(só HTTPS do bcb.gov.br)"]
    end

    subgraph C8["Camada 8 — Observabilidade — src/layer8_observability/observability.py"]
        OBS["registrar_interacao()"]
        LOG[("logs/interacoes.jsonl\n(JSON Lines, append-only)")]
    end

    Usuario -->|pergunta em texto| CLI
    Usuario -->|pergunta no navegador| WEB
    CLI -->|"responder(pergunta)"| ORC
    WEB -->|"responder(pergunta)\n(um Orchestrator por sessão)"| ORC
    ORC --> INTERP
    INTERP -->|"classifica (temp. 0): normativo /\nparecer_juridico / fora_de_escopo"| LLM
    INTERP --> RECUSAS

    RECUSAS -->|parecer_juridico| GOVREC1
    RECUSAS -->|fora_de_escopo| GOVREC2
    RECUSAS -->|normativo| BUSCA

    BUSCA --> TOOL
    TOOL --> KB
    KB --> GOLD
    KB -->|trechos citáveis\nFonte + URL + texto| TOOL
    TOOL -->|contexto normativo| BUSCA
    BUSCA --> SEMBASE
    SEMBASE -->|sim| GOVREC3
    SEMBASE -->|não| SINT

    MEM -->|histórico formatado\nda sessão| SINT
    POLITICA -->|system| SINT
    SINT -->|"prompt: histórico + contexto\n+ pergunta (temp. 0,1)"| LLM
    LLM -->|resposta sintetizada| SINT
    SINT --> VALID
    VALID --> GOVVALID
    GOVVALID -->|"resposta + avisos + fontes consultadas\n+ aviso de validação humana"| VALID

    ORC -->|adicionar pergunta + resposta\n(pré-validação, sem avisos)| MEM

    GOVREC1 --> OBS
    GOVREC2 --> OBS
    GOVREC3 --> OBS
    VALID -->|resposta final| OBS
    OBS --> LOG
    OBS -->|RegistroInteracao\n(ultimo_registro)| ORC

    INGEST -.->|"valida a URL de origem"| GOVFONTE
    INGEST -->|escreve| GOLD

    ORC -->|resposta final +\nproveniência da Camada 8| CLI
    ORC -->|resposta final +\nproveniência da Camada 8| WEB
    CLI -->|resposta + fontes\n+ avisos| Usuario
    WEB -->|resposta + fontes\n+ avisos| Usuario
```

## Legenda — camada conceitual → pasta/módulo

| Camada (Maia et al., 2026) | Pasta / arquivo | Classe/função principal |
|---|---|---|
| 1 — Interação com o Usuário | `src/layer1_interaction/cli.py`, `web.py` (+ `static/index.html`) | `main()` (CLI, `main.py`); `main()` (web, `main_web.py`) |
| 2 — Núcleo de Raciocínio do LLM | `src/layer2_llm_core/core.py` | `LLMCore.generate()` |
| 3 — Orquestração e Fluxo de Trabalho | `src/layer3_orchestration/orchestrator.py` | `Orchestrator.responder()` |
| 4 — Integração de Ferramentas e Serviços | `src/layer4_tools/tools.py` | `buscar_normativo()` |
| 5 — Integração de Conhecimento (RAG) | `src/layer5_knowledge/knowledge_base.py`, `ingest_normativos.py` | `KnowledgeBase.buscar()` |
| 6 — Contexto e Memória | `src/layer6_memory/memory.py` | `Memoria` |
| 7 — Governança e Segurança | `src/layer7_governance/governance.py` | `POLITICA_SINTESE`, `validar_resposta()`, `recusar_parecer_juridico()`, `recusar_fora_de_escopo()`, `recusar_sem_base()`, `validar_fonte_publica()` |
| 8 — Observabilidade e Proveniência | `src/layer8_observability/observability.py` | `registrar_interacao()` |

## Três caminhos de fluxo (visíveis no diagrama)

1. **Recusa direta** (`parecer_juridico` / `fora_de_escopo`): `_interpretar`
   → `_RECUSAS` → função de recusa fixa da Camada 7 → Camada 8 — sem
   nenhuma chamada às Camadas 4, 5 ou 6 para buscar ou sintetizar, e sem
   segunda chamada ao LLM (só a classificação). É o caminho ~80x mais rápido
   observado no benchmark (`docs/tabela_resultados_empiricos.csv`,
   `docs/evidencias_empiricas.md`).
2. **Recusa sem base**: `_interpretar` → `_buscar_normativo` (Camadas 4→5)
   devolve `NENHUM_TRECHO_ENCONTRADO` → `recusar_sem_base()` (Camada 7) →
   Camada 8 — sem síntese. Só ocorre quando algum limiar está ligado ou a
   recuperação não acha trecho algum.
3. **Caminho normativo**: `_interpretar` → `_buscar_normativo` (Camadas 4→5)
   → `_sintetizar_resposta` (Camadas 2 e 6, com `POLITICA_SINTESE` da
   Camada 7 como `system`) → `_validar_resposta` (`validar_resposta()` da
   Camada 7) → Camada 8 — duas chamadas ao LLM (classificação + síntese), o
   que explica a latência maior e mais variável observada.

Em todos os caminhos a Camada 8 registra um registro por interação, com o
`desfecho` e o campo `recuperacao` (modo, modelo e versão dos índices).
