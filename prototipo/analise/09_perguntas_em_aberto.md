# Perguntas em Aberto

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

O que não consegui determinar com certeza durante esta análise, e onde
procurar para resolver.

## 1. Qual é a diferença exata entre `data/normativos/circular_4015_2020.md` e `data/normativos/1_bronze_raw/circular_4015_2020.md`

**O que sei**: são arquivos diferentes (confirmado por `diff`), embora
`etapa_bronze()` (`ingest_normativos.py:239-246`) faça cópia byte-a-byte sem
transformação — então a única explicação plausível é que a fonte foi editada
depois da última execução do pipeline (ver `07_riscos.md`, item 7).

**O que não sei**: se a diferença é substantiva (conteúdo normativo
alterado) ou trivial (espaçamento, encoding, uma correção de metadado no
frontmatter). Não fiz um diff de conteúdo linha a linha — só confirmei que
os arquivos diferem.

**Onde descobrir**: `diff data/normativos/circular_4015_2020.md
data/normativos/1_bronze_raw/circular_4015_2020.md` (e o mesmo para
`resolucao_conjunta_1_2020.md`, que não cheguei a comparar). Se
`git log` tivesse mais de um commit tocando esses arquivos, `git log -p`
resolveria isso diretamente — mas o repositório tem um único commit
(`34dbc2e`), então a resposta não está no histórico do git.

## 2. Origem exata e motivo de `_openfinance_limpo.md` não ter sido removido

**O que sei**: é o texto extraído da Instrução Normativa BCB nº 759/2026
(mesma norma do PDF `normativoOpenFinance.pdf`), não referenciado por
nenhum código, provavelmente um artefato manual anterior ao pipeline
automatizado (ver `07_riscos.md`, item 6).

**O que não sei**: se foi criado antes ou depois de `ingest_normativos.py`
existir, por que ficou na raiz do projeto em vez de `data/normativos/`, e se
foi intencionalmente deixado como material de referência para a monografia
ou simplesmente esquecido.

**Onde descobrir**: perguntar diretamente ao autor/pesquisador — não há
registro em `docs/decisoes_arquitetura.md` nem `docs/evidencias_empiricas.md`
sobre esse arquivo especificamente.

## 3. Se o bug de ordem de import do `OLLAMA_HOST` (ver `07_riscos.md`, item 0) já se manifestou na prática

**O que sei**: por leitura do código-fonte instalado da biblioteca `ollama`,
o bug existe estruturalmente — `OLLAMA_HOST` definido só em `.env` não
chega a ser usado pelo cliente real.

**O que não sei**: se algum dia alguém rodou o protótipo com um
`OLLAMA_HOST` diferente do default, encontrou um erro de conexão
inesperado, e não documentou a causa — ou se isso simplesmente nunca
aconteceu porque ninguém saiu do setup default (localhost:11434).

**Onde descobrir**: não há menção a esse comportamento em
`docs/evidencias_empiricas.md` nem `docs/decisoes_arquitetura.md`. Só um
teste real (definir `OLLAMA_HOST` para um valor diferente do default em
`.env`, sem exportá-lo no shell, e rodar `python main.py` apontando para um
servidor Ollama nesse endereço) confirmaria o comportamento em tempo de
execução — não cheguei a rodar o programa, só li o código.

## 4. Cobertura completa do texto integral dos 2 normativos curados

**O que sei**: li o frontmatter e o início de
`data/normativos/resolucao_conjunta_1_2020.md` (72.580 bytes) e
`circular_4015_2020.md` (11.771 bytes), e usei trechos citados em
`docs/decisoes_arquitetura.md`/`tests/casos_teste.md` como amostra
representativa do conteúdo normativo.

**O que não sei**: se há algum artigo específico, dentro do texto integral
desses dois arquivos, com uma particularidade de formatação (ex.: um
artigo sem "Art." no início da linha, quebrando a divisão por regex de
`knowledge_base.py:70`) que eu não identifiquei por não ter lido o texto
completo dos dois arquivos linha a linha.

**Onde descobrir**: leitura integral de
`data/normativos/resolucao_conjunta_1_2020.md` e
`data/normativos/circular_4015_2020.md`, ou rodar `run_check_knowledge.py`
e inspecionar `len(kb.documentos)` e o conteúdo de cada `Documento.trecho`
para confirmar que a divisão por artigo produziu o número esperado de
trechos sem trechos anormalmente grandes (sintoma de uma quebra de artigo
não detectada).

## 5. Se a Circular nº 4.015/2020 e a Resolução Conjunta nº 1/2020 no corpus são as versões consolidadas mais recentes

**O que sei**: o frontmatter de `resolucao_conjunta_1_2020.md` declara
`versao: "consolidada (v7), obtida em 2026-08-14"` — uma versão específica,
com data de obtenção.

**O que não sei**: se houve alguma alteração normativa posterior a
2026-08-14 que tornaria essa versão desatualizada no momento em que esta
análise foi escrita (2026-09-23) — normativos do BCB são frequentemente
alterados por normas posteriores (o próprio corpus gerado pelo pipeline
ilustrativo, ao processar `normativoPix.pdf`, mostra múltiplas redações
alteradas por resoluções de 2021, 2024 e 2025 para o mesmo artigo — ver
`data/normativos/3_gold_indexed/normativoPix.json`).

**Onde descobrir**: consultar diretamente
`https://normativos.bcb.gov.br/Lists/Normativos/Attachments/51028/Res_Conj_0001_v7_L.pdf`
(URL declarada no frontmatter) e comparar com a versão vigente no portal do
BCB.

## 6. Se a taxa de 60% de aviso de citação não verificada no cenário "Norma Ausente" seria diferente com o bug do item 1 de `07_riscos.md` corrigido

**O que sei**: o bug da stopword `"são"` não filtrada contribui, em
princípio, para recuperação de trechos irrelevantes por sobreposição
lexical incidental — o mesmo fenômeno por trás da taxa de 60%.

**O que não sei**: se o efeito é mensurável ou desprezível — não reexecutei
o benchmark com a correção aplicada (fora do escopo desta análise, que é só
leitura, não modificação de código).

**Onde descobrir**: corrigir `_STOPWORDS` (`knowledge_base.py:21-26`,
adicionar `"sao"`), rodar `python run_benchmark.py` de novo, e comparar a
nova taxa de aviso no cenário `norma_ausente_fronteira` contra o valor atual
(60%, `docs/tabela_resultados_empiricos.csv`).

## 7. Se há uma convenção de versionamento/branching não documentada

**O que sei**: o repositório tem um único commit
(`34dbc2e — "Implementa protótipo LLM-Native de compliance regulatório (8
camadas)"`) na branch `main`, com várias mudanças não commitadas no momento
desta análise (`git status` no início da sessão mostrava vários arquivos
modificados/novos).

**O que não sei**: se há uma convenção pretendida de commits incrementais
por camada (o que seria natural dado o estilo de trabalho documentado em
`docs/decisoes_arquitetura.md`, uma entrada por camada, com datas) que
simplesmente não foi seguida no controle de versão, squashando tudo em um
commit único no final.

**Onde descobrir**: perguntar ao autor sobre o fluxo de trabalho de commits
pretendido, ou verificar se há um repositório remoto/histórico anterior não
sincronizado com este clone local.
