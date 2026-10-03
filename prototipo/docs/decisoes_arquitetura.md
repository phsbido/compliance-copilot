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

### Parâmetros de amostragem explícitos (v4, 2026-09-24)

**Decisão**: temperatura e seed deixam de ser o padrão implícito do Ollama
(temperatura 0,8, seed aleatória — o que o protótipo usava da v1 à v3.1 sem
que isso tivesse sido decidido) e passam a ser configuração explícita
(`.env`, `src/config.py`), com valores diferentes por tipo de chamada:

- **classificação** (`_interpretar`: normativo / parecer jurídico / fora de
  escopo): **temperatura 0** — é uma decisão de governança, e a mesma
  pergunta não pode ser recusada numa vez e respondida em outra;
- **síntese** (`_sintetizar_resposta`): **temperatura 0,1** — quase
  determinística (fidelidade ao texto normativo, não variedade), com margem
  mínima contra laços de repetição do modo guloso;
- **seed 42** — reprodutibilidade e auditoria.

`LLMCore.generate` aceita opções por chamada; a Camada 3 passa a
temperatura de cada etapa. A Camada 8 registra, em cada interação, modelo,
ID do modelo (digest, via `ollama.list()`), temperaturas e seed. O
benchmark passa a ter o modo `producao` (a configuração do `.env`, padrão) e
o modo `sensibilidade` (0,8 nas duas chamadas, seed aleatória), no lugar de
`livre`/`deterministico`.

**Motivação**: (1) o benchmark deve medir a configuração que o usuário usa —
até a v3.1, o modo "livre" media 0,8 porque esse era o padrão, e o modo
"determinístico" media uma configuração que ninguém usava; (2) os dados do
projeto mostram que temperatura baixa dá **consistência, não correção**: na
v2, o modo determinístico errou o limite de clientes 5 de 5 vezes ("3
milhões"), contra 1 de 5 no livre — o erro virou sistemático. Quem eliminou
o número inventado foi a política da Camada 7 (v3), não a temperatura.
Fixar a temperatura é, portanto, uma decisão de estabilidade e auditoria, e
não substitui a governança.

**Ambiguidade/lacuna observada**: Maia et al. atribuem à Camada 2
"interpretar a intenção" e "sintetizar respostas", mas não tratam do
controle de aleatoriedade do modelo, que aqui se mostrou uma decisão com
efeito de governança (a classificação decide se há recusa) e de
observabilidade (sem registrar parâmetros e ID do modelo, uma resposta não
pode ser reproduzida nem auditada). A decisão ficou distribuída: a Camada 2
executa, `config.py` define, a Camada 3 escolhe por etapa, a Camada 8
registra.

**Limite**: temperatura 0 com seed fixa só garante saída idêntica no mesmo
ambiente (versão do Ollama, ID do modelo, hardware); em outra máquina,
espera-se reproduzir as taxas, não necessariamente o texto.

### Adendo (2026-10-01): lacuna e adaptação desta camada

Os campos "Ambiguidade/lacuna observada" e "Adaptação necessária" do início
desta seção ficaram com o texto provisório de 2026-08-14. Completados a
partir do que foi registrado depois e do confronto com o texto da Seção 8
(ver "Confronto com o texto da Seção 8", no fim deste documento):

- **Ambiguidade/lacuna**: o controle de aleatoriedade do modelo. A Figura 4
  cita *Guardrails & Model Controls* nesta camada, mas o texto não diz quais
  controles nem com que critério. Resolvido na v4 (subseção acima).
- **Adaptação necessária**: `LLMCore.generate` passou a aceitar opções por
  chamada (v4), para que a Camada 3 use uma temperatura por etapa.
- **Prescrito e não implementado**: a camada não gera planos, chamadas de
  ferramenta nem saídas estruturadas ("plans, tool calls, decision
  rationales"). O LLM só classifica a pergunta e sintetiza texto, e o fluxo
  é fixo na Camada 3.

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

### Revisão da Camada 5: ingestão por URL e consumo da Gold (2026-09-24)

Plano aprovado pelo usuário antes da implementação, com duas escolhas
explícitas: corpus de runtime = 3 normas de Open Finance (Pix fica só no
pipeline) e busca BM25 lexical (em vez de embeddings ou híbrido).

**Decisão**: o pipeline Bronze/Silver/Gold (`ingest_normativos.py`), até
aqui um artefato ilustrativo paralelo, passa a ser **a** fonte da Camada 5.
A `KnowledgeBase` lê somente a Gold; os `.md` curados manualmente saíram do
runtime (ficam no histórico do git, tag `v1.0-monografia`). Entrada única:
`data/normativos/fontes_url.json`, com a URL oficial da página de cada norma.

- **Bronze**: resposta JSON da página (endpoint que a própria página
  consome) e, quando a página lista versões consolidadas, o PDF "limpo" de
  maior versão (`_vN_L.pdf`), sem alteração.
- **Silver**: texto vigente, estruturado. Descarta texto tachado do HTML
  (redações revogadas), rodapés de página e artefatos de espaçamento do PDF;
  reconstrói parágrafos (HTML e PDF quebram linhas no meio da frase); separa
  as anotações de alteração ("(Redação dada pela…)") do texto, guardando-as
  como metadado; estrutura por artigo (com capítulo/seção como contexto) ou,
  em anexos sem artigos, por seção numerada; marca unidades revogadas;
  para ao encontrar a nota técnica/voto que a página publica após a norma.
- **Gold**: trechos de até 2.500 caracteres, cada um com cabeçalho de
  contexto no próprio texto ("Resolução Conjunta nº 1/2020 — CAPÍTULO III
  … — Seção II Da Participação no Open Finance — Art. 6º"), frequência de
  tokens pré-calculada, e `indice_bm25.json` com as estatísticas do corpus
  de runtime.
- **Busca**: BM25 (k1 = 1,5; b = 0,75) sobre a Gold, com tokenização
  compartilhada entre ingestão e consulta (`texto.py`): sem acento, sem
  stopwords, radical por remoção de sufixos (tabela curta inspirada no
  RSLP). A interface `buscar()` -> `Documento(titulo, ementa, url_oficial,
  trecho)` não mudou; Camadas 4, 7 e 8 intactas.

**Motivação**: (1) reprodutibilidade — qualquer pessoa regera o corpus a
partir de URLs públicas, e a Bronze versionada permite regerar Silver/Gold
offline (`--a-partir-da-bronze`); (2) atualidade — ver achado abaixo;
(3) qualidade do contexto entregue ao LLM — trechos menores, limpos e
rotulados com norma e artigo, em vez de artigos inteiros de até 8.000
caracteres com anotações de alteração misturadas ao texto.

**Ambiguidade/lacuna observada (achado)**: para normas anteriores a 2021,
o campo `Texto` da página do BCB é a **redação original**, não a vigente —
a Resolução Conjunta nº 1/2020 ainda diz "Open Banking" no HTML. O texto
consolidado só existe nos PDFs listados no campo `Documentos` da mesma
página. Consequência lateral: o corpus curado usado na v1 também estava
desatualizado (Resolução Conjunta nº 1 na v7, vigente v9; Circular nº 4.015
na v3, vigente v5). "Ingerir da página" exige, portanto, saber qual das
representações que a página oferece é a vigente — mais um exemplo de que
fontes governamentais não são machine-readable de forma uniforme (ver
lacuna original desta camada, acima).

**Adaptações necessárias**:
- `pypdf` volta a ser dependência (agora do pipeline, que também é quem
  gera a base de runtime).
- Reconhecimento de seções do anexo da IN BCB nº 759 (manual em HTML sem
  marcação semântica): o título vem colado ao conteúdo ou com o número em
  linha própria; células de tabela como "3. NIF" ou "90. Formato numérico"
  imitam seções. Resolvido com regra de sequência plausível (a seção só é
  aceita se o número de topo é o atual ou o seguinte) e com seções que são
  só título virando contexto das subseções.
- Ajustes da busca derivados de um teste de recuperação com 8 perguntas
  (resultado detalhado em `docs/evidencias_empiricas.md`, 2026-09-24):
  radical em vez de só plural ("participar"/"participação"/"participantes"
  -> `particip`), e verbos que só emolduram a pergunta ("funciona",
  "existe", "significa"…) como stopwords. Cabeçalho de contexto mantido no
  índice: testado sem ele, a recuperação piorou.

### v4.1: limpeza do texto extraído de PDF (2026-10-01)

Plano apresentado e aprovado pelo usuário antes do código. É a única
mudança em relação à v4.

**Decisão**: nova etapa `_limpar_artefatos_pdf`, aplicada só ao texto que
vem do PDF consolidado (Resolução Conjunta nº 1/2020 e Circular nº
4.015/2020). As normas lidas do HTML não passam por ela. Duas regras:

1. **Espaço antes do hífen**: "palavra -palavra" vira "palavra-palavra".
   Corrigiu 14 casos: pronomes enclíticos ("Excetuam -se", "considera -se"),
   "pré -paga" e identificadores de artigo ("Art. 13 -A", "22 -A" a "22 -E",
   "6º -A"). O inciso com travessão ("I - no caso") não é afetado, porque
   tem espaço depois do hífen.
2. **Palavra partida**: "X Y" vira "XY" quando "XY" aparece em outro ponto
   do mesmo documento e uma das partes é rara nele (até 2 ocorrências). O
   próprio texto da norma serve de dicionário, sem dependência nova.
   Corrigiu 7 casos ("implem entação", "dete ntora", "res ponsabilidade",
   "p reviamente", "de vem", "Ce ntral").

**Motivação**: os artefatos tinham dois efeitos. Na Camada 5, "implem" e
"entação" não casam com "implementação" na busca BM25. Na Camada 7, a
citação correta "art. 22-A" gerava aviso de artigo não verificado, porque o
contexto trazia "22 -A". O defeito estava na ingestão, e a governança
acusava o modelo por ele.

**Alternativa descartada**: o modo `layout` do pypdf resolve mais palavras
partidas, mas altera a estrutura de linhas usada na reconstrução de
parágrafos e não resolve "implem entação".

**Resíduo conhecido**: "refere m" e "especializ ada" continuam na Silver,
porque a forma inteira não aparece em outro ponto do documento. Mantidos
de propósito: uma regra para um caso único não generaliza.

**Também verificado**: o salto do inciso II para o IV no art. 6º da
Resolução Conjunta nº 1/2020 é correto. O inciso III foi revogado pela
Resolução Conjunta nº 15/2025, e a anotação de revogação é removida do
texto pela Silver.

**Testes**: `tests/test_ingestao.py` (8 testes). Cobrem as duas regras, o
inciso com travessão, palavras frequentes que não devem ser juntadas, o
resíduo conhecido, a ausência dos artefatos na Gold e a citação "art. 22-A"
sem aviso, com o trecho real da Gold. Resultados em
`docs/evidencias_empiricas.md`, v4.1.

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

### Camada 7 v2 — revisão da governança (2026-09-24)

Plano apresentado e aprovado pelo usuário antes do código (escopo completo,
itens A a H), com a justificativa de que a governança é o "coração" de uma
aplicação LLM-Native. Motivada por uma revisão do validador contra as 40
respostas normativas dos benchmarks v1 e v2, que achou 8 problemas; os
principais:

1. a regex de norma não reconhecia "Instrução Normativa **BCB** nº" — 13
   menções à IN 759 nas respostas, nenhuma verificada;
2. nomear uma norma para dizer que ela está ausente contava como citação —
   9 de 10 avisos da v2 no cenário "norma ausente" eram recusas honestas;
3. valores numéricos não eram verificados — e distorção de número é o erro
   mais recorrente do projeto (2026-08-14; "cinco milhões" -> "3 milhões"
   em 2026-09-24);
4. o artigo não era conferido contra a norma a que a resposta o atribui;
5. com a busca vazia, o LLM respondia sem base;
6. "sempre linkar fonte" e "só fontes públicas" não estavam garantidos em
   código.

**Decisão**: a governança passa a atuar em três momentos, todos
determinísticos e no mesmo módulo (`governance.py`):

- **Antes da geração**: `POLITICA_SINTESE` — as regras de síntese (só o
  contexto; declarar norma ausente; citar norma e artigo do cabeçalho;
  copiar valores sem converter; dizer quando o contexto não basta; sem
  parecer) passam a ser definidas pela Camada 7 e só injetadas pela
  Camada 3. `recusar_sem_base` fecha a rota "busca vazia -> LLM responde de
  memória", do mesmo jeito que parecer e fora de escopo.
- **Depois da geração**: `validar_resposta` devolve um `ResultadoValidacao`
  com categorias separadas:
  - *norma não verificada* vs. *ausência declarada*: a resposta é dividida
    em frases (sem quebrar em "Art. 6º"); uma menção numa frase com
    marcador de ausência ("não encontrei", "não consta", "não está no
    contexto"…) é ausência declarada, sem aviso — a menos que a mesma norma
    apareça como fonte em outra frase;
  - *artigo não verificado* e *artigo fora da norma*: cada artigo é
    associado à norma mais próxima na mesma frase e conferido contra os
    pares (norma, artigo) atestados no contexto — o cabeçalho de cada trecho
    da Gold diz a que norma ele pertence, e remissões explícitas no texto
    ("art. 44 … da Resolução Conjunta nº 1") também atestam o par;
  - *valor não verificado*: quantidades com unidade (dias, meses, anos,
    horas, %, R$) ou multiplicador (mil, milhões), em dígitos ou por extenso
    ("cinco milhões" = "5 milhões"), precisam aparecer no contexto;
  - normas reconhecidas: Lei, Lei Complementar, Decreto, Resolução
    (Conjunta, BCB, CMN, CNSP), Circular (e Circular Susep), Instrução
    Normativa BCB; comparação sem acento, sem caixa e sem ponto de milhar.
  O texto final recebe os avisos, as **fontes consultadas (título e URL)
  extraídas do contexto** — "sempre linkar fonte" deixa de depender do LLM
  — e o aviso de validação humana (que também deixou de ser pedido ao
  modelo).
- **Na ingestão**: `validar_fonte_publica` — a Camada 5 só baixa URL HTTPS
  de `www.bcb.gov.br`, `bcb.gov.br` ou `normativos.bcb.gov.br`.

**Rastreabilidade e comparabilidade**: a Camada 8 registra o `desfecho`
(resposta ou qual recusa) e as categorias da validação. A métrica antiga
(`aviso_citacao_nao_verificada`) continua sendo calculada pelo validador da
v1/v2, preservado sem mudança (`_aviso_legado`), para que v1, v2 e v3 sejam
comparáveis com a mesma régua. O benchmark guarda a resposta do LLM e o
contexto de cada execução, e `run_benchmark.py --revalidar` reaplica a
Camada 7 atual a esse dado sem nova geração — uma mudança futura na
governança pode ser medida isoladamente.

**Testes**: `tests/test_governanca.py` (20 testes, `unittest`, sem LLM),
com casos reais — a invenção da Resolução BCB nº 32 na v1 deve gerar aviso;
"Não encontrei a Resolução BCB nº 32/2020" na v2 não deve; "3 milhões"
contra "cinco milhões" deve; IN BCB com número inventado deve. Revalidadas
as 20 respostas normativas da v2 com o contexto reconstruído: 0 falsos
positivos de norma e de artigo; os avisos de valor apontaram exatamente as
distorções achadas na leitura manual ("3 milhões" ×5, "100 mil") e um
valor correto ("5 milhões") que não estava nos trechos consultados — aviso
correto pela regra, porque o modelo o trouxe de fora do contexto.

**Ambiguidade da arquitetura**: Maia et al. descrevem a governança como
camada, mas, na prática, ela precisou atuar em três pontos do fluxo
(ingestão, prompt, pós-geração) e em três outras camadas (5, 3 e 8). Uma
"camada" de governança aqui é um conjunto de políticas com pontos de
aplicação distribuídos, não uma etapa do pipeline.

**Ajustes pós-benchmark (v3.1)**: (1) a detecção de ausência deixou de ser
uma lista fechada de expressões e passou a ser "negação + termo de
disponibilidade" (encontrar, disponível, menção, contexto, informação…),
depois de falsos positivos achados na leitura das respostas v3 e v3.1;
(2) a regra 3 da política deixou de pedir a citação "como aparece no
cabeçalho entre colchetes" — o modelo passou a copiar cabeçalhos para
artigos fora do contexto — e pede a citação entre parênteses, sem copiar os
colchetes nem mencionar artigo fora do contexto. Ver
`docs/evidencias_empiricas.md`, entradas v3 e v3.1.

**Limites declarados**: verificação lexical — não detecta afirmação falsa
que não cite norma, artigo ou valor; não verifica o histórico da conversa;
a detecção de ausência é heurística (negar algo *sobre o conteúdo* de uma
norma, "a norma X não exige Y", é tratado como citação, mas frases
ambíguas podem ser classificadas errado). Um verificador semântico
(ex.: LLM-juiz) cobriria parte disso, ao custo do determinismo — registrado
como trabalho futuro.

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

### Adendo (2026-10-01): campos atuais do registro

A decisão acima descreve o registro da v1. Campos acrescentados depois,
registrados em outras seções:

- `desfecho` (`resposta`, `recusa_parecer_juridico`,
  `recusa_fora_de_escopo`, `recusa_sem_base`) e `validacao` (categorias do
  `ResultadoValidacao`: norma não verificada, ausência declarada, artigo não
  verificado, artigo fora da norma, valor não verificado). Origem: Camada 7
  v2. O campo `aviso_citacao_nao_verificada` foi mantido com a régua da
  v1/v2, para comparação entre versões.
- `parametros_llm` (modelo, ID do modelo, temperaturas de classificação e
  de síntese, seed). Origem: v4, ver Camada 2.
- O registro passou a ser gravado em todos os desfechos de `responder()`:
  as três recusas e a resposta normal.

Em relação ao texto da Seção 8 (ver "Confronto com o texto da Seção 8"), o
log de runtime **não registra** o prompt, os trechos recuperados (guardados
só pelo benchmark, em `docs/resultados/`), os acessos à memória nem a
versão do índice. Também não há monitoramento, alertas ou *feedback*. A
ambiguidade registrada acima ("não distingue proveniência de telemetria")
foi reclassificada naquela entrada como implementação parcial.

---

## Benchmark Empírico (avaliação end-to-end, Camadas 1-8)

**Decisão**: com as 8 camadas já ligadas ponta a ponta e os 4 casos
qualitativos de `tests/casos_teste.md` documentados, foi construído um
segundo artefato de avaliação, quantitativo: `tests/casos_teste.json`
(4 cenários — Caminho Feliz/RAG BACEN, Norma Ausente/Fronteira, Solicitação
de Parecer/Governança, Fora de Escopo/Governança) e `run_benchmark.py`, que
instancia um `Orchestrator` novo por execução (sessão sem histórico, para
isolar o comportamento por pergunta) e roda cada cenário 5 vezes contra o
Ollama local, medindo latência (`time.perf_counter`) e lendo
`orchestrator.ultimo_registro` (Camada 8) para capturar, por execução: se a
classificação da Camada 3 desviou para uma recusa da Camada 7
(`tipo_classificacao in {"parecer_juridico", "fora_de_escopo"}`) e se a
Camada 7 sinalizou aviso de citação não verificada. Saída bruta em
`logs/resultados_benchmark.json` (20 registros) e uma tabela agregada por
cenário (via `pandas.DataFrame.groupby`, contagem, médias, mediana, desvio
padrão) em `docs/tabela_resultados_empiricos.csv`.

**Motivação**: os 4 casos de `tests/casos_teste.md` são evidência
qualitativa (uma execução cada, com leitura detalhada da resposta). Para a
análise de viabilidade (Capítulo 1, Seção 5, item e) também é útil ter
evidência quantitativa — latência por tipo de fluxo e taxa de recorrência
dos comportamentos já observados (aviso de citação não verificada) — que
uma única execução por caso não demonstra, já que a saída do LLM varia entre
chamadas.

**Ambiguidade/lacuna observada**: a arquitetura de Maia et al. (2026) não
define nenhum processo de avaliação/benchmark para uma aplicação LLM-Native
construída sobre ela — não há orientação sobre quais métricas capturar por
camada nem sobre como o "produtor" das camadas (aqui, Camada 8) deveria
alimentar um processo de avaliação externo à aplicação. A decisão de reusar
`orchestrator.ultimo_registro` (já exposto para a Camada 1, ver entrada
acima) como fonte de dados do benchmark, em vez de ler `logs/interacoes.jsonl`
do disco, foi de implementação: evita reabrir/parsear o log a cada execução
e mantém o benchmark acoplado à mesma interface pública já usada pela CLI.

**Adaptação necessária**: `pandas` foi adicionado como dependência
(`requirements.txt`) — a única biblioteca de terceiros do projeto que não é
`ollama`/`python-dotenv`. Decisão: aceitável porque não é uma abstração de
orquestração de LLM (o non-negotiable é não usar CrewAI/LangGraph/etc. para
esconder decisões de camada) — é uma ferramenta de análise de dados
tabulares, usada só no script de benchmark, fora do runtime do protótipo
(`main.py`/`Orchestrator` não dependem dela).

**Resultado da primeira execução** (2026-09-22, 20 execuções, `llama3.1` via
Ollama): ver `docs/evidencias_empiricas.md` para a análise dos números.

**Extensão (2026-09-23) — diagrama de arquitetura e gráficos de
publicação**: `docs/diagrama_arquitetura.md` (diagrama Mermaid, gerado por
inspeção direta de `src/layerN_*/` — não é uma versão idealizada, os nomes
de classe/função citados existem literalmente no código) e
`scripts/plot_benchmark.py` (lê `docs/tabela_resultados_empiricos.csv`,
gera `docs/figuras/grafico_latencia_cenarios.png` e
`grafico_taxas_governanca.png` via `matplotlib`/`seaborn`, 300 DPI). Mesma
justificativa da adição de `pandas`: ferramentas de análise/visualização de
dados, usadas só nesses dois scripts auxiliares, não fazem parte do runtime
do protótipo (`main.py`) nem escondem decisões de camada — adicionadas a
`requirements.txt`.

**Ambiguidade encontrada e resolvida durante o diagrama**: a primeira versão
do pedido de diagrama descrevia a Camada 5 como "RAG com base do BACEN em
Medalhão" (arquitetura de dados em camadas Bronze/Silver/Gold). Ao inspecionar
`src/layer5_knowledge/knowledge_base.py` para construir o diagrama, confirmei
que a implementação real é busca lexical simples sobre arquivos Markdown
(ver decisão da Camada 5 acima) — não há nenhuma camada Bronze/Silver/Gold no
código. O diagrama foi construído refletindo o código real, com uma nota
explícita sobre essa discrepância, em vez de desenhar uma arquitetura
"medalhão" que não existe — mesmo princípio de rastreabilidade
código-documentação que motiva todo este registro de decisões.

**Pedido subsequente (2026-09-23) — pipeline de ingestão Bronze/Silver/Gold,
mantido paralelo ao runtime**: em uma sessão seguinte, foi pedida a
implementação de fato do pipeline medalhão para a Camada 5 (`1_bronze_raw/`,
`2_silver_cleaned/`, `3_gold_indexed/` dentro de `data/normativos/`, mais
`src/layer5_knowledge/ingest_normativos.py`), incluindo reescrever
`knowledge_base.py` para consumir o índice Gold. Como essa mudança
reorganizaria o corpus já curado (proveniência verificada manualmente, ver
Camada 5) e alteraria uma camada já validada — citada nos 4 casos de teste,
no benchmark de 20 execuções e no Apêndice A (`docs/apendice_casos_teste.md`)
— o risco de invalidar evidência empírica já coletada foi levantado ao
usuário antes de implementar. **Decisão do usuário**: manter
`knowledge_base.py` e o corpus (`data/normativos/*.md`) intocados; o
pipeline Bronze/Silver/Gold foi implementado como um artefato **paralelo e
ilustrativo** — `ingest_normativos.py` só lê os `.md` já curados (nunca
escreve neles) e gera as 3 camadas em subpastas novas de
`data/normativos/`, que `KnowledgeBase._carregar` não enxerga (usa
`Path.glob("*.md")`, não recursivo). Nenhum dos dois caminhos de execução
suportados (`python -m src.layer5_knowledge.ingest_normativos` e
`python src/layer5_knowledge/ingest_normativos.py`) depende do Ollama nem
de outras camadas — script autocontido (`json`, `re`, `pathlib`,
`dataclasses`, stdlib).

**Ambiguidade/lacuna observada**: a camada "Bronze" deste pipeline não
representa o PDF oficial original — a extração de PDF (`pypdf`) foi um
passo manual único, fora do runtime, já documentado na decisão da Camada 5
acima. "Bronze" aqui significa apenas "como o arquivo chegou a este
pipeline" (cópia verbatim do `.md` já curado), documentado explicitamente na
docstring do módulo para não passar a falsa impressão de que há
rastreabilidade adicional até o PDF original além da já existente
(`url_oficial` no frontmatter).

**Registrado como evidência de pesquisa**: este episódio (pedido de mudança
estrutural em uma camada já validada, checado contra o código real antes de
executar, decisão explícita do usuário por manter o runtime estável) é, em
si, um dado relevante para a discussão de viabilidade — mostra o
`docs/decisoes_arquitetura.md` funcionando como pretendido: checkpoint que
evita uma mudança de arquitetura não intencional em cima de evidência
empírica já coletada.

**Extensão (2026-09-23) — teste do pipeline com PDF bruto real**: o usuário
anexou 2 PDFs reais (`normativoOpenFinance.pdf` = Instrução Normativa BCB nº
759/2026; `normativoPix.pdf` = Resolução BCB nº 1/2020, arranjo Pix) para
testar `ingest_normativos.py` contra entrada não processada, não apenas
contra os `.md` já curados. Dois pontos resolvidos com o usuário antes de
implementar:

1. **Escopo**: a Resolução do Pix está fora do escopo declarado do projeto
   ("Open Finance / contas PJ"). Usuário optou por incluir mesmo assim, mas
   **só no pipeline ilustrativo** — não é uma decisão de expandir o escopo
   do corpus real (`data/normativos/*.md`), que continua com os mesmos 2
   normativos de antes.
2. **Verificação de fonte**: diferente do corpus curado (URL oficial
   confirmada manualmente), um PDF local não carrega uma URL oficial
   verificável. `_heuristica_metadados()` extrai título/ementa/data por
   regex sobre a primeira página (best-effort, não NLP), mas sempre grava
   `url_oficial: ""` e `fonte_confirmada: "false"` no frontmatter Bronze —
   nunca apresenta um dado inferido como se fosse curado. Mesmo princípio
   de `data/normativos/PENDENTES.md`, aplicado agora a um pipeline
   automatizado em vez de a um documento manual.

Os PDFs foram colocados em `data/normativos/*.pdf` (não em `docs/`, onde o
usuário os anexou inicialmente) porque o `.gitignore` já ignorava esse
padrão desde a extração manual original da Camada 5 — convenção
pré-existente, não inventada para este teste.

**Achado técnico durante o teste**: a extração via `pypdf` do
`normativoPix.pdf` corrompeu especificamente a ligadura tipográfica "ti"
(ex: "Institui" -> "Ins�tui", "instituições" -> "ins�tuições") para
`�` (caractere de substituição Unicode) em quase todas as ocorrências,
enquanto outras ligaduras do mesmo PDF (ex: "fi" em "financeiras" ->
"ﬁnanceiras") foram decodificadas corretamente. Diferente do artefato de
espaçamento já documentado para o corpus curado ("Art. 3 1." em vez de
"Art. 31."), esta é uma classe de erro de extração distinta — perda
seletiva de caracteres, não apenas espaçamento — específica ao mapeamento
de fonte daquele PDF. Não corrigido (fora do escopo de um pipeline
ilustrativo), mas reforça empiricamente por que o corpus real exige revisão
manual antes da inclusão: um pipeline de extração 100% automatizado, mesmo
bem estruturado (Bronze/Silver/Gold), ainda produziria erros de conteúdo
silenciosos se fosse a única linha de defesa.

### Benchmark v5 — bateria ampliada (2026-10-02)

**Decisão**: a bateria de `tests/casos_teste.json` passou de 4 cenários para
**66 casos em cinco grupos** — `normativo_corpus` (39: 28 da Resolução
Conjunta nº 1/2020, 6 da Circular nº 4.015/2020, 5 da IN BCB nº 759/2026,
incluindo o caminho feliz original), `norma_ausente` (6), `parecer_juridico`
(7), `fora_de_escopo` (7) e `robustez` (7: premissa falsa, linguagem
informal, pergunta em inglês, injeção de instrução e pergunta sobre duas
normas). Os 4 primeiros casos são os cenários v1–v4.1, com os mesmos ids e
perguntas. Cada caso declara:

- `comportamento_esperado`: `resposta_fundamentada` (desfecho "resposta" sem
  aviso da Camada 7), `ausencia_declarada` (ausência declarada ou recusa,
  sem aviso), `recusa` ou `sem_alucinacao` (qualquer desfecho sem aviso). A
  execução tem **sucesso** quando a classificação está entre as aceitas e o
  comportamento foi observado;
- `tipos_aceitos` (opcional), para fronteiras em que mais de uma
  classificação é defensável (ex.: norma ausente fora de Open Finance, como
  a Circular nº 3.978/2020 de PLD, aceita `fora_de_escopo`);
- `relevantes`: rótulo de recuperação (norma + identificador do trecho na
  Gold) para os 44 casos normativos e de robustez com resposta esperada no
  corpus;
- `termos_esperados`: grupos de termos que a resposta deve conter (ex.:
  "cinco anos" para o art. 49).

`run_benchmark.py` passou a medir, além das colunas da Camada 7: taxa de
sucesso; **Acerto@3, Recall@3 e MRR** da Camada 5, sobre os mesmos 3 trechos
que a Camada 4 entrega à síntese (calculados com uma instância própria de
`KnowledgeBase`, também em modo isolado, `--somente-recuperacao`, sem LLM);
cobertura de termos esperados; matriz de confusão da Camada 3; e, por grupo,
**IC 95% de Wilson**. Repetições: 3 por caso (198 execuções por modo), nos
modos produção e sensibilidade. Rodadas parciais (`--grupo`, `--casos`)
gravam em `logs/benchmark_parcial/`, para não sobrescrever os artefatos
versionados. Testes das métricas e da integridade da bateria (rótulos
existentes na Gold, ids únicos, campos válidos) em `tests/test_benchmark.py`.
Resultados da v4.1 arquivados em `docs/resultados/v4.1/`.

**Motivação**: com 4 cenários, cada comportamento tinha uma única pergunta
como evidência; uma taxa de 100% em 5 repetições quase idênticas (produção,
temperatura 0,1, seed 42) dizia mais sobre a reprodutibilidade de um prompt
do que sobre o comportamento do sistema. A bateria ampliada mede a variação
**entre perguntas**, que é a que importa para a viabilidade. Também cumpre
o que a Seção 8 prescreve para a Camada 5 ("retrieval (...) as a runtime
subsystem with its own observability and evaluation requirements", p. 16) e
o passo aprovado em 2026-09-24 (conjunto rotulado com Recall@3/MRR antes de
qualquer busca híbrida).

**Decisões de método**:

1. **Rótulos fixados antes de olhar a recuperação.** Os `relevantes` e
   `termos_esperados` foram escritos a partir do texto da Gold, e só depois
   a recuperação foi rodada. Os casos em que o BM25 erra não foram
   reescritos nem relabelados: o objetivo é medir a Camada 5, não ajustar a
   bateria a ela.
2. **IC sobre casos, não sobre execuções.** No modo produção as repetições
   são quase idênticas; tratá-las como independentes estreitaria o
   intervalo artificialmente. O IC de Wilson usa o caso como unidade (um
   caso conta como sucesso se acertou em todas as repetições). A taxa por
   execução é publicada ao lado, sem IC.
3. **3 repetições, não 5.** Escolha aprovada pelo usuário: com 66 casos, 3
   repetições bastam para separar o efeito da primeira execução (observado
   desde a v4) do comportamento estável, e mantêm cada modo em cerca de 1 h.
4. **A cobertura de termos é aproximação.** Mede presença lexical de termos
   do dispositivo, não correção jurídica (mesma limitação da Camada 7). É
   publicada como indicador, não entra no critério de sucesso.
5. **Critério de ausência corrigido no teste de fumaça, antes da rodada.** No
   caso da Resolução BCB nº 1/2020 (Pix, fora do runtime), o modelo declarou
   corretamente a ausência, mas a categoria `ausencia_declarada` da Camada 7
   não foi marcada: ela só é calculada para normas que não aparecem no
   contexto, e a IN BCB 759/2026 (seção 6.2) menciona a Resolução BCB nº
   1/2020. O critério do benchmark passou a aceitar também a ausência
   declarada detectada pelo mesmo detector de frases da Camada 7 sobre a
   resposta inteira (`declara_ausencia_de_norma`). A Camada 7 não mudou: a
   resposta não tinha aviso, só a métrica a contava errado.
6. **Auditoria manual como artefato, depois da rodada.** A leitura das
   respostas mostrou que o sucesso automático (sem aviso) inclui abstenções
   e erros de interpretação. Em vez de mudar o critério depois de ver os
   resultados, a correção foi medida à parte: `scripts/auditoria_v5.py`
   guarda um veredito por resposta distinta (correta, parcial, abstenção,
   incorreta, recusa pelo modelo), com nota, e gera
   `docs/auditoria_respostas_v5.csv`. Vereditos feitos pelo assistente,
   sujeitos à revisão do autor. Resultados em `evidencias_empiricas.md`
   (2026-10-02).

**Ambiguidade encontrada na arquitetura original**: a Seção 8 pede avaliação
da recuperação e a Figura 4 lista "Evaluation & Quality Metrics" na
observabilidade, mas não diz se a avaliação é de cada camada isolada (a
recuperação, a classificação) ou do sistema ponta a ponta, nem qual é a
unidade de análise. O benchmark v5 faz as duas coisas e separa as métricas
por camada: Camada 3 (matriz de confusão), Camada 5 (Acerto@3/Recall@3/MRR),
Camada 7 (avisos) e sistema (sucesso por caso).

**Adaptação**: nenhuma no runtime. A bateria e as métricas são artefatos de
avaliação; nenhuma camada foi alterada.

---

### v6 — experimentos sobre a linha de base v5 (2026-10-02)

**Decisão**: o benchmark v5 (66 casos × 3 repetições, produção e
sensibilidade) e a auditoria manual são a **linha de base** da monografia e
não são alterados. Toda rodada nova grava numa pasta própria
(`run_benchmark.py --saida <pasta>`): JSON bruto, CSVs no formato do v5 e a
tabela de recuperação. Sem `--saida`, o script continua gravando nos
caminhos do v5 (teste `TestCaminhosSaida`). Pastas: `docs/resultados/v6/`
(Tarefa A, limiar BM25), `docs/resultados/ablacao_c1/` e
`docs/resultados/ablacao_c2/` (Tarefa C, ablação da Camada 7).

**Protocolo das rodadas**: o mesmo ambiente do v5 (Ollama 0.33.2,
`llama3.1` ID `46e0c10c039e`, contexto de 4.096 tokens, seed 42, modo
produção, 3 repetições seguidas por caso). O servidor Ollama é reiniciado
antes de cada rodada completa, e a data e a hora ficam registradas. Motivo:
o texto gerado depende do estado do cache de prompts do servidor
(`diagnostico_falhas_v5.md`, Seção 3). Por isso a comparação com o v5 é
feita sobre métricas, não sobre a identidade dos textos.

---

## Reprodutibilidade (preparação para publicação no GitHub, 2026-09-24)

Ajustes feitos para que um terceiro (orientadora, banca, leitor da
monografia) reproduza os experimentos a partir de um clone do repositório,
sem arquivos locais do autor.

**1. Parâmetros de amostragem da Camada 2 passam a ser configuráveis.**
`LLMCore` ganhou o argumento opcional `options`, repassado sem alteração a
`ollama.chat`. Padrão `None` = comportamento anterior (parâmetros default do
modelo), então `main.py` e os resultados já publicados não mudam. Todas as
chamadas ao LLM passam por `LLMCore.generate` (classificação em
`_interpretar` e síntese em `_sintetizar_resposta`), então a opção cobre o
fluxo inteiro.

**2. Benchmark em dois modos** (`run_benchmark.py --modo`):
- `livre` (padrão): mede o protótipo como um usuário o usaria — são os
  resultados de 2026-09-22 (`docs/tabela_resultados_empiricos.csv`).
- `deterministico`: `temperature=0`, `seed=42`. Não substitui o modo livre
  (temperatura zero não é como o protótipo roda em uso real); serve para
  separar quanto da variação observada vem da amostragem do LLM e para dar
  a terceiros um alvo de reprodução exata.
- Nova coluna `n_respostas_distintas` na tabela agregada (respostas
  textualmente diferentes nas N repetições), que torna essa comparação
  direta. Resultados em `docs/evidencias_empiricas.md`, 2026-09-24.
- **Ambiguidade/limite**: `seed` + `temperature=0` garantem saída idêntica
  apenas no mesmo ambiente (mesma versão do Ollama, mesmo digest do modelo,
  mesmo hardware/backend CPU vs. GPU). Em outra máquina, espera-se
  reprodução das *taxas* (classificação, recusa), não necessariamente do
  texto exato. Por isso o ambiente de referência é registrado no README.

**3. Dado bruto versionado.** `logs/` continua ignorado pelo git (contém
`interacoes.jsonl`, log de uso local). O JSON bruto do benchmark foi movido
para `docs/resultados/`, versionado, e `run_benchmark.py --somente-tabela`
regera a tabela agregada a partir dele sem chamar o LLM — a orientadora pode
conferir a agregação sem Ollama instalado.

> **Atualização (mesmo dia)**: o item 4 abaixo foi superado pela "Revisão da
> Camada 5: ingestão por URL e consumo da Gold" (seção Camada 5): o pipeline
> deixou de ser ilustrativo e passou a alimentar o runtime, e as normas
> curadas também passaram a ser ingeridas por URL.

**4. Pipeline ilustrativo de ingestão passa a usar URL oficial em vez de
PDF local.** A versão anterior de `ingest_normativos.py` lia PDFs baixados
manualmente para `data/normativos/*.pdf`, padrão ignorado pelo git — quem
clonasse o repositório não conseguiria rodar a ingestão. Agora a entrada é
`data/normativos/fontes_url.json`, com as URLs oficiais da Resolução BCB nº
1/2020 (Pix) e da Instrução Normativa BCB nº 759/2026 (Manual de Escopo do
Open Finance) informadas pelo autor. A página `exibenormativo` do BCB é
renderizada via JavaScript; o texto integral e os metadados vêm do endpoint
JSON que a própria página consome (`/api/conteudo/app/normativos/
exibenormativo?p1=<tipo>&p2=<numero>`). Só biblioteca padrão (`urllib`,
`html.parser`) — `pypdf` saiu das dependências.

Consequências:
- Metadados deixam de ser heurística sobre a primeira página do PDF e passam
  a vir de campos oficiais da API (título, assunto, data, versão), por isso
  esses registros saem com `fonte_confirmada: true`.
- O defeito de extração registrado acima (ligadura "ti" virando `�` no
  `pypdf`) desaparece: o texto HTML não tem essa camada de mapeamento de
  fonte. Verificado: zero caracteres de substituição nos dois normativos.
- Nova limitação: a API devolve sempre a **versão vigente** (ex.: Resolução
  BCB nº 1 estava na versão 41 em 2026-09-24). O JSON bruto salvo no Bronze
  (`obtido_em`, `VersaoNormativo`) registra qual versão foi usada; rodar a
  ingestão no futuro pode gerar texto diferente se o BCB alterar a norma.
- O texto consolidado do BCB mantém redações anteriores junto das vigentes,
  então a estrutura Silver tem identificadores de artigo repetidos (ex.:
  "Art. 3º" duas vezes na Resolução BCB nº 1). Não tratado — o pipeline é
  ilustrativo e continua fora do runtime (`KnowledgeBase` segue lendo só
  `data/normativos/*.md`).
- Os artefatos antigos `normativoPix*`/`normativoOpenFinance*` em
  `1_bronze_raw/`, `2_silver_cleaned/` e `3_gold_indexed/` foram
  substituídos por `resolucao_bcb_1_2020*` e `instrucao_normativa_bcb_759_2026*`.
  O arquivo avulso `_openfinance_limpo.md` (texto da IN 759 limpo
  manualmente, sem referência no código) saiu do repositório: seu papel é
  cumprido pela camada Silver.

**5. Versões fixadas.** `requirements.txt` mantém os mínimos (`>=`);
`requirements-lock.txt` (saída de `pip freeze`) fixa as versões exatas do
ambiente de referência. Python, Ollama e digest do modelo ficam registrados
no README, seção "Ambiente de referência".

---

## Confronto com o texto da Seção 8 (2026-10-01)

**Contexto**: até aqui, as entradas deste diário registravam a prescrição
de Maia et al. por paráfrase de uma linha ("Maia et al. atribuem à Camada X
…"). Na consolidação da evidência de independência
(`docs/validacao_independencia.md`), cada ambiguidade registrada foi
confrontada com o texto da Seção 8 (8.1 a 8.3, pp. 15–17) e com a Figura 4.
O confronto mostrou que parte das "ambiguidades" eram prescrições do artigo
que a paráfrase havia perdido.

**Esta entrada não reescreve as anteriores.** Elas continuam como registro
do que se sabia em cada data. Aqui, cada ponto é reclassificado em uma de
três categorias, e o que foi confirmado é registrado à parte.

**Ambiguidade genuína encontrada no confronto: numeração das camadas.** O
texto da 8.1 apresenta as camadas sem número, na ordem Interação, LLM Core,
Orquestração, Ferramentas e Serviços, Conhecimento, Contexto e Memória,
Governança, Observabilidade. A Figura 4 numera 4 = Knowledge Integration,
5 = Context & Memory e 6 = Tool & Service Integration. O protótipo segue a
ordem do texto (`layer4_tools`, `layer5_knowledge`, `layer6_memory`).
Decisão: manter a numeração do texto e citar a divergência na monografia.

### 1. Ambiguidades genuínas (resistem ao texto)

| Camada | Ambiguidade | Por que resiste |
|---|---|---|
| 1 | Expor ou não, na interface, artefatos de outras camadas (a proveniência). | O texto trata a interface como fonte de sinais de intenção, mas não fala do que ela devolve ao usuário. |
| 2 | Controle de aleatoriedade (temperatura e seed). | A Figura 4 cita *Model Controls*; o texto não diz quais controles nem com que critério. |
| 3 | Comportamento durante a construção incremental, com camadas ainda ausentes. | O texto descreve o sistema completo. A forma de implementação é dada como lista de opções (motor de *workflow*, máquina de estados, *planner-executor*, multiagente). |
| 5 | Qual representação da fonte é a vigente: o HTML da página do BCB traz a redação original de normas anteriores a 2021, e o texto vigente só existe no PDF consolidado. | O texto pressupõe fontes prontas para ingestão. |
| 6 | Tamanho da janela, formato de injeção e critério de seleção. | "Relevance filtering" é citado sem critério. |
| 7 | O que validar e como: citação de norma, artigo e valor, ausência declarada. Alcance da validação diante da memória. | "Output validation" é prescrita sem conteúdo. |
| 8 | Formato e granularidade do registro. | O texto lista o que registrar, não como. |

### 2. Desvios (decisão diferente do que o texto prescreve)

Nenhum desses desvios foi tomado com o texto completo à vista. Os
desvios com motivação registrada que continua válida estão marcados como
**justificados**; os demais, como **não intencionais**.

| Camada | O texto prescreve | O protótipo fez | Tipo |
|---|---|---|---|
| 4 | "Typed and auditable interfaces"; a Prática 1 pede ferramentas como subsistemas com interface explícita. | `buscar_normativo` devolve `str` pronta para o prompt. | Não intencional. A motivação registrada (um único caso de uso, sem abstração prematura) não trata da tipagem. |
| 5 | Pipeline com *embeddings*, busca híbrida e *reranking*. | BM25 lexical. | Justificado: auditabilidade e decisão explícita de não esconder a recuperação (Camada 5, v1 e v2). |
| 6 | A memória "actively shapes orchestration and reasoning". | O histórico só entra na síntese. | Não intencional. A entrada da Camada 6 trata o ponto como lacuna da arquitetura. |
| 6 | A memória de longo prazo faz parte da camada. | Só memória de processo, sem persistência. | Justificado como corte de escopo (sem caso de uso), mas registrado antes como lacuna, e não como corte. |

### 3. Componentes prescritos e não implementados

| Camada | Não implementado |
|---|---|
| 1 | Sinais estruturados de intenção, restrições e *feedback*; *dashboards*, voz e APIs. |
| 2 | Planos, chamadas de ferramenta, saídas estruturadas e justificativas de decisão: o LLM só classifica e sintetiza texto. |
| 3 | Planejamento, delegação, *retries*, *checkpointing* e tratamento de falha parcial (não há `try`/`except` no fluxo). |
| 4 | APIs externas, *sandboxes* de código, bancos de dados, tratamento de erro e *fallback* de ferramenta. |
| 5 | Avaliação da recuperação como subsistema (planejada: conjunto rotulado com Recall@3/MRR) e observabilidade própria da recuperação. |
| 6 | Resultados intermediários de ferramentas e rastros de execução no contexto; memória de longo prazo. |
| 7 | Checagem de permissão, aprovação humana ativa (há só o aviso fixo), checagem de viés, regras de privacidade e controle de acesso. |
| 8 | Prompt, trechos recuperados (guardados só pelo benchmark), acessos à memória e versão do índice no log de runtime; monitoramento, alertas, métricas de qualidade em operação e *feedback loops*. |

### 4. Confirmações da arquitetura

- **Governança transversal (Camada 7).** O que a entrada "Camada 7 v2"
  registrou como ambiguidade (a governança atuar em ingestão, prompt e
  pós-geração, dentro de outras camadas) é o que a Figura 4 prescreve: a
  governança marcada como *cross-cutting*.
- **Prática 3.** "Cannot rely on prompt-level constraints alone": o
  protótipo combina política no prompt com validadores em código. O dado
  empírico da v3 acrescenta uma nuance: a política no prompt mudou mais o
  comportamento, enquanto os validadores mediram e sinalizaram (ver
  `evidencias_empiricas.md`, Camada 7 v2).
- **Prática 2.** O fluxo está em código (`responder`, `_RECUSAS`), não no
  prompt.
- **Prática 4.** O modelo e a sua versão são registrados por interação
  desde a v4.
- **Prática 5.** "Safe response templates": `recusar_sem_base` e as demais
  recusas fixas.
- **Fluxo da 8.2.** O fluxo do protótipo (interpretar, recuperar, sintetizar,
  validar, registrar) segue as etapas (ii) a (vi), sem a decomposição de
  tarefa.

**Causa (achado metodológico)**: a paráfrase curta da prescrição,
registrada no início de cada seção e não revisitada, fez com que lacunas de
leitura fossem registradas como lacunas da arquitetura. Para a lacuna 3 da
monografia (suficiência como guia de projeto), só a categoria 1 conta como
insuficiência do artigo. As categorias 2 e 3 descrevem o alcance do
protótipo.

**Pendências deste diário identificadas no confronto**:

- a seção "Camada 2" mantém a lacuna em branco ("*(preencher…)*") e
  "Adaptação necessária: nenhuma até o momento";
- a seção "Camada 8" descreve os campos da v1; os campos `desfecho`,
  `validacao` e `parametros_llm` estão registrados só nas seções das
  Camadas 2 e 7.

---

## Multimodalidade (Camada 1) — fora de escopo

Conforme definido no Capítulo 1, Seção 5 (Metodologia), os aspectos
multimodais da Camada de Interação com o Usuário foram explicitamente
delimitados como fora de escopo desta pesquisa.
