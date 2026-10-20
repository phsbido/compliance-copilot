# `src/layer3_orchestration/orchestrator.py` — Camada 3 (Orquestração e Fluxo de Trabalho)

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`orchestrator.py:1-19`): coordenar as etapas do
fluxo de resposta — interpretar → buscar normativo → sintetizar → validar
citação. É o único módulo que conhece e importa de todas as outras 7
camadas (`orchestrator.py:22-30`) — o "hub" central do sistema.

## Constantes de módulo

- `TIPOS_INTERPRETACAO = {"normativo", "parecer_juridico", "fora_de_escopo"}`
  (`orchestrator.py:32`) — os 3 valores válidos que `_interpretar` pode
  produzir.
- `_RECUSAS` (`orchestrator.py:36-39`) — dicionário `tipo -> função de
  recusa`:
  ```python
  _RECUSAS = {
      "parecer_juridico": recusar_parecer_juridico,
      "fora_de_escopo": recusar_fora_de_escopo,
  }
  ```
  **[EVIDÊNCIA]** Este dicionário não existiu desde o início — foi
  introduzido em 2026-08-15 para generalizar um mecanismo que originalmente
  só existia para `parecer_juridico`, depois que um teste revelou que
  perguntas `fora_de_escopo` seguiam o fluxo normal sem sentido
  (`docs/decisoes_arquitetura.md:129-144`, `docs/evidencias_empiricas.md:179-227`).
  É o exemplo mais claro do projeto de uma correção de design documentada
  com "antes" e "depois" comprováveis (ver `tests/casos_teste.md`, Caso 4).

## `@dataclass Interpretacao` (`orchestrator.py:42-45`)

Estrutura de dados simples: `pergunta_original: str`, `tipo: str`. Existe só
para dar nome/tipo ao valor de retorno de `_interpretar`, em vez de retornar
uma tupla solta — melhora legibilidade em troca de uma classe extra
minúscula.

## `class Orchestrator`

### `__init__(self, llm=None, memoria=None)` (`orchestrator.py:49-56`)

- Injeção de dependência opcional para `LLMCore` e `Memoria` — mesmo padrão
  de `LLMCore.__init__` (ver `layer2_llm_core.md`). Permite testes/scripts
  passarem instâncias customizadas sem tocar em `.env` nem esperar 5
  interações de warm-up de memória.
- `self.ultimo_registro: RegistroInteracao | None = None`
  (`orchestrator.py:56`) — comentário no código explica exatamente por que
  existe (`orchestrator.py:52-55`): expor o registro de proveniência da
  última chamada a `responder()` para camadas superiores (Camada 1) sem
  precisar (a) reabrir o log em disco, nem (b) mudar o tipo de retorno de
  `responder()`, que já é consumido como `str` puro por vários scripts
  (`run_check_orchestration.py`, `main.py` indiretamente via `cli.py`).
  **[EVIDÊNCIA]** Esta é uma decisão de projeto explicitamente registrada em
  `docs/decisoes_arquitetura.md:61-67`, incluindo o trade-off considerado
  (mudar a assinatura de `responder()` quebraria consumidores existentes).

### `responder(self, pergunta: str) -> str` (`orchestrator.py:58-79`)

Método público único da classe — toda a lógica de orquestração passa por
aqui. Detalhamento passo a passo em `02_fluxo_execucao.md` Seção 4. Pontos
que merecem atenção linha a linha:

- `orchestrator.py:61`: `if interpretacao.tipo in _RECUSAS:` — despacho por
  dicionário em vez de `if/elif` encadeado; adicionar um novo tipo de recusa
  no futuro é uma linha em `_RECUSAS`, não uma nova branch aqui.
- `orchestrator.py:69-73` (comentário): explica por que a memória guarda a
  resposta **sem** os avisos de `_validar_citacao` — **[EVIDÊNCIA]**
  documentado como correção de um bug real observado em teste (disclaimer
  ecoado pelo modelo em turnos seguintes), com remissão a
  `docs/evidencias_empiricas.md`. Ver `05_decisoes_de_design.md`.
- `orchestrator.py:75-78`: a chamada final a `registrar_interacao` recebe
  `resposta_validada` (com avisos) e `normativo` (o contexto bruto usado) —
  diferente do ramo de recusa, onde `registrar_interacao` é chamado sem o
  parâmetro `normativo` (que tem default `""` em
  `observability.py:60`), resultando em `fontes_normativas: []` no log.

### `_interpretar(self, pergunta: str) -> Interpretacao` (`orchestrator.py:81-93`)

- Monta um `system prompt` que restringe a resposta do LLM a exatamente uma
  de 3 palavras (`orchestrator.py:82-89`) — técnica de *prompt engineering*
  para transformar geração de texto livre em uma pseudo-classificação.
- `orchestrator.py:90`: `.strip().lower()` normaliza a resposta do modelo
  (o LLM pode retornar com espaços, maiúsculas, pontuação incidental).
- `orchestrator.py:91-92`: **fallback conservador** — se a resposta não
  bater exatamente com um dos 3 valores esperados (ex.: o modelo respondeu
  uma frase completa em vez de uma palavra), assume `"normativo"`. Comentário
  inline chama isso de "fallback conservador" — **[INFERÊNCIA]** "conservador"
  aqui provavelmente significa "no pior caso, o sistema tenta responder com
  base em normativo real e ainda passa pela validação de citação da Camada
  7", em vez de arriscar recusar uma pergunta legítima ou, pior, tratar como
  fora de escopo algo que não é. Não há teste automatizado que force esse
  ramo (não localizei nenhum caso de teste que provoque uma resposta de
  classificação malformada do LLM).

### `_buscar_normativo(self, interpretacao) -> str` (`orchestrator.py:95-96`)

Wrapper de uma linha sobre `buscar_normativo` (Camada 4) — existe como
método próprio (em vez de chamar a função direto em `responder`)
**[INFERÊNCIA]** para manter a interface interna consistente com os outros
3 métodos privados (`_interpretar`, `_sintetizar_resposta`,
`_validar_citacao`), todos seguindo o mesmo padrão de "um método por etapa
do fluxo declarado no docstring do módulo" (`orchestrator.py:7-8`).

### `_sintetizar_resposta(self, pergunta, normativo) -> str` (`orchestrator.py:98-112`)

- `system` prompt instrui: usar o contexto normativo fornecido, nunca dar
  parecer jurídico definitivo, sempre recomendar validação humana
  (`orchestrator.py:99-104`) — a segunda linha de defesa contra parecer
  jurídico (a primeira é a classificação + recusa; esta é uma instrução
  defensiva mesmo dentro do fluxo normativo, para o caso de uma pergunta
  ambígua ter sido classificada como `normativo`).
- `orchestrator.py:105-111`: monta o prompt final concatenando, nesta ordem:
  histórico da sessão (se houver) → contexto normativo → pergunta. A ordem
  importa para como o modelo pondera as informações — não há evidência
  documentada de que essa ordem específica foi testada contra alternativas
  (ex.: pergunta primeiro), é uma decisão de implementação não discutida
  explicitamente nos docs.

### `_validar_citacao(self, resposta, normativo) -> str` (`orchestrator.py:114-115`)

Wrapper de uma linha sobre `validar_citacao` (Camada 7).

## Quem chama / quem é chamado

- **Chamado por**: `src/layer1_interaction/cli.py:38,53` e
  `run_benchmark.py:33,53`, além de todos os `run_check_orchestration.py`.
- **Chama**: `LLMCore` (Camada 2), `buscar_normativo` (Camada 4), `Memoria`
  (Camada 6), `recusar_fora_de_escopo`/`recusar_parecer_juridico`/
  `validar_citacao` (Camada 7), `registrar_interacao` (Camada 8).
