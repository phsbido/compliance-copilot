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
