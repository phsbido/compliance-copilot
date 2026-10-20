# `src/layer1_interaction/cli.py` — Camada 1 (Interação com o Usuário)

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring do módulo (`cli.py:1-16`): a arquitetura conceitual
de Maia et al. atribui a esta camada a interface com o usuário; aspectos
multimodais estão fora de escopo da pesquisa (ver `README.md`), então a
implementação mínima natural é uma CLI de texto puro. É a única camada que
interage diretamente com `stdin`/`stdout` — todas as outras trabalham só com
dados em memória/disco.

## `COMANDOS_SAIDA` (`cli.py:19`)

```python
COMANDOS_SAIDA = {"sair", "exit", "quit"}
```
Conjunto (não lista) de palavras que encerram o loop — comparação é
case-insensitive (`pergunta.lower() in COMANDOS_SAIDA`, `cli.py:49`).
Escolha de 3 sinônimos (português + inglês) — **[INFERÊNCIA]** provavelmente
para tolerar o hábito do usuário vindo de outras ferramentas de linha de
comando (`exit`/`quit` são convenções comuns em REPLs), sem evidência
documentada específica.

## `_formatar_proveniencia(registro) -> str` (`cli.py:22-31`)

Função "privada" (prefixo `_`) — não exportada para uso fora do módulo.

- Parâmetro: `registro`, do tipo `RegistroInteracao | None` (Camada 8), embora
  a anotação de tipo não esteja escrita explicitamente na assinatura
  (`cli.py:22`) — **[FATO]**, é passado sem type hint, diferente do padrão
  usado em outros módulos do projeto (ex.: `orchestrator.py:58`), uma
  pequena inconsistência de estilo, não um erro funcional.
- Linha 23-24: se `registro` for `None` (nunca houve interação ainda),
  retorna string vazia — usado no primeiro turno antes de qualquer resposta
  ter sido dada, embora na prática `main()` só chama esta função depois de
  `orchestrator.responder()` já ter rodado, então `registro` nunca é `None`
  no fluxo real; é uma guarda defensiva para o caso de `ultimo_registro`
  ainda não ter sido setado.
- Linha 26-28: se há fontes normativas, monta uma linha `"[Fontes: título1,
  título2]"` juntando só os títulos (não as URLs) com vírgula.
- Linha 29-30: se `registro.aviso_citacao_nao_verificada` é `True`, adiciona
  uma segunda linha de alerta fixo.
- Linha 31: junta as linhas com `\n` — se nada foi adicionado, retorna string
  vazia (lista `linhas` vazia → `"\n".join([])` → `""`).

## `main() -> None` (`cli.py:34-62`)

1. `cli.py:35-36`: imprime cabeçalho e instrução de saída, usando
   `'/'.join(COMANDOS_SAIDA)` — **[FATO]** como `COMANDOS_SAIDA` é um `set`,
   a ordem de iteração não é garantida pela linguagem para todo tipo de
   objeto, mas para `str` em CPython moderno a ordem de um set pequeno tende
   a ser estável entre execuções do mesmo processo (baseado no hash),
   embora não seja uma garantia formal da linguagem. Não é um bug prático
   (é só texto de ajuda), mas é uma escolha um pouco frágil — uma lista
   ordenada teria comportamento determinístico garantido.
2. `cli.py:38`: `orchestrator = Orchestrator()` — instanciado **uma vez**,
   fora do loop. Ver `02_fluxo_execucao.md` para por que isso importa
   (acúmulo de memória de sessão).
3. `cli.py:40-58`: loop principal, detalhado em `02_fluxo_execucao.md`
   Seção 3.

## Efeitos colaterais

- I/O de terminal: `print()`/`input()` em várias linhas.
- Via `Orchestrator()`, dispara toda a cadeia de inicialização descrita em
  `02_fluxo_execucao.md` Seção 1 (inclusive carregar o corpus em memória e
  ler `.env`).
- Cada pergunta gera uma escrita em `logs/interacoes.jsonl` (indiretamente,
  via `Orchestrator.responder` → Camada 8).

## Exceções

Só `EOFError` e `KeyboardInterrupt` são tratadas (`cli.py:41-45`), e apenas
para permitir uma saída limpa. Qualquer outra exceção (ex.: erro de conexão
com o Ollama) não é capturada aqui — propaga e derruba o processo. Ver
`07_riscos.md`.

## Quem chama / quem é chamado

- **Chamado por**: `main.py:7,10` (único ponto de entrada real).
- **Chama**: `src.layer3_orchestration.orchestrator.Orchestrator` — nenhuma
  outra camada diretamente (a Camada 1 não sabe nada sobre RAG, memória,
  governança etc.; só fala com o `Orchestrator`).
