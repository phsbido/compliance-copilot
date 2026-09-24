# Diagrama de Arquitetura

Diagrama de componentes do protótipo, mapeando 1:1 as 8 camadas conceituais
de Maia et al. (2026, Seção 8) às pastas/módulos concretos do repositório, e
o fluxo de dados de uma interação completa (`Orchestrator.responder()`, ver
`src/layer3_orchestration/orchestrator.py`).

Gerado a partir da inspeção do código-fonte real em `src/layerN_*/`
(2026-09-22) — nomes de classes, funções e arquivos abaixo correspondem
literalmente à implementação, não a uma versão idealizada da arquitetura.
Ver `docs/decisoes_arquitetura.md` para a justificativa de cada decisão de
projeto por trás de cada camada.

**Nota sobre a Camada 5**: a base de conhecimento (`KnowledgeBase`) usa
busca lexical simples (sobreposição de tokens, sem stopwords/acentos) sobre
arquivos Markdown em `data/normativos/` — **não** há arquitetura em camadas
Bronze/Silver/Gold ("medalhão") nem embeddings/vector DB nesta
implementação (decisão registrada em `docs/decisoes_arquitetura.md`,
Camada 5). O diagrama reflete isso.

```mermaid
graph TD
    Usuario(["Usuário"])

    subgraph C1["Camada 1 — Interação — src/layer1_interaction/cli.py"]
        CLI["main() — loop CLI"]
    end

    subgraph C3["Camada 3 — Orquestração — src/layer3_orchestration/orchestrator.py"]
        ORC["Orchestrator.responder()"]
        INTERP["_interpretar()"]
        RECUSAS{"tipo em _RECUSAS?"}
        BUSCA["_buscar_normativo()"]
        SINT["_sintetizar_resposta()"]
        VALID["_validar_citacao()"]
    end

    subgraph C2["Camada 2 — Núcleo de Raciocínio LLM — src/layer2_llm_core/core.py"]
        LLM["LLMCore.generate()\n(ollama.chat, modelo llama3.1)"]
    end

    subgraph C4["Camada 4 — Ferramentas — src/layer4_tools/tools.py"]
        TOOL["buscar_normativo()"]
    end

    subgraph C5["Camada 5 — Conhecimento / RAG — src/layer5_knowledge/knowledge_base.py"]
        KB["KnowledgeBase.buscar()\nbusca lexical por sobreposição de tokens\n(sem embeddings, sem medalhão)"]
        CORPUS[("data/normativos/*.md\n(2 normativos indexados,\n2 pendentes)")]
    end

    subgraph C6["Camada 6 — Memória — src/layer6_memory/memory.py"]
        MEM["Memoria\n(buffer das últimas 5 interações\nem processo, sem persistência)"]
    end

    subgraph C7["Camada 7 — Governança — src/layer7_governance/governance.py"]
        GOVVALID["validar_citacao()\n(regex: artigo/norma citados\nvs. contexto do turno)"]
        GOVREC1["recusar_parecer_juridico()"]
        GOVREC2["recusar_fora_de_escopo()"]
    end

    subgraph C8["Camada 8 — Observabilidade — src/layer8_observability/observability.py"]
        OBS["registrar_interacao()"]
        LOG[("logs/interacoes.jsonl\n(JSON Lines, append-only)")]
    end

    Usuario -->|pergunta em texto| CLI
    CLI -->|"responder(pergunta)"| ORC
    ORC --> INTERP
    INTERP -->|classifica: normativo /\nparecer_juridico / fora_de_escopo| LLM
    INTERP --> RECUSAS

    RECUSAS -->|parecer_juridico| GOVREC1
    RECUSAS -->|fora_de_escopo| GOVREC2
    RECUSAS -->|normativo| BUSCA

    BUSCA --> TOOL
    TOOL --> KB
    KB --> CORPUS
    KB -->|trechos citáveis\nFonte + URL + texto| TOOL
    TOOL -->|contexto normativo| BUSCA
    BUSCA --> SINT

    MEM -->|histórico formatado\nda sessão| SINT
    SINT -->|prompt: histórico + contexto\n+ pergunta| LLM
    LLM -->|resposta sintetizada| SINT
    SINT --> VALID
    VALID --> GOVVALID
    GOVVALID -->|resposta + avisos\n+ disclaimer de validação humana| VALID

    ORC -->|adicionar pergunta + resposta\n(pré-validação, sem avisos)| MEM

    GOVREC1 --> OBS
    GOVREC2 --> OBS
    VALID -->|resposta final| OBS
    OBS --> LOG
    OBS -->|RegistroInteracao\n(ultimo_registro)| ORC

    ORC -->|resposta final +\nproveniência da Camada 8| CLI
    CLI -->|resposta + fontes\n+ avisos| Usuario
```

## Legenda — camada conceitual → pasta/módulo

| Camada (Maia et al., 2026) | Pasta / arquivo | Classe/função principal |
|---|---|---|
| 1 — Interação com o Usuário | `src/layer1_interaction/cli.py` | `main()` |
| 2 — Núcleo de Raciocínio do LLM | `src/layer2_llm_core/core.py` | `LLMCore.generate()` |
| 3 — Orquestração e Fluxo de Trabalho | `src/layer3_orchestration/orchestrator.py` | `Orchestrator.responder()` |
| 4 — Integração de Ferramentas e Serviços | `src/layer4_tools/tools.py` | `buscar_normativo()` |
| 5 — Integração de Conhecimento (RAG) | `src/layer5_knowledge/knowledge_base.py` | `KnowledgeBase.buscar()` |
| 6 — Contexto e Memória | `src/layer6_memory/memory.py` | `Memoria` |
| 7 — Governança e Segurança | `src/layer7_governance/governance.py` | `validar_citacao()`, `recusar_parecer_juridico()`, `recusar_fora_de_escopo()` |
| 8 — Observabilidade e Proveniência | `src/layer8_observability/observability.py` | `registrar_interacao()` |

## Dois caminhos de fluxo (visíveis no diagrama)

1. **Caminho de recusa** (`parecer_juridico` / `fora_de_escopo`): `_interpretar`
   → `_RECUSAS` → função de recusa fixa da Camada 7 → Camada 8 — sem
   nenhuma chamada às Camadas 4, 5 ou 6, e sem segunda chamada ao LLM (só a
   classificação). É o caminho ~80x mais rápido observado no benchmark
   (`docs/tabela_resultados_empiricos.csv`, `docs/evidencias_empiricas.md`).
2. **Caminho normativo**: `_interpretar` → `_buscar_normativo` (Camadas 4→5)
   → `_sintetizar_resposta` (Camadas 2+6) → `_validar_citacao` (Camada 7) →
   Camada 8 — duas chamadas ao LLM (classificação + síntese), o que explica
   a latência maior e mais variável observada.
