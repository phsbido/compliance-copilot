# `src/layer2_llm_core/core.py` — Camada 2 (Núcleo de Raciocínio do LLM)

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`core.py:1-13`): interpretar intenção, sintetizar
artefatos de raciocínio, produzir saídas estruturadas — mas o próprio
docstring admite que o **estágio atual é mínimo**: "apenas geração de texto
simples, sem tool calling e sem integração com as demais camadas"
(`core.py:8-10`). **[EVIDÊNCIA — desatualização documentada]**: essa frase
descreve o estado do módulo no início da construção (Estágio 1, ver
`docs/decisoes_arquitetura.md:24-44`); na versão final do sistema, `LLMCore`
já é usado com tool calling implícito via prompt (a Camada 3 monta prompts
que incluem contexto de ferramentas) — o docstring não foi atualizado depois
que as outras camadas passaram a usá-lo, um exemplo pequeno mas real de
comentário desatualizado. Isso não muda o comportamento do código, só a
precisão da documentação inline.

## `class LLMCore` (`core.py:18-36`)

### Atributos

- `self.model: str` — nome do modelo Ollama a usar.

### `__init__(self, model: str | None = None)` (`core.py:19-20`)

```python
self.model = model or settings.ollama_model
```
Se `model` não for passado (ou for `None`/string vazia, já que `or` avalia
falsiness, não só `None`), usa o valor de `settings.ollama_model` (Camada de
configuração). **[INFERÊNCIA]** O parâmetro opcional permite injeção de
dependência para testes (instanciar `LLMCore(model="outro-modelo")` sem
mexer em `.env`) — mesmo padrão usado em `Orchestrator.__init__`
(`orchestrator.py:49`) para `llm` e `memoria`. Não há teste automatizado que
exercite essa flexibilidade especificamente, mas o padrão é consistente em
todo o projeto (ver `05_decisoes_de_design.md`).

### `generate(self, prompt: str, system: str | None = None) -> str` (`core.py:22-36`)

```python
messages = []
if system:
    messages.append({"role": "system", "content": system})
messages.append({"role": "user", "content": prompt})

response = ollama.chat(model=self.model, messages=messages)
return response["message"]["content"]
```

- Monta uma lista de mensagens no formato esperado pela API de chat do
  Ollama (compatível com o padrão OpenAI-like de `role`/`content`).
- `system` é opcional — só é incluído se truthy (`core.py:31`). Todos os
  chamadores atuais (`orchestrator.py:90,112`) sempre passam um `system`
  não-vazio, então esse ramo condicional nunca é exercitado no fluxo real do
  protótipo, só potencialmente em testes/uso direto de `LLMCore`.
- **Efeito colateral**: `ollama.chat(...)` (`core.py:35`) é uma chamada de
  rede síncrona e bloqueante ao servidor Ollama (`http://localhost:11434`
  por padrão) — é o único ponto do sistema inteiro que faz I/O de rede.
  Não há timeout configurado, não há retry.
- Retorno: extrai `response["message"]["content"]` — acesso direto a chaves
  de dicionário, sem `.get()` nem tratamento se a resposta vier em formato
  inesperado. Se o Ollama retornar algo sem essas chaves (ex.: erro
  estruturado diferente), levanta `KeyError`, não capturado em lugar nenhum
  do projeto.

## Quem chama / quem é chamado

- **Chamado por**: `src/layer3_orchestration/orchestrator.py:50,90,112`
  (dentro de `Orchestrator`) e diretamente por `run_check.py:18-22` (script
  de validação isolada).
- **Chama**: só a biblioteca `ollama` (função `ollama.chat`) e
  `src.config.settings`.

## Por que é "fina" (thin wrapper)

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:26-35`: a decisão explícita foi
um "wrapper fino sobre o cliente Python do Ollama, isolando a camada
superior (Orquestração) do provedor de LLM específico" — a arquitetura de
Maia et al. não prescreve tecnologia, e a escolha por Ollama local foi
motivada por reprodutibilidade científica (qualquer pessoa roda sem custo,
sem chave de API). **[INFERÊNCIA]** A consequência prática dessa camada de
abstração é que, se o projeto precisasse trocar de provedor (ex.: para a API
da OpenAI/Anthropic), só `LLMCore.generate` precisaria mudar — nenhuma outra
camada conhece o formato específico de mensagens do Ollama, só a interface
`generate(prompt, system) -> str`.
