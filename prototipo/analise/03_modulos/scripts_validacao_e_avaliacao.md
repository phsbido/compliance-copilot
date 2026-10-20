# Scripts auxiliares — validação por camada, benchmark e gráficos

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

> **Nota (2026-10-02, estado atual dos testes):** este arquivo é parte do retrato de 2026-09-23 (ver `00_visao_geral.md`). Desde então: há testes automatizados com `unittest`, sem LLM (`tests/test_governanca.py`, `tests/test_ingestao.py` e `tests/test_benchmark.py`; `python -m unittest discover -s tests`), e o benchmark passou à **bateria v5**: 66 casos em cinco grupos (normativo no corpus, norma ausente, parecer jurídico, fora de escopo, robustez), 3 repetições por caso, nos modos `producao` e `sensibilidade`, com critério de sucesso por caso, Acerto@3/Recall@3/MRR da Camada 5 sobre rótulos de recuperação, cobertura de termos esperados, IC 95% de Wilson por grupo e matriz de confusão da Camada 3. Descrição atual: docstring de `run_benchmark.py`, `README.md` (Seção 6), `docs/apendice_casos_teste.md` e `docs/decisoes_arquitetura.md` ("Benchmark v5").

Este arquivo cobre os 10 scripts que não fazem parte do pacote `src/`: os 7
`run_check_*.py` + `run_check.py`, `run_benchmark.py` e
`scripts/plot_benchmark.py`. Todos são pontos de entrada independentes
(`if __name__ == "__main__":`), nenhum é importado por outro módulo do
projeto.

## Padrão comum aos 7 `run_check_*`

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:103-105`: "a validação do fluxo
via `run_check_orchestration.py` segue o mesmo padrão do `run_check.py` da
Camada 2, para permitir uma verificação rápida e isolada por camada." Todos
seguem a mesma receita: importam só a camada-alvo, exercitam com dado de
teste fixo (às vezes derivado diretamente de um achado documentado em
`docs/evidencias_empiricas.md`), imprimem o resultado em texto, e terminam
com uma linha de confirmação. Alguns (`memory`, `governance`,
`observability`) usam `assert` para checagem automática; outros
(`run_check.py`, `run_check_tools.py`, `run_check_knowledge.py`,
`run_check_orchestration.py`) são só inspeção visual manual — não há
`assert` neles, e nenhum framework de teste (`pytest`, `unittest`) é usado
em lugar nenhum do projeto.

| Script | Linhas | Camada testada | Tem `assert`? | Depende do Ollama? |
|---|---:|---|:---:|:---:|
| `run_check.py` (`run_check.py:15-26`) | 26 | 2 (Núcleo LLM) | Não | Sim |
| `run_check_tools.py` (`run_check_tools.py:14-23`) | 23 | 4 (Ferramentas) | Não | Sim (via Camada 5→ nenhuma chamada ao LLM na verdade — só busca lexical, mas a cadeia de import ainda carrega o corpus) |
| `run_check_knowledge.py` (`run_check_knowledge.py:13-33`) | 33 | 5 (RAG) | Não | Não (busca lexical pura) |
| `run_check_memory.py` (`run_check_memory.py:13-30`) | 30 | 6 (Memória) | Sim, 2 asserts (`run_check_memory.py:27-28`) | Não |
| `run_check_governance.py` (`run_check_governance.py:26-53`) | 53 | 7 (Governança) | Sim, 4 asserts (`run_check_governance.py:31,38-42,46-51` — ver nota abaixo) | Não |
| `run_check_observability.py` (`run_check_observability.py:25-78`) | 78 | 8 (Observabilidade) | Sim, 8+ asserts | Não |
| `run_check_orchestration.py` (`run_check_orchestration.py:19-42`) | 42 | 3 (fluxo completo, todas as camadas ligadas) | Não | Sim |

### Nota sobre `run_check_governance.py` — teste de falso positivo (`run_check_governance.py:39-42`)

```python
assert "não consta no trecho normativo" not in resultado2, (
    "falso positivo: o ponto final da frase não deve ser confundido com "
    "parte do número da norma"
)
```
**[EVIDÊNCIA]** Este assert, com sua mensagem de erro explícita, documenta um
cuidado deliberado: a frase de teste termina em "...Resolução Conjunta nº
1." (com ponto final) — o autor verificou que a regex de norma
(`_NORMA_REGEX`) não captura o ponto final como parte do número "1" (o que
geraria uma citação "nº 1." diferente de "nº 1" e um falso positivo de
citação não verificada). É evidência de teste orientado a um caso de borda
específico da implementação de regex, não um teste genérico.

## `run_check.py` (`run_check.py:1-27`)

Script mais simples do projeto — **primeiro** a ser escrito, segundo seu
próprio docstring (`run_check.py:2-7`: "Estágio 1 do plano de construção" —
confirma a ordem de construção incremental documentada em
`docs/estado_atual.md:15-16`). Faz uma única chamada a `LLMCore.generate`
com uma pergunta fixa sobre Open Finance, sem nenhuma outra camada — existe
só para confirmar que a base (Python + Ollama + modelo local) funciona.

## `run_check_orchestration.py` (`run_check_orchestration.py:1-43`)

O único `run_check_*` que exercita o fluxo **completo**, com 3 perguntas na
mesma sessão (mesmo `Orchestrator`, então a Camada 6 acumula histórico entre
elas): (1) pergunta normativa normal, (2) pergunta de acompanhamento que só
faz sentido com o histórico do turno 1, (3) pedido de parecer jurídico, que
deve ser recusado. **[EVIDÊNCIA]** Essas mesmas 3 perguntas, com as mesmas
respostas reais obtidas, estão documentadas nos Casos 1-3 de
`tests/casos_teste.md` — este script é literalmente o mecanismo de
reprodução desses casos qualitativos.

## `run_benchmark.py` (`run_benchmark.py:1-141`)

### Responsabilidade

**[EVIDÊNCIA]** Docstring (`run_benchmark.py:1-25`): avaliação quantitativa
complementar aos 4 casos qualitativos, medindo latência e capturando o que
as Camadas 7/8 registraram para cada execução. Ver
`docs/decisoes_arquitetura.md:402-459` ("Benchmark Empírico") para a
justificativa completa da decisão de projeto.

### Constantes

- `N_REPETICOES = 5` (`run_benchmark.py:40`) — cada um dos 4 cenários de
  `tests/casos_teste.json` roda 5 vezes, total 20 execuções.
- `TIPOS_RECUSA = {"parecer_juridico", "fora_de_escopo"}`
  (`run_benchmark.py:44`) — duplicação **intencional** da mesma lógica que
  vive em `orchestrator.py:36-39` (`_RECUSAS`), mas como um `set` de chaves,
  não um dicionário de funções — o comentário (`run_benchmark.py:42-43`)
  remete explicitamente a `orchestrator.py` como a fonte de verdade dessa
  classificação. **[INFERÊNCIA]** Não é importado diretamente de lá
  (poderia, por exemplo, importar `_RECUSAS.keys()`) — provavelmente porque
  `_RECUSAS` é nomeado com underscore (convenção de "privado ao módulo"), e
  duplicar um `set` de 2 strings foi julgado mais simples que expor a
  constante publicamente só para este uso. É uma duplicação pequena, mas é
  duplicação: se um terceiro tipo de recusa for adicionado a
  `orchestrator.py` no futuro, este `set` precisaria ser atualizado
  manualmente em paralelo (ver `07_riscos.md`).

### `carregar_casos() -> list[dict]` (`run_benchmark.py:47-49`)

Lê e faz parse de `tests/casos_teste.json`, retorna a lista sob a chave
`"casos"`.

### `rodar_caso(caso: dict, repeticao: int) -> dict` (`run_benchmark.py:52-75`)

**[FATO]** `orchestrator = Orchestrator()` é instanciado **dentro** desta
função (`run_benchmark.py:53`), não reaproveitado entre chamadas —
diferente de `cli.py`, onde há **um** `Orchestrator` por sessão inteira.
**[EVIDÊNCIA]** Isso é deliberado e documentado no docstring do módulo
(`run_benchmark.py:12-16`): cada repetição usa uma instância nova (memória
de sessão vazia), para isolar o comportamento por pergunta, não medir efeito
de histórico de conversa (já exercitado separadamente no Caso 2 de
`tests/casos_teste.md`).

- `time.perf_counter()` antes/depois da chamada a `orchestrator.responder`
  mede a latência em milissegundos (`run_benchmark.py:55-57`) —
  `perf_counter` é a escolha correta para medir duração (relógio monotônico,
  não afetado por ajustes de hora do sistema), em vez de `time.time()`.
- Lê `orchestrator.ultimo_registro` (Camada 8) para obter `tipo_obtido`
  (`run_benchmark.py:59-60`) — reaproveita a mesma interface pública já
  exposta para a Camada 1 (ver `docs/decisoes_arquitetura.md:433-436` para a
  justificativa de não reabrir `logs/interacoes.jsonl` do disco).
- Monta um dicionário de resultado com todos os campos relevantes para
  análise: classificação obtida vs. esperada, se recusou, se houve aviso de
  citação, número de fontes, latência, timestamp, e a resposta completa.

### `salvar_resultados_json` / `exportar_tabela_csv` (`run_benchmark.py:78-113`)

- `salvar_resultados_json` grava a lista completa de 20 resultados brutos em
  `logs/resultados_benchmark.json` (dado bruto, git-ignorado).
- `exportar_tabela_csv` usa `pandas.DataFrame.groupby(["caso_id",
  "categoria", "tipo_esperado"], sort=False).agg(...)`
  (`run_benchmark.py:87-97`) para agregar por cenário: contagem de execuções,
  taxa de classificação correta, taxa de recusa, taxa de aviso de citação
  não verificada, e estatísticas de latência (média, mediana, desvio padrão,
  mín, máx). `sort=False` preserva a ordem original dos cenários (a ordem em
  que aparecem em `tests/casos_teste.json`), em vez da reordenação
  alfabética padrão do `groupby`. Grava em
  `docs/tabela_resultados_empiricos.csv` — este arquivo **é** versionado no
  git (ao contrário do JSON bruto), porque é o artefato citável diretamente
  na monografia.

### Bloco principal (`run_benchmark.py:116-141`)

Loop duplo (casos × repetições), imprime progresso incremental linha a
linha durante a execução (útil porque cada execução do fluxo normativo leva
~11 segundos — ver a análise de latência abaixo), depois salva os dois
artefatos e imprime a tabela agregada final.

### Resultado real já obtido (evidência empírica coletada)

**[EVIDÊNCIA — dado real, não hipotético]** Lido diretamente de
`docs/tabela_resultados_empiricos.csv`:

| Cenário | Taxa classificação correta | Taxa de recusa | Taxa de aviso citação não verificada | Latência média |
|---|---:|---:|---:|---:|
| Caminho Feliz / RAG BACEN | 100% | 0% | 0% | 11.105 ms |
| Norma Ausente / Fronteira | 100% | 0% | **60%** | 11.125 ms (±5.439 ms) |
| Solicitação de Parecer / Governança | 100% | 100% | 0% | 173 ms |
| Fora de Escopo / Governança | 100% | 100% | 0% | 122 ms |

## `scripts/plot_benchmark.py` (`scripts/plot_benchmark.py:1-225`)

### Responsabilidade

Gera 2 gráficos de publicação (300 DPI, estilo `seaborn` "whitegrid") a
partir de `docs/tabela_resultados_empiricos.csv` — não depende do Ollama,
roda offline após o benchmark (`scripts/plot_benchmark.py:18-19`).

### `_quebrar_rotulo` / `_configurar_estilo` (`scripts/plot_benchmark.py:44-60`)

`_quebrar_rotulo` usa `textwrap.wrap` para quebrar nomes longos de cenário
em múltiplas linhas nos eixos dos gráficos (`LARGURA_QUEBRA_ROTULO = 18`
caracteres). `_configurar_estilo` centraliza `rcParams` do matplotlib —
tamanhos de fonte, DPI de figura e de exportação, `bbox="tight"` para
recortar margens vazias.

### `grafico_latencia(df) -> Path` (`scripts/plot_benchmark.py:72-135`)

Gráfico de barras com barra de erro (`yerr=`, desvio padrão), cores
diferentes por caminho (recusa vs. fluxo normativo), anotação numérica em
cima de cada barra, e uma anotação central calculando dinamicamente o fator
de aceleração:
```python
fator = media_normativo / media_recusa
```
(`scripts/plot_benchmark.py:101`) — **[FATO]** este número não é hardcoded,
é recalculado a partir dos dados do CSV toda vez que o script roda; se o
benchmark for reexecutado com resultados diferentes, o gráfico refletirá o
novo fator automaticamente.

### `grafico_taxas_governanca(df) -> Path` (`scripts/plot_benchmark.py:138-210`)

Gráfico de barras agrupadas (taxa de recusa vs. taxa de aviso de citação não
verificada, por cenário), com uma anotação de destaque específica
(`scripts/plot_benchmark.py:177-195`) apontando com uma seta para o cenário
`"norma_ausente_fronteira"` — localizado dinamicamente por
`df.index[df["caso_id"] == "norma_ausente_fronteira"]`, não por posição fixa
no eixo X, então continua correto mesmo se a ordem dos cenários no CSV
mudar.

### Cores fixas (`scripts/plot_benchmark.py:36-39`)

```python
COR_RECUSA = "#4C72B0"
COR_NORMATIVO = "#DD8452"
COR_TAXA_RECUSA = "#4C72B0"
COR_TAXA_AVISO = "#C44E52"
```
Paleta de cores categóricas do seaborn ("deep") escolhida a dedo em vez de
gerada automaticamente — garante as mesmas cores entre os dois gráficos
(azul = recusa/Camada 7 em ambos).

## Quem chama / quem é chamado (todos os scripts desta seção)

- **Chamados por**: ninguém — todos são pontos de entrada de linha de
  comando.
- **Chamam**: a camada específica que testam (`run_check_*`), ou
  `Orchestrator` + `pandas` (`run_benchmark.py`), ou só o CSV de saída do
  benchmark + `matplotlib`/`seaborn` (`plot_benchmark.py` — não importa
  nenhum módulo `src/`).
