# Estado Atual do Protótipo (para retomar em outra sessão)

**Última atualização**: 2026-09-24 (preparação para publicação no GitHub:
benchmark em modo determinístico, ingestão por URL oficial, dado bruto
versionado, versões fixadas, README movido para a raiz do repositório — ver
seção "Reprodutibilidade e publicação" abaixo).

Este documento é um resumo de handoff — para o histórico completo de
decisões e evidências, ver `docs/decisoes_arquitetura.md` e
`docs/evidencias_empiricas.md`, que são as fontes primárias. Este arquivo
só resume o estado para retomar o trabalho rapidamente, em nova sessão.

## Onde estamos na sequência de construção (ver README.md)

1. ✅ Esqueleto do repo + Camada 2 (Núcleo de Raciocínio)
2. ✅ `run_check.py` validado pelo usuário
3. ✅ Camada 3 (Orquestração) — `src/layer3_orchestration/orchestrator.py`
4. ✅ Camada 5 (Conhecimento/RAG) — `src/layer5_knowledge/knowledge_base.py`
5. ✅ Camada 4 (Ferramentas) — `src/layer4_tools/tools.py`
6. ✅ Camada 6 (Memória) — `src/layer6_memory/memory.py`
7. ✅ Camada 7 (Governança) — `src/layer7_governance/governance.py`
8. ✅ Camada 8 (Observabilidade) — `src/layer8_observability/observability.py`
9. ✅ Camada 1 (Interação/CLI) — `src/layer1_interaction/cli.py` (`python main.py`)
10. ✅ Casos de teste documentados em `tests/casos_teste.md` (4 casos)
11. ✅ Benchmark quantitativo (`tests/casos_teste.json` + `run_benchmark.py`), 20
    execuções (4 cenários x 5 repetições) rodadas com sucesso — ver seção
    "Benchmark quantitativo" abaixo.

Cada camada implementada tem: código em `src/layerN_*/`, script de
validação `run_check_*.py` na raiz, entrada em
`docs/decisoes_arquitetura.md`, e (quando relevante) entrada em
`docs/evidencias_empiricas.md`.

## Como validar o que já existe

```bash
python run_check.py                # Camada 2
python run_check_orchestration.py  # Camada 3, fluxo completo (3 perguntas: normativa, acompanhamento, parecer jurídico)
python run_check_knowledge.py      # Camada 5
python run_check_tools.py          # Camada 4
python run_check_memory.py         # Camada 6
python run_check_governance.py     # Camada 7
python run_check_observability.py  # Camada 8
```

Nota de ambiente: neste ambiente Windows, `python` só resolve corretamente
dentro do venv do projeto (`venv\Scripts\activate`) ou usando o caminho
completo `C:\Users\pedro\AppData\Local\Programs\Python\Python314\python.exe`
— sessões de shell abertas antes da instalação do Python não pegam o PATH
atualizado.

## Corpus atual (Camada 5) — `data/normativos/`

Indexados com texto integral:
- `resolucao_conjunta_1_2020.md` — Resolução Conjunta nº 1/2020 (marco do Open Finance)
- `circular_4015_2020.md` — Circular nº 4.015/2020 (escopo de dados e serviços)

Pendentes (ver `data/normativos/PENDENTES.md`) — ementa/citação confirmadas,
texto oficial ainda não localizado com segurança:
- Resolução BCB nº 339/2023 (duplicata escritural) — há uma página oficial
  de referência confirmada (`bcb.gov.br/estabilidadefinanceira/duplicatas-escriturais`),
  mas não o PDF direto.
- Resolução BCB nº 32/2020 (requisitos técnicos) — nem página nem PDF confirmados.

## Principais achados empíricos até agora (ver `docs/evidencias_empiricas.md` para detalhes)

1. Sem Camada 5/7: o modelo citou uma norma inventada ("Resolução do CPM 4.665/2021").
2. Com Camada 5 (contexto real), o modelo ainda distorceu um número presente no próprio contexto (disse "50 mil clientes" onde o texto dizia "cinco milhões").
3. Erro de atribuição de artigo ("art. 51" em vez do correto Art. 6º) apareceu em execuções independentes — padrão recorrente, não isolado.
4. Camada 7 pegou corretamente uma citação de artigo não presente no contexto em teste controlado.
5. Bug de implementação encontrado e corrigido: memória guardava a resposta já com o disclaimer de governança anexado, causando eco/duplicação do disclaimer em turnos seguintes.
6. Limitação conhecida, não corrigida: `validar_citacao` só valida contra o contexto normativo do turno atual, não contra o que está na memória de turnos anteriores — pode gerar aviso "tecnicamente correto" mas que soa como falso positivo ao ler a conversa inteira.
7. `logs/interacoes.jsonl` (Camada 8), gerado ao rodar `run_check_orchestration.py` com as 3 perguntas de teste, confirma em registro estruturado o padrão do achado 3: a segunda pergunta tem `aviso_citacao_nao_verificada: true`, citando "art. 6, 36" fora do trecho normativo daquele turno — mesma classe de erro de atribuição de artigo, agora capturada também na proveniência, não só no texto da resposta.
8. Gap encontrado ao formalizar `tests/casos_teste.md` (Caso 4): a classificação `fora_de_escopo` (Camada 3) era calculada corretamente, mas — diferente de `parecer_juridico` — não desviava o fluxo, causando busca normativa sem sentido e disclaimer de compliance indevido. **Corrigido na mesma sessão** — `_RECUSAS` generalizou o desvio já usado para `parecer_juridico`; ver `tests/casos_teste.md`, Caso 4 (execução 2, após a correção).

## Convenções de trabalho estabelecidas nesta sessão (aplicar nas próximas)

- Propor o plano de cada camada e aguardar aprovação antes de implementar — camada por camada, não tudo de uma vez.
- Atualizar `docs/decisoes_arquitetura.md` a cada camada (decisão, motivação, ambiguidade, adaptação).
- Registrar observações de teste (comportamento do modelo, bugs encontrados) em `docs/evidencias_empiricas.md`, separado das decisões de projeto.
- Fontes do corpus: só atos normativos públicos e oficiais do BACEN — nunca conhecimento interno/proprietário de instituição financeira (o usuário trabalha em fintech PJ — conflito de interesse a evitar).
- Preferir decisões de implementação mínimas e explícitas (funções simples em vez de abstrações genéricas) até haver um segundo caso de uso real que justifique generalizar — aplicado nas Camadas 4 e 6.

## Benchmark quantitativo (2026-09-22)

Complementa os 4 casos qualitativos de `tests/casos_teste.md` (uma execução
cada) com dado quantitativo (múltiplas repetições, latência):

- `tests/casos_teste.json` — os mesmos 4 cenários (Caminho Feliz/RAG BACEN,
  Norma Ausente/Fronteira, Parecer Jurídico/Governança, Fora de
  Escopo/Governança), em formato estruturado para o benchmark.
- `run_benchmark.py` — roda cada cenário 5x contra o Ollama local (sessão
  nova por execução), mede latência e lê `orchestrator.ultimo_registro`
  (Camada 8) para capturar classificação, recusa (Camada 7) e aviso de
  citação não verificada.
- `logs/resultados_benchmark.json` — 20 registros brutos (git-ignorado,
  como o resto de `logs/`).
- `docs/tabela_resultados_empiricos.csv` — tabela agregada por cenário
  (via pandas), versionada — é o artefato citável na monografia.

Rodar de novo: `venv\Scripts\python.exe run_benchmark.py` (usa o venv, que
agora tem `pandas` instalado — `requirements.txt` atualizado).

Resultado da primeira execução (100% classificação correta nos 4 cenários,
60% de taxa de aviso de citação não verificada no cenário de norma ausente,
latência ~80x menor nas recusas que no fluxo normativo): análise completa
em `docs/evidencias_empiricas.md` (entrada de 2026-09-22) e decisão de
projeto em `docs/decisoes_arquitetura.md` ("Benchmark Empírico").

## Artefatos visuais para o Capítulo 3 (2026-09-23)

Geração de gráficos e do diagrama de arquitetura **concluída com sucesso**,
prontos para inclusão no Capítulo 3 da monografia:

- `docs/diagrama_arquitetura.md` — diagrama de componentes em Mermaid
  (`graph TD`), mapeando 1:1 as 8 camadas de Maia et al. (2026) às pastas
  `src/layerN_*/` reais, com o fluxo de dados completo (caminho de recusa da
  Camada 7 vs. caminho normativo com RAG). Inclui nota explícita: a Camada 5
  usa busca lexical simples sobre Markdown, **não** uma arquitetura em
  camadas "medalhão" (Bronze/Silver/Gold) — o diagrama reflete o código real,
  não uma versão idealizada (ver `docs/decisoes_arquitetura.md`, seção
  "Benchmark Empírico", para o registro dessa checagem).
- `scripts/plot_benchmark.py` — lê `docs/tabela_resultados_empiricos.csv` e
  gera, via `matplotlib`/`seaborn` (300 DPI, adicionados a
  `requirements.txt`):
  - `docs/figuras/grafico_latencia_cenarios.png` — latência média por
    cenário, com barra de erro e anotação do fator de aceleração calculado a
    partir dos dados (~75x mais rápido na recusa direta vs. fluxo normativo
    completo).
  - `docs/figuras/grafico_taxas_governanca.png` — taxa de recusa e taxa de
    aviso de citação não verificada por cenário, com destaque no
    comportamento de borda do cenário de norma ausente (60%).

Rodar de novo: `venv\Scripts\python.exe scripts\plot_benchmark.py` (regenera
as duas figuras a partir do CSV já versionado; não depende do Ollama).

## Polimento final e Apêndice A (2026-09-23)

Três tarefas de finalização, **concluídas com sucesso**:

1. **`README.md` reescrito** como guia de reprodutibilidade científica
   completo: visão geral, pré-requisitos, instalação, como subir o Ollama,
   como reproduzir o benchmark e os gráficos (Seção 6), como validar cada
   camada isoladamente, árvore de pastas completa (`src/layer1_interaction/`
   a `layer8_observability/` e o resto do repositório), fontes de dados e
   ponteiros para `docs/decisoes_arquitetura.md`/`docs/estado_atual.md`.

2. **`docs/apendice_casos_teste.md`** — Apêndice A da monografia, gerado a
   partir de `tests/casos_teste.json`: tabela-resumo dos 4 cenários (CT01–
   CT04) e detalhamento individual de cada um, com resultado empírico
   (dados reais de `docs/tabela_resultados_empiricos.csv`) e justificativa
   de enquadramento segundo os critérios de avaliação de artefatos de
   Hevner et al. (2004) — pronto para cópia no corpo da monografia.

3. **`src/layer5_knowledge/ingest_normativos.py`** — pipeline de ingestão
   Bronze/Silver/Gold (`data/normativos/1_bronze_raw/`, `2_silver_cleaned/`,
   `3_gold_indexed/`), executável via `python -m
   src.layer5_knowledge.ingest_normativos` ou diretamente. **Importante**:
   este pipeline é **paralelo/ilustrativo**, não está ligado ao runtime —
   `knowledge_base.py` continua sendo a implementação real da Camada 5
   (busca lexical sobre `data/normativos/*.md`), validada no benchmark e
   nos casos de teste. A pedido original desta tarefa incluía reescrever
   `knowledge_base.py` para consumir o índice Gold, mas isso reorganizaria o
   corpus já curado e alteraria uma camada já validada — o risco foi
   levantado ao usuário, que optou por manter o runtime intocado (decisão e
   justificativa completas em `docs/decisoes_arquitetura.md`, extensão de
   2026-09-23 na seção "Benchmark Empírico"). Confirmado após rodar o
   script: `data/normativos/*.md` sem alteração (`git status` limpo) e
   `KnowledgeBase` continua carregando os mesmos 67 documentos de antes.

   **Teste adicional (mesmo dia)**: usuário anexou 2 PDFs reais (Instrução
   Normativa BCB nº 759/2026 e Resolução BCB nº 1/2020 — Pix) para testar o
   pipeline contra entrada bruta de verdade, não só `.md` já curado.
   Estendido `ingest_normativos.py` para extrair PDF via `pypdf` (novo em
   `requirements.txt`) com metadados por heurística de regex — sempre
   marcados `fonte_confirmada: false` e `url_oficial: ""`, nunca
   apresentados como curados. PDFs vivem em `data/normativos/*.pdf`
   (gitignorado, mesma convenção já usada na extração manual original da
   Camada 5). Achado técnico: `pypdf` corrompeu a ligadura "ti" em parte do
   texto do PDF do Pix (`Institui` -> `Ins�tui`) — artefato de extração
   diferente do já documentado, reforça por que curadoria manual continua
   necessária antes de qualquer inclusão no corpus real. Detalhes completos
   em `docs/decisoes_arquitetura.md`. Corpus real e `KnowledgeBase`
   reconfirmados intocados após o teste.

## Reprodutibilidade e publicação (2026-09-24)

Detalhes em `docs/decisoes_arquitetura.md` ("Reprodutibilidade") e
`docs/evidencias_empiricas.md` (2026-09-24).

- `LLMCore(options=...)` e `run_benchmark.py --modo {livre,deterministico}`.
  Modo determinístico: 1 resposta distinta por cenário em 5 repetições;
  aviso de citação no cenário "norma ausente" = 100% (vs. 60% no livre).
- `run_benchmark.py --somente-tabela` regera o CSV a partir do JSON bruto
  sem Ollama. JSONs brutos agora em `docs/resultados/` (versionados).
- `ingest_normativos.py` lê `data/normativos/fontes_url.json` (URLs
  oficiais da Resolução BCB 1/2020 e IN BCB 759/2026) via API do BCB, em vez
  de PDFs locais. `pypdf` removido. Continua fora do runtime.
- `requirements-lock.txt` com versões exatas; `.gitignore` na raiz ignora
  `*.rar`/`*.zip`; `_openfinance_limpo.md` movido para fora do repositório.
- `README.md` passou para a raiz do repositório, com tutorial de
  reprodução passo a passo.

## Próximo passo sugerido

Todos os itens da sequência de construção original (README.md) estão
concluídos: 8 camadas implementadas e ligadas ponta a ponta, 4 casos de
teste formais documentados em `tests/casos_teste.md`, e agora também um
benchmark quantitativo de 20 execuções.

Com o protótipo completo, a evidência quantitativa levantada, os artefatos
visuais do Capítulo 3 gerados (diagrama + 2 gráficos), e o polimento final
do repositório (README, Apêndice A, esteira de ingestão documentada), o
próximo passo de mais alto nível passa a ser de síntese para a monografia,
não mais de construção: revisar `docs/decisoes_arquitetura.md` e
`docs/evidencias_empiricas.md` como um todo, junto com
`docs/tabela_resultados_empiricos.csv`, `docs/diagrama_arquitetura.md`,
`docs/figuras/` e `docs/apendice_casos_teste.md`, para compilar a análise de
viabilidade (Capítulo 1, Seção 5, itens d/e), redigir o Capítulo 3 e
finalizar os apêndices para a banca examinadora.
