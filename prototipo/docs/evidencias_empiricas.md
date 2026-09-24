# Evidências Empíricas — Observações Durante a Construção

Este documento é um log corrido de **observações empíricas** feitas ao testar
o protótipo durante a construção — resultados inesperados, comportamentos do
modelo, falhas e acertos observados na prática. É complementar a
`docs/decisoes_arquitetura.md` (que registra decisões de projeto e
ambiguidades da arquitetura): aqui o foco é o que foi *observado ao rodar o
sistema*, não o que foi *decidido ao projetá-lo*.

Este arquivo alimenta a compilação posterior de evidências para a análise da
monografia (Capítulo 1, Seção 5, itens (d) e (e)) — não é o texto da
monografia em si.

Formato por entrada: Data, Camada relacionada, Contexto (o que foi
executado), Observação, Relevância para a pesquisa.

---

## 2026-08-14 — Alucinação de citação normativa (Camada 3, sem Camadas 5/7)

**Camada relacionada**: Camada 3 (Orquestração), evidenciando a necessidade
das Camadas 5 (Conhecimento/RAG) e 7 (Governança).

**Contexto**: execução de `run_check_orchestration.py`, testando o fluxo
completo de 4 etapas do `Orchestrator` com a pergunta "Quais são os
requisitos para uma instituição PJ participar do Open Finance?". Neste
estágio, `_buscar_normativo` é um stub (não retorna conteúdo normativo real)
e `_validar_citacao` também é um stub (não valida nada) — a etapa de síntese
depende inteiramente do conhecimento paramétrico do modelo (`llama3.1` via
Ollama).

**Observação**: a resposta citou uma **"Resolução do CPM 4.665/2021"**
como fonte normativa para requisitos de conformidade em contas digitais. Essa
citação aparenta ser fabricada: "CPM" (Comitê de Política Monetária) não é o
nome de um órgão emissor de resoluções normativas nesse formato no sistema
regulatório brasileiro — o número "4.665" e o formato de citação lembram
atos normativos reais (ex: Circulares/Resoluções do BCB), mas a combinação
específica não corresponde a um ato normativo verificável. O modelo
apresentou a citação com o mesmo nível de confiança textual que informações
corretas na mesma resposta (ex: menção genérica a LGPD e à necessidade de
autorização do Bacen).

**Relevância para a pesquisa**: evidência empírica direta, obtida **antes**
de as Camadas 5 e 7 existirem, de por que a arquitetura de Maia et al.
(2026) as torna necessárias em domínios de alto risco de alucinação
factual — especificamente domínios regulatórios, onde uma citação
verossímil porém falsa é um risco de compliance real, não apenas um erro
factual genérico. Serve como baseline "sem RAG, sem validação" para
comparação posterior com o comportamento do sistema já com as Camadas 5 e 7
implementadas (comparação a ser feita em `tests/casos_teste.md`).

---

## 2026-08-14 — Quase-erro ao localizar automaticamente um PDF oficial (Camada 5)

**Camada relacionada**: Camada 5 (Conhecimento/RAG).

**Contexto**: ao montar o corpus inicial, tentei localizar de forma
automatizada (busca + padrão de URL conhecido) o PDF oficial da Resolução
BCB nº 339, de 24/08/2023 (duplicata escritural), a partir do padrão de
nomenclatura observado em outros normativos já confirmados
(`Res_XXXX_vN_L.pdf`).

**Observação**: a URL construída (`.../Res_0339_v1_O.pdf`) retornou um
documento real e existente no domínio oficial `normativos.bcb.gov.br` — mas
era a **Resolução nº 339, de 13 de agosto de 1975**, uma norma antiga e
completamente não relacionada, coincidindo apenas no número. O erro só foi
percebido por verificar o conteúdo do PDF antes de apresentá-lo como fonte
(confirmação de título/data), não pela URL em si, que parecia plausível.

**Relevância para a pesquisa**: reforça, de um ângulo diferente, a mesma
lição da entrada anterior (alucinação de citação pela Camada 2): mesmo uma
fonte que *parece* uma URL oficial legítima — mesmo domínio, mesmo padrão de
nomenclatura, mesmo formato — pode ser uma referência incorreta se não for
verificada por conteúdo, não apenas por forma. Isso é diretamente relevante
para o desenho da Camada 7 (Governança): validar citação não pode se limitar
a checar se uma URL "parece" oficial — precisa checar se o conteúdo
referenciado de fato corresponde à norma citada. Motivou a decisão de não
incluir a norma 339 no corpus com um link não verificado, documentando-a
como pendente em `data/normativos/PENDENTES.md` (ver
`docs/decisoes_arquitetura.md`, Camada 5).

---

## 2026-08-14 — Distorção de fato mesmo com contexto correto (Camadas 3+4+5, sem Camada 7)

**Camada relacionada**: Camada 3 (Orquestração) já ligada às Camadas 4
(Ferramentas) e 5 (Conhecimento), evidenciando a necessidade da Camada 7
(Governança).

**Contexto**: execução de `run_check_orchestration.py` após `_buscar_normativo`
passar a usar a busca real (Camada 4 sobre Camada 5), com a mesma pergunta
de teste ("Quais são os requisitos para uma instituição PJ participar do
Open Finance?"). Desta vez o modelo recebeu, como contexto normativo, o
texto correto do Art. 6º da Resolução Conjunta nº 1/2020, que diz: "as
instituições individuais e as instituições pertencentes a conglomerados com
número de clientes superior a **cinco milhões**" (critério de participação
obrigatória).

**Observação**: a resposta do modelo afirmou "ter um número de clientes
acima de **50 mil** (segundo o parágrafo 5º do **Artigo 51**)" — um número
duas ordens de grandeza menor que o correto (5 milhões), atribuído a um
artigo errado (o critério está no Art. 6º, não no 51). Diferente da
alucinação registrada na entrada anterior (uma norma inteiramente
inventada), aqui o modelo tinha o texto correto disponível no próprio
contexto fornecido e ainda assim o distorceu ao sintetizar a resposta.

**Relevância para a pesquisa**: evidência de que RAG (Camada 5) por si só
**não elimina** o risco de erro factual em domínio regulatório — reduz o
risco de citar uma norma inexistente, mas não garante fidelidade ao
conteúdo da norma real fornecida como contexto. Isso é uma justificativa
empírica mais forte ainda para a Camada 7 (Governança): validação de
citação precisa, no mínimo, conferir se números e artigos citados na
resposta final batem com o trecho de contexto que os originou — não apenas
se a norma citada existe.

**Atualização (mesma data, validação da Camada 6)**: em nova execução de
`run_check_orchestration.py`, agora com duas perguntas em sequência para
testar a memória de sessão, o número de clientes veio correto ("5 milhões")
— mas a resposta atribuiu o requisito ao **"art. 51"** novamente, o mesmo
artigo errado da execução anterior (o correto é o Art. 6º). A recorrência do
mesmo número de artigo errado, em execuções diferentes, sugere que não é um
erro aleatório isolado, e sim algo mais sistemático (possivelmente o modelo
associando "art. 51" a esse tema por familiaridade com outras normas do
Sistema Financeiro Nacional em seu conhecimento paramétrico, já que o número
citado é plausível mas nunca corresponde ao artigo real no contexto
fornecido). Reforça a necessidade de a Camada 7 validar não só a existência
da norma, mas a correspondência exata entre o número de artigo citado e o
número de artigo presente no trecho de contexto usado.

---

## 2026-08-14 — Camada 7 pega o erro recorrente da Camada 4/6; e dois efeitos colaterais novos

**Camada relacionada**: Camada 7 (Governança), interagindo com Camadas 3 e 6.

**Contexto**: `validar_citacao` foi construída especificamente para pegar o
tipo de erro já observado duas vezes (artigo citado que não está no
contexto normativo real). Testada primeiro isoladamente
(`run_check_governance.py`), depois no fluxo completo
(`run_check_orchestration.py`, 3 perguntas: normativa, acompanhamento,
parecer jurídico).

**Observação 1 (esperada)**: a validação funcionou como desenhada — uma
citação de "art. 51" não presente no contexto de teste foi corretamente
sinalizada; uma citação de "art. 6º" presente no contexto não gerou aviso
falso.

**Observação 2 (efeito colateral, encontrado e corrigido)**: na primeira
execução do fluxo completo, a resposta à pergunta de acompanhamento (turno
2) veio com o disclaimer de validação humana **duplicado** — um gerado pelo
próprio modelo (ecoando, parafraseado, o disclaimer do turno 1, que estava
salvo na memória) e outro anexado pela Camada 7. Causa: a Camada 3 salvava
na memória a resposta já com os avisos da Camada 7 anexados. Corrigido
salvando na memória a versão pré-validação.

**Observação 3 (limitação documentada, não corrigida)**: também no turno 2,
`validar_citacao` sinalizou "art. 1, 6" como não verificados — mas esses
artigos *tinham* aparecido no contexto do turno 1 (acessível ao modelo via
memória). A validação de citação só olha o contexto normativo do turno
atual, não o que está na memória — então um aviso "tecnicamente correto"
(não estava *neste* contexto) pode soar como falso positivo do ponto de
vista de quem está lendo a conversa inteira.

**Relevância para a pesquisa**: mostra que implementar uma camada
posterior (Governança) usando achados de camadas anteriores como
especificação funcionou — o erro recorrente documentado foi efetivamente
pego. Mas também mostra que a integração *entre* camadas (aqui, Memória e
Governança) introduz sua própria classe de problema, não antecipada pela
arquitetura de Maia et al.: cada camada isolada pode estar correta em
relação ao seu próprio escopo de dados, e ainda assim produzir um resultado
estranho quando combinada com outra camada que tem um escopo de dados
diferente (contexto do turno vs. memória de sessão inteira). Vale como
evidência para a discussão de viabilidade sobre integração entre camadas,
não só sobre cada camada isoladamente.

---

## 2026-08-15 — Classificação `fora_de_escopo` é calculada mas não desvia o fluxo (Camada 3)

**Camada relacionada**: Camada 3 (Orquestração), ao consolidar casos de
teste formais (`tests/casos_teste.md`) com todas as 8 camadas já ligadas.

**Contexto**: chamada direta a `Orchestrator.responder("Qual e a capital da
Franca?")` — pergunta claramente fora do domínio (Open Finance/contas PJ).

**Observação**: `_interpretar` classificou corretamente a pergunta como
`fora_de_escopo`. Mas, diferente de `parecer_juridico` (que desvia o fluxo
para recusa direta desde a Camada 7), `fora_de_escopo` não tem tratamento
especial em `responder()` — o fluxo segue normal: `_buscar_normativo` faz
busca lexical na base de normativos de Open Finance mesmo sem relação com a
pergunta, e retornou um trecho da Circular nº 4.015/2020 (provavelmente por
sobreposição lexical incidental de palavras comuns). O modelo, então,
recebeu esse trecho irrelevante como "contexto normativo" e produziu uma
resposta que reconhece a irrelevância do contexto ("o texto normativo que
você forneceu não contém nenhuma informação sobre a capital da França") mas
ainda assim responde à pergunta fora de escopo (corretamente, "Paris") e
recebe o rodapé de disclaimer padrão ("Esta resposta é apoiada em atos
normativos públicos do BCB..."), que não faz sentido para uma resposta sobre
geografia. A Camada 8 registrou essa fonte irrelevante como se fosse
proveniência real da resposta (`fontes_normativas` não-vazio).

**Relevância para a pesquisa**: mostra que a classificação de intenção
(Camada 3) só tem efeito prático quando uma camada posterior explicitamente
implementa um desvio de fluxo para ela — ter a informação calculada não
basta (mesma lição já registrada para `parecer_juridico` antes da Camada 7
existir, ver entrada de 2026-08-14, "Alucinação de citação normativa").
Aqui o caso ficou sem correção proposta ao usuário ainda: é uma decisão de
projeto em aberto (adicionar um desvio de fluxo para `fora_de_escopo`
semelhante ao de `parecer_juridico`?), não apenas uma observação passiva.
Também evidencia um efeito colateral na Camada 8: proveniência registrada
sem checagem de relevância pode ser enganosa (um "Fontes:" listado que não
tem relação real com o conteúdo da resposta).

**Correção (mesma data)**: adicionado desvio de fluxo para `fora_de_escopo`
em `Orchestrator.responder`, generalizando o padrão já usado para
`parecer_juridico` (dicionário `_RECUSAS`), com nova função
`recusar_fora_de_escopo()` (Camada 7). Reexecutando a mesma pergunta
("Qual e a capital da Franca?") após a correção: `tipo_classificacao:
fora_de_escopo`, `fontes_normativas: []`, resposta é a recusa fixa, sem
busca normativa nem síntese. Confirma que generalizar o mecanismo de desvio
já existente (em vez de tratar `fora_de_escopo` como um caso à parte)
resolveu o problema com uma mudança pequena — evidência de que o desenho
inicial da Camada 3 (stub explícito, depois um único desvio para
`parecer_juridico`) já comportava essa generalização sem refatoração
maior.

---

## 2026-09-22 — Primeira execução do benchmark quantitativo (20 execuções, todas as 8 camadas)

**Camada relacionada**: transversal (Camadas 1-8 ligadas), avaliação
quantitativa complementar aos 4 casos qualitativos de
`tests/casos_teste.md` — ver `docs/decisoes_arquitetura.md` ("Benchmark
Empírico") para a decisão de projeto por trás de `run_benchmark.py`.

**Contexto**: `python run_benchmark.py`, 4 cenários
(`tests/casos_teste.json`) x 5 repetições cada, `llama3.1` via Ollama local,
uma instância nova de `Orchestrator` por execução (sem memória entre
repetições). Dado bruto em `logs/resultados_benchmark.json`, agregado em
`docs/tabela_resultados_empiricos.csv`.

**Observação 1 — classificação (Camada 3) 100% estável nas 20 execuções**:
todas as execuções, nos 4 cenários, classificaram como esperado
(`normativo`/`parecer_juridico`/`fora_de_escopo`). Diferente dos erros de
conteúdo já documentados nas entradas anteriores (número distorcido, artigo
errado), a etapa de *classificação de intenção* não mostrou variação entre
repetições neste conjunto de perguntas — evidência de que o risco de
alucinação observado até aqui está concentrado na etapa de síntese
(`_sintetizar_resposta`), não na de interpretação (`_interpretar`).

**Observação 2 — cenário de fronteira (norma ausente) gera aviso de
citação não verificada em 3 das 5 execuções (60%)**: a pergunta sobre a
Resolução BCB nº 32/2020 (não indexada no corpus, ver
`data/normativos/PENDENTES.md`) fez a Camada 5 retornar, por sobreposição
lexical, trechos de normativos *diferentes* (os 2 realmente indexados) como
"contexto normativo". Em 3 execuções, a resposta sintetizada citou
artigo(s) não presentes nesse contexto retornado, e a Camada 7 sinalizou
corretamente o aviso; nas outras 2, não citou nenhum artigo fora do
contexto (ex: respondeu de forma mais genérica, sem número específico) e
não houve aviso. Não observado: o sistema nunca afirmou ter a Resolução BCB
nº 32/2020 em si — o comportamento de risco aqui não é "citar a norma
ausente como se existisse no corpus", e sim citar, com confiança, um número
de artigo específico tirado do contexto (irrelevante) recuperado por engano.

**Relevância para a pesquisa**: quantifica, pela primeira vez com múltiplas
repetições, uma taxa de ocorrência (60%) para a classe de erro já descrita
qualitativamente nas entradas de 2026-08-14 ("art. 51" recorrente) — antes
só havia evidência de que o padrão *se repetia*, não de *com que
frequência*. Também mostra que a Camada 7, desenhada para o cenário "corpus
tem a norma certa mas o modelo erra o artigo", generaliza razoavelmente bem
para o cenário "corpus não tem a norma perguntada e retorna a errada por
engano" — mesmo mecanismo de checagem (citação vs. contexto do turno) pega
os dois casos, sem ajuste adicional.

**Observação 3 — latência ~80x menor nos fluxos de recusa que no fluxo
normativo**: recusas (`parecer_juridico`: média 173ms; `fora_de_escopo`:
média 122ms) só fazem uma chamada ao LLM (`_interpretar`, texto curto de
saída). O fluxo normativo (média ~11.1s nos dois cenários que o
exercitaram) faz uma segunda chamada, `_sintetizar_resposta`, com prompt
maior (contexto normativo + histórico + pergunta) e saída mais longa. A
variabilidade também é maior no fluxo normativo (desvio padrão até
~5.4s no cenário de norma ausente, contra <100ms nos dois cenários de
recusa) — plausivelmente porque prompts/saídas de tamanho variável (a
resposta muda a cada chamada, mesmo com a mesma pergunta) dominam o tempo
de geração token a token, enquanto a recusa é um texto fixo sem geração.

**Relevância para a pesquisa**: evidência quantitativa de que o desvio de
fluxo da Camada 7 (`_RECUSAS`, ver Camada 3/7 em
`docs/decisoes_arquitetura.md`) não é só uma decisão de correção de
conteúdo — tem um efeito de custo/latência mensurável e favorável, já que
evita a chamada mais cara ao LLM (síntese) quando a pergunta não deveria
ser respondida de qualquer forma. Relevante para a discussão de viabilidade
sobre custo operacional de aplicações LLM-Native em produção, não só sobre
qualidade de resposta.

---

## 2026-09-24 — Benchmark em modo determinístico (temperature=0, seed=42)

**Contexto**: mesmos 4 cenários × 5 repetições do benchmark de 2026-09-22,
agora com `python run_benchmark.py --modo deterministico` (ver
`docs/decisoes_arquitetura.md`, "Reprodutibilidade"). Dado bruto em
`docs/resultados/resultados_benchmark_deterministico.json`, agregado em
`docs/tabela_resultados_empiricos_deterministico.csv`. Mesmo ambiente do
modo livre (Ollama 0.33.2, `llama3.1:latest` ID `46e0c10c039e`, Q4_K_M).

| Cenário | Respostas distintas (livre → determ.) | Aviso de citação (livre → determ.) | Latência média (livre → determ.) |
|---|---|---|---|
| Caminho Feliz / RAG BACEN | 5 → 1 | 0% → 0% | 11,1s → 11,5s |
| Norma Ausente / Fronteira | 5 → 1 | 60% → 100% | 11,1s → 13,1s |
| Solicitação de Parecer | 1 → 1 | 0% → 0% | 173ms → 155ms |
| Fora de Escopo | 1 → 1 | 0% → 0% | 122ms → 135ms |

Classificação correta e taxa de recusa: 100% e idênticas nos dois modos.

**Observação 1 — a variação textual do modo livre vem da amostragem**: com
temperatura zero e seed fixa, cada cenário produziu uma única resposta nas 5
repetições (antes: 5 respostas diferentes em cada cenário de RAG). A
reprodução exata é possível no mesmo ambiente.

**Observação 2 — a taxa de 60% de aviso de citação não é uma propriedade
estável do cenário**: no modo determinístico, o cenário "norma ausente"
disparou o aviso da Camada 7 em 5/5 execuções, porque a única resposta
gerada contém a atribuição de artigo indevida. Ou seja, os 60% do modo livre
medem a frequência com que a amostragem leva o modelo a esse erro, e o modo
determinístico "congela" um dos resultados possíveis. Para a monografia:
reportar o modo livre como a medida de comportamento em uso e o determinístico
como evidência de reprodutibilidade, sem tratar o 100% como taxa de erro.

**Observação 3 — a variância de latência cai no fluxo normativo quando a
saída é fixa** (desvio padrão de 5,4s para 0,6s no cenário "norma ausente"),
o que confirma a explicação dada em 2026-09-22 de que o tamanho variável da
resposta domina a variação de tempo. A primeira execução do caminho feliz
(16,4s) inclui o carregamento do modelo na memória.

---

## 2026-09-24 — Camada 5 v2 (Gold + BM25): teste de recuperação e achados da ingestão

**Contexto**: a Camada 5 passou a ler a camada Gold do pipeline
Bronze/Silver/Gold, ingerido pelas URLs oficiais do BCB, com busca BM25 (ver
`docs/decisoes_arquitetura.md`, "Revisão da Camada 5"). Antes de rodar o
LLM, a recuperação foi comparada isoladamente com a v1 (`.md` curados +
contagem de palavras em comum, recuperada da tag `v1.0-monografia`).

**Achado 1 — o HTML da página não é o texto vigente para normas antigas**:
para a Resolução Conjunta nº 1/2020 e a Circular nº 4.015/2020, o campo
`Texto` da página do BCB traz a redação original de 2020 ("Open Banking");
o texto consolidado só existe nos PDFs listados no campo `Documentos`. E o
corpus curado da v1 já estava desatualizado: Resolução Conjunta nº 1 na v7
(vigente: v9), Circular nº 4.015 na v3 (vigente: v5).

**Achado 2 — recuperação por pergunta (top 3)**:

| Pergunta | v1 (palavras em comum) | v2 (Gold + BM25) |
|---|---|---|
| Requisitos para instituição PJ participar do Open Finance (cenário "caminho feliz") | RC1 Arts. 5º, 6º, 51 | RC1 Arts. 7º, 6º; IN 759 Art. 1º |
| Instituições que participam de forma obrigatória | RC1 Arts. 5º, 6º, 44 | RC1 Art. 6º (partes 1 e 2); IN 759 Art. 1º |
| Dados cadastrais de pessoa jurídica | Circ. Art. 4º; RC1 Arts. 2º, 36 | Circ. Art. 6º-A; IN 759 seções 4.2 (Pessoa jurídica) e 3.1 |
| Consentimento e prazo de validade | RC1 Arts. 5º, 2º, 6º | RC1 Arts. 13-A, 14; IN 759 seção 6.1.3 |

Na v1, os artigos mais longos (Arts. 5º e 6º, com mais de 4 mil caracteres)
apareciam em quase toda pergunta, porque a contagem de palavras em comum
favorece trecho grande. O BM25 normaliza pelo tamanho e pondera palavras
raras, e a v2 passa a trazer o dispositivo específico (consentimento →
seção "Do Consentimento"). O contexto enviado ao LLM também encolheu: trechos
de até ~2,5 mil caracteres, contra até ~6 mil na v1.

**Achado 3 — dois ajustes de tokenização vieram do próprio teste**:
(a) com redução só de plural, a pergunta do caminho feliz trazia artigos do
"CAPÍTULO IV DOS REQUISITOS…" (a palavra "requisitos" do cabeçalho), e não a
seção "Da Participação": "participar", "participação" e "participantes"
eram tokens diferentes. Com radical (`particip`), o Art. 6º voltou ao topo.
(b) com radical, "Como funciona a autenticação…" passou a trazer o Art. 1º
("autorizadas a funcionar"), porque `funcion` é raro no corpus e tem peso
alto. "Funciona" é moldura da pergunta, como "quais" e "como", e virou
stopword junto com verbos análogos. Testado também indexar sem o cabeçalho
de contexto: a recuperação piorou, e o cabeçalho foi mantido.

**Relevância para a pesquisa**: a Camada 5 de Maia et al. não prescreve a
preparação do conhecimento. Aqui, a preparação (qual representação da fonte
é a vigente, limpeza, granularidade do trecho, contexto no trecho) mudou
mais a qualidade da recuperação do que a fórmula de ranqueamento em si. E
cada ajuste da busca foi motivado por um caso observável, o que o mantém
explicável e rastreável.

**Achado 4 — benchmark v2 (mesmos 4 cenários × 5 repetições, dois modos)**.
Dado bruto em `docs/resultados/`; v1 arquivada em `docs/resultados/v1/`.

| Cenário | Métrica | v1 livre | v2 livre | v1 determ. | v2 determ. |
|---|---|---|---|---|---|
| Caminho Feliz | latência média | 11,1 s | 9,5 s | 11,5 s | 10,8 s |
| Caminho Feliz | desvio padrão | 2,7 s | 1,3 s | 2,9 s | 0,8 s |
| Norma Ausente | aviso de citação | 60% | 80% | 100% | 100% |
| Norma Ausente | latência média | 11,1 s | 10,6 s | 13,1 s | 18,0 s |
| Parecer / Fora de escopo | classificação e recusa | 100% | 100% | 100% | 100% |

Classificação correta: 100% em todas as 80 execuções (v1 + v2). Modo
determinístico: 1 resposta distinta por cenário nas duas versões.

**Leitura qualitativa (o que as taxas não mostram)**:

- *Caminho feliz*: a v2 estrutura a resposta em participação obrigatória e
  voluntária, a partir dos Arts. 6º e 7º (seção "Da Participação"), em vez
  dos Arts. 5º, 6º e 51 da v1. Mas o erro numérico persiste nas duas
  versões, com o trecho correto no contexto: o Art. 6º diz "número de
  clientes superior a cinco milhões"; a v1 determinística respondeu "mais de
  100 mil contas" e a v2 determinística "3 milhões de clientes". Mesma classe
  de erro registrada em 2026-08-14 (distorção de fato com contexto correto),
  e a Camada 7 não a detecta porque só confere números de artigo e de norma.
- *Norma ausente*: a taxa de aviso subiu (60% → 80% no livre), mas o
  comportamento melhorou. A v1 determinística **inventou** o conteúdo da
  Resolução BCB nº 32/2020 ("De acordo com a Resolução BCB nº 32/2020, os
  requisitos técnicos … incluem: 1. … interface aberta …"). A v2 determinística
  começa com "Não encontrei a Resolução BCB nº 32/2020" e responde com o que
  o corpus tem (Art. 46 da Resolução Conjunta nº 1). No modo livre, a v2
  declara a ausência em 4 de 5 respostas. Todos os avisos, nas duas versões,
  são do tipo "a resposta cita Resolução BCB nº 32, que não consta no
  trecho": o validador da Camada 7 dispara também quando o modelo nomeia a
  norma para dizer que ela não está disponível. **A taxa de aviso desse
  cenário mistura alucinação com recusa honesta e não deve ser lida como
  taxa de erro.** A resposta mais longa da v2 determinística (3,8 mil contra
  2,2 mil caracteres) explica a latência maior nesse cenário.

**Relevância para a pesquisa**: melhorar a Camada 5 (recuperação mais
precisa, contexto menor e rotulado) reduziu latência e variância e mudou o
comportamento diante de norma ausente, mas não corrigiu a distorção de
números, que depende do Núcleo de Raciocínio (Camada 2) e de uma
verificação que a Camada 7 ainda não faz. As camadas se compensam só
parcialmente, e a métrica automática da Camada 7 precisa de leitura
qualitativa para não ser mal interpretada.
