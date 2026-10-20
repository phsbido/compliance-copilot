# Glossário

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Termos de domínio (Open Finance / regulatório)

- **Open Finance**: compartilhamento padronizado de dados e serviços
  financeiros entre instituições, mediante consentimento do cliente —
  definido no Art. 2º, I, da Resolução Conjunta nº 1/2020
  (`data/normativos/resolucao_conjunta_1_2020.md:32-34`).
- **BACEN / BCB**: Banco Central do Brasil — autoridade reguladora cujos
  atos normativos formam o único corpus de conhecimento permitido no
  projeto (`data/normativos/README.md:15-20`).
- **Instituição participante**: instituição financeira, de pagamento ou
  outra autorizada a funcionar pelo BCB, sujeita às regras de Open Finance
  (Resolução Conjunta nº 1/2020, Art. 1º).
- **Parecer jurídico definitivo**: decisão jurídica conclusiva sobre um caso
  concreto — o sistema é desenhado para **nunca** emitir isso (Camada 7),
  só indicar o que normas dizem em geral (`governance.py:36-42`).
- **Resolução Conjunta / Resolução BCB / Circular / Instrução Normativa**:
  tipos de ato normativo brasileiro, cada um com hierarquia/procedimento
  próprios — todos casados pela regex `_NORMA_REGEX`
  (`governance.py:25-28`) e `_TITULO_PDF_REGEX`
  (`ingest_normativos.py:89-94`).
- **Art. / Artigo, § / Parágrafo, Inciso**: unidades de subdivisão de um ato
  normativo brasileiro — o "artigo" é tratado como a unidade natural de
  citação em todo o sistema (`knowledge_base.py:66-69`).
- **CPM**: Comitê de Política Monetária — citado em
  `docs/evidencias_empiricas.md:32-41` como parte de uma citação **fabricada**
  pelo modelo ("Resolução do CPM 4.665/2021"), não um órgão real emissor de
  resoluções nesse formato — mencionado aqui só para registrar que é
  exemplo de alucinação, não um termo válido do domínio.

## Termos e nomes internos do projeto

- **Camada N** (Camada 1 a 8): as 8 camadas da arquitetura conceitual de
  Maia et al. (2026, Seção 8), cada uma mapeada 1:1 a uma pasta
  `src/layerN_*/` — ver `docs/diagrama_arquitetura.md:102-113` para a
  tabela completa camada → módulo → classe/função principal.
- **Camada 3 / Orquestração**: `Orchestrator`, o "hub" que coordena as
  outras 7 camadas via `responder()` (`orchestrator.py:58-79`).
- **`_RECUSAS`**: dicionário em `orchestrator.py:36-39` que mapeia tipo de
  classificação → função de recusa da Camada 7, usado para desviar o fluxo
  antes de buscar/sintetizar.
- **Fluxo de recusa / caminho de recusa**: o caminho de execução para
  `parecer_juridico`/`fora_de_escopo` — 1 chamada ao LLM, sem RAG, ~80x mais
  rápido que o fluxo normativo (`docs/evidencias_empiricas.md:276-296`).
- **Fluxo normativo / caminho normativo**: o caminho completo —
  interpretar → buscar → sintetizar → validar — 2 chamadas ao LLM.
- **RAG**: *Retrieval-Augmented Generation* — buscar conteúdo externo
  (aqui, o corpus de normativos) para fundamentar a geração do modelo. Neste
  projeto, implementado como busca lexical simples, não semântica.
- **Busca lexical**: técnica de recuperação usada pela Camada 5 — pontua
  documentos por interseção literal de palavras (tokens) entre pergunta e
  trecho, sem embeddings (`knowledge_base.py:96-105`).
- **Corpus**: conjunto de arquivos `.md` em `data/normativos/` que formam a
  base de conhecimento real (Camada 5) — hoje, 2 normativos com texto
  integral.
- **Fonte confirmada / `fonte_confirmada`**: campo booleano usado no
  pipeline ilustrativo (`ingest_normativos.py`) e no princípio de
  transparência do corpus curado — indica se a URL/proveniência de um
  normativo foi verificada manualmente (`true`) ou inferida
  automaticamente, sem garantia (`false`).
- **Bronze / Silver / Gold (medalhão)**: as 3 etapas do pipeline
  **ilustrativo** de ingestão (`ingest_normativos.py`) — Bronze = cópia
  bruta, Silver = texto limpo e estruturado por Artigo/Parágrafo, Gold =
  metadados + estrutura combinados, pronto para indexação (mas não indexado
  de fato por nada no projeto). Ver `03_modulos/layer5_knowledge.md`.
- **`ultimo_registro`**: atributo de `Orchestrator` que guarda o
  `RegistroInteracao` (Camada 8) da última chamada a `responder()`, exposto
  para a Camada 1 mostrar proveniência sem mudar o tipo de retorno de
  `responder()` (`orchestrator.py:56`, `docs/decisoes_arquitetura.md:61-67`).
- **`Documento`**: unidade indexada pela Camada 5 — **um trecho (artigo)**,
  não um normativo inteiro (`knowledge_base.py:29-34`).
- **`RegistroInteracao`**: estrutura de proveniência gravada pela Camada 8 a
  cada interação, persistida em `logs/interacoes.jsonl`
  (`observability.py:31-38`).
- **Aviso de citação não verificada**: mensagem anexada pela Camada 7
  quando um artigo/norma citado na resposta do modelo não aparece no
  contexto normativo usado naquele turno (`governance.py:66-72,81-87`).
- **Disclaimer de validação humana**: texto fixo sempre anexado ao final de
  toda resposta do fluxo normativo, lembrando que a resposta não é parecer
  jurídico definitivo (`AVISO_VALIDACAO_HUMANA`, `governance.py:30-34`).
- **`casos_teste.md` vs. `casos_teste.json`**: `.md` é a leitura
  qualitativa detalhada de 4 casos, com execuções reais transcritas; `.json`
  é a bateria estruturada consumida por `run_benchmark.py` — 4 cenários até
  a v4.1, **66 casos em cinco grupos desde a v5** (2026-10-02), dos quais os
  4 primeiros são os cenários originais.
- **CT01–CT04**: identificadores dos 4 cenários originais no Apêndice A
  (`docs/apendice_casos_teste.md`) — correspondem, na ordem, a
  `caminho_feliz_rag_bacen`, `norma_ausente_fronteira`,
  `solicitacao_parecer_governanca`, `fora_de_escopo_governanca` em
  `tests/casos_teste.json`. Na v5, o Apêndice A organiza a bateria por grupo.
- **Grupo (v5)**: unidade de agregação do benchmark —
  `normativo_corpus`, `norma_ausente`, `parecer_juridico`, `fora_de_escopo`,
  `robustez` (`docs/tabela_resultados_por_grupo.csv`).
- **Sucesso (v5)**: o comportamento esperado do caso foi observado na
  execução (`resposta_fundamentada`, `ausencia_declarada`, `recusa` ou
  `sem_alucinacao`; `run_benchmark.py`, `avaliar_sucesso`).
- **Acerto@3, Recall@3, MRR**: métricas da recuperação da Camada 5 sobre os
  rótulos `relevantes` (norma + trecho da Gold) — algum relevante entre os 3
  trechos entregues à síntese; fração dos rótulos recuperada; média do
  inverso da posição do primeiro relevante (`docs/tabela_recuperacao.csv`).
- **`run_check_*.py`**: convenção de nome para os scripts de validação
  manual de uma camada isolada — um por camada implementada (exceto Camada
  1, que não tem script próprio, já que é testada indiretamente por todos
  os outros e pelo uso interativo de `main.py`).
- **DSR (Design Science Research)**: metodologia de pesquisa do projeto —
  construir e avaliar um artefato (o protótipo) para responder uma questão
  de viabilidade de uma arquitetura conceitual (`README.md:3-5`).
- **Hevner et al. (2004)**: referência metodológica usada para justificar o
  enquadramento de cada caso de teste no Apêndice A
  (`docs/apendice_casos_teste.md`) — critérios como "funcionalidade",
  "acurácia", "adequação ao contexto organizacional".
