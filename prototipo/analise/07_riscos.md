# Riscos e Pontos de Atenção

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

Cada item abaixo foi verificado por leitura direta do código (não é
suposição). Marcado por severidade percebida para o propósito do projeto
(protótipo de pesquisa, não produto em produção).

---

## 0. [Bug confirmado — verificado na biblioteca instalada] `OLLAMA_HOST` do `.env` é ignorado por ordem de import

**Onde**: `src/layer2_llm_core/core.py:14-15` (`import ollama` antes de
`from src.config import settings`) vs. `venv/Lib/site-packages/ollama/__init__.py:44`
(`_client = Client()`, instanciado no import do pacote) e
`venv/Lib/site-packages/ollama/_client.py:113`
(`base_url=_parse_host(host or os.getenv('OLLAMA_HOST'))`).

**O que acontece**: a função `ollama.chat()` usada em `core.py:35` é a
função de módulo do pacote `ollama`, que delega a um cliente HTTP singleton
criado **uma única vez, no momento em que `import ollama` é executado**
(`ollama/__init__.py:44`). Esse cliente resolve o host do servidor lendo
`os.getenv('OLLAMA_HOST')` **naquele momento exato**
(`ollama/_client.py:113`). Em `core.py`, a ordem das duas primeiras linhas
é:
```python
import ollama                      # linha 14 — cliente Ollama já é criado aqui, lendo OLLAMA_HOST do os.environ ATUAL
from src.config import settings    # linha 15 — dispara config.py, que só ENTÃO chama load_dotenv() (config.py:15)
```
Como `load_dotenv()` só roda depois que `ollama` já foi importado (e o
cliente já construído), **um `OLLAMA_HOST` definido apenas no arquivo
`.env` nunca chega a influenciar o cliente realmente usado** — ele só teria
efeito se a variável já estivesse presente no ambiente do processo do
sistema operacional *antes* de `python main.py` iniciar (ex.: exportada no
shell), não apenas no arquivo `.env` do projeto.

**Por que passou despercebido**: o valor default documentado em
`.env.example:5` (`http://localhost:11434`) é **idêntico** ao default que a
própria biblioteca `ollama` usaria de qualquer forma na ausência de
`OLLAMA_HOST` (comportamento padrão do cliente HTTP da biblioteca) — então,
no fluxo de instalação documentado no `README.md` (rodar tudo localmente,
sem customizar o host), o bug nunca se manifesta. Só afetaria alguém que
tentasse apontar o protótipo para um servidor Ollama remoto ou em porta
diferente, alterando exclusivamente `.env`.

**Correção sugerida (não aplicada — fora do escopo desta análise)**:
inverter a ordem das duas linhas em `core.py` (importar `src.config`
primeiro, disparando `load_dotenv()`, e só depois `import ollama`), ou
chamar `load_dotenv()` explicitamente no início de `core.py` antes do
`import ollama`.

---

## 1. [Bug confirmado] Stopword "são" nunca é filtrada por `KnowledgeBase`

**Onde**: `src/layer5_knowledge/knowledge_base.py:21-26` (`_STOPWORDS`) e
`knowledge_base.py:37-45` (`_normalizar`, `_tokenizar`).

**O que acontece**: `_tokenizar` sempre chama `_normalizar(texto)` **antes**
de comparar cada palavra contra `_STOPWORDS` (`knowledge_base.py:44`:
`re.findall(r"\w+", _normalizar(texto))`). `_normalizar` remove acentos via
decomposição NFKD (`knowledge_base.py:37-40`). Isso significa que toda
palavra tokenizada já está sem acento no momento da comparação com
`_STOPWORDS`. Mas `_STOPWORDS` contém a entrada `"são"` **com** acento
(`knowledge_base.py:24`), e não contém a forma sem acento `"sao"`. Como o
token normalizado de qualquer ocorrência de "são" no texto é `"sao"` (não
`"são"`), a comparação `"sao" not in _STOPWORDS` é sempre verdadeira — a
entrada nunca casa.

**[Verificação adicional]**: as outras 3 entradas acentuadas de
`_STOPWORDS` (`"é"`, `"à"`, `"às"`) **não** têm o mesmo problema, por
coincidência: `"é"` normalizado vira `"e"`, que já está separadamente na
lista (linha 22, a conjunção "e"); `"à"` vira `"a"` (já presente); `"às"`
vira `"as"` (já presente). Só `"são"` não tem uma forma sem acento
equivalente já cadastrada — é o único caso realmente quebrado.

**Cenário de falha concreto**: qualquer pergunta contendo "são" (verbo
extremamente comum em português, ex.: "quais instituições **são**
obrigadas...") gera um token real `"sao"` que participa da pontuação de
relevância por sobreposição lexical (`knowledge_base.py:96-105`). Como
"são" também aparece com alta frequência em qualquer trecho normativo
(qualquer artigo que define algo tende a usar "são"), esse token infla
artificialmente a pontuação de trechos que não têm relação semântica real
com a pergunta, além dos tokens de conteúdo relevantes.

**Relevância**: contribui, em grau não quantificado, para o mesmo fenômeno
documentado empiricamente no cenário "Norma Ausente/Fronteira" do benchmark
(`docs/tabela_resultados_empiricos.csv`: 60% de aviso de citação não
verificada) — recuperação de trechos por sobreposição lexical incidental,
não semântica. Não é a única causa (a limitação de busca lexical sem
embeddings já é reconhecida e documentada como trade-off consciente, ver
`05_decisoes_de_design.md` item 10), mas é um bug concreto e corrigível
independente dessa limitação de desenho maior — bastaria adicionar `"sao"`
a `_STOPWORDS` (ou normalizar as entradas do próprio conjunto).

---

## 2. [Risco de acoplamento silencioso] Formato de string como contrato implícito entre 3 camadas

**Onde**: `src/layer4_tools/tools.py:33` produz `f"Fonte: {doc.titulo}
({doc.url_oficial})\n{doc.trecho}"`; `src/layer8_observability/observability.py:28`
(`_FONTE_REGEX`) e o parsing de `resposta_final` em
`observability.py:68` (`"Aviso:" in resposta_final`) dependem desse formato
exato de texto para extrair proveniência e detectar avisos.

**Cenário de falha concreto**: se alguém alterar a formatação em
`tools.py:33` (ex.: mudar `"Fonte: "` para `"Fonte oficial: "`, ou trocar a
ordem título/URL), `_FONTE_REGEX` para de casar, `_extrair_fontes` passa a
retornar `[]` silenciosamente — **sem exceção, sem aviso** — e todo registro
de proveniência gravado em `logs/interacoes.jsonl` a partir daí perde as
fontes normativas, mesmo que a busca da Camada 5 continue funcionando
normalmente. O mesmo vale se o prefixo `"Aviso:"` usado em
`governance.py:69,84` for alterado sem atualizar `observability.py:68`:
`aviso_citacao_nao_verificada` passaria a ser sempre `False`, mascarando
justamente o sinal mais importante da Camada 7 no log de auditoria.

**Por que é um risco real, não só teórico**: não há teste automatizado que
cubra a integração ponta a ponta desses três pontos (o teste mais próximo,
`run_check_observability.py`, usa strings de teste **hardcoded** que já
seguem o formato certo — `run_check_observability.py:19-23` — não deriva o
texto de teste chamando `tools.py` de verdade, então uma quebra de formato
em `tools.py` não seria pega por esse script).

---

## 3. [Ausência de tratamento de erro] Nenhuma captura de exceção fora do loop de input

**Onde**: confirmado por leitura completa de `src/layer1` a `layer8` — o
único `try/except` do projeto inteiro é `src/layer1_interaction/cli.py:41-45`,
e cobre só `EOFError`/`KeyboardInterrupt`.

**Cenário de falha concreto**: se o servidor Ollama não estiver rodando (ou
cair no meio de uma sessão), `ollama.chat(...)` em `core.py:35` levanta uma
exceção de conexão não capturada — o processo `python main.py` termina com
um traceback bruto no meio de uma pergunta do usuário, perdendo a memória de
sessão acumulada (não persistida, ver `layer6_memory.md`). Não há retry, não
há mensagem amigável, não há timeout configurado na chamada.

**Avaliação de severidade**: aceitável para um protótipo de pesquisa de uso
manual e supervisionado (o próprio pesquisador percebe o erro
imediatamente), mas seria inaceitável em qualquer contexto de uso não
supervisionado.

---

## 4. [Duplicação de lógica] `TIPOS_RECUSA` em `run_benchmark.py` duplica `_RECUSAS` de `orchestrator.py`

**Onde**: `run_benchmark.py:44` (`TIPOS_RECUSA = {"parecer_juridico",
"fora_de_escopo"}`) e `scripts/plot_benchmark.py:34` (mesma constante,
mesmo valor, terceira cópia) vs. `src/layer3_orchestration/orchestrator.py:36-39`
(`_RECUSAS`, fonte de verdade real).

**Cenário de falha concreto**: se um terceiro tipo de recusa for adicionado
a `_RECUSAS` no futuro (ex.: uma nova classificação `"dados_sensiveis"`),
`run_benchmark.py` e `plot_benchmark.py` continuariam calculando `recusou`/
`caminho` com a lista antiga de 2 tipos, produzindo estatísticas e gráficos
incorretos sem qualquer erro ou aviso — a nova classificação seria contada
como parte do "fluxo normativo completo" no gráfico de latência, mesmo
sendo, na verdade, uma recusa rápida sem síntese.

**Mitigação existente**: ambos os arquivos têm um comentário apontando
explicitamente para `orchestrator.py`/`_RECUSAS` como a fonte de verdade
(`run_benchmark.py:42-43`, `scripts/plot_benchmark.py:32-33`) — reduz o
risco de alguém alterar um lado sem perceber a duplicação, mas não elimina
o risco estruturalmente.

---

## 5. [Ineficiência não crítica hoje] Re-tokenização completa a cada busca

**Onde**: `src/layer5_knowledge/knowledge_base.py:96-105` (`buscar`) chama
`_tokenizar(doc.trecho)` para **todo** documento indexado, a **cada**
chamada de `buscar` — não há cache dos tokens de cada trecho calculado uma
vez no carregamento.

**Avaliação**: com o corpus atual (67 documentos/trechos, ver
`docs/estado_atual.md:169`), o custo é imperceptível. Escalaria mal (O(n)
tokenizações repetidas por busca, para um corpus de milhares de trechos) se
o corpus crescesse significativamente — o que é um cenário plausível dado
que só 2 das 4 normas planejadas estão indexadas hoje
(`data/normativos/PENDENTES.md`).

---

## 6. [Arquivo órfão] `_openfinance_limpo.md` na raiz do projeto

**Onde**: `_openfinance_limpo.md` (2.780 linhas), na raiz de `prototipo/`,
**fora** de `data/normativos/`.

**[FATO — confirmado por busca]**: nenhum arquivo `.py` do projeto referencia
esse nome (busca por `"openfinance_limpo"` em todo o repositório não
encontrou nenhuma ocorrência fora do próprio arquivo). Não está listado no
`.gitignore`, então seria commitado se adicionado ao git (aparece como
untracked no `git status` no início desta sessão).

**Conteúdo**: ao inspecionar, é o texto integral extraído (aparentemente
"limpo" manualmente, dado o nome) da Instrução Normativa BCB nº 759/2026 —
o mesmo normativo cujo PDF bruto (`normativoOpenFinance.pdf`) foi usado para
testar o pipeline `ingest_normativos.py` (`docs/decisoes_arquitetura.md:511-536`).

**[INFERÊNCIA]**: provavelmente um artefato intermediário de uma etapa
manual de preparação/limpeza de texto, criado antes ou em paralelo à
construção do pipeline automatizado, e nunca removido depois. Não afeta o
comportamento do sistema (não é lido por nada), mas é ruído no repositório —
um leitor futuro do código pode razoavelmente se perguntar se é usado em
algum lugar (como eu me perguntei, até confirmar que não é).

---

## 7. [Inconsistência de proveniência dos dados] `data/normativos/circular_4015_2020.md` difere do seu "bronze"

**Onde**: comparação direta (`diff`) entre `data/normativos/circular_4015_2020.md`
(fonte curada) e `data/normativos/1_bronze_raw/circular_4015_2020.md`
(gerado por `etapa_bronze()`, que deveria ser cópia **verbatim** segundo o
próprio código — `ingest_normativos.py:239-246`).

**[FATO]**: os dois arquivos diferem (confirmado por `diff -q`, que reporta
diferença de conteúdo).

**[INFERÊNCIA]**: como `etapa_bronze()` faz cópia byte-a-byte
(`destino.write_text(conteudo, encoding="utf-8")`, sem transformação — linha
245), a única explicação é que o arquivo de origem
(`data/normativos/circular_4015_2020.md`) foi editado **depois** da última
vez que o pipeline rodou e gerou o Bronze — ou seja, `1_bronze_raw/` está
desatualizado em relação à fonte atual. Isso não afeta o runtime (Bronze não
é lido por `KnowledgeBase`), mas é um sinal de que os artefatos gerados pelo
pipeline ilustrativo não são regenerados automaticamente a cada mudança do
corpus curado — quem olhar `1_bronze_raw/` esperando ver o estado atual do
corpus pode ser enganado. Não investiguei a diferença exata de conteúdo
(fora do escopo desta análise de código), então não posso afirmar se é uma
mudança de conteúdo substantiva ou só de formatação/espaçamento.

---

## 8. [Robustez de teste] `assert` é removido em modo otimizado do Python

**Onde**: `run_check_memory.py:27-28`, `run_check_governance.py:31,38-42,46-51`,
`run_check_observability.py` (múltiplos).

**Risco teórico**: se qualquer um desses scripts for executado com a flag
`python -O` (modo otimizado), todos os `assert` são removidos do bytecode e
os scripts "passam" sem checar nada, imprimindo as mesmas mensagens de
sucesso mesmo que o comportamento esteja quebrado. Não há evidência de que
isso seja um cenário real de uso do projeto (o `README.md` sempre instrui
`python script.py`, nunca `-O`), mas é uma fragilidade inerente a usar
`assert` como único mecanismo de verificação em vez de um framework de teste
dedicado (`pytest`, que levanta `AssertionError` de forma independente do
modo de otimização do interpretador).

---

## 9. [Ausência de timeout] Chamada ao LLM sem limite de tempo

**Onde**: `src/layer2_llm_core/core.py:35` — `ollama.chat(model=self.model,
messages=messages)`, sem parâmetro de timeout.

**Cenário de falha concreto**: se o modelo local travar (ex.: recursos
insuficientes de RAM/GPU fazendo *paging* excessivo — risco mencionado
explicitamente no próprio `README.md:55-57` sobre modelos maiores como
`llama3.1:70b`), a chamada bloqueia indefinidamente, sem nenhum feedback
visual na CLI (`cli.py` não imprime nenhum indicador de "processando..."
antes de chamar `orchestrator.responder`) — do ponto de vista do usuário, o
programa simplesmente para de responder, sem diferenciar "processando" de
"travado".

---

## 10. Limitações já conhecidas e conscientemente aceitas (não bugs, mas riscos residuais documentados)

Estes já estão detalhados em `05_decisoes_de_design.md`, listados aqui só
para completude do inventário de riscos:

- `validar_citacao` só valida contra o contexto do turno atual, não contra a
  memória de turnos anteriores — pode gerar aviso "tecnicamente correto" mas
  lido como falso positivo (`docs/decisoes_arquitetura.md:337-348`).
- Busca lexical sem embeddings recupera trechos irrelevantes por
  coincidência de palavras — taxa de 60% de aviso no cenário de fronteira
  (`docs/tabela_resultados_empiricos.csv`).
- Corpus real cobre só 2 de 4 normas planejadas
  (`data/normativos/PENDENTES.md`).
- `_interpretar` tem um fallback conservador para `"normativo"` se a
  classificação do LLM vier malformada (`orchestrator.py:91-92`) — não há
  garantia de que uma pergunta ambígua nunca escorregue por esse caminho
  para o fluxo normativo completo (mitigado parcialmente pela instrução
  anti-parecer-jurídico dentro do próprio prompt de síntese,
  `orchestrator.py:99-104`, mas é uma segunda linha de defesa mais fraca que
  a recusa direta).

## O que **não** encontrei

Não identifiquei nenhum problema de segurança convencional (injeção,
credenciais expostas, path traversal) — o sistema não expõe rede (exceto
para `localhost`), não recebe input de fontes não confiáveis além do próprio
usuário via terminal, e não faz nenhuma operação de escrita fora dos
diretórios `logs/` e (só no pipeline ilustrativo) `data/normativos/1_bronze_raw|2_silver_cleaned|3_gold_indexed/`.
Coerente com a natureza do projeto (protótipo de pesquisa local, sem
superfície de ataque de rede real).
