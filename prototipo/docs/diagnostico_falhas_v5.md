# Diagnóstico das falhas — benchmark v5 (Fase 1)

Data: 2026-10-02. Escopo: atribuir cada execução com problema da v5 a uma
camada de origem, **sem alterar o protótipo**. As Fases 2 e 3 (intervenções
e nova rodada) ficam como trabalho futuro.

Artefatos:

- `docs/diagnostico_falhas_v5.csv`: uma linha por execução, com camada
  principal, contributiva e evidência (gerado por
  `scripts/diagnostico_v5.py`, que contém a tabela de atribuição);
- `docs/resultados/diagnostico_v5_experimento_cache.json`: as 52 chamadas
  do experimento da Seção 3 (`scripts/experimento_cache_ollama.py`).

**Dependência**: os vereditos da auditoria (`auditoria_respostas_v5.csv`)
ainda são do assistente e aguardam revisão do autor. Se algum mudar, rode
`python scripts/diagnostico_v5.py`: o script falha se uma execução incluída
ficar sem atribuição, e as contagens das Seções 2 e 4 devem ser refeitas.

## 1. Método

**Execuções incluídas** (84): nos dois modos, toda execução com falha no
critério automático ou aviso da Camada 7. No modo produção, também as com
veredito `incorreta`, `parcial` ou `abstencao` na auditoria. O modo
sensibilidade não foi auditado; dele entram só as falhas automáticas e os
avisos.

| Modo | Execuções | Falha automática | Aviso da Camada 7 | Só pelo veredito |
|---|---|---|---|---|
| Produção | 67 | 15 | 3 | 52 |
| Sensibilidade | 17 | 17 | 3 | — |

**Evidência**: para cada execução, o JSON bruto (`resposta_sintetizada`,
`contexto_normativo`, `trechos_recuperados`), o rótulo de recuperação do
caso (`tests/casos_teste.json`) e os prompts do código: classificação em
`Orchestrator._interpretar` (temperatura 0 em produção, 0,8 em
sensibilidade), política de síntese em `POLITICA_SINTESE` (Camada 7),
validador em `validar_resposta` e critério em `run_benchmark.avaliar_sucesso`
e `declara_ausencia_de_norma`. Onde a nota da auditoria afirmava que um
trecho estava ou não no contexto, a afirmação foi conferida no
`contexto_normativo` da execução.

**Categorias de origem**:

| Código | Camada de origem | Quando se aplica |
|---|---|---|
| C2/3 classificação | Camadas 2 e 3 | O tipo da pergunta saiu errado (prompt de `_interpretar` e temperatura) |
| C2 síntese | Camada 2 | O trecho que responde à pergunta **estava** no contexto e a resposta o leu errado, omitiu ou contradisse |
| C5 recuperação | Camada 5 | O trecho que responde à pergunta **não estava** entre os 3 recuperados |
| C7 política | Camada 7 (antes da geração) | A política de síntese permitiu ou induziu o erro (ex.: "o trecho não contém" virou "a norma não contém") |
| C7 validador | Camada 7 (depois da geração) | Aviso falso positivo sobre uma resposta correta |
| Critério | Medição do benchmark | Resposta adequada contada como falha (falso negativo da medição) |

**Regra de decisão**: a camada **principal** é a que precisaria mudar para
o resultado esperado ser possível. Se o trecho relevante não veio, a
principal é a Camada 5, mesmo que a síntese também tenha errado. Sem o
trecho, a melhor resposta possível é a abstenção. A **contributiva** é a
camada que agravou o erro ou o deixou passar. Duas categorias contributivas
não previstas na lista inicial surgiram da evidência: o formato do trecho
na Gold (cabeçalho embutido no texto) e o estado do cache do servidor de
inferência (Seção 3).

## 2. Atribuição por caso

### Modo produção (67 execuções, 23 casos)

| Caso | Exec. | Veredito | Trecho relevante no contexto? | Principal | Contributiva | Evidência resumida |
|---|---|---|---|---|---|---|
| `caminho_feliz_rag_bacen` | 3 | incorreta | Parcial: art. 6º só a parte 2/2 | C2 síntese | C5 recuperação | O § 4º (dispensa), presente, vira requisito; a parte 1/2 (S1/S2, cinco milhões de clientes) não veio |
| `rc1_definicao_open_finance` | 3 | incorreta | Não (art. 2º) | C5 | C7 política | "Não há uma definição explícita (...) na Resolução": ausência no contexto vira ausência na norma |
| `rc1_objetivos` | 3 | abstenção | Não (art. 3º) | C5 | — | Abstém-se "no trecho fornecido", como a política pede |
| `rc1_participacao_obrigatoria` | 3 | abstenção | Não (art. 6º) | C5 | — | BM25 traz arts. 44 e 38 |
| `rc1_requisitos_consentimento` | 3 | incorreta | Não (art. 10) | C5 | C2 síntese | Texto do art. 5º, § 3º ("nos termos do art. 10") atribuído ao art. 10; o validador aceita porque "art. 10" ocorre no contexto |
| `rc1_consentimento_iniciacao` | 3 | parcial | Não (arts. 13 e 13-A) | C5 | C2 síntese | Lista da IN 759, seção 6.1.3, apresentada como regra geral |
| `rc1_prazo_revogacao` | 1 (rep. 1) | incorreta | Sim (art. 15, § 3º) | C2 síntese | C2 inferência | Escolhe o inciso II ("de forma imediata") em vez do I ("em até um dia"); só na repetição 1 (Seção 3) |
| `rc1_portabilidade_proponente` | 3 | incorreta | Não (art. 22-A) | C5 | C2 síntese | Os temas do art. 22-E viram obrigações da proponente |
| `rc1_parceria_nao_autorizada` | 3 | parcial | Sim (art. 36) | C2 síntese | — | Omite o § 1º (consentimento prévio e expresso), que está no contexto |
| `rc1_guarda_cinco_anos` | 3 | parcial | Sim (art. 49) | C2 síntese | C5 formato do trecho | Parêntese confuso e cópia do cabeçalho do trecho, contra a regra 3 da política |
| `rc1_continuidade_negocios` | 3 | parcial | Sim (art. 48) | C2 síntese | — | O caput diz "com relação à continuidade de negócios"; a resposta diz que os incisos não se ligam ao Open Finance |
| `circ_canais_eletronicos` | 3 | parcial | Sim (Circular, art. 2º) | C2 síntese | — | Estende aos canais eletrônicos a menção a dados abertos, que o artigo faz para dependências e correspondentes |
| `circ_servicos_iniciacao` | 3 | abstenção | Não (Circular, art. 6º) | C5 | — | Só seções da IN 759 |
| `circ_portabilidade_modalidades` | 3 | abstenção | Não, apesar do rótulo (ver Seção 5) | C5 | — | A seção 8 diz que as modalidades serão implementadas "de forma gradual", sem listá-las; a lista está na 8.1 e no art. 6º-A, ausentes |
| `in759_cadastro_pj` | 3 | abstenção | Não (seção 4.2) | C5 | — | Seções 1, 5.1 e 5.2 |
| `ausente_res_339_duplicata` | 3 | correta | n/a | Critério | — | "Não está disponível no contexto fornecido." não nomeia a norma |
| `parecer_notificacao_multa` | 3 | recusa pelo modelo | n/a | C2/3 classificação | — | Classificada como normativo; a política conteve |
| `parecer_redigir_defesa` | 3 | recusa pelo modelo | n/a | C2/3 classificação | — | Idem |
| `fora_codigo_python` | 3 | recusa pelo modelo | n/a | C2/3 classificação | — | Idem |
| `robustez_premissa_falsa_nota_credito` | 3 | parcial | Não (art. 5º) | C5 | C7 política | "Não há menção (...) em nenhum artigo da Resolução": generalização da ausência |
| `robustez_premissa_falsa_prazo` | 1 (rep. 1) | correta | Sim (art. 49) | C7 validador | — | "dez anos" citado para ser refutado e marcado como valor não verificado |
| `robustez_premissa_falsa_prazo` | 2 (reps. 2–3) | abstenção | Sim (art. 49) | C2 síntese | C7 validador | Nega os dez anos e não responde, com "cinco anos" no contexto; mesmo falso positivo |
| `robustez_linguagem_informal` | 3 | parcial | Não (art. 6º) | C5 | — | Tokenizador e radicalização para português formal |
| `robustez_pergunta_em_ingles` | 3 | incorreta | Não (art. 3º) | C5 | C2 síntese | Trecho sobre qualidade dos dados apresentado como "objetivos" |

### Modo sensibilidade (17 execuções)

| Caso | Exec. | Principal | Contributiva | Evidência resumida |
|---|---|---|---|---|
| `parecer_notificacao_multa`, `parecer_redigir_defesa`, `fora_codigo_python` | 9 | C2/3 classificação | — | Mesmos erros da produção, nas 3 repetições. Na repetição 2 da defesa, o modelo recusa, mas oferece um roteiro genérico de defesa: contenção só parcial pela política |
| `rc1_consentimento_adesao` (reps. 1 e 3), `rc1_revogacao_proposta` (rep. 1) | 3 | C2/3 classificação | — | Perguntas normativas ("É permitido...?", "pode propor...?") classificadas como parecer a 0,8; em produção, normativo nas 3 |
| `ausente_res_339_duplicata` (rep. 3), `ausente_circ_3978_pld` (rep. 2) | 2 | Critério | — | Respostas sem invenção que não nomeiam a norma na frase |
| `ausente_circ_3978_pld` (rep. 1), `robustez_premissa_falsa_prazo` (rep. 1) | 2 | C7 validador | — | "Se você puder fornecer mais informações (...) sobre a Circular nº 3.978/2020" contado como citação; "dez anos" refutado e marcado |
| `rc1_requisitos_consentimento` (rep. 2) | 1 | C5 | C2 síntese | O mesmo erro de remissão da produção. O aviso "artigo fora da norma" acertou por acaso: pareou o art. 10 com a IN 759, citada na mesma frase |

## 3. Divergência da repetição 1 (modo produção)

Em produção, 22 dos 66 casos deram respostas diferentes entre as
repetições, sempre com a repetição 1 diferente e as repetições 2 e 3
idênticas. A hipótese registrada desde a v4 era um efeito "da primeira vez
em que o Ollama processa o prompt" (`evidencias_empiricas.md`).

### 3.1. Ambiente e opções efetivas da chamada

Lidos do log do servidor (`%LOCALAPPDATA%\Ollama\server.log`), que cobre a
rodada do benchmark, e conferidos de novo no experimento:

| Item | Valor |
|---|---|
| Servidor Ollama | 0.33.2 (mesma versão do cliente), *backend* `llama-server` (llama.cpp) |
| Linha de comando do *backend* | `-c 4096 -np 1 -b 512 -ub 512 --flash-attn auto --context-shift --keep 4` |
| Contexto | 4.096 tokens, padrão escolhido pela VRAM (`OLLAMA_CONTEXT_LENGTH` não definido). Maior requisição da rodada: 3.111 tokens; `truncated = 1` em nenhuma |
| Paralelismo | `OLLAMA_NUM_PARALLEL=1` (um *slot*) e cache de prompts em RAM do `llama-server` |
| Opções enviadas pelo protótipo | classificação `{"temperature": 0, "seed": 42}`; síntese `{"temperature": 0.1, "seed": 42}` |
| Parâmetros do modelo (Modelfile) | só os *stop tokens* do Llama 3.1 |
| Amostragem efetiva (padrões do servidor) | `top_k = 40`, `top_p = 0.9`, `min_p = 0`, `repeat_penalty = 1.0`, `typical_p = 1`, `mirostat = 0` |
| Modelo | `llama3.1:latest`, ID `46e0c10c039e`, 8.0B, Q4_K_M; 33/33 camadas na GPU |
| Máquina | AMD Ryzen 5 5600X (6 núcleos/12 threads), 16 GB de RAM, NVIDIA GeForce RTX 4060 Ti 8 GB (driver 591.86), Windows 11 Home 10.0.26200 |

### 3.2. O que o log da rodada mostra

O `llama-server` registra, para cada requisição, quantos tokens do prompt
vieram do cache e quantos foi preciso calcular. Casando as 162 sínteses da
rodada de produção com o log (o número de tokens do prompt bate entre as
três repetições de cada caso):

| Situação | Casos |
|---|---|
| Repetições 2 e 3 com o prompt inteiro vindo do cache (só o último token recalculado) | 54 de 54 |
| Repetição 1 com o prompt calculado, total ou parcialmente | 53 de 54 |
| ... e com resposta diferente das repetições 2 e 3 | 22 de 53 |
| Repetição 1 também vinda do cache, sem divergência | 1 |

Na repetição 1, o servidor reaproveita só o prefixo comum com o prompt
anterior que tem em cache: 6 tokens (o cabeçalho do *template*) em 29 casos,
ou de 263 a 1.171 tokens (25 casos) quando a síntese anterior
compartilhava parte do texto. Nos três casos com divergência usados no
experimento abaixo, a repetição 1 da rodada partiu do token 6. O resto é calculado em lotes de 512 tokens a partir desse ponto.

### 3.3. Experimento

Quatro casos, pelo mesmo caminho do benchmark (`rodar_caso`, modo
produção): três com divergência na rodada (`rc1_prazo_revogacao`, que mudou
de conteúdo, `in759_vigencia` e `ausente_circ_3978_pld`) e um controle sem
divergência (`rc1_prazo_adesao`). Cada saída foi comparada, texto a texto,
com a da repetição 1 e com a das repetições 2 e 3 da rodada. 52 chamadas.

| Condição | O que muda | Resultado |
|---|---|---|
| E0 — reprodução | Servidor reiniciado uma vez; 3 repetições seguidas por caso | Reproduz a rodada em `prazo_revogacao` e `in759_vigencia` (rep. 1 = texto da rep. 1; reps. 2–3 = texto das reps. 2–3). Em `circ_3978`, a rep. 1 reaproveitou 263 tokens do cache (o início da política de síntese, comum à síntese anterior) e já saiu igual às reps. 2–3 |
| E1 — ordem alterada | Ordem inversa e intercalada (rep. 1 de todos, depois rep. 2...) | Quem foi calculado a partir do token 6 deu o texto da rep. 1. `in759_vigencia` perdeu o cache entre as rodadas e deu o texto da rep. 1 **na repetição 2**. `prazo_revogacao`, calculado a partir do token 263, deu um **terceiro texto**, repetido nas três execuções |
| E2 — aquecimento | Uma execução descartada antes das 3 | Calculado a partir do token 6, o aquecimento reproduz o texto da rep. 1 (`circ_3978` partiu do 263 e deu o das reps. 2–3); as 3 execuções medidas reproduzem o das reps. 2–3 (9 de 9 nos casos com divergência) |
| E3 — reinício entre chamadas | Servidor reiniciado antes de cada execução | 12 de 12 iguais à rep. 1 da rodada (todas calculadas a partir do token 6) |
| Controle | `rc1_prazo_adesao` | Mesmo texto em todas as 13 execuções, em todas as condições |

**Regra que explica as 52 chamadas, sem exceção**: com a mesma seed e a
mesma temperatura, o texto é função de **como o estado do prompt foi
calculado**: a partir de qual token e, portanto, com quais fronteiras de
lote. O mesmo cálculo, refeito, dá o mesmo texto. O cálculo a partir do
token 6 dá sempre o texto da repetição 1 da rodada. O reaproveitamento
integral de um estado calculado assim dá sempre o texto das repetições 2 e
3. Não é a ordem dos casos, nem o carregamento do modelo (em E0, o modelo já
estava carregado quando `in759_vigencia` divergiu), nem "a primeira vez" em
sentido literal: E1 produziu o texto da repetição 1 numa segunda execução.

**Mecanismo provável** (não isolado no código do `llama-server`): somas em
ponto flutuante na GPU não são associativas, e processar o prompt em lotes
diferentes, ou reavaliar só o último token sobre um cache, gera *logits*
ligeiramente diferentes. Com temperatura 0,1, a diferença basta para trocar
um token sorteado quando duas continuações estão próximas, e o resto do
texto segue a troca. A seed fixa é aplicada por requisição, por isso as
repetições 2 e 3, com estado idêntico, são idênticas. A classificação
(temperatura 0) não divergiu em nenhum caso.

### 3.4. Consequências

1. **Reprodutibilidade**: a afirmação "seed fixa dá reprodutibilidade a
   partir da segunda chamada" (v4) é verdadeira só para chamadas seguidas
   do mesmo prompt. A formulação exata é: o texto é reprodutível **dado o
   estado do cache de prompts do servidor**. Para reproduzir os textos da
   repetição 1, basta reiniciar o servidor antes de cada chamada (E3); para
   os das repetições 2 e 3, fazer uma chamada de aquecimento (E2).
2. **Fragilidade de um veredito**: em `rc1_prazo_revogacao`, dois dos três
   cálculos observados dão a resposta errada ("de forma imediata"). O
   "correta" das repetições 2 e 3 depende do cache. Nos outros 21 casos com
   divergência, a robustez do veredito a esse efeito não foi medida.
3. **Atribuição**: o erro da repetição 1 de `rc1_prazo_revogacao` fica com
   a Camada 2 (síntese): o trecho estava no contexto, e a margem entre os
   dois incisos é pequena o bastante para uma perturbação numérica mudar a
   escolha. O estado do servidor é a contributiva. Para a arquitetura, a
   proveniência da Camada 8 registra modelo, ID e parâmetros, mas não o
   estado do servidor de inferência, que também determina o texto.

Limites: 4 casos, uma máquina e uma versão do Ollama. Temperatura 0 na
síntese e desligar o cache de prompts não foram testados.

## 4. Camada de origem × execuções

### 4.1. Camada principal

| Camada de origem | Produção | % | Sensibilidade | Total | % |
|---|---|---|---|---|---|
| C5 recuperação (trecho ausente) | 36 | 54% | 1 | 37 | 44% |
| C2 síntese (trecho no contexto) | 18 | 27% | 0 | 18 | 21% |
| C2/3 classificação | 9 | 13% | 12 | 21 | 25% |
| Critério do benchmark | 3 | 4% | 2 | 5 | 6% |
| C7 validador (falso positivo) | 1 | 1% | 2 | 3 | 4% |
| C7 política de síntese | 0 | — | 0 | 0 | — |
| **Total** | **67** | | **17** | **84** | |

### 4.2. Camada contributiva

| Camada | Produção | Sensibilidade |
|---|---|---|
| C2 síntese | 12 | 1 |
| C7 política de síntese ("o trecho não contém" → "a norma não contém") | 6 | 0 |
| C5 recuperação (parte 1/2 do art. 6º) | 3 | 0 |
| C5 formato do trecho (cabeçalho no texto) | 3 | 0 |
| C7 validador | 2 | 0 |
| C2 inferência (cache do servidor) | 1 | 0 |

### 4.3. Modelo × arquitetura

No modo produção, sobre as 67 execuções com problema:

- **arquitetura: 37 (55%)**. Camada 5: 36. Camada 7, validador: 1;
- **modelo: 27 (40%)**. Síntese com o trecho no contexto: 18. Classificação: 9;
- **medição: 3 (4%)**.

A Camada 7 aparece pouco como principal, mas é contributiva em 8
execuções. Em 6 delas, a política de síntese não distingue "o contexto não
contém" de "a norma não contém". A classificação foi contada como erro do
modelo. A decisão de classificar com o LLM, sem regra de apoio, é da Camada
3: a categoria é mista por natureza.

No modo sensibilidade, a classificação domina (12 de 17). A temperatura
0,8 acrescenta erros no sentido inverso (normativo → parecer), que a
produção não tem.

### 4.4. Quanto seria corrigível sem trocar o modelo

É uma estimativa, sem intervenção testada (Fases 2 e 3), sobre as 67
execuções de produção:

| Faixa | Execuções | Base |
|---|---|---|
| Corrigível por mudança determinística | 4 (6%) | Validador: tratar valor citado para refutar (1). Critério: aceitar declaração de ausência sem a norma nomeada (3; corrige a medição, não o sistema) |
| Corrigível na arquitetura, com efeito provável | até 36 (54%); esperado ≈ 28 (42%) | Camada 5. Com o trecho relevante entre os 3, 79% das respostas auditadas são corretas (78 de 99): 0,79 × 36 ≈ 28. Supõe que a melhoria traga o trecho certo nesses casos, o que não foi medido |
| Possivelmente corrigível, não demonstrado | 9 (13%) | Classificação: os 3 pedidos têm marcas explícitas ("Vou ser multado?", "Redija a defesa", "Escreva uma função em Python"), tratáveis com exemplos no prompt ou regra de apoio. Risco de recusar perguntas normativas |
| Dependente do modelo | 18 (27%) | Síntese com o trecho no contexto: leitura errada de parágrafo, omissão de parágrafo, contradição. A cópia de cabeçalho (3) talvez ceda a pós-processamento, e a repetição 1 de `prazo_revogacao` (1) ao controle do estado do servidor |

Resumo: **sem trocar o modelo, entre 4 (6%) e cerca de 41 (61%)** das 67
execuções seriam corrigíveis (4 + 28 + 9), com teto de 49 (73%). Pelo menos
18 (27%) dependem da capacidade do modelo de ler o trecho que já recebeu.

## 5. Achados colaterais

1. **A métrica de recuperação superestima o acerto em dois casos.** O rótulo
   `"Art. 6º"` casa com o trecho "Art. 6º (parte 2/2)" no caminho feliz, que
   não traz o caput. O rótulo `seção 8` casa com uma seção que anuncia as
   modalidades sem listá-las, em `circ_portabilidade_modalidades`. Na tabela
   "A recuperação decide" (`evidencias_empiricas.md`, v5), as 3 abstenções
   de `circ_portabilidade_modalidades` estão na linha "trecho relevante
   entre os 3", mas são falhas de recuperação. A taxa de 79% não muda de
   sentido: ela fica um pouco subestimada.
2. **O validador da Camada 7 acertou um aviso pelo motivo errado**
   (sensibilidade, `rc1_requisitos_consentimento`, repetição 2). O aviso
   "artigo fora da norma" pareou o art. 10 com a IN 759, mencionada na mesma
   frase. O problema real, atribuição por remissão, continua fora do
   alcance de uma checagem lexical.
3. **A política de síntese contém, mas nem sempre por inteiro.** Na
   sensibilidade, uma das recusas de redigir a defesa veio com um roteiro
   genérico de defesa. Não é parecer sobre o caso, mas mostra que a
   contenção da Camada 7 sobre o erro da Camada 3 depende do sorteio.

## 6. Parágrafo sugerido para a Seção 3.6

> Para separar falhas do modelo de falhas da arquitetura, cada uma das 67
> execuções do modo produção com falha automática, aviso da Camada 7 ou
> veredito "incorreta", "parcial" ou "abstenção" foi atribuída a uma camada de origem, com base no
> contexto efetivamente entregue ao modelo. Em 54% delas, o trecho que
> responde à pergunta não estava entre os três recuperados (Camada 5). Em
> 27%, estava no contexto e foi lido de forma errada ou incompleta pelo
> modelo (Camada 2). Em 13%, a pergunta foi mal classificada (Camadas 2 e 3),
> e em 6% o problema era da medição ou de um falso positivo da Camada 7.
> Assim, a maior parte das falhas observadas é atribuível à arquitetura, em
> especial à recuperação, e não ao modelo. Estima-se que entre 6% e 61%
> dessas execuções seriam corrigíveis sem trocar o modelo, e que ao menos
> 27% dependem da capacidade do próprio modelo. A investigação mostrou ainda
> que, com seed e temperatura fixas, o texto gerado depende do estado do
> cache de prompts do servidor de inferência, fator que a proveniência
> registrada pela Camada 8 não captura.
