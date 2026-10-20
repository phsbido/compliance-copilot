# Decisões de Design — o "Porquê"

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

Para cada decisão, uso: o que foi decidido, evidência/inferência do porquê,
alternativas óbvias e o trade-off assumido, e uma avaliação (bom motivo,
motivo histórico que não se aplica mais, ou problema).

---

## 1. Estrutura de pastas espelha a teoria acadêmica, não o domínio do problema

**Decisão**: `src/layerN_nome/` para cada uma das 8 camadas de Maia et al.
(2026), em vez de uma estrutura orientada a funcionalidade (ex.: `chat/`,
`rag/`, `guardrails/`).

**[EVIDÊNCIA]** `README.md:18-20`: "para rastreabilidade direta entre a
proposta teórica e a implementação" — objetivo explícito é permitir a um
leitor da monografia (a banca examinadora) ligar cada seção da arquitetura
conceitual a uma pasta concreta de código, sem precisar inferir o
mapeamento.

**Alternativa óbvia**: organizar por domínio (`chat/`, `rag/`, `compliance/`)
— mais idiomático para um projeto de software "normal", pior para o
propósito de pesquisa deste projeto específico.

**Avaliação**: bom motivo, e apropriado ao propósito declarado (artefato de
avaliação de viabilidade de uma arquitetura, não um produto). Para qualquer
outro tipo de projeto, essa estrutura seria um antipadrão (acoplar
organização de código a uma teoria externa tende a envelhecer mal se a
teoria mudar).

---

## 2. Sem abstração de "ferramenta" genérica na Camada 4

**Decisão**: `buscar_normativo` é uma função solta, não uma classe
implementando uma interface `Tool` com nome/descrição/registro.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:170-184`: "só existe um caso de
uso real hoje; generalizar agora seria abstração prematura sem justificativa
concreta." Candidatos concretos a uma segunda ferramenta (APIs públicas do
BCB — Portal de Dados Abertos, SGS, IFData) são citados como o gatilho que
justificaria generalizar no futuro.

**Alternativa óbvia**: um registro de ferramentas com `nome`, `descricao`,
`parametros_schema`, `executar()` — o padrão comum em frameworks de agentes
(function calling estruturado).

**Avaliação**: bom motivo — evita "abstração especulativa" (código genérico
sem caso de uso que o exercite de fato, historicamente uma fonte comum de
complexidade acidental). O critério de decisão ("generalizar só quando
houver um segundo caso de uso real") é aplicado de forma consistente em
outras camadas (ver itens 3 e 6 abaixo), então não é um princípio isolado —
é uma convenção de projeto deliberada, documentada em
`docs/estado_atual.md:82`: "Preferir decisões de implementação mínimas e
explícitas (...) até haver um segundo caso de uso real que justifique
generalizar — aplicado nas Camadas 4 e 6."

---

## 3. Memória de sessão sem persistência entre execuções

**Decisão**: `Memoria` (Camada 6) guarda estado só em uma lista Python em
processo — reiniciar `python main.py` começa do zero.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:271-277`: persistência entre
sessões (retomar uma investigação em outro dia) foi "deixada explicitamente
fora de escopo" — não porque fosse tecnicamente difícil, mas porque nenhum
caso de uso real do protótipo (um copiloto de pergunta-resposta de uma
sessão) exige isso.

**Alternativa óbvia**: salvar o histórico em SQLite/arquivo JSON, associado a
um identificador de sessão.

**Avaliação**: bom motivo para um protótipo de pesquisa com escopo definido
(CLI de sessão única). Seria uma lacuna real para um produto de compliance
de uso contínuo, onde um analista plausivelmente quer retomar uma
investigação — mas isso está fora do escopo declarado da pesquisa
(`README.md:41-42`, aspectos multimodais/de produto fora de escopo).

---

## 4. Validação de citação por regex, não por segunda chamada ao LLM

**Decisão**: `validar_citacao` (Camada 7) confere citações com expressões
regulares determinísticas, não pedindo ao próprio modelo para
"auto-verificar" a resposta.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:326-335`: escolha deliberada —
"mais previsível, sem custo computacional adicional, e sem o risco de o
próprio verificador alucinar." Trade-off assumido conscientemente: só pega
o formato padrão de citação brasileira, não é verificação semântica.

**Alternativa óbvia**: um segundo prompt tipo "confira se esta resposta é
fiel ao contexto fornecido" (padrão comum de *LLM-as-judge*).

**Avaliação**: bom motivo, e a limitação é reconhecida explicitamente, não
escondida — o próprio docstring do módulo (`governance.py:14-16`) admite que
"não detecta toda fabricação possível". O risco descartado (verificador que
também alucina) é real e documentado na literatura de LLM — a escolha é
defensável tecnicamente, não só por conveniência de implementação.

---

## 5. Memória guarda a resposta *antes* da validação de citação

**Decisão**: `Orchestrator.responder` salva na memória a resposta sintetizada
(`resposta_sintetizada`), não a resposta final com avisos/disclaimer
(`resposta_validada`) — `orchestrator.py:69-74`.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:350-357`: correção de um **bug
real encontrado em teste**, não uma decisão de design a priori. A versão
original salvava a resposta já com os avisos de governança anexados; isso
fazia o disclaimer entrar no histórico da conversa e o modelo passava a
ecoá-lo (parafraseado) na resposta seguinte, produzindo disclaimer
duplicado. Detalhado também em `docs/evidencias_empiricas.md:149-155`
(Observação 2 da entrada de 2026-08-14).

**Avaliação**: bom motivo — é um exemplo raro no projeto de uma decisão
motivada inteiramente por comportamento observado do modelo em produção
(teste manual), não por raciocínio a priori sobre a arquitetura. Reforça o
valor de `docs/evidencias_empiricas.md` como fonte de evidência empírica
para a pesquisa: sem essa observação registrada, a razão de ser desta linha
de código não seria recuperável só lendo o código.

---

## 6. `_RECUSAS`: desvio de fluxo generalizado via dicionário, não `if/elif`

**Decisão**: `orchestrator.py:36-39` mapeia `tipo -> função de recusa`;
`responder()` faz `if interpretacao.tipo in _RECUSAS: resposta =
_RECUSAS[interpretacao.tipo]()`.

**[EVIDÊNCIA]** Não nasceu assim — nasceu como um `if` único para
`parecer_juridico` (Estágio inicial, `docs/decisoes_arquitetura.md:86-127`).
Um teste revelou (`docs/evidencias_empiricas.md:179-227`, 2026-08-15) que
`fora_de_escopo` era calculado mas não desviava o fluxo, causando busca
normativa sem sentido e disclaimer indevido. A correção generalizou o
padrão em vez de adicionar um segundo `if` — `docs/decisoes_arquitetura.md:216-226`
registra explicitamente essa escolha ("generalizar o mecanismo de desvio já
existente... resolveu o problema com uma mudança pequena — evidência de que
o desenho inicial (...) já comportava essa generalização sem refatoração
maior").

**Alternativa óbvia**: `if tipo == "parecer_juridico": ... elif tipo ==
"fora_de_escopo": ...`.

**Avaliação**: bom motivo, e uma evidência interessante para a pesquisa em
si — mostra um caso onde a arquitetura conceitual (que não define
explicitamente "a quem cabe agir sobre uma classificação calculada",
`docs/decisoes_arquitetura.md:107-120`) permitiu, na prática, um refinamento
incremental sem redesenho, quando o defeito foi corrigido generalizando um
padrão já presente.

---

## 7. Pipeline Bronze/Silver/Gold mantido paralelo, não substituindo `knowledge_base.py`

**Decisão**: `ingest_normativos.py` foi implementado como artefato
ilustrativo, sem alterar a Camada 5 real.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:472-484`: o pedido original
incluía reescrever `knowledge_base.py` para consumir o índice Gold; isso
reorganizaria o corpus já curado e alteraria uma camada **já validada**
(citada em 4 casos de teste, 20 execuções de benchmark, e no Apêndice A). O
risco de invalidar evidência empírica já coletada foi levantado ao usuário
antes de implementar — decisão explícita do usuário de manter o runtime
intocado.

**Alternativa óbvia**: implementar o pipeline e migrar `KnowledgeBase` para
consumi-lo, unificando a Camada 5 em uma única implementação.

**Avaliação**: bom motivo, e um caso interessante de metodologia de
pesquisa: o próprio `docs/decisoes_arquitetura.md:503-509` registra este
episódio como "dado relevante para a discussão de viabilidade" — mostra o
processo de registro de decisões funcionando como um checkpoint que evita
mudança de arquitetura não intencional em cima de evidência empírica já
coletada. Efeito colateral aceito conscientemente: hoje existem **duas
implementações de busca/indexação de normativos no repositório**, uma real e
uma ilustrativa, o que exige que qualquer leitor futuro do código (inclusive
esta análise) saiba diferenciar as duas — ver `07_riscos.md` para o risco de
confusão que isso cria para quem não lê a documentação primeiro.

---

## 8. Corpus incompleto documentado como pendente, não incluído com fonte incerta

**Decisão**: `data/normativos/PENDENTES.md` documenta 2 normas
aprovadas-mas-não-incluídas, em vez de incluir um texto obtido por caminho
não verificado.

**[EVIDÊNCIA]** `docs/evidencias_empiricas.md:54-82`: motivado por um
quase-erro real — uma tentativa automatizada de localizar o PDF da
Resolução BCB nº 339/2023 por padrão de URL retornou um documento real,
existente no domínio oficial, mas de **1975**, não 2023 (mesma numeração,
ano errado). O erro só foi percebido verificando o conteúdo, não a URL.
`PENDENTES.md:1-6` aplica esse aprendizado como regra geral: "não incluir
texto não verificado verbatim no corpus — o mesmo cuidado que motiva a
Camada 7."

**Alternativa óbvia**: incluir o texto obtido automaticamente e confiar na
Camada 7 para pegar eventuais erros de citação depois.

**Avaliação**: bom motivo, e coerente com o princípio mais amplo do projeto
de nunca apresentar dado não verificado como se fosse verificado (o mesmo
padrão reaparece em `_heuristica_metadados()` do pipeline ilustrativo, que
sempre marca `fonte_confirmada: false` para PDFs brutos — ver
`03_modulos/layer5_knowledge.md`). É also uma decisão que **limita
deliberadamente a cobertura do corpus** (2 de 4 normas planejadas) em troca
de integridade — um trade-off explícito entre completude e confiabilidade.

---

## 9. Sem framework de orquestração de agentes

**Decisão**: nenhuma dependência de LangChain, LangGraph, CrewAI, etc. — o
fluxo inteiro é uma classe Python com métodos privados chamados em sequência
fixa.

**[EVIDÊNCIA]** Inferido da ausência dessas bibliotecas em
`requirements.txt` e da menção recorrente, em várias entradas de
`docs/decisoes_arquitetura.md`, ao princípio de "não introduzir abstração
sem caso de uso concreto" — mas não encontrei uma entrada específica que
declare esse "non-negotiable" de forma isolada e explícita no corpo dos
documentos lidos, exceto a menção indireta em
`docs/decisoes_arquitetura.md:441-442` ("o non-negotiable é não usar
CrewAI/LangGraph/etc. para esconder decisões de camada"), ao justificar por
que `pandas` foi aceito como dependência mas não conta como violação dessa
regra.

**Alternativa óbvia**: usar LangGraph para modelar o fluxo
`interpretar -> buscar -> sintetizar -> validar` como um grafo de estados.

**Avaliação**: bom motivo para o propósito de pesquisa — o objetivo é testar
a arquitetura conceitual de Maia et al., e um framework de terceiros
introduziria uma segunda camada de abstração (as primitivas do framework)
entre a teoria sendo testada e o código, dificultando a rastreabilidade que
é o objetivo central do projeto (ver item 1).

---

## 10. Busca lexical simples em vez de embeddings/vector DB

**Decisão**: `KnowledgeBase.buscar` pontua por interseção de conjuntos de
tokens normalizados, sem embeddings nem biblioteca de vetores.

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:214-222`: escolha decidida com
o usuário, priorizando que "a técnica de recuperação seja uma decisão de
implementação explícita e auditável (...) em detrimento da robustez
semântica que embeddings ofereceriam." Trade-off assumido conscientemente:
buscas por paráfrase (sem sobreposição lexical) tendem a falhar.

**Alternativa óbvia**: embeddings (ex.: `sentence-transformers`) + busca por
similaridade de cosseno, ou uma vector DB (Chroma, FAISS).

**Avaliação**: motivo defensável para os objetivos de pesquisa (auditabilidade,
menos dependências, reprodutibilidade sem GPU/modelo de embedding adicional),
mas é também a limitação que **mais diretamente explica** o achado empírico
central do projeto — a taxa de 60% de aviso de citação não verificada no
cenário "Norma Ausente" (`docs/tabela_resultados_empiricos.csv`, linha
`norma_ausente_fronteira`) é, em grande parte, consequência direta de busca
lexical recuperando trechos irrelevantes por coincidência de palavras
comuns, não semanticamente relacionados à pergunta. **[INFERÊNCIA]**: se a
Camada 5 usasse embeddings, é plausível que a taxa de recuperação incidental
fosse menor (embeddings tendem a diferenciar melhor "Resolução BCB nº
32/2020" — ausente — de outras normas do corpus do que sobreposição de
palavras comuns como "Open Finance", "instituições", "requisitos") — mas
isso é uma hipótese não testada neste projeto, não um resultado empírico.
