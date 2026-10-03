# Validação da Lacuna 2 — Generalização de Domínio

Este documento avalia se a definição abstrata de cada camada da arquitetura
de Maia et al. (2026, Seção 8) se manteve ao passar do domínio em que os
autores a ilustraram para o domínio deste protótipo. O domínio de origem é a
revisão de literatura científica, no sistema SCRIBE (Seção 9). O domínio de
destino é o compliance regulatório de Open Finance e contas PJ. A pergunta,
para cada camada, é se o papel dela coube no domínio novo sem ser
descaracterizado.

Este documento **não registra decisões novas de projeto** e não altera código.
Ele compara três coisas:

- o **papel abstrato** de cada camada no texto da Seção 8, com as citações já
  conferidas em `docs/validacao_independencia.md`, Seção 2;
- a **instanciação no SCRIBE**, usando **somente** os trechos da Seção 9
  transcritos e verificados pelo autor diretamente do PDF, em 2026-10-01.
  Nada sobre o funcionamento do SCRIBE além desses trechos foi inferido, e o
  código do SCRIBE continua não consultado (ver `validacao_independencia.md`);
- a **instanciação neste protótipo**, conforme `docs/decisoes_arquitetura.md`,
  `docs/evidencias_empiricas.md` e o código, no commit `183d43c` (v4.1).

**Leitura da Seção 9.** O `validacao_independencia.md` registra que, em
2026-10-01, só a p. 18 (início da Seção 9) havia sido lida. Os trechos usados
aqui cobrem as subseções 9.1 a 9.3 e foram lidos depois de todas as decisões
de projeto. Nenhuma decisão do protótipo os usou.

**Numeração.** Segue a ordem do texto da Seção 8.1 (4 = Ferramentas,
5 = Conhecimento, 6 = Contexto e Memória), como no resto do repositório. Os
trechos do SCRIBE seguem a mesma ordem.

---

## 1. Critério de avaliação

Cada camada recebe uma de três avaliações. Todas respondem à mesma pergunta:
o papel abstrato precisou mudar para caber no domínio regulatório?

| Avaliação | Significado |
|---|---|
| **A — Sem tensão** | O papel se aplica diretamente. As diferenças em relação ao SCRIBE são de conteúdo do domínio (artigos científicos vs. normas), de tecnologia ou de cobertura, sem afetar o que a camada é. |
| **B — Tensão dentro do papel** | A migração produziu algo que exige análise: uma responsabilidade mudou de camada, uma estratégia se inverteu, o domínio acrescentou uma responsabilidade que o texto não menciona, ou o mecanismo mudou o que a camada garante. Mesmo assim, o papel abstrato acomoda o resultado. |
| **C — Reinterpretação** | A camada só coube no domínio regulatório mudando o que ela é ou o que ela garante no nível abstrato. |

**Cobertura** é avaliada à parte. Ela mede quanto do papel abstrato o
protótipo de fato exercita (alta, parcial ou baixa). As duas dimensões são
independentes. Um componente não implementado não gera tensão: ele deixa
aquela parte do papel **sem teste**. Por isso, uma avaliação A com cobertura
baixa é evidência fraca de generalização, e não evidência forte.

---

## 2. Comparação por camada

| Camada | Papel abstrato (Seção 8) | Instanciação no SCRIBE (revisão de literatura) | Instanciação neste protótipo (compliance regulatório) | Avaliação |
|---|---|---|---|---|
| **1 — Interação com o Usuário** | Interfaces conversacionais, *dashboards*, voz, IDEs; a camada "is not merely a frontend, but a source of structured intent signals, constraints, and feedback loops" (p. 15). | Interface conversacional em linguagem natural; o usuário refina o pedido com restrições: "Users may refine their requests by specifying constraints and preferences such as publication venues, time ranges, or inclusion criteria." Exporta artefatos: "BibTeX entries and structured outlines". | CLI de texto, um `Orchestrator` por sessão, pergunta em texto livre. As fontes consultadas vêm na própria resposta, anexadas pela Camada 7 v2; a CLI só destaca, depois da resposta, quando a Camada 7 encontrou algo não verificado. Não captura restrições estruturadas nem *feedback* e não exporta artefatos (`src/layer1_interaction/cli.py`). | **A**. Cobertura **parcial**. O papel cabe no domínio sem ajuste. Restrições estruturadas teriam análogo direto, como norma específica ou data de vigência, mas não foram implementadas. A lista de fontes anexada à resposta cumpre a mesma função que a exportação de BibTeX: devolver ao usuário o artefato que torna a resposta rastreável. |
| **2 — Núcleo de Raciocínio** | "Responsible for interpreting user intents, synthesizing intermediate reasoning artifacts, and producing structured outputs"; gera "plans, tool calls, decision rationales, and evidence-backed responses" (p. 16). | "The LLM core is responsible for interpreting the research question, generating the review plan, and producing the final synthesis." Produz artefatos intermediários ("refined search queries, structured execution plans, and synthesis outlines") num fluxo de cinco fases ("context understanding, pre-plan, plan, execution, and post-execution"). | Duas chamadas ao `llama3.1`: classificação da pergunta (`normativo`, `parecer_juridico`, `fora_de_escopo`) com temperatura 0 e síntese com temperatura 0,1, seed 42 (v4). Não gera planos, consultas refinadas nem saídas estruturadas além do rótulo (`orchestrator.py:117,137`). | **A**. Cobertura **baixa**. Interpretar a intenção e produzir resposta fundamentada em evidência se mantêm iguais nos dois domínios. A parte mais exigente do papel (planos e artefatos intermediários) não foi exercitada, porque a tarefa do protótipo é pergunta e resposta, não um processo de várias etapas. |
| **3 — Orquestração** | "Planning, delegation, retries, checkpointing, and termination"; motor de *workflow*, máquina de estados, *planner-executor* ou multiagente; "must handle partial failures and uncertainty" (p. 16). | "Operationalizes the literature review process as a dynamic workflow in which stages are assembled and adapted according to the user's request." Trata falhas por ampliação: "controlled fallback strategies such as query expansion, alternative reranking strategies, or scope reduction under resource constraints." | Fluxo fixo de 4 etapas em `responder()`, uma máquina de estados mínima. Condições de término por roteamento: `_RECUSAS` (parecer, fora de escopo) e `recusar_sem_base` quando a busca vem vazia (`orchestrator.py:43,79-99`). Sem *retries*, *checkpointing* nem `try`/`except`. | **B**. Cobertura **parcial**. O *fallback* do domínio regulatório vai na direção **oposta** à do SCRIBE: diante de evidência insuficiente, o protótipo recusa em vez de ampliar a busca. E a decisão de término passou a ser definida pela Camada 7. Ver Seção 3.3. |
| **4 — Ferramentas e Serviços** | Expõe APIs externas, *sandboxes* de código, bancos de dados e serviços como ferramentas; "the primary architectural goal of this layer is to provide typed and auditable interfaces"; tratamento de erro e *fallback* (p. 16). | "Connectors to bibliographic Databases for metadata retrieval, PDF parsing utilities for extracting abstracts and sections, citation extraction modules, and table generators". Agentes especializados: "a RAG agent, a download agent, a bibliographic search agent, a BibTeX generation agent, and a reference validation agent." | Uma única função, `buscar_normativo`, que embrulha a Camada 5 e devolve `str` pronta para o prompt (`src/layer4_tools/tools.py:24`). Não há chamada a serviço externo em tempo de execução. | **B**. Cobertura **baixa**. É redução de escopo compatível com a camada, mas as capacidades que o SCRIBE coloca nesta camada (download, *parsing* de PDF, validação de referência, saída de citação) existem no protótipo **em outras camadas**. Evidência fraca. Ver Seção 3.1. |
| **5 — Conhecimento (RAG)** | "Document ingestion, chunking, embedding generation, indexing, hybrid retrieval, reranking, and citation packaging"; recuperação como "runtime subsystem with its own observability and evaluation requirements" (p. 16). | "SCRIBE treats retrieval as a first-class architectural subsystem rather than a simple preprocessing step." A evidência sai "packaged with provenance metadata, including source, DOI, venue, year, and section references, and is explicitly bound to synthesis steps to support citation-backed generation." | Pipeline Bronze/Silver/Gold a partir das URLs oficiais do BCB. A Silver escolhe o PDF consolidado quando o HTML traz a redação original, remove o texto tachado, marca as unidades revogadas e guarda as anotações de alteração como metadado; a Gold exclui as unidades revogadas. Trechos de até 2.500 caracteres com cabeçalho "norma — capítulo — seção — artigo". Busca BM25 (`ingest_normativos.py`, `knowledge_base.py`). | **B**. Cobertura **alta**. O empacotamento de proveniência tem paralelo direto (DOI, *venue*, ano e seção correspondem a norma, URL, capítulo e artigo). O domínio **acrescentou** uma responsabilidade que nem o texto nem o trecho do SCRIBE mencionam: decidir qual versão da fonte está vigente. Ver Seção 3.4. |
| **6 — Contexto e Memória** | Curto prazo ("conversation history, intermediate tool results, and active execution traces") e longo prazo (preferências, planos passados, *workflows* aprendidos); a memória "actively shapes orchestration and reasoning", com "relevance filtering" (pp. 16–17). | Curto prazo: "the active query, candidate paper sets, intermediate screening decisions, extracted evidence snippets, and the synthesis outline". Longo prazo: "prior review sessions, validated inclusion/exclusion templates, and domain-specific categorization schemes". "Because memory influences reasoning outcomes, SCRIBE enforces retention policies and relevance filtering mechanisms". | *Buffer* das últimas 5 interações (pergunta e resposta) em memória de processo, injetado só na síntese. Sem longo prazo e sem filtragem (`src/layer6_memory/memory.py:21`). Dois achados de integração com a Camada 7: o eco do aviso fixo e o falso positivo de citação vinda da memória (`evidencias_empiricas.md`, 2026-08-14). | **A**. Cobertura **baixa**. A preocupação que o SCRIBE declara (a memória influencia o resultado e precisa de política) apareceu concretamente no protótipo, nos dois achados de integração. O papel se manteve. A metade de longo prazo, que é a mais dependente do domínio, não foi testada. |
| **7 — Governança e Segurança** | Restrições "through policies, validators, permission checks, and human-in-the-loop approval points"; "prompt filtering, output validation, bias checks, privacy rules, access control"; aplicações críticas "cannot rely on prompt-level constraints alone" (p. 17); transversal na Figura 4. | "A dedicated Governance Agent that acts as a policy enforcement layer throughout the execution pipeline." Duas fases: "during planning, the agent ensures that proposed execution plans comply with domain-specific constraints (...); during execution, it validates outputs to guarantee that claims remain supported by citations". | Determinística, sem LLM verificador, em **três** pontos desde a v2 (não em uma fase só): antes da geração (`POLITICA_SINTESE`, recusas por classificação, `recusar_sem_base`), depois da geração (`validar_resposta`: norma, artigo, par norma–artigo e valor devem constar no contexto; ausência declarada; fontes anexadas em código) e na ingestão (`validar_fonte_publica`). Sinaliza, não bloqueia (`governance.py:39,97,101,372,419`). | **B**. Cobertura **parcial**. É uma adaptação válida do papel abstrato. Em relação ao SCRIBE, a garantia da fase de execução é **mais estreita**: o protótipo verifica a presença lexical dos identificadores citados, enquanto o SCRIBE declara verificar se as afirmações são sustentadas por citações. Ver Seção 3.2. |
| **8 — Observabilidade e Proveniência** | Rastro de execução "including prompts, intermediate reasoning artifacts, tool calls, retrieval results, memory accesses, and policy decisions"; liga saídas à evidência e "to versioned models and indexes" (p. 17). | "End-to-end traces of the workflow, including generated search plans, tool calls, retrieved candidate papers, screening rationales, evidence snippets used in synthesis, and the final output." "Versioning of retrieval indices and logging of model and tool versions, enabling reproducibility and auditing when underlying corpora evolve over time." | JSON Lines por interação: classificação, fontes (título e URL), desfecho, categorias da validação, modelo, ID do modelo, temperaturas e seed (`src/layer8_observability/observability.py:42,69`). Os trechos recuperados ficam só no benchmark. Não registra prompt, acessos à memória nem versão do índice. A versão de cada norma fica na Bronze, mas não no registro da interação. | **A**. Cobertura **parcial**. O papel é o mesmo nos dois domínios, e o regulatório só reforça a necessidade dele. O que o SCRIBE resolve com "versioning of retrieval indices", para corpora que mudam, é justamente o que o domínio regulatório mais exige, porque as normas mudam de versão. O protótipo não liga a resposta à versão do índice: é uma lacuna de implementação, não uma tensão do papel. |

**Contagem**: 4 camadas em A (1, 2, 6, 8), 4 em B (3, 4, 5, 7), nenhuma em C.

---

## 3. Pontos de tensão

### 3.1 Camada 4 — uma ferramenta contra cinco agentes

**O que a evidência mostra.** A diferença não é só de quantidade. Das
capacidades que o trecho do SCRIBE atribui à Camada 4, várias têm
correspondente no protótipo, mas **em outra camada**:

| Capacidade no SCRIBE (Camada 4) | Correspondente no protótipo | Onde está |
|---|---|---|
| "download agent" | Download da página e do PDF consolidado por URL oficial | Camada 5, ingestão (`ingest_normativos.py`), fora do tempo de execução |
| "PDF parsing utilities" | Extração com `pypdf` e limpeza de artefatos (v4.1) | Camada 5, ingestão |
| "reference validation agent" | Conferência de norma, artigo e valor contra o contexto | Camada 7 (`validar_resposta`) |
| "BibTeX generation agent" / "citation extraction modules" | Lista "Fontes consultadas" (título e URL), montada em código | Camada 7 (`_montar_texto`) |
| "RAG agent" | `buscar_normativo` | Camada 4, sobre a Camada 5 |
| "bibliographic search agent" (bases externas) | Nenhum: não há consulta a serviço externo em tempo de execução | — |

O próprio trecho do SCRIBE já coloca um "RAG agent" na Camada 4. Portanto,
uma ferramenta que embrulha a recuperação não destoa do que os autores fazem.

**Por que as capacidades mudaram de camada.** Há duas causas, uma do domínio
e uma de projeto:

- **Domínio e escopo.** O corpus regulatório deste protótipo é pequeno
  (3 normas), fechado e de fonte única, o BCB. Por isso, o acesso ao serviço
  externo pôde ser feito **na ingestão**, e não em tempo de execução. Na
  revisão de literatura, o conjunto de artigos não é conhecido antes da
  pergunta, e a busca em bases externas precisa acontecer em tempo de
  execução.
- **Projeto.** A validação de referência foi tratada como governança, e não
  como ferramenta, porque no domínio regulatório a citação errada é o risco
  central (`decisoes_arquitetura.md`, Camada 7). O SCRIBE também cita
  verificação de citação na Camada 7 ("claims remain supported by
  citations"). Os trechos não dizem como o SCRIBE divide essa
  responsabilidade entre o "reference validation agent" e o "Governance
  Agent".

**Avaliação.** O papel é definido pela função (expor capacidades externas
como interfaces invocáveis e auditáveis), e não pelo número de ferramentas.
A redução é compatível com a camada. Mas três fatos impedem tratar isso como
evidência forte de generalização:

1. o papel é **mais amplo** do que o protótipo cobre: em tempo de execução,
   a Camada 4 do protótipo é um adaptador de formato sobre a Camada 5;
2. a interface devolve `str`, o que é um **desvio** do "typed and auditable
   interfaces" (`decisoes_arquitetura.md`, "Confronto com o texto da Seção
   8"). O desvio não foi causado pelo domínio;
3. o fato de a mesma capacidade (validar referência) ser ferramenta num
   sistema e governança no outro mostra que a **fronteira** da Camada 4 não
   é fixada pela definição abstrata.

Conclusão: a Camada 4 **não foi refutada** pela migração de domínio, mas
também **não foi testada de forma significativa**. É a camada em que a
avaliação B mais se aproxima de "inconclusivo". O domínio tem candidatas
naturais a ferramentas de tempo de execução, como as APIs de dados abertos do
BCB com o cadastro de instituições autorizadas
(`decisoes_arquitetura.md`, Camada 4). Uma segunda ferramenta seria o teste
que falta.

### 3.2 Camada 7 — *Governance Agent* em duas fases contra validação determinística

**Correção da premissa.** A governança do protótipo não é mais "validação
por regex em uma única fase (pós-síntese)". Esse era o desenho da v1. Desde a
Camada 7 v2 (2026-09-24), ela atua em três pontos:

| Momento | SCRIBE (trecho) | Protótipo |
|---|---|---|
| Antes da execução | Fase de planejamento: os planos devem cumprir "domain-specific constraints (such as publication year thresholds or peer-review requirements)". | Não há plano a validar. Atuam antes da geração: recusa por classificação (parecer jurídico, fora de escopo), recusa sem base e `POLITICA_SINTESE` (só o contexto, declarar norma ausente, copiar valores, sem parecer). |
| Depois da geração | Fase de execução: "validates outputs to guarantee that claims remain supported by citations". | `validar_resposta`: norma, artigo, par norma–artigo e valores citados devem aparecer no contexto recuperado; ausência declarada não conta como citação; fontes anexadas em código; aviso fixo de validação humana. |
| Na ingestão | Não mencionado nos trechos. | `validar_fonte_publica`: só HTTPS em domínios do BCB. |

**O que muda no mecanismo.** O SCRIBE usa um agente dedicado. Os trechos não
dizem se ele é baseado em LLM. Dizem que ele atua "rather than relying solely
on the model's probabilistic outputs". O protótipo escolheu verificação
determinística por motivo de domínio: previsibilidade, ausência de custo
adicional e o risco de um verificador baseado em LLM também alucinar
(`decisoes_arquitetura.md`, Camada 7). Em compliance, um validador que pode
dar respostas diferentes para a mesma entrada é ele próprio um problema de
auditoria.

**O que muda na garantia.** Este é o ponto que precisa ser declarado:

- O trecho do SCRIBE diz que a fase de execução garante que as **afirmações**
  são sustentadas por citações. A afirmação é dos autores e não foi
  verificada aqui.
- O protótipo garante algo mais estreito: que **os identificadores citados**
  (norma, artigo, valor) **constam** no contexto recuperado. Ele não detecta
  uma afirmação falsa que não cite nada, nem uma interpretação errada de um
  trecho citado corretamente. Há um caso registrado: na v4.1, a resposta lista
  o § 4º do art. 6º (dispensa de participação) como requisito, e a Camada 7
  não acusa nada, porque norma, artigo e valores estão no contexto
  (`evidencias_empiricas.md`, v4.1, Observação 4).
- O protótipo **sinaliza** e não bloqueia. O trecho do SCRIBE usa
  "guarantee".
- Por outro lado, o domínio regulatório **acrescentou** à governança coisas
  que não aparecem no trecho do SCRIBE: restrição de fonte na ingestão,
  modelos fixos de resposta segura para recusa (Prática 5 da Seção 8) e uma
  categoria de recusa sem análogo na revisão de literatura (parecer jurídico
  sobre caso concreto).

**Avaliação.** Em relação ao **papel abstrato** da Seção 8, é uma adaptação
válida. O texto prescreve "validators" e "output validation" sem dizer se a
validação deve ser semântica ou lexical, e prescreve não depender só do
prompt (Prática 3), o que o protótipo cumpre. A atuação em vários pontos do
fluxo confirma o caráter transversal da Figura 4. Em relação à
**instanciação do SCRIBE**, a garantia pós-geração do protótipo é mais fraca
na semântica e mais forte na reprodutibilidade. A camada continua sendo a
mesma, mas **o que ela garante mudou**, e a monografia deve dizer isso. Não é
reinterpretação, porque a Seção 8 define a camada num nível que acomoda as
duas garantias. Mas é a tensão mais substantiva das oito camadas.

### 3.3 Camada 3 — *fallback* por ampliação contra *fallback* por recusa

O trecho do SCRIBE descreve o *fallback* como **ampliação**: "query
expansion, alternative reranking strategies, or scope reduction". No
protótipo, evidência insuficiente leva à **recusa**: `recusar_sem_base` com a
busca vazia, e a política de síntese pedindo que o modelo declare a norma
ausente. A inversão tem base empírica no domínio. Em 2026-08-15, uma pergunta
fora de escopo recuperou, por sobreposição lexical, um trecho irrelevante da
Circular nº 4.015, e a resposta saiu com aparência de fundamentada. No
cenário "norma ausente", a busca devolveu trechos de outras normas, e o
modelo citou artigos deles com confiança (`evidencias_empiricas.md`,
2026-08-15 e 2026-09-22). Em compliance, ampliar a busca aumenta a chance de
fundamentar a resposta na norma errada. Em revisão de literatura, ampliar
costuma ser a reação certa a poucos resultados.

A decisão de término também mudou de lugar: as recusas são definidas na
Camada 7, e a Camada 3 só as roteia. O papel abstrato ("termination",
"must handle partial failures and uncertainty") acomoda as duas estratégias.
A tensão está na direção do *fallback*, e não no papel.

### 3.4 Camada 5 — a vigência da fonte

No trecho do SCRIBE, a evolução do corpus aparece na Camada 8 ("versioning of
retrieval indices (...) when underlying corpora evolve over time"): o
conjunto de documentos muda, e o índice é versionado. No domínio regulatório,
o próprio documento muda. A mesma norma tem várias versões consolidadas
(Resolução Conjunta nº 1/2020 na v9; o corpus curado da v1 estava na v7), e
partes do texto são revogadas. Para normas anteriores a 2021, a página do BCB
traz a redação **original** no HTML, e o texto vigente só existe no PDF
consolidado (`evidencias_empiricas.md`, 2026-09-24, Achado 1).

Isso acrescentou à ingestão uma responsabilidade que o texto da Seção 8 não
menciona: decidir **qual representação da fonte está vigente**. É a mesma
ambiguidade genuína registrada no confronto com a Seção 8
(`decisoes_arquitetura.md`). O papel da camada (trazer evidência externa com
proveniência para a geração) não mudou. Mudou o que "proveniência" precisa
conter: no domínio regulatório, ela inclui a validade da fonte no tempo.
Por isso a avaliação é B por **extensão**, e não por redução.

---

## 4. Sobreposição de família: o teste é mais fraco do que parecia

**O que o artigo diz do SCRIBE** (Seção 9.1): "SCRIBE can be primarily
characterized as a Workflow-centric LLM-native application", com "strong
RAG-centric characteristics" e elementos Governance-critical "when deployed
in contexts that demand reproducibility, transparency, and auditable
inclusion or exclusion criteria".

**O que está registrado sobre o protótipo.** Nada. A classificação de família
do protótipo **não aparece** no `decisoes_arquitetura.md`, nos demais
documentos do repositório nem na `monografia_v2.docx`. O Capítulo 2 dessa
versão (Seção 2.3) define as seis famílias e repete a classificação do
SCRIBE, mas não classifica o protótipo. A classificação abaixo é derivada
**neste documento**, com as definições da Seção 2.3 da monografia, e precisa
ser confirmada pelo autor antes de entrar no texto.

| Família (definição da monografia, Seção 2.3) | SCRIBE (Seção 9.1) | Protótipo (derivado aqui) |
|---|---|---|
| Governance-critical: "conformidade, auditabilidade e controle de risco como preocupações arquiteturais de primeira classe" | Presente, **condicional** ao contexto de uso | **Dominante e intrínseca ao domínio**: governança em três pontos, recusas, validação determinística |
| RAG-centric: "geração fundamentada em evidências externas como requisito central de confiabilidade" | Forte | **Dominante**: responde só com base nas normas do BCB e recusa sem base |
| Workflow-centric: "execução de processos multi-etapa com checkpoints, retentativas e logs de proveniência" | **Primária** | **Fraca**: fluxo de várias etapas e log de proveniência, mas sem *checkpoints* nem *retries* |
| Agentic, Tool-heavy, Memory-intensive | Não citadas na classificação dos autores | Ausentes: um só LLM, uma ferramenta, sem memória de longo prazo |

**Achado.** Os dois sistemas combinam **as mesmas três famílias**. A ordem de
dominância é diferente: Workflow-centric primeiro no SCRIBE;
Governance-critical e RAG-centric no protótipo. Além disso, os dois domínios
compartilham a mesma tarefa central: produzir respostas apoiadas em citações,
a partir de um corpus de documentos. Artigos científicos e atos normativos
ocupam o mesmo lugar estrutural, e DOI, *venue*, ano e seção correspondem a
norma, URL, capítulo e artigo.

**Consequência para a lacuna 2.** A sobreposição **enfraquece** o teste, e
isso não deve ser minimizado:

1. O que foi testado é a generalização entre **domínios de aplicação** dentro
   de um **mesmo perfil arquitetural**, e não entre perfis diferentes. Os
   paralelos fortes das Camadas 5, 7 e 8 são, em parte, consequência de os
   dois sistemas serem do mesmo tipo.
2. As camadas que menos foram exercitadas por este par de sistemas são as
   que caracterizam as famílias ausentes nos dois: a Camada 4 (Tool-heavy),
   a Camada 6 de longo prazo (Memory-intensive) e o planejamento e a delegação
   das Camadas 2 e 3 (Agentic). As avaliações A das Camadas 2 e 6 não dizem
   nada sobre como essas camadas se comportariam num sistema dessas famílias.
3. A diferença de dominância não é irrelevante. O SCRIBE é governance-critical
   só em certos contextos de uso. O protótipo é governance-critical por causa
   do domínio. Foi essa diferença que produziu as tensões das Camadas 3 e 7.

**O que o teste ainda mostra.** Mesmo com o perfil compartilhado, o domínio
regulatório trouxe propriedades que não aparecem nos trechos do SCRIBE, e a
arquitetura as absorveu sem mudar o papel de nenhuma camada:

- a validade da fonte no tempo (vigência, versões, texto revogado), na Camada 5;
- o custo assimétrico do erro, que inverte o *fallback* de ampliação para
  recusa, nas Camadas 3 e 7;
- a preferência por verificação determinística, por auditabilidade, na
  Camada 7;
- a restrição a fontes públicas oficiais, aplicada na ingestão, na Camada 7;
- uma classe de pedido que deve ser recusada (parecer jurídico sobre caso
  concreto), sem análogo na revisão de literatura, nas Camadas 3 e 7.

A conclusão que o teste sustenta é estreita: a arquitetura resistiu a uma
mudança de **perfil de risco do domínio** dentro do mesmo perfil de família.

---

## 5. Síntese

A generalização de domínio **se sustentou nas oito camadas**: nenhuma
precisou de reinterpretação do papel abstrato para caber no domínio de
compliance regulatório. Quatro camadas (1, 2, 6 e 8) mantiveram o papel sem
tensão. Quatro (3, 4, 5 e 7) tiveram tensão, mas permaneceram dentro do
papel definido na Seção 8. Esse resultado precisa ser lido com duas
restrições, que limitam o quanto ele prova.

A primeira restrição é a **cobertura**. Das quatro camadas sem tensão, três
(1, 2 e 6) foram exercitadas só em parte, e em duas delas (2 e 6) a parte
mais exigente do papel ficou de fora: planos e artefatos intermediários na
Camada 2, memória de longo prazo e filtragem por relevância na Camada 6.
Ausência de tensão, nesses casos, é em boa parte ausência de teste. O padrão
é visível na tabela: onde o protótipo exercitou a camada a fundo (Camadas 5 e
7), a tensão apareceu. A Camada 8 é o caso mais sólido de A, porque foi
razoavelmente exercitada e o domínio só reforçou o seu papel.

A segunda restrição é a **sobreposição de família** (Seção 4). O SCRIBE e o
protótipo combinam as mesmas três famílias e a mesma tarefa central, que é a
geração apoiada em citações sobre um corpus de documentos. O teste mostra
generalização entre domínios dentro de um perfil arquitetural, e não entre
perfis. Ele não diz nada sobre sistemas Agentic, Tool-heavy ou
Memory-intensive. O que ele mostra é que propriedades do domínio regulatório
que a revisão de literatura não tem foram absorvidas sem mudar o papel das
camadas: vigência da fonte, custo assimétrico do erro, exigência de
verificação determinística e recusas obrigatórias.

Entre as camadas com tensão, **a Camada 7 é a que mais se aproximou de uma
reinterpretação**. O papel abstrato se manteve, mas o que a camada garante
mudou em relação ao SCRIBE. O protótipo verifica que os identificadores
citados constam no contexto, sinaliza e não bloqueia. O SCRIBE declara
garantir que as afirmações são sustentadas por citações. A troca foi
deliberada e motivada pelo domínio: perde-se cobertura semântica, ganha-se
reprodutibilidade e auditabilidade. A Seção 8 define a governança num nível
que acomoda as duas garantias. Mas, se a monografia comparar o protótipo com
o SCRIBE, e não só com a Seção 8, essa diferença de garantia deve aparecer
como achado. A Camada 5 teve a tensão de **extensão** mais clara: a
proveniência precisou passar a incluir a validade da fonte no tempo. A
Camada 3 inverteu a estratégia de *fallback*.

A **Camada 4** é o elo fraco da avaliação. A redução de cinco agentes para
uma ferramenta é compatível com a camada. Parte das capacidades do SCRIBE
reaparece no protótipo em outras camadas: download e *parsing* na ingestão da
Camada 5, validação de referência e lista de fontes na Camada 7. Isso mostra
que a fronteira da Camada 4 não é fixada pela definição abstrata, mas não
refuta o papel. A avaliação B dessa camada está mais perto de "não testado"
do que de "generalizou". Uma segunda ferramenta de tempo de execução, como
as APIs de dados abertos do BCB, seria o teste necessário para concluir
alguma coisa sobre ela.

Para a monografia, a formulação que a evidência sustenta é: **a arquitetura
generalizou para o domínio regulatório sem reinterpretação de nenhuma camada,
com tensões em quatro camadas e uma mudança de garantia na Camada 7; o teste
é limitado pela sobreposição de família entre os dois sistemas e pela baixa
cobertura das Camadas 2, 4 e 6.**

---

## Adendo (2026-10-02): o que o benchmark v5 acrescenta

O benchmark v5 (66 casos, `evidencias_empiricas.md`, 2026-10-02) não muda a
formulação acima, mas dá números a duas das tensões:

- **Camada 7, garantia mais estreita (§3.2).** Nos 39 casos normativos do
  corpus, as 117 execuções passaram pela validação sem aviso, e a auditoria
  manual encontrou 13 (11%) com erro material: artigo atribuído pela
  remissão de outro artigo, ausência no contexto apresentada como ausência
  na norma, itens de um artigo apresentados como resposta a outra
  pergunta. Verificar a presença lexical do que é citado não garante que a
  afirmação seja sustentada pela citação, que é a garantia que o SCRIBE
  declara.
- **Camada 3, *fallback* por recusa (§3.3).** Com a recuperação falhando
  (nenhum trecho relevante entre os 3), o modelo se absteve em 12 de 33
  execuções e errou em 12. As normas fora do corpus foram declaradas
  ausentes em 6 de 6 casos, sem invenção. A recusa protege contra norma
  inventada, mas não contra a resposta errada fundamentada no trecho errado.
  Esse é o risco que motiva a inversão do *fallback*, e ele continua
  presente.

