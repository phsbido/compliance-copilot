# Validação da Lacuna 3 — Suficiência como Guia de Projeto

Este documento responde se as oito camadas de Maia et al. (2026, Seção 8)
bastam como guia de projeto ou se exigiram adaptações que os autores não
previram. O material de partida é a entrada "Confronto com o texto da Seção 8"
de `docs/decisoes_arquitetura.md` (2026-10-01). Essa entrada foi produzida como
efeito colateral da auditoria de independência, e não como auditoria
sistemática. Aqui, cada item dela é conferido de novo contra o texto do artigo
e classificado por um critério explícito.

Este documento **não registra decisões novas de projeto** e não altera código
nem o diário. Onde a reverificação contradiz o Confronto, a correção fica
registrada aqui (Seção 4). O diário continua como registro datado.

**Fonte do texto.** `referencias/maia.pdf`, versão *preprint* SSRN ("This
preprint research paper has not been peer reviewed", *Journal of Systems and
Software*, 2026). O texto das pp. 15–18 foi extraído com `pdftotext`, com a
hifenização de fim de linha desfeita. A Figura 4 é uma imagem sem texto
extraível. Ela foi extraída da p. 16 e lida diretamente. Todas as citações
abaixo estão no inglês original.

**Páginas.** Os documentos anteriores citam a Seção 8 como "pp. 15–17". As
Práticas 4 e 5 da Seção 8.3 estão na **p. 18**. As páginas usadas aqui são:
p. 15 (introdução da Seção 8 e Camada 1), p. 16 (Figura 4 e Camadas 2 a 6),
p. 17 (fim da Camada 6, Camadas 7 e 8, Seção 8.2 e Práticas 1 a 3) e p. 18
(Práticas 4 e 5).

**Numeração.** Segue a ordem do texto da Seção 8.1 (4 = Ferramentas,
5 = Conhecimento, 6 = Contexto e Memória), como no resto do repositório.

Consolidado em 2026-10-01, sobre o commit `183d43c` (v4.1).

---

## 1. Critério de classificação

O teste é sempre o mesmo: **o texto da Seção 8, lido por inteiro, deu
elementos para tomar a decisão?** Quatro regras tornam esse teste operacional.

1. **Ler a seção inteira, e não só o parágrafo da camada.** Uma decisão que
   se deriva da combinação de passagens (por exemplo, a Camada 2 e a Camada 5)
   conta como derivável.
2. **Decisão de tecnologia não é insuficiência.** O artigo declara que deixa
   "the inherent technological decisions (e.g., protocols, tools, frameworks)
   to the developers who will instantiate it" (p. 15), e que "our conceptual
   architecture does not impose any of these protocols" (p. 17). Escolher
   formato de log, técnica de busca ou valor de parâmetro é uso dessa
   delegação, e não lacuna. O mesmo vale para o **conteúdo de domínio**: uma
   arquitetura que se declara agnóstica de domínio não deve listar quais
   identificadores um validador regulatório confere.
3. **Distinguir prescrição de exemplo pelo modo verbal.** "Must", "is
   necessary", "should" e frases afirmativas ("This layer enforces…")
   prescrevem. "Such as", "may include" e "often" dão exemplos ou opções. Um
   item opcional que o protótipo não implementou não é prescrição descumprida.
4. **Insuficiência é a falta de um elemento de arquitetura.** Ou seja, falta
   uma responsabilidade, uma fronteira entre camadas ou um critério que o
   próprio texto exige e não fornece. Os casos típicos são dois: o texto
   nomeia uma preocupação, mas o mecanismo que dá para ela não cobre o caso;
   ou duas passagens, aplicadas juntas, não dizem o que fazer.

| Categoria | Critério |
|---|---|
| **Insuficiência real** | A Seção 8 não dá elementos para a decisão, mesmo lida por inteiro, e a decisão não é de tecnologia nem de conteúdo de domínio (regras 1, 2 e 4). Exigiu julgamento do autor que não se deriva do texto. |
| **Escolha de escopo** | O texto é claro sobre o que prescreve (regra 3), e o protótipo não implementou ou implementou em parte. A justificativa informa se isso foi **registrado como decisão** no diário. Alguns itens não foram: são omissões que só apareceram no Confronto. Ficam nesta categoria porque, para a pergunta de suficiência, o que importa é que o texto era claro. A diferença entre decisão e omissão é registrada, mas não muda a categoria. |
| **Ambiguidade editorial** | Divergência entre texto e figura (ou entre passagens) que não afetou nenhuma decisão do protótipo. Afeta só a leitura do artigo. |
| **Não se sustenta** | Item do Confronto que, conferido contra o texto, não é insuficiência nem desvio: a decisão era derivável, ou era de tecnologia ou domínio delegada pelo artigo, ou está fora do objeto de uma arquitetura. Não entra na contagem das três categorias. |

---

## 2. Itens confirmados

Itens numerados por categoria: **E** (editorial), **I** (insuficiência real),
**S** (escolha de escopo). Entre parênteses, a origem no Confronto:
A1–A8 = tabela 1 (ambiguidades, pela camada), D1–D4 = tabela 2 (desvios, na
ordem da tabela), N1–N8 = tabela 3 (não implementados, pela camada).

| Item | Camada(s) afetada(s) | Trecho da Seção 8 (citação exata) | O que o protótipo fez | Categoria | Justificativa da categoria |
|---|---|---|---|---|---|
| **E1** (numeração) | 4, 5, 6 | Texto: as camadas aparecem sem número, na ordem Ferramentas, Conhecimento, Memória, repetida em 8.2: "(iv) the tool integration layer and the knowledge integration layer provide external actions and evidence" (p. 17), e no fecho de 8.1: "explicit engineering of orchestration, tool-use, retrieval, memory, governance, and observability" (p. 17). Figura 4: "4. Knowledge Integration Layer", "5. Context & Memory Layer", "6. Tool & Service Integration Layer" (p. 16). | Segue a ordem do texto (`layer4_tools`, `layer5_knowledge`, `layer6_memory`). | Ambiguidade editorial | **Confirmado** por inspeção da imagem. O texto é coerente consigo mesmo nas três passagens; só a figura diverge. Nenhuma responsabilidade muda com a numeração. O efeito se limita a nomes de diretório e à correspondência na leitura do artigo. |
| **E2** (novo) | 2, 3 | "(ii) the LLM core interprets the request and produces an initial task decomposition" (8.2, p. 17). Figura 4, na Camada 3: "Task Decomposition & Planning" (p. 16). Camada 3: "including planning, delegation, retries…" (p. 16). | Não há decomposição nem plano: o fluxo é fixo. | Ambiguidade editorial | **Item novo**, encontrado na reverificação. A decomposição é atribuída ao LLM em 8.2 e à orquestração na figura. A Prática 2 permite conciliar as duas leituras: "Although the LLM core is responsible for reasoning, the orchestration layer should manage execution flow" (p. 17), ou seja, o LLM produz o plano e a orquestração o conduz. Não afetou nenhuma decisão porque o protótipo não planeja. Num sistema agêntico poderia afetar. Aqui fica **sem teste**. |
| **I1** (A2) | 2 (decisão distribuída em 3 e 8) | Figura 4, na Camada 2: "Guardrails & Model Controls" (p. 16). O texto da Camada 2 não fala de controle do modelo. Prática 4: "LLM-native systems are inherently stochastic (…) provenance mechanisms must be built in from the beginning, including logging of tool results, retrieval evidence, memory accesses, and model versions" (p. 18). | Na v4: temperatura 0 na classificação, 0,1 na síntese e seed 42. `config.py` define os valores, a Camada 3 escolhe por etapa e a Camada 8 registra os parâmetros e o ID do modelo. Antes da v4, valia o padrão implícito do Ollama, sem decisão. | Insuficiência real | **Confirmado.** O texto reconhece a estocasticidade e responde só com o registro da versão do modelo. Isso não atinge o objetivo que a própria Prática 4 declara ("scientific reproducibility"): sem os parâmetros de amostragem, uma resposta não se reproduz. "Model Controls" aparece só como rótulo da figura, sem conteúdo. *Guardrails* aparece tanto na Camada 2 quanto na 7 ("Content Safety & Guardrails"), sem divisão entre elas. Os **valores** são decisão de tecnologia (regra 2). O que faltou é de arquitetura: tratar a amostragem como um controle com efeito de governança, decidido por etapa, atribuído a uma camada e registrado. O efeito de governança é medido: na v2 determinística o número saiu errado 5/5 vezes, e a 0,8 (v4, sensibilidade) o modelo inventou o número 2/5 vezes. |
| **I2** (A5) | 5 (reflexo em 8) | Camada 5: "retrieval pipelines, including document ingestion, chunking, (…)" (p. 16). Prática 4: "may depend on evolving knowledge bases" (p. 18). Camada 8: "outputs can be linked to supporting evidence and to versioned models and indexes" (p. 17). | A Silver escolhe o PDF consolidado quando o HTML da página traz a redação original, descarta o texto revogado e guarda as anotações de alteração como metadado (`ingest_normativos.py`). | Insuficiência real | **Confirmado.** O texto trata a evolução do conhecimento no nível do **índice** (índice versionado). Não trata o caso em que **o próprio documento** tem versões e a fonte oferece mais de uma representação. Nenhuma frase dá critério para escolher a vigente, e nenhuma camada recebe essa responsabilidade. Esta é a mesma evidência da lacuna 2, §3.4 (ver Seção 5). A diferença em relação a uma questão de domínio: qualquer corpus com documentos consolidados tem o mesmo problema (normas, padrões técnicos, documentação de API, diretrizes clínicas). Ressalva: o diário (Camada 5, 2026-08-14) disse que a dificuldade de **obter** as fontes "não é uma ambiguidade da arquitetura". Isso continua certo para a obtenção (portal SPA, URL que leva à norma errada), que é problema de dado. A vigência é diferente, porque é uma decisão sobre **o que a camada entrega**. |
| **I3** (A7, 2ª parte) | 6 × 7 (e 8) | Camada 6: "memory in LLM-native applications actively shapes orchestration and reasoning" (p. 16) e "it introduces privacy and governance concerns due to long-term retention" (p. 17). Camada 7: "output validation" (p. 17). Camada 8: "outputs can be linked to supporting evidence" (p. 17). | `validar_resposta` confere só contra o contexto recuperado no turno. Uma citação que veio do turno anterior, pela memória, gera aviso de não verificada, o que parece um falso positivo para quem lê a conversa inteira. Mantido e documentado (`evidencias_empiricas.md`, 2026-08-14, Observação 3). | Insuficiência real | **Confirmado.** O texto diz que a memória molda o raciocínio e que traz preocupação de governança, mas só no eixo da retenção e da privacidade. Não diz se o conteúdo da memória conta como **evidência** para a validação de saída e para a ligação de proveniência. Um sistema que siga as duas frases (a memória molda o raciocínio; a saída é validada contra a evidência) chega exatamente a esse conflito. É uma fronteira entre camadas, e não um detalhe de tecnologia. Também independe de domínio: vale para qualquer RAG conversacional com validação. Não aparece na lacuna 2. |
| **S1** (D1) | 4 | "The primary architectural goal of this layer is to provide typed and auditable interfaces that reduce ambiguity and mitigate unsafe actions" (p. 16). Prática 1: "A recurring anti-pattern in current LLM-enabled systems is to implement retrieval, tool calls, and memory as ad-hoc scripts tightly coupled to prompts" (p. 17). | `buscar_normativo(pergunta: str, top_k: int = 3) -> str` devolve texto já formatado para o prompt (`tools.py:24`). A Camada 8 recupera as fontes desse texto por regex. | Escolha de escopo (**não registrada**) | **Confirmado.** O texto é claro, e a Prática 1 descreve como antipadrão exatamente o que foi feito. A anotação `-> str` não atende ao "typed" do texto, cujo propósito é "reduce ambiguity": o consumidor precisa de regex para recuperar a fonte. A decisão registrada no diário (não criar uma abstração genérica de ferramenta) não trata da tipagem. É uma falha de leitura, e não uma insuficiência do texto. Mesma evidência da lacuna 2, §3.1, item 2. |
| **S2** (D3) | 6 (efeito em 3) | "Unlike conventional state persistence, memory in LLM-native applications actively shapes orchestration and reasoning, requiring explicit memory retrieval strategies and relevance filtering" (p. 16). | O histórico entra só no prompt da síntese (`orchestrator.py:142`). A classificação e a consulta à busca (`buscar_normativo(interpretacao.pergunta_original)`) não usam a memória. | Escolha de escopo (**registrada**) | **Confirmado, com duas correções.** (1) O Confronto marca este desvio como "não intencional". O diário da Camada 6 registra, porém, "decisão de escopo: por ora, só a síntese usa o histórico". A decisão foi deliberada. O erro estava na crença de que a arquitetura não decidia o ponto. (2) O desvio é **parcial**. A síntese é raciocínio (a Camada 2 inclui "synthesizing"), então a memória já molda o raciocínio. O que falta é moldar a orquestração (a busca usa só a pergunta atual) e a interpretação. |
| **S3** (D4) | 6 | "In LLM-native applications, it is necessary to maintain short-term and long-term context. This is the responsibility of the Context and Memory layer" (p. 16). | Só memória de processo, sem persistência entre sessões. | Escolha de escopo (**registrada**) | **Confirmado.** O texto é claro ("necessary"), mas também permite compor as camadas conforme a família: "composed differently depending on the target family" (p. 15), e a camada é "dominant in memory-intensive families" (pp. 16–17). O protótipo não pertence a essa família. A decisão foi registrada ("deixada explicitamente fora de escopo"), mas com a justificativa errada, de que a arquitetura não resolvia o ponto. Inclui a "memória de longo prazo" que o Confronto listava também entre os componentes não implementados da Camada 6. Aqui é contada uma vez só. |
| **S4** (N1) | 1 | "the interaction layer is not merely a frontend, but a source of structured intent signals, constraints, and feedback loops" (p. 15). | A pergunta é texto livre, sem restrições estruturadas nem *feedback*. | Escolha de escopo (**não registrada**) | **Confirmado em parte.** A caracterização é clara. Mas *dashboards*, voz e IDEs vêm com "such as conversational UIs, dashboards, voice interfaces, or integrated development environments" (p. 15): são exemplos de interface, e não componentes exigidos. A Figura 4 inclui a CLI ("UI / Frontends (Web, Mobile, CLI)"). Esses itens saem da lista de não implementados. |
| **S5** (N2) | 2 | "The LLM core is responsible for interpreting user intents, synthesizing intermediate reasoning artifacts, and producing structured outputs" (p. 16). | Classifica a pergunta (rótulo de três valores) e sintetiza texto livre. | Escolha de escopo (registrada em parte: "estágio inicial, apenas geração de texto simples") | **Confirmado em parte.** A responsabilidade é afirmativa, e o protótipo a cumpre no mínimo: o rótulo é a única saída estruturada. Mas "the LLM core in LLM-native systems **often** generates plans, tool calls, decision rationales, and evidence-backed responses" (p. 16) descreve o que é frequente, e não o que é exigido. A falta de planos e de chamadas de ferramenta é coerente com um fluxo fixo. As respostas apoiadas em evidência estão implementadas. |
| **S6** (N3) | 3 | "Architecturally, orchestration must handle partial failures and uncertainty, since tool calls, retrieval, and model reasoning may fail independently" (p. 16). Prática 5: "LLM-native applications must support fallback behaviors" (p. 18). | O término está implementado (`_RECUSAS`, `recusar_sem_base`). Não há *retries* nem *checkpointing*, e não há `try`/`except` em `orchestrator.py`: com o Ollama indisponível, a execução é interrompida. | Escolha de escopo (**não registrada**) | **Confirmado.** O texto usa "must". A incerteza sobre a evidência é tratada (recusa sem base). A falha de execução não é. Planejamento e delegação dependem da família (*workflow-centric*, *agentic*). Mesma evidência da lacuna 2, §3.3 (ver Seção 5). |
| **S7** (N4) | 4 | "exposing external APIs, code execution sandboxes, databases, and enterprise services as callable tools" (p. 16) e "Tool invocation is a major source of non-determinism in LLM-native systems, motivating robust error handling and fallback strategies" (p. 16). | Nenhuma ferramenta externa em tempo de execução e nenhum tratamento de erro de ferramenta. | Escolha de escopo (**registrada**: "generalização adiada") | **Confirmado.** O texto é claro sobre o que a camada encapsula, e a camada é a dominante de outra família ("Tool-heavy families typically emphasize this layer", p. 16). Mesma evidência da lacuna 2, §3.1. |
| **S8** (N5) | 5 | "The architecture should explicitly treat retrieval not as a pre-processing step, but as a runtime subsystem with its own observability and evaluation requirements" (p. 16). Prática 1: "explicit interfaces, evaluation criteria, and observability hooks" (p. 17). | Houve um teste de recuperação *ad hoc* com 8 perguntas (`evidencias_empiricas.md`, 2026-09-24). Um conjunto rotulado com Recall@3/MRR está planejado (`estado_atual.md`) e não foi feito. Os trechos recuperados não vão para o log de tempo de execução. | Escolha de escopo (**registrada**: planejada) | **Confirmado.** O texto usa "should" e é específico. |
| **S9** (N6 + A6) | 6 | "Short-term context includes conversation history, intermediate tool results, and active execution traces" e "requiring explicit memory retrieval strategies and relevance filtering" (p. 16). | *Buffer* das últimas 5 perguntas e respostas, sem resultados de ferramenta, sem rastro de execução e sem filtragem por relevância (`memory.py:21`). | Escolha de escopo (registrada em parte: "sem introduzir complexidade (…) sem caso de uso real") | **Reclassificação de A6.** O Confronto tratou como ambiguidade "tamanho da janela, formato de injeção e critério de seleção". Tamanho e formato são parâmetros de tecnologia (regra 2). A falta de critério de relevância só seria insuficiência **observada** se o protótipo tivesse precisado escolher um critério. Não precisou, porque não implementou filtragem. Fica registrada como **insuficiência potencial, não testada**. |
| **S10** (N7) | 7 | "This layer enforces constraints on system behavior through policies, validators, permission checks, and human-in-the-loop approval points" e "Governance becomes particularly important in systems where LLM outputs influence decisions or trigger real-world actions" (p. 17). | Políticas e validadores estão implementados. A aprovação humana se resume a um aviso fixo. Não há checagem de permissão. | Escolha de escopo (**não registrada**) | **Confirmado em parte.** Checagem de permissão e aprovação humana estão na frase afirmativa, e um copiloto de compliance produz saídas que "influence decisions". Mas "Governance mechanisms **may include** prompt filtering, output validation, bias checks, privacy rules, access control, and restrictions on tool execution" (p. 17) é uma lista de opções. Checagem de viés, regras de privacidade e controle de acesso saem da lista de não implementados. |
| **S11** (N8) | 8 | "the execution trace of the system, including prompts, intermediate reasoning artifacts, tool calls, retrieval results, memory accesses, and policy decisions is recorded" e "outputs can be linked to supporting evidence and to versioned models and indexes" e "performance monitoring" (p. 17). Figura 4: "Monitoring & Alerting", "Feedback Loops & Continuous Improvement". | São registrados decisões de política (`desfecho`, `validacao`), modelo, ID e parâmetros, e fontes (título e URL). Não são registrados o prompt, os trechos (só o benchmark os guarda), os acessos à memória e a versão do índice. Não há monitoramento nem *feedback*. | Escolha de escopo (em parte: o monitoramento ficou fora por decisão registrada, "não telemetria operacional"; o resto não foi registrado) | **Confirmado.** O texto é claro e específico sobre o conteúdo. A versão do índice é a parte que o domínio regulatório mais exige (lacuna 2, Camada 8). |

---

## 3. Itens do Confronto que não se sustentam

| Item original | O que o Confronto registrou | O que o texto diz | Por que não se sustenta |
|---|---|---|---|
| **A1** (Camada 1) | Não diz se a interface deve expor artefatos de outras camadas, como a proveniência. | "evidence-backed responses" (Camada 2, p. 16); "citation packaging" (Camada 5, p. 16); "outputs can be linked to supporting evidence" (Camada 8, p. 17). | **Derivável** (regra 1). O parágrafo da Camada 1 não fala do que ela devolve, mas o texto inteiro diz que a resposta sai com a evidência e as citações. No protótipo, as fontes já são anexadas à resposta pela Camada 7 (`_montar_texto`). O que sobra é qual camada desenha o rodapé, e isso é implementação. |
| **A3** (Camada 3) | (a) Comportamento durante a construção incremental, com camadas ausentes. (b) A forma de implementação é uma lista de opções. | (a) A arquitetura é um "conceptual scaffold" (p. 15), e a Prática 5 dá o princípio aplicável: "safe response templates" (p. 18). (b) "Orchestration can be implemented as a workflow engine, a state machine, a planner-executor loop, or a multi-agent coordination substrate" (p. 16). | (a) **Fora do objeto**: a ordem de construção é questão de processo, e não de estrutura. E o texto tinha o elemento: o *stub* de busca devolvia um texto fixo, e o modelo inventou a "Resolução do CPM 4.665/2021" (2026-08-14). Um *stub* que recusasse teria seguido a Prática 5. (b) **Delegação explícita** (regra 2): uma lista de opções é a forma de o texto dizer que a escolha é do desenvolvedor. |
| **A7, 1ª parte** (Camada 7) | O que validar e como: citação de norma, artigo e valor, ausência declarada. | "validate outputs" (Prática 3, p. 17); "evidence traceability is mandatory" em aplicações *governance-critical* (Camada 5, p. 16); "evidence-backed responses" (Camada 2, p. 16). | O **como** (regex ou LLM verificador) é decisão de tecnologia (regra 2). O **quê**, no nível de arquitetura (validar que a saída se apoia na evidência recuperada), é **derivável** das três passagens. Dizer quais identificadores conferir (norma, artigo, valor) e tratar a ausência declarada é conteúdo de domínio, que uma arquitetura agnóstica não deveria fixar. A segunda parte de A7, o alcance da validação diante da memória, se sustenta: é o item I3. |
| **A8** (Camada 8) | Formato e granularidade do registro. | "the execution trace of the system, including prompts, intermediate reasoning artifacts, tool calls, retrieval results, memory accesses, and policy decisions is recorded" (p. 17). | O **formato** (JSON Lines) é decisão de tecnologia (regra 2). O **conteúdo** e a granularidade, no nível dos passos do rastro de execução, estão prescritos. O que o protótipo não registra é escopo (S11), e não lacuna. |
| **D2** (Camada 5) | Desvio justificado: BM25 lexical em vez de *embeddings*, busca híbrida e *reranking*. | "retrieval pipelines, **including** document ingestion, chunking, embedding generation, indexing, hybrid retrieval, reranking, and citation packaging" (p. 16). Figura 4, Camada 5 do texto: "RAG / Vector Stores", "Document Repositories", "Knowledge Graphs", "External Knowledge Sources". | **Não é desvio.** A técnica de recuperação é decisão de tecnologia que o artigo delega (p. 15). A figura apresenta alternativas (um grafo de conhecimento não é um *pipeline* de *embeddings*), o que mostra que a lista é um cardápio. O que é normativo na Camada 5 ("should (…) treat retrieval (…) as a runtime subsystem with its own observability and evaluation requirements") continua cobrado em S8. |

**Itens do diário que o Confronto não listou.** Dois registros do diário
também tratam de "lacuna da arquitetura" e foram conferidos para não ficarem
de fora sem justificativa. Nenhum dos dois se sustenta, e eles não entram na
contagem:

- **Fronteira entre orquestração e governança** (Camada 3, classificada como
  "fraca" em `validacao_independencia.md`, §3). O texto atribui à governança
  "prompt filtering" (p. 17). Recusar uma pergunta pelo tipo (parecer
  jurídico, fora de escopo) é filtragem de entrada, uma função da Camada 7 que
  a Camada 3 só roteia. É assim que o protótipo ficou desde 2026-08-15.
- **Avaliação e benchmark** ("Benchmark Empírico"). O texto pede "evaluation
  criteria" (Prática 1), "evaluation requirements" (Camada 5) e, na Figura 4,
  "Evaluation & Quality Metrics" na Camada 8.

---

## 4. Mapa das correções em relação ao Confronto

| Item do Confronto | Classificação no Confronto | Resultado da reverificação |
|---|---|---|
| Numeração | Ambiguidade genuína | Mantido, como **editorial** (E1). |
| A1 | Ambiguidade genuína | **Não se sustenta**: derivável. |
| A2 | Ambiguidade genuína | Mantido: **insuficiência real** (I1). |
| A3 | Ambiguidade genuína | **Não se sustenta**: fora do objeto e delegação explícita. |
| A5 | Ambiguidade genuína | Mantido: **insuficiência real** (I2). |
| A6 | Ambiguidade genuína | **Reclassificado** como escolha de escopo (S9). A insuficiência fica como potencial, não testada. |
| A7 | Ambiguidade genuína | **Dividido**: o quê e como validar não se sustenta; o alcance diante da memória é **insuficiência real** (I3). |
| A8 | Ambiguidade genuína | **Não se sustenta**: formato delegado, conteúdo prescrito. |
| D1 | Desvio não intencional | Mantido: escopo, não registrado (S1). |
| D2 | Desvio justificado | **Não é desvio**: o texto permite. |
| D3 | Desvio **não intencional** | **Corrigido** para escopo **registrado** e parcial (S2). |
| D4 | Desvio justificado | Mantido: escopo, registrado (S3). |
| N1, N2, N7 | Não implementados | Mantidos **em parte** (S4, S5, S10). Saem *dashboards* e voz ("such as"), planos e chamadas de ferramenta ("often"), viés, privacidade e acesso ("may include"). |
| N6 | Não implementado | Mantido sem a memória de longo prazo, que já é S3 (S9). |
| N3, N4, N5, N8 | Não implementados | Mantidos (S6, S7, S8, S11). |
| — | — | **Novo**: E2, a decomposição de tarefa em 8.2 contra a Figura 4. |

---

## 5. Conexão com a lacuna 2 (generalização de domínio)

As camadas 3, 4, 5 e 7 tiveram tensão registrada em
`docs/validacao_generalizacao_dominio.md`. A evidência é a mesma, mas a
pergunta é outra. Lá a pergunta era se **o papel da camada mudou** ao passar
para o domínio regulatório. Aqui é se **o texto foi claro o bastante para
guiar a decisão**, em qualquer domínio. A análise não é repetida. Fica só a
resposta à pergunta desta lacuna.

| Camada | Tensão na lacuna 2 | O texto guiou a decisão? | Item aqui |
|---|---|---|---|
| 3 | §3.3: o *fallback* por recusa inverte o *fallback* por ampliação do SCRIBE. | **Sim.** A Prática 5 inclui "safe response templates" entre os *fallbacks* (p. 18), e a Camada 3 inclui "termination". A direção do *fallback* é uma das opções do texto. O que falta é o tratamento de falha de execução, que o texto pede com "must". | S6 |
| 4 | §3.1: uma ferramenta contra cinco agentes; a interface devolve `str`. | **Sim.** O texto é claro sobre interfaces tipadas e sobre o antipadrão "tightly coupled to prompts". O desvio é de leitura. | S1, S7 |
| 5 | §3.4: o domínio acrescentou a decisão sobre a vigência da fonte. | **Não.** É a mesma evidência. A lacuna 2 mostrou que o papel acomodou a extensão. Aqui, o texto não deu critério: trata a evolução no nível do índice, não do documento. O domínio regulatório fez o problema aparecer, mas o problema não é exclusivo dele. | I2 |
| 7 | §3.2: a validação lexical estreita a garantia em relação ao SCRIBE. | **Sim, no nível que cabe a uma arquitetura.** A lacuna 2 já registrou que a Seção 8 "acomoda as duas garantias". Para a suficiência, isso significa que a escolha entre lexical e semântico foi delegada, e não deixada sem orientação. O ponto da Camada 7 que o texto **não** cobre é outro, e não aparece na lacuna 2: o alcance da validação diante da memória. | A7 (1ª parte) não se sustenta; I3 |

---

## 6. Onde o texto guiou

Para equilibrar a lista de lacunas, estes são os pontos em que a Seção 8 deu
orientação suficiente e o protótipo a seguiu. Todos foram conferidos no texto:

- **Fluxo em código, e não no prompt.** "the orchestration layer should manage
  execution flow, retries, and failure handling" (Prática 2, p. 17):
  `responder()` e `_RECUSAS`.
- **Governança além do prompt.** "Governance-critical applications cannot rely
  on prompt-level constraints alone" (Prática 3, p. 17): `POLITICA_SINTESE`
  mais `validar_resposta`. O protótipo mostrou também que a política no prompt
  mudou mais o comportamento, e que os validadores mediram e sinalizaram
  (`evidencias_empiricas.md`, Camada 7 v2).
- **Governança transversal.** "with governance and observability as
  cross-cutting concerns" (legenda da Figura 4, p. 16): a governança atua na
  ingestão, no prompt e depois da geração. O diário registrou isso como
  ambiguidade, mas é o que a figura prescreve.
- **Recusa por tipo de pergunta.** "prompt filtering" (Camada 7, p. 17):
  parecer jurídico e fora de escopo.
- **Resposta segura.** "safe response templates" (Prática 5, p. 18): as três
  recusas fixas.
- **Versão do modelo.** "model versions" (Prática 4, p. 18): ID do modelo por
  interação desde a v4.
- **Sequência do fluxo.** As etapas (ii) a (vi) de 8.2 correspondem a
  interpretar, recuperar, sintetizar, validar e registrar, sem a decomposição
  de tarefa.

---

## 7. Síntese

A reverificação confirmou **16 itens** e descartou **5**. Dos confirmados,
**3 são insuficiências reais** da Seção 8, **11 são escolhas de escopo** e
**2 são ambiguidades editoriais** (uma delas nova, encontrada nesta
verificação). O Confronto registrava 7 ambiguidades genuínas. Delas, 2
sobreviveram inteiras como insuficiência (I1, I2) e 1 sobreviveu em parte
(I3, a segunda metade de A7). As outras deixaram de ser lacunas por um destes
três motivos: a decisão se derivava de outras passagens do texto (A1, A7 na
primeira parte); a decisão era de tecnologia, que o artigo declara delegar
(A3 na parte b, A8); ou o ponto nunca foi exercitado pelo protótipo (A6). A
resposta direta à pergunta de pesquisa é que **a arquitetura é
majoritariamente suficiente como guia de projeto, com três pontos cegos
identificados**. A maior parte do que o protótipo fez diferente do texto foi
decisão de alcance, e não falta de orientação. A Seção 6 lista os pontos em que
o texto guiou de fato decisões que o domínio regulatório tornou críticas.

As insuficiências **não se concentram em uma camada**. Cada uma está numa
camada diferente: amostragem na Camada 2, vigência da fonte na Camada 5,
alcance da validação diante da memória entre as Camadas 6 e 7. Contando as
camadas atingidas de forma secundária, nenhuma camada tem mais de um item. O
padrão está em outro lugar: **duas das três insuficiências estão em
fronteiras entre camadas**. I1 é uma decisão que acabou distribuída entre
`config.py` e as Camadas 2, 3 e 8. I3 é o conflito entre duas camadas que, cada
uma correta no seu escopo, discordam sobre o que conta como evidência. A
terceira, I2, é do mesmo tipo de lacuna que I1. Nos dois casos, o texto
**nomeia a preocupação** (estocasticidade, *knowledge bases* que evoluem) e dá
um mecanismo (registrar a versão do modelo, versionar o índice) que não cobre
o caso encontrado. O diário de evidências já apontava esse padrão sem nomeá-lo:
"interação entre camadas não antecipada pela arquitetura" aparece em
2026-08-14 (memória e validação) e na v4.1 (ingestão e governança). A segunda
dessas interações é defeito de implementação, e não lacuna do texto, mas é do
mesmo tipo. Para o Capítulo 4, isso sugere apresentar as insuficiências como
achado sobre a **especificação das interfaces entre camadas e das
preocupações transversais**, e não sobre uma camada fraca.

Os quatro desvios do Confronto **não são evidência de insuficiência**. Um
deles (D2, BM25) não é desvio: o artigo delega a técnica de recuperação, e a
Figura 4 lista alternativas. Dois (D3 e D4, os dois da Camada 6) são
simplificações deliberadas e registradas no diário, compatíveis com a
permissão explícita do texto de compor as camadas conforme a família. O
protótipo não é *memory-intensive*. Mas foram justificados na época com o
argumento errado, de que a arquitetura não decidia o ponto. O quarto (D1, a
ferramenta que devolve `str`) também não é simplificação deliberada: o texto
era claro, a Prática 1 descreve o antipadrão em que o protótipo caiu, e a
decisão registrada não tratava do assunto. É falha de leitura. Isso deve ser
declarado como tal, e não apresentado como escolha de projeto.

As 11 escolhas de escopo se concentram nas partes do papel de cada camada que
caracterizam as famílias ausentes do protótipo: planos e decomposição
(*agentic*), ferramentas externas (*tool-heavy*), memória de longo prazo e
filtragem por relevância (*memory-intensive*), *retries* e *checkpointing*
(*workflow-centric*). Isso é coerente com o texto, que propõe camadas "composed
differently depending on the target family" (p. 15). Mas implica a mesma
restrição da lacuna 2: **sobre essas partes, a suficiência do texto não foi
testada**. Há pelo menos duas insuficiências potenciais que o protótipo não
exercitou: o critério de "relevance filtering" da memória (S9) e a atribuição
da decomposição de tarefa (E2). Além disso, 4 das 11 escolhas de escopo
(S1, S4, S6 e S10) não foram registradas como decisão no diário, e outras 3
(S5, S9 e S11) foram registradas só em parte. Essas omissões só apareceram no
Confronto. Para a monografia, "escopo" deve ser lido
como o alcance do artefato, e nem sempre como uma escolha consciente.

Formulação que a evidência sustenta: **as oito camadas da Seção 8 foram
suficientes como guia de projeto para um sistema RAG-centric e
governance-critical; a reverificação encontrou três insuficiências reais, em
camadas diferentes, duas delas em fronteiras entre camadas, e nenhuma delas
exigiu alterar o papel de uma camada.** Há três limites a declarar. (1) A
fronteira entre "decisão de tecnologia delegada" e "insuficiência" é
interpretativa. Uma leitura mais estrita, que trate a amostragem como pura
tecnologia, deixa 2 insuficiências. Uma mais permissiva, que conte o "quê
validar" da Camada 7, chega a 4. O intervalo plausível é de **2 a 4**, e não
muda a conclusão qualitativa. (2) A classificação foi feita por um único
revisor, o autor, com apoio de um assistente baseado em LLM, sem segundo
avaliador independente. (3) O texto usado é o *preprint* SSRN. Se a versão
publicada mudar a Seção 8, as citações precisam ser conferidas de novo.
