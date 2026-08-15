# Registro de Decisões de Arquitetura

Este documento acompanha a construção do protótipo, registrando — para cada
camada da arquitetura conceitual de Maia et al. (2026, Seção 8) — as decisões
de projeto tomadas, as ambiguidades encontradas na proposta original dos
autores, e as adaptações necessárias para viabilizar a implementação.

**Importante**: este documento deve ser preenchido *durante* a construção de
cada camada, não retroativamente ao final. Ele é a evidência primária que
sustenta a avaliação de viabilidade descrita no Capítulo 1, Seção 5
(Metodologia), item (d), e alimenta diretamente a síntese do item (e).

Para cada entrada, preencher:
- **Decisão**: o que foi implementado e como.
- **Motivação**: por que essa decisão foi tomada (o que a arquitetura de
  Maia et al. orientou, ou deixou de orientar).
- **Ambiguidade/lacuna observada**: onde a arquitetura não foi suficiente
  para decidir sozinha, exigindo julgamento do autor.
- **Adaptação necessária**: o que teve que ser adaptado em relação à
  proposta original (se houver).

---

## Camada 2 — Núcleo de Raciocínio do LLM

**Decisão**: implementação de um wrapper fino (`LLMCore`) sobre o cliente
Python do Ollama, isolando a camada superior (Orquestração) do provedor de
LLM específico.

**Motivação**: Maia et al. (2026) definem a responsabilidade da camada
(interpretar intenção, produzir planos e respostas estruturadas), mas não
prescrevem qual provedor ou tecnologia usar — a arquitetura é agnóstica de
implementação nessa dimensão. A escolha por um modelo local via Ollama foi
motivada por reprodutibilidade: qualquer pessoa pode clonar o repositório e
rodar o protótipo sem custo e sem chave de API.

**Ambiguidade/lacuna observada**: *(preencher conforme o desenvolvimento
avançar — por exemplo, ao decidir como a camada deve lidar com respostas
malformadas do modelo, ou como equilibrar qualidade de raciocínio versus
custo computacional local)*

**Adaptação necessária**: nenhuma até o momento (estágio inicial, apenas
geração de texto simples).

---

## Camada 1 — Interação com o Usuário

**Decisão**: loop de CLI em texto puro (`src/layer1_interaction/cli.py`,
ponto de entrada `main.py`). Um único `Orchestrator` é instanciado uma vez
por sessão (não por pergunta), para que a Camada 6 (memória) acumule as
interações da sessão inteira, como já validado em
`run_check_orchestration.py`. Após cada resposta, um rodapé de proveniência
é impresso a partir de `orchestrator.ultimo_registro` (o `RegistroInteracao`
da Camada 8 mais recente): títulos das fontes normativas usadas e, se a
Camada 7 sinalizou citação não verificada, um aviso adicional. Decisão
combinada com o usuário: mostrar esse resumo legível em vez do log JSON
bruto (`logs/interacoes.jsonl`), que existe para auditoria/análise
posterior, não para leitura durante a conversa.

**Adaptação na Camada 3**: `Orchestrator.__init__` passou a manter
`self.ultimo_registro`, atualizado nos dois pontos de saída de
`responder()` com o retorno de `registrar_interacao(...)` (que já calculava
esse dado internamente, mas o descartava). Escolhido em vez de mudar o tipo
de retorno de `responder()` para incluir o registro, o que quebraria os
consumidores existentes que esperam uma `str`
(`run_check_orchestration.py` e outros scripts de validação).

**Motivação**: Maia et al. (2026) atribuem à Camada 1 a interface com o
usuário, mas excluem multimodalidade do escopo desta pesquisa (ver README),
o que deixa uma CLI de texto como a implementação mínima natural. Não há
argparse, arquivo de configuração de sessão nem comandos além de
sair/exit/quit — nenhum caso de uso real pediu mais que isso ainda.

**Ambiguidade/lacuna observada**: a arquitetura não é explícita sobre se a
Camada 1 deve expor artefatos de outras camadas (aqui, a proveniência da
Camada 8) ou se deve ser uma interface "burra" que só repassa texto — ficou
como decisão de projeto, resolvida a favor de expor um resumo de
proveniência, dado que o domínio (compliance regulatório) tem transparência
sobre fontes como parte do valor central do sistema, não um extra.

**Adaptação necessária**: nenhuma além da já registrada acima.

---

## Camada 3 — Orquestração e Fluxo de Trabalho

**Decisão**: implementação de uma classe `Orchestrator`
(`src/layer3_orchestration/orchestrator.py`) com um único método público
`responder(pergunta)`, que coordena 4 etapas privadas em sequência fixa:
`_interpretar` -> `_buscar_normativo` -> `_sintetizar_resposta` ->
`_validar_citacao`. As etapas de busca de normativo e de validação de
citação são **stubs explícitos** neste estágio: `_buscar_normativo` retorna
um placeholder textual fixo (ainda não há corpus indexado), e
`_validar_citacao` apenas repassa a resposta sem alterá-la. `_interpretar`
usa a Camada 2 (`LLMCore`) para classificar a pergunta em um destes tipos:
`normativo`, `parecer_juridico` ou `fora_de_escopo`.

**Motivação**: Maia et al. (2026) atribuem à Camada 3 a coordenação das
etapas do fluxo de trabalho, mas não prescrevem a granularidade das etapas
nem como estruturar o código — a divisão em 4 métodos privados nomeados
segundo o fluxo já descrito no README foi uma escolha de implementação para
manter cada etapa isolada e testável individualmente. A validação do fluxo
via `run_check_orchestration.py` segue o mesmo padrão do `run_check.py` da
Camada 2, para permitir uma verificação rápida e isolada por camada.

**Ambiguidade/lacuna observada**: a arquitetura conceitual não define como
uma camada superior deve se comportar quando camadas das quais ela depende
funcionalmente (aqui, Camadas 4, 5 e 7) ainda não foram implementadas. Isso
é relevante especificamente para uma construção *incremental* como a deste
protótipo — a arquitetura parece pressupor que todas as camadas já existem
quando descreve as interações entre elas. Uma segunda ambiguidade: a
classificação produzida por `_interpretar` (ex: `parecer_juridico`) é
calculada mas **ainda não altera o fluxo** — não há, nesta camada, uma
definição de a quem cabe agir sobre essa classificação (recusar, desviar o
fluxo, etc.); isso foi deliberadamente deixado para a Camada 7 (Governança),
já que a arquitetura separa "orquestrar o fluxo" de "aplicar constraints",
mas não é explícita sobre onde a fronteira entre as duas fica quando o
resultado de uma etapa de orquestração já contém informação relevante para
governança.

**Adaptação necessária**: uso de stubs explícitos e comentados no lugar das
Camadas 4/5 e 7, como uma decisão temporária de sequenciamento de
construção — a ser substituída sem alterar a interface pública
(`responder`) quando essas camadas forem implementadas. Combinado com o
usuário: este desenho é propositalmente mínimo agora e será refinado em uma
etapa posterior de refatoração, já com as demais camadas presentes.

**Atualização (2026-08-15)**: a classificação `parecer_juridico` passou a
desviar o fluxo (Camada 7). A terceira classificação possível,
`fora_de_escopo`, inicialmente permaneceu **sem tratamento especial** —
mesma ambiguidade original. Achado empírico registrado em
`docs/evidencias_empiricas.md` (2026-08-15): uma pergunta fora de escopo
seguia o fluxo normal, buscava (sem sentido) na base de normativos, e
recebia resposta com disclaimer de compliance que não se aplicava.
**Resolvido, mesma sessão**: `_RECUSAS`, um dicionário `tipo -> função de
recusa` em `orchestrator.py`, generaliza o desvio de fluxo já usado para
`parecer_juridico` para qualquer classificação que deva recusar sem
buscar/sintetizar — `fora_de_escopo` foi adicionado usando a nova
`recusar_fora_de_escopo()` (Camada 7). Reproduzido após a correção: a
mesma pergunta de teste agora retorna a recusa fixa, sem busca normativa e
com `fontes_normativas: []` na Camada 8 (antes vinha com uma fonte
irrelevante). Ver `tests/casos_teste.md`, Caso 4, para o resultado
atualizado.

**Observação empírica (validação via `run_check_orchestration.py`)**: com o
stub de `_buscar_normativo` (sem corpus real) e sem `_validar_citacao` real,
o modelo respondeu citando uma "Resolução do CPM 4.665/2021" — uma citação
normativa aparentemente fabricada (o nome do órgão não corresponde a uma
autoridade emissora real de resoluções normativas no formato citado). Este é
um resultado empírico relevante para a avaliação de viabilidade: evidencia
concretamente, antes mesmo de as Camadas 5 e 7 existirem, por que a
arquitetura de Maia et al. torna essas camadas necessárias em domínios de
alto risco de alucinação factual — sem base de conhecimento indexada (Camada
5) e sem validação de citação (Camada 7), o núcleo de raciocínio (Camada 2)
produz números de norma verossímeis, mas não verificáveis nem
necessariamente reais. Detalhamento completo desta observação registrado em
`docs/evidencias_empiricas.md`.

---

## Camada 4 — Integração de Ferramentas e Serviços

**Decisão**: uma única ferramenta, `buscar_normativo` (função, não classe)
em `src/layer4_tools/tools.py`, que embrulha a `KnowledgeBase` (Camada 5) e
formata os resultados em texto citável (fonte + URL + trecho). O
`Orchestrator._buscar_normativo` (Camada 3) passou a chamar essa função,
substituindo o stub anterior.

**Motivação**: deliberadamente **não** foi criada uma abstração genérica de
"ferramenta" (interface comum com nome/descrição/execução, registro de
múltiplas ferramentas) — decisão discutida com o usuário. Só existe um caso
de uso real hoje; generalizar agora seria abstração prematura sem
justificativa concreta. O BCB expõe outras APIs públicas de dados abertos
(Portal de Dados Abertos / plataforma Olinda — ex: dados cadastrais de
instituições autorizadas, SGS, IFData) que são candidatas naturais a uma
segunda ferramenta futura; a generalização fica adiada para quando (e se)
essa segunda ferramenta for implementada.

**Ambiguidade/lacuna observada**: a arquitetura de Maia et al. não indica em
que ponto a "integração de ferramentas" deveria ganhar uma abstração formal
versus permanecer uma chamada de função direta — isso ficou como julgamento
do implementador, apoiado no princípio geral (também usado nas Camadas 2/3)
de não introduzir abstração sem caso de uso concreto puxando o desenho.

**Adaptação necessária**: nenhuma além da já registrada na Camada 3 (troca
do stub pela chamada real).

**Observação empírica** (validação via `run_check_orchestration.py`, agora
com Camadas 4/5 ligadas): mesmo recebendo o texto correto do normativo como
contexto, o modelo distorceu um número citado nele (relatou "50 mil
clientes" onde o texto fornecido dizia "cinco milhões"). Detalhado em
`docs/evidencias_empiricas.md` — reforça que a Camada 7 precisará validar
fidelidade ao conteúdo do contexto, não só a existência da norma citada.

---

## Camada 5 — Integração de Conhecimento (RAG)

**Decisão**: corpus inicial em `data/normativos/` com 2 atos normativos com
texto integral incluído — Resolução Conjunta nº 1/2020 (marco regulatório do
Open Finance) e Circular nº 4.015/2020 (escopo de dados e serviços) — e 2
pendentes documentados em `data/normativos/PENDENTES.md` (Resolução BCB nº
339/2023, sobre duplicata escritural, e Resolução BCB nº 32/2020, requisitos
técnicos), cujo texto oficial ainda não foi localizado com segurança. Cada
arquivo do corpus é um Markdown com cabeçalho de metadados (título, ementa,
URL oficial, data, versão) seguido do texto integral. A indexação/busca
(`src/layer5_knowledge/knowledge_base.py`, classe `KnowledgeBase`) é lexical
simples: divide cada normativo em trechos por artigo (unidade natural de
citação em atos normativos brasileiros) e pontua por sobreposição de
palavras (sem stopwords, sem acentos) entre a pergunta e cada trecho — sem
embeddings e sem biblioteca de vector DB.

**Motivação**: Maia et al. (2026) atribuem à Camada 5 a integração de
conhecimento externo, mas não prescrevem a técnica de indexação/recuperação.
A escolha por busca lexical simples (decidida com o usuário, ver também
Camada 3) prioriza que a técnica de recuperação seja uma decisão de
implementação explícita e auditável — coerente com a decisão de não usar
frameworks/abstrações de terceiros escondendo decisões de camada — em
detrimento da robustez semântica que embeddings ofereceriam. Trade-off
assumido conscientemente: buscas por paráfrase (sem sobreposição lexical)
tendem a falhar.

**Ambiguidade/lacuna observada**: obter o *texto oficial verbatim* de atos
normativos públicos do BCB mostrou-se mais difícil do que o esperado — o
portal `bcb.gov.br` é uma SPA (Angular) sem busca programável, e uma
tentativa automatizada de localizar o PDF da Resolução BCB nº 339/2023 por
padrão de URL retornou uma norma **diferente e não relacionada** (mesma
numeração, ano diferente: 1975). Isso não é uma ambiguidade da arquitetura
de Maia et al. em si, mas evidencia uma dificuldade prática de qualquer
implementação real da Camada 5 em domínio regulatório brasileiro: a
"integração de conhecimento" pressupõe fontes machine-readable, e fontes
governamentais públicas brasileiras nem sempre são. Detalhado em
`docs/evidencias_empiricas.md`. Segunda ambiguidade: a extração de texto de
PDF introduz artefatos de espaçamento (ex: "Art. 3 1." em vez de "Art. 31.")
que afetam a precisão da divisão em trechos por artigo — mitigado
parcialmente, não eliminado, pela regex de divisão.

**Adaptação necessária**: uso de extração de texto via biblioteca `pypdf`
(dependência adicionada apenas à etapa manual de preparação do corpus, não
ao runtime do protótipo — `KnowledgeBase` não depende de `pypdf`) para
converter os PDFs oficiais baixados em texto plano, já que a leitura de PDF
grande (>10 páginas) pelo pipeline padrão de ferramentas exigia
`poppler-utils`, indisponível no ambiente. Corpus incompleto (2 de 4 normas
aprovadas) é uma adaptação temporária, documentada e rastreável via
`PENDENTES.md`, seguindo o mesmo padrão de transparência dos stubs da
Camada 3.

---

## Camada 6 — Contexto e Memória

**Decisão**: classe `Memoria` (`src/layer6_memory/memory.py`) que guarda as
últimas N interações (`Interacao(pergunta, resposta)`, padrão N=5) em
memória de processo — sem persistência em disco entre execuções. Expõe
`adicionar(pergunta, resposta)` e `contexto_formatado()`. O `Orchestrator`
(Camada 3) passou a manter uma `Memoria` própria por instância; em
`_sintetizar_resposta`, o histórico formatado é injetado como contexto
extra antes do contexto normativo, e a interação é registrada na memória ao
final de `responder()`.

**Motivação**: Maia et al. (2026) atribuem à Camada 6 a manutenção do
estado da conversa, mas não especificam limite de tamanho, formato de
injeção no prompt, nem se deve haver persistência entre sessões. Optou-se
por um corte simples (buffer circular das últimas N interações, injeção
como texto plano no prompt) por ser suficiente para o caso de uso de
perguntas de acompanhamento em uma sessão CLI (Camada 1, ainda não
construída), sem introduzir complexidade (ex: sumarização de histórico
longo, banco de dados) sem caso de uso real que a justifique.

**Ambiguidade/lacuna observada**: a arquitetura não define se a "memória"
deveria influenciar também a etapa de interpretação (`_interpretar`), não só
a síntese — decisão de escopo: por ora, só a síntese usa o histórico, dado
que o objetivo mínimo é permitir perguntas de acompanhamento fazerem
sentido, não mudar a classificação da pergunta. Persistência entre sessões
(ex: retomar uma investigação em outro dia) também não está resolvida pela
arquitetura original e foi deixada explicitamente fora de escopo aqui.

**Adaptação necessária**: nenhuma além da integração com o `Orchestrator`
já descrita.

**Observação empírica** (validação via `run_check_orchestration.py` com 2
perguntas em sequência): a segunda pergunta ("e qual o prazo... considerando
o que você acabou de explicar?") foi respondida corretamente usando o
histórico da primeira, confirmando que a memória de fato influencia a
síntese. Na mesma execução, o erro de atribuição de artigo já observado na
Camada 4 se repetiu (novamente "art. 51" em vez do correto Art. 6º) — ver
`docs/evidencias_empiricas.md` para a atualização dessa entrada.

---

## Camada 7 — Governança e Segurança

**Decisão**: módulo `src/layer7_governance/governance.py` com duas funções
puras, construídas diretamente sobre os achados de
`docs/evidencias_empiricas.md`:

- `validar_citacao(resposta, contexto_normativo)`: checagem determinística
  por regex. Extrai números de artigo (`art\.?\s*\d+`) e nomes/números de
  norma (`Resolução[...]/Circular/Instrução Normativa nº N`) citados na
  resposta e confere se aparecem literalmente no trecho normativo usado
  como contexto naquela chamada. O que não bate vira um aviso anexado à
  resposta (não bloqueia — sinaliza). Sempre anexa, ao final, o aviso fixo
  de que a resposta não é parecer jurídico definitivo.
- `recusar_parecer_juridico()`: texto de recusa fixo.
- `recusar_fora_de_escopo()` (adicionada em 2026-08-15): texto de recusa
  fixo para perguntas fora do domínio Open Finance/PJ, mesmo padrão de
  `recusar_parecer_juridico`. Ver atualização na entrada da Camada 3 sobre
  o achado que motivou essa adição.

**Adaptação na Camada 3**: a classificação `interpretacao.tipo ==
"parecer_juridico"`, calculada desde a Camada 3 mas nunca usada (ambiguidade
documentada naquela entrada), agora desvia o fluxo em `responder()` — recusa
direta, sem buscar normativo nem sintetizar. `_validar_citacao` deixou de
ser stub e passou a receber também o `normativo` usado na síntese (mudança
de assinatura), necessário para checar a citação contra o contexto certo.

**Motivação**: os 3 achados empíricos documentados (norma inventada;
número distorcido mesmo com contexto correto; artigo citado incorretamente
de forma recorrente) mostraram que o risco concreto neste domínio não é
just "o modelo alucina às vezes" — é especificamente citação de artigo/norma
incorreta, mesmo quando o contexto correto está disponível. Por isso a
validação foi desenhada para checar exatamente esse tipo de erro, em vez de
uma validação genérica.

**Ambiguidade/lacuna observada**: Maia et al. (2026) atribuem à Camada 7 a
aplicação de constraints, mas não descem ao nível de "como" validar uma
citação — a escolha por regex determinístico (em vez de, por exemplo, uma
segunda chamada ao LLM pedindo para "auto-verificar" a resposta) foi
deliberada: mais previsível, sem custo computacional adicional, e sem o
risco de o próprio verificador alucinar. Trade-off: só pega citações no
formato padrão de atos normativos brasileiros — não é verificação
semântica. A regra "usar apenas fontes públicas" não tem checagem em
runtime aqui; é garantida estruturalmente pela curadoria do corpus na
Camada 5 — decisão consciente de não duplicar essa responsabilidade.

Uma segunda ambiguidade, encontrada ao testar a interação Camada 6 + Camada
7: `validar_citacao` só valida contra o contexto normativo **da pergunta
atual**, não contra o que está na memória de turnos anteriores. Em teste
(ver `docs/evidencias_empiricas.md`), uma resposta de acompanhamento citou
artigos que apareciam no contexto do turno anterior (via memória), mas não
no contexto recuperado para o turno atual — gerando um aviso de "citação
não verificada" tecnicamente correto (não estava no contexto *daquela*
chamada), mas que pode ser um falso positivo do ponto de vista do usuário,
que via a citação como coerente com a conversa. Decisão: manter o
comportamento atual (validar só contra o contexto do turno) e documentar a
lacuna, em vez de expandir o escopo da validação para toda a memória sem um
caso de uso que justifique a complexidade adicional.

**Adaptação necessária**: ao testar, descobri um bug de implementação (não
da arquitetura): a Camada 3 estava salvando na Camada 6 (memória) a resposta
**já com os avisos de governança anexados**. Isso fazia o disclaimer de
validação humana entrar no histórico da conversa e o modelo passou a
ecoá-lo (parafraseado) dentro da resposta seguinte, resultando em disclaimer
duplicado. Corrigido: a memória agora guarda a resposta sintetizada, antes
da validação de citação; `_validar_citacao` é aplicada só na resposta
retornada ao usuário, não na que entra no histórico.

---

## Camada 8 — Observabilidade e Proveniência

**Decisão**: função `registrar_interacao(...)`
(`src/layer8_observability/observability.py`) que grava, para cada
interação, um registro estruturado em JSON Lines (`logs/interacoes.jsonl`,
um objeto por linha): timestamp, pergunta, classificação da Camada 3
(`tipo_classificacao`), fontes normativas usadas (`fontes_normativas`, lista
de `{titulo, url_oficial}`), se a Camada 7 sinalizou citação não verificada
(`aviso_citacao_nao_verificada`, booleano) e a resposta final entregue ao
usuário. As fontes são extraídas do texto já formatado que a Camada 4
retorna (linhas `"Fonte: título (url)"`) via regex determinístico — mesmo
padrão de parsing já usado na Camada 7 — com deduplicação por
`(titulo, url)`, já que vários trechos recuperados pela Camada 5 podem vir
do mesmo documento. O `Orchestrator` (Camada 3) passou a chamar
`registrar_interacao` nos dois pontos de saída de `responder()`: na recusa
de parecer jurídico (sem fontes) e no fluxo normal, após `_validar_citacao`.

**Motivação**: Maia et al. (2026) atribuem à Camada 8 o registro de
proveniência para rastreabilidade, mas não prescrevem formato de log nem
quais campos capturar. JSON Lines foi escolhido por ser append-only,
legível linha a linha e trivial de processar depois (ex: para a análise
empírica da monografia) sem depender de biblioteca de log estruturado ou
banco de dados. Ao contrário da Camada 6 (memória em processo, sem
persistência — decisão deliberada por ali não ser o propósito da camada),
aqui a persistência em disco é o próprio propósito: proveniência que não
sobrevive ao processo não serve para auditoria.

**Ambiguidade/lacuna observada**: a arquitetura não distingue "log de
observabilidade" de "métricas/tracing" no sentido de observabilidade de
sistemas distribuídos (latência, erros de infraestrutura) — aqui a leitura
adotada foi a mais alinhada ao domínio do protótipo: proveniência de
conteúdo (o que fundamentou cada resposta), não telemetria operacional, já
que o objetivo do trabalho é avaliar viabilidade da arquitetura em um
domínio de compliance regulatório, não operar o sistema em produção.

**Adaptação necessária**: nenhuma além da integração com o `Orchestrator`
já descrita. `logs/` foi adicionado ao `.gitignore` (dado de execução, não
código-fonte).

---

## Multimodalidade (Camada 1) — fora de escopo

Conforme definido no Capítulo 1, Seção 5 (Metodologia), os aspectos
multimodais da Camada de Interação com o Usuário foram explicitamente
delimitados como fora de escopo desta pesquisa.
