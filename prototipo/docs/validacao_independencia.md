# Validação da Lacuna 1 — Independência de Implementação

Este documento consolida a evidência de que a arquitetura conceitual de Maia
et al. (2026, Seção 8) foi implementada **sem coordenação com os autores
originais e sem consulta ao código do SCRIBE**, a única instanciação
publicada pelos próprios autores.

O código do SCRIBE é **público**: o repositório `gesad-science/SCRIBE-CREW`
está no GitHub. A independência, portanto, não decorre de falta de acesso. É
uma escolha metodológica: o código foi deliberadamente não consultado, e o
repositório não foi clonado. A clonagem foi oferecida em 2026-10-01 e
recusada pelo mesmo motivo.

Este documento **não registra decisões novas de projeto**. Ele reorganiza o
que já está em `docs/decisoes_arquitetura.md` e `docs/evidencias_empiricas.md`
e, desde 2026-10-01, confronta esse registro com o texto da Seção 8 (pp. 15–17
do artigo). O confronto mostrou que parte das "ambiguidades" registradas no
diário eram, na verdade, prescrições do artigo (Seção 3).

Consolidado em 2026-10-01, sobre o estado do repositório no commit `3f554f9`.

---

## 1. Auditoria do repositório

**Escopo verificado**:

- todos os arquivos versionados (código, `docs/`, `analise/`, README,
  testes, dados de `data/normativos/`);
- o histórico completo de commits (`git log --all`, mensagens e diffs);
- as dependências (`requirements.txt`) e o remoto (`origin`);
- o arquivo local não versionado `prototipo.rar`.

**Busca realizada**: termos `SCRIBE`, `GESAD`, `UECE`, `Maia`, `et al.`,
`github.com`, `arxiv`, `doi.org`, `copiad`, `inspirad`, `baseado em` e
`adaptado de`, sem distinção de caixa.

| Verificação | Achado |
|---|---|
| Menções a SCRIBE, GESAD ou UECE em arquivos versionados | Nenhuma (antes da criação deste documento). |
| Menções a SCRIBE, GESAD ou UECE no histórico de commits | Nenhuma. Um falso positivo da busca: a sequência "uece" dentro de "aq**uece**r" (README, commit `ee2f2b1`). |
| Menções a "Maia et al." | Somente como referência à arquitetura especificada: cabeçalhos dos módulos (`src/layerN_*/*.py`, linha 2), README, `docs/` e `analise/`. Nenhuma citação de código, repositório ou documento interno dos autores. |
| Dependências de terceiros | `ollama`, `python-dotenv`, `pypdf` (runtime e ingestão); `pandas`, `matplotlib` (só scripts de avaliação; o `seaborn`, usado na primeira versão dos gráficos, foi removido no commit `0886517`). Nenhuma é do grupo de pesquisa original. Nenhum framework de orquestração de LLM foi usado (decisão registrada em `decisoes_arquitetura.md`, "Benchmark Empírico"). |
| URLs externas usadas pelo código | Somente páginas oficiais do BCB (`data/normativos/fontes_url.json`), com domínio restrito em código por `validar_fonte_publica` (`src/layer7_governance/governance.py:101`). |
| Remoto do repositório | `github.com/phsbido/prototipo_esqueleto` (repositório do autor). |
| `prototipo.rar` (não versionado, `.gitignore`) | Cópia de segurança da própria pasta `prototipo/`. A busca acusa "scribe" dentro do arquivo, mas a ocorrência é `pandas/.../describe.py`, no `venv` empacotado. |
| Referências externas **públicas** que influenciaram decisões | BM25 (Camada 5); radicalização "inspirada nas etapas" do RSLP (`src/layer5_knowledge/texto.py:42`); padrão Bronze/Silver/Gold de engenharia de dados (Camada 5). Nenhuma provém dos autores de Maia et al. Hevner et al. (2004) entra como referência de **método** (enquadramento DSR dos cenários de avaliação), não de projeto: nenhuma decisão de arquitetura do diário se apoia nele. |

**Conclusão da auditoria**: nenhum achado contradiz a independência.

**Limites da auditoria**:

- **Fora do repositório.** A auditoria prova a ausência *no repositório*. A
  ausência de comunicação com os autores é uma declaração do autor (ver
  Seção 5).
- **Ordem da construção.** O histórico do git não comprova a construção
  camada por camada: as 8 camadas e o `decisoes_arquitetura.md` com as 8
  seções entraram num único commit inicial (`34dbc2e`, 2026-08-14). A ordem
  das decisões depende das datas registradas nos documentos. Os commits a
  partir de 2026-09-24 são granulares por camada.
- **Leitura da Seção 9.** Em 2026-10-01, junto com as páginas da Seção 8,
  foi lida a p. 18, que contém o início da Seção 9 (descrição do SCRIBE no
  próprio artigo: perfil *workflow-centric*, interface conversacional, LLM
  core com *structured output schemas* e um fluxo de cinco fases). É texto
  público do artigo, não código, e foi lido depois de todas as decisões
  registradas aqui. Nenhuma decisão do protótipo o usou.

---

## 2. Decisões tomadas sem apoio dos autores, por camada

**Numeração das camadas.** O próprio artigo é inconsistente. O texto da
Seção 8.1 (pp. 15–17) apresenta as camadas sem número, na ordem Interação,
LLM Core, Orquestração, **Ferramentas e Serviços, Conhecimento, Contexto e
Memória**, Governança, Observabilidade. A Figura 4 (p. 16) numera **4 =
Knowledge Integration, 5 = Context & Memory, 6 = Tool & Service
Integration**. O protótipo segue a ordem do texto (`layer4_tools`,
`layer5_knowledge`, `layer6_memory`), e é ela que esta tabela usa. É uma
ambiguidade real do artigo, resolvida por escolha própria e até aqui não
registrada no diário.

A coluna "O que prescreve" resume o texto da Seção 8 (8.1 e práticas da
8.3), com as expressões originais entre aspas. A coluna "Onde foi ambígua"
traz só o que **resiste** ao confronto com o texto. As ambiguidades do
diário que o texto contesta estão na Seção 3.

| Camada | O que Maia et al. (2026, Seção 8) prescreve | Onde a prescrição foi ambígua/insuficiente | Decisão tomada de forma independente | Evidência (arquivo e trecho de código ou commit) |
|---|---|---|---|---|
| **1 — Interação com o Usuário** | Interfaces como UIs conversacionais, *dashboards*, voz e IDEs; a camada "is not merely a frontend, but a source of structured intent signals, constraints, and feedback loops" (p. 15). Figura 4: usuários humanos, UI (Web, Mobile, CLI), APIs e sistemas externos. | Não diz se a interface deve expor artefatos de outras camadas, como a proveniência da Camada 8. | CLI de texto com um `Orchestrator` por sessão. As fontes consultadas vêm na própria resposta, anexadas pela Camada 7 v2, em vez do log JSON bruto, por razão de domínio: em compliance, a transparência sobre a fonte é parte do valor central. A CLI só destaca, depois da resposta, quando a Camada 7 encontrou algo não verificado. A captura de intenção estruturada, restrições e *feedback* **não foi implementada**: a pergunta é texto livre. | `decisoes_arquitetura.md`, "Camada 1"; `src/layer1_interaction/cli.py:32`; `src/layer3_orchestration/orchestrator.py:85,96,111` (`ultimo_registro`); commit `34dbc2e`. |
| **2 — Núcleo de Raciocínio do LLM** | "Responsible for interpreting user intents, synthesizing intermediate reasoning artifacts, and producing structured outputs"; gera "plans, tool calls, decision rationales, and evidence-backed responses"; pode ser um modelo, vários ou multiagente (p. 16). Figura 4: *Guardrails & Model Controls*. | A Figura 4 nomeia *Model Controls*, mas o texto não diz quais controles nem com que critério. O controle de aleatoriedade mostrou ter efeito de governança (a classificação decide a recusa) e de reprodutibilidade, e essa decisão teve de ser tomada sem orientação. | Modelo local `llama3.1` via Ollama, num wrapper fino (`LLMCore`). Na v4: classificação com temperatura 0, síntese com 0,1, seed 42, por etapa. Antes disso valia o padrão implícito do Ollama, usado sem decisão. A decisão ficou distribuída entre a Camada 2 (executa), `config.py` (define), a Camada 3 (escolhe por etapa) e a Camada 8 (registra). Planos, chamadas de ferramenta e saídas estruturadas **não foram implementados**: o LLM só classifica e sintetiza texto. | `decisoes_arquitetura.md`, "Camada 2" e "Parâmetros de amostragem explícitos (v4)"; `src/layer2_llm_core/core.py:31`; `src/config.py:33` (`ParametrosAmostragem`); commit `c6644d8`. |
| **3 — Orquestração e Fluxo de Trabalho** | Controla a execução de tarefas em vários passos: "planning, delegation, retries, checkpointing, and termination". Pode ser motor de *workflow*, máquina de estados, *planner-executor* ou multiagente, e "must handle partial failures and uncertainty" (p. 16). Prática 2: separar a lógica de orquestração do raciocínio do modelo (p. 17). | (a) Não define como uma camada se comporta enquanto as camadas de que depende ainda não existem: a arquitetura descreve o sistema completo, não a construção incremental. (b) A forma de implementação é deixada em aberto (lista de opções). | Fluxo fixo em 4 etapas sob um único `responder()`, que funciona como máquina de estados mínima, com stubs explícitos durante a construção. O roteamento para recusa (`_RECUSAS`) foi generalizado depois do achado de 2026-08-15. Isso é coerente com a Prática 2: o fluxo está em código, não no prompt. *Retries*, *checkpointing* e tratamento de falha parcial **não foram implementados**. | `decisoes_arquitetura.md`, "Camada 3"; `evidencias_empiricas.md`, 2026-08-15; `src/layer3_orchestration/orchestrator.py:43` (`_RECUSAS`), `:79`; commit `34dbc2e`. |
| **4 — Integração de Ferramentas e Serviços** | Expõe APIs externas, *sandboxes* de execução de código, bancos de dados e serviços como ferramentas; "the primary architectural goal of this layer is to provide typed and auditable interfaces"; prevê tratamento de erro e *fallback* (p. 16). Prática 1: ferramentas como subsistemas de primeira classe, com interfaces explícitas, critérios de avaliação e *hooks* de observabilidade (p. 17). | Nenhuma ambiguidade registrada resiste ao texto (ver Seção 3). | Uma única ferramenta, `buscar_normativo`, que devolve texto pronto para o prompt (`str`), sem abstração de ferramenta, por haver um único caso de uso. Em relação ao texto, isso é um **desvio**: a interface não é tipada, e a ferramenta só embrulha a Camada 5. | `decisoes_arquitetura.md`, "Camada 4"; `src/layer4_tools/tools.py:24` (`-> str`); commit `34dbc2e`. |
| **5 — Integração de Conhecimento (RAG)** | Pipelines de recuperação "including document ingestion, chunking, embedding generation, indexing, hybrid retrieval, reranking, and citation packaging"; a recuperação deve ser tratada como "runtime subsystem with its own observability and evaluation requirements" (p. 16). | O texto pressupõe fontes prontas para ingestão. No domínio regulatório brasileiro, não são: o portal do BCB é uma SPA; uma URL "plausível" devolveu outra norma (Res. 339 de 1975); para normas anteriores a 2021, o HTML da página traz a redação **original**, e o texto vigente só existe no PDF consolidado. Decidir *qual representação da fonte é a vigente* não é coberto pela prescrição. | Pipeline Bronze/Silver/Gold a partir das URLs oficiais, com o PDF consolidado escolhido quando existe e as anotações de alteração como metadado. Para a recuperação, BM25 lexical **em vez de** *embeddings*, híbrido e *reranking*: um desvio deliberado do texto, justificado por auditabilidade, com a busca ajustada por casos observados. Normas sem fonte verificada ficam em `PENDENTES.md`. | `decisoes_arquitetura.md`, "Camada 5" e "Revisão da Camada 5"; `evidencias_empiricas.md`, 2026-08-14 (Res. 339) e 2026-09-24 (Camada 5 v2); `src/layer5_knowledge/ingest_normativos.py:117`; `src/layer5_knowledge/knowledge_base.py:42,91`; commits `34dbc2e`, `dc13930`. |
| **6 — Contexto e Memória** | Contexto de curto prazo ("conversation history, intermediate tool results, and active execution traces") e de longo prazo (preferências, planos passados, *workflows* aprendidos); a memória "actively shapes orchestration and reasoning, requiring explicit memory retrieval strategies and relevance filtering"; há riscos de privacidade e governança na retenção (pp. 16–17). | O texto não define tamanho da janela, formato de injeção nem estratégia de seleção ("relevance filtering" é citado, sem critério). | *Buffer* das últimas N=5 interações em memória de processo, injetado como texto só na síntese. A memória de longo prazo foi declarada fora de escopo. Correção de integração com a Camada 7: a memória guarda a resposta antes dos avisos. Em relação ao texto, há dois **desvios**: não há memória de longo prazo, e a memória não influencia a orquestração. | `decisoes_arquitetura.md`, "Camada 6"; `evidencias_empiricas.md`, 2026-08-14 (Observação 2); `src/layer6_memory/memory.py:21,31`; commit `34dbc2e`. |
| **7 — Governança e Segurança** | Impõe restrições "through policies, validators, permission checks, and human-in-the-loop approval points"; inclui "prompt filtering, output validation, bias checks, privacy rules, access control" (p. 17). Prática 3: aplicações críticas "cannot rely on prompt-level constraints alone"; validadores explícitos devem validar saídas (p. 17). Figura 4: governança é **transversal** (*cross-cutting*). | (a) O texto prescreve "output validation", mas não diz o que validar nem como. Validar citação normativa (norma, artigo, valor, ausência declarada) foi decidido pelo domínio. (b) Não define o alcance da validação diante da memória: só o turno ou a conversa inteira. | Validação determinística por regex, e não um LLM verificador, desenhada a partir dos erros observados (norma inventada, número distorcido, artigo errado). Na v2, a governança atua antes da geração (`POLITICA_SINTESE`, `recusar_sem_base`), depois (`validar_resposta`) e na ingestão (`validar_fonte_publica`), o que é coerente com a Prática 3 e com o caráter transversal da Figura 4. O alcance foi restrito ao turno, com a limitação documentada. Aprovação humana ativa (há só um aviso), controle de acesso e checagem de viés **não foram implementados**. | `decisoes_arquitetura.md`, "Camada 7" e "Camada 7 v2"; `evidencias_empiricas.md`, 2026-08-14 a 2026-09-24; `src/layer7_governance/governance.py:39,101,372`; `tests/test_governanca.py`; commits `7bcff9f`, `304f0d3`. |
| **8 — Observabilidade e Proveniência** | Registra o rastro de execução, "including prompts, intermediate reasoning artifacts, tool calls, retrieval results, memory accesses, and policy decisions"; liga as saídas à evidência e "to versioned models and indexes"; serve a *debugging*, reprodutibilidade, auditoria e "performance monitoring" (p. 17). Prática 4: registrar resultados de ferramentas, evidência recuperada, acessos à memória e versões do modelo. Figura 4: *Logging & Tracing*, *Monitoring & Alerting*, *Evaluation & Quality Metrics*, *Feedback Loops*. | O texto lista o que registrar, mas não o formato nem a granularidade do registro. | JSON Lines *append-only* com classificação, fontes (título e URL), desfecho, categorias da validação e, desde a v4, modelo, ID do modelo, temperaturas e seed (atende "versioned models"). Em relação ao texto, **ficaram de fora do log de runtime** o prompt, os trechos recuperados (guardados só pelo benchmark), os acessos à memória, a versão do índice, o monitoramento e o *feedback*. | `decisoes_arquitetura.md`, "Camada 8" e "Parâmetros de amostragem explícitos (v4)"; `src/layer8_observability/observability.py:41-51,69`; commits `34dbc2e`, `c6644d8`. |

---

## 3. Ambiguidades do diário contestadas pelo texto da Seção 8

O diário (`decisoes_arquitetura.md`) registrou como "ambiguidade/lacuna da
arquitetura" pontos que o texto da Seção 8 prescreve. Esses registros
**não são retificados no diário**, que é um registro datado e contemporâneo.
São reclassificados aqui. Nenhum deles afeta a independência: são decisões
tomadas sem os autores, mas a partir de uma leitura incompleta do artigo, e
não por omissão dele.

| Camada | O que o diário registrou como ambiguidade | O que o texto diz | Reclassificação |
|---|---|---|---|
| 3 | A fronteira entre orquestrar e aplicar restrições não é explícita: a classificação `parecer_juridico` não alterava o fluxo. | O fluxo da 8.2 separa os papéis: a orquestração seleciona e roteia (*Routing & Decision Making*, Figura 4), a governança "validates actions and outputs" (p. 17). | Ambiguidade **fraca**: o texto orienta, mesmo sem detalhar. |
| 4 | Não indica quando a integração deve ganhar uma abstração formal. | O objetivo principal da camada é oferecer "typed and auditable interfaces"; a Prática 1 pede interfaces explícitas. | **Contestada.** A função que devolve `str` é um **desvio** da prescrição, não a resolução de uma lacuna. |
| 5 | Não prescreve a técnica de indexação/recuperação nem a preparação do conhecimento. | Cita ingestão, *chunking*, *embeddings*, indexação, busca híbrida, *reranking* e empacotamento de citação, e pede avaliação da recuperação como subsistema. | **Contestada** quanto à técnica: BM25 é um **desvio justificado** (auditabilidade). A ambiguidade sobre a vigência da fonte **resiste**. A avaliação isolada da recuperação, pedida pelo texto, foi feita no benchmark v5 (2026-10-02): 44 casos rotulados, Acerto@3 = 0,75, MRR = 0,67 (`docs/tabela_recuperacao.csv`). |
| 6 | Não define se a memória deve influenciar a interpretação, nem se deve haver persistência entre sessões. | A memória "actively shapes orchestration and reasoning"; a memória de longo prazo faz parte da camada. | **Contestada.** Restringir a memória à síntese e excluir o longo prazo são **desvios de escopo**, não lacunas. |
| 7 | A governança é descrita "como camada", mas precisou atuar em três pontos do fluxo e em outras três camadas. | A Figura 4 marca a governança como transversal; o texto lista filtragem de prompt, validação de saída e restrição de ferramentas; a Prática 3 pede validadores explícitos além do prompt. | **Contestada.** O achado é uma **confirmação** da arquitetura, não uma ambiguidade. |
| 8 | Não distingue proveniência de conteúdo de telemetria operacional, nem diz como alimentar avaliação externa. | Inclui "performance monitoring" (p. 17) e, na Figura 4, *Monitoring & Alerting* e *Evaluation & Quality Metrics*. | **Contestada.** O protótipo implementou só a parte de proveniência: uma **implementação parcial**, não uma lacuna. |

**Achado metodológico.** A paráfrase de uma linha usada no diário ("Maia et
al. atribuem à Camada X…") perdia o detalhe do texto. Seis registros de
"ambiguidade" (camadas 3 a 8) foram feitos sem confrontar a prescrição
completa. A reclassificação reforça a lacuna 1, porque as decisões foram
tomadas sem apoio dos autores a ponto de desviar do texto deles. Mas ela
**reduz** o número de ambiguidades genuínas que podem ser atribuídas à
arquitetura na lacuna 3 (suficiência como guia).

---

## 4. Força da evidência por camada

| Camada | Força | Motivo |
|---|---|---|
| 1 | Adequada | Ambiguidade concreta, que resiste ao texto, com decisão justificada pelo domínio. |
| 2 | Adequada | A ambiguidade de amostragem resiste: *Model Controls* é citado sem critério. A seção original do diário tem a lacuna em branco; a evidência está na subseção v4. |
| 3 | Forte | A construção incremental resiste ao texto; há um achado empírico (2026-08-15) e evolução no código. |
| 4 | **Fraca** | A única ambiguidade registrada é contestada pelo texto; a decisão é um desvio, e a camada foi pouco exercitada. |
| 5 | Forte | A ambiguidade da vigência da fonte resiste e é específica do domínio; o desvio na técnica tem justificativa registrada. |
| 6 | **Fraca** | As duas ambiguidades principais são contestadas; resta a falta de critério de tamanho e seleção. |
| 7 | Forte | O "como validar" e o alcance diante da memória resistem; a atuação transversal confirma a arquitetura. |
| 8 | **Fraca** | A ambiguidade registrada é contestada; resta só formato e granularidade. A seção do diário também está desatualizada (campos da v1). |

---

## 5. Síntese

Nenhuma linha de código, dependência ou documento de design dos autores de
Maia et al. (2026) foi usado em qualquer etapa deste protótipo. A auditoria
da Seção 1, sobre todos os arquivos versionados e o histórico completo de
commits, não encontrou referência ao código do SCRIBE nem ao grupo GESAD/UECE.
O código do SCRIBE é público, e a decisão de não consultá-lo foi deliberada e
mantida mesmo quando o acesso foi oferecido. A especificação usada foi o texto
publicado do artigo. Que não houve comunicação com os autores é uma
declaração do autor deste protótipo, registrada como tal, porque nenhuma
inspeção de repositório pode prová-la.

O artigo declara que não prescreve tecnologia: deixa "the inherent
technological decisions (e.g., protocols, tools, frameworks) to the
developers" (p. 15). Em todas as oito camadas, essas decisões foram tomadas
sem apoio dos autores, várias delas forçadas por achados do domínio
regulatório que não poderiam ter vindo do SCRIBE, cujo domínio é a revisão de
literatura científica. Exemplos: norma inventada, número distorcido com o
contexto correto, URL oficial apontando para outra norma, HTML com a redação
revogada. Em quatro camadas (4, 5, 6 e 8), essas decisões **divergem** do que
o texto prescreve. Essa divergência é a evidência mais forte de que a
implementação não foi guiada por material dos autores, ao custo de mostrar
que a leitura do artigo durante a construção foi incompleta.

Há quatro pontos a declarar com transparência:

- **Assistência de IA.** O julgamento do autor foi exercido com apoio de um
  assistente de programação baseado em LLM (Claude, Anthropic), que aparece
  como coautor em parte dos commits. O diário registra várias decisões como
  "combinadas com o usuário" ou "plano aprovado pelo usuário". Isso não
  compromete a independência em relação aos autores de Maia et al., mas as
  decisões derivam da leitura do artigo somada a sugestões de uma ferramenta
  cujo conhecimento de treinamento não pode ser auditado.
- **Referências públicas externas.** Algumas decisões apoiaram-se em
  referências públicas não relacionadas aos autores: BM25, RSLP e o padrão
  Bronze/Silver/Gold. Hevner et al. (2004) é referência de método (avaliação
  DSR), não de projeto.
- **Leitura da Seção 9.** O texto público da Seção 9 (descrição do SCRIBE no
  artigo) foi lido em parte em 2026-10-01, depois das decisões registradas.
- **Ambiguidades não resolvidas.** Algumas ficaram documentadas sem decisão,
  e nenhuma foi resolvida por consulta a material dos autores originais.

Quanto à força da evidência: as camadas 3, 5 e 7 são fortes; as 1 e 2,
adequadas; as 4, 6 e 8, fracas, porque a ambiguidade registrada no diário é
contestada pelo texto. Para a lacuna 1, isso não enfraquece a conclusão:
decisões tomadas sem os autores e divergentes do texto deles também são
prova de independência. O efeito real recai sobre a lacuna 3. Antes de
redigi-la, o diário precisa de um registro datado do confronto com o texto
da Seção 8, como o desta Seção 3. Esse registro deve separar três
categorias: ambiguidades genuínas (incluindo a numeração inconsistente entre
o texto e a Figura 4), desvios deliberados e componentes prescritos não
implementados.
