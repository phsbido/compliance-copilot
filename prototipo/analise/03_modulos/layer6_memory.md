# `src/layer6_memory/memory.py` — Camada 6 (Contexto e Memória)

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`memory.py:1-10`): manter o estado da conversa em
andamento para permitir considerar interações anteriores da mesma sessão.
Decisão de projeto explícita: memória **em processo apenas**, sem persistir
em disco entre execuções, limitada às últimas N interações — contraste
deliberado com a Camada 8 (Observabilidade), onde persistência é o próprio
propósito (`docs/decisoes_arquitetura.md:383-386`).

## `@dataclass Interacao` (`memory.py:15-18`)

`pergunta: str`, `resposta: str` — par simples, sem timestamp nem
identificador (diferente de `RegistroInteracao` da Camada 8, que tem
timestamp). **[INFERÊNCIA]** Faz sentido: a Camada 6 existe só para dar
contexto textual ao próximo prompt, não para auditoria — não precisa de
metadados extras.

## `class Memoria`

### `__init__(self, limite: int = 5)` (`memory.py:22-24`)

`self.limite = limite`, `self._interacoes: list[Interacao] = []`. O valor
default `5` é o mesmo mencionado em `docs/decisoes_arquitetura.md:253`
("padrão N=5") e no diagrama de arquitetura (`docs/diagrama_arquitetura.md:52`,
"buffer das últimas 5 interações"). **[EVIDÊNCIA]** A motivação registrada
é: suficiente para o caso de uso de perguntas de acompanhamento em uma
sessão CLI, sem complexidade adicional (sumarização de histórico longo,
banco de dados) sem caso de uso real que a justifique
(`docs/decisoes_arquitetura.md:262-269`).

### `adicionar(self, pergunta: str, resposta: str) -> None` (`memory.py:26-29`)

```python
self._interacoes.append(Interacao(pergunta, resposta))
if len(self._interacoes) > self.limite:
    self._interacoes = self._interacoes[-self.limite:]
```
Buffer circular implementado da forma mais simples possível: sempre
adiciona, depois trunca se excedeu o limite, reatribuindo a lista inteira
(fatiamento `[-self.limite:]`) em vez de usar uma estrutura mais eficiente
como `collections.deque(maxlen=...)`. **[INFERÊNCIA]** Para N=5 e uma sessão
de CLI interativa (não milhares de interações por segundo), a diferença de
performance entre essa abordagem e `deque` é irrelevante — é uma escolha
legítima de simplicidade sobre eficiência marginal, coerente com o
princípio geral do projeto (ver `05_decisoes_de_design.md`) de evitar
otimização/abstração sem necessidade concreta.

### `contexto_formatado(self) -> str` (`memory.py:31-38`)

```python
if not self._interacoes:
    return ""
blocos = [
    f"Pergunta anterior: {i.pergunta}\nResposta anterior: {i.resposta}"
    for i in self._interacoes
]
return "\n\n".join(blocos)
```
Serializa o histórico inteiro (até `limite` interações) em texto plano, um
bloco por interação, rótulos fixos em português ("Pergunta anterior"/
"Resposta anterior"). Esse texto é injetado diretamente no prompt de síntese
pela Camada 3 (`orchestrator.py:105-108`). **[FATO]** Não há nenhum limite de
tamanho de caractere/token aqui — se as respostas anteriores forem longas, o
prompt final pode crescer sem controle (mitigado só indiretamente pelo
limite de 5 *interações*, não de tamanho de texto).

## Ambiguidade documentada

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:271-277`: a arquitetura de
Maia et al. não define se a memória deveria influenciar também a etapa de
interpretação (`_interpretar`), não só a síntese. Decisão de escopo: só a
síntese usa o histórico — a classificação de cada pergunta é feita sem
contexto de turnos anteriores. Persistência entre sessões foi deixada
explicitamente fora de escopo.

## Quem chama / quem é chamado

- **Chamado por**: `src/layer3_orchestration/orchestrator.py:24,51,63,74,105`
  e `run_check_memory.py:10,16,20-22,24-28` (script de validação isolada,
  único lugar que testa o comportamento do limite com `assert`).
- **Chama**: nada além de `dataclasses` (stdlib).
