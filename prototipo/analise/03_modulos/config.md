# `src/config.py` — Configuração transversal

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Responsabilidade

**[FATO]** Único ponto do projeto que lê variáveis de ambiente/`.env`.
Declarado no próprio docstring do módulo como "transversal — usada pela
Camada 2 (...) e por qualquer outra camada que precise saber qual provedor
de LLM está ativo" (`config.py:4-5`). Na prática, hoje só a Camada 2
(`src/layer2_llm_core/core.py:15,20`) a usa.

## Leitura linha a linha

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()          # linha 15 — efeito colateral de import


@dataclass
class Settings:
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")


settings = Settings()  # linha 24 — singleton de módulo
```

- `load_dotenv()` (`config.py:15`) roda **no momento do import**, antes de
  qualquer outro código do módulo. Ela procura um arquivo `.env` a partir do
  diretório de trabalho atual (comportamento padrão de `python-dotenv`) e
  injeta suas variáveis em `os.environ`, sem sobrescrever variáveis já
  definidas no ambiente do processo por padrão.
- `Settings` é uma `@dataclass` cujos valores default são calculados **uma
  vez, na definição da classe** (`os.getenv(...)` roda quando o módulo é
  importado, não a cada instanciação) — `ollama_model: str =
  os.getenv("OLLAMA_MODEL", "llama3.1")` (`config.py:20`) e
  `ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")`
  (`config.py:21`). **[INFERÊNCIA]** Isso significa que, se `.env` for
  criado ou alterado depois do import (por exemplo, um teste que muda a
  variável de ambiente em runtime e reinstancia `Settings()`), o valor
  default já capturado na classe não muda — só uma chamada explícita
  `Settings(ollama_model="outro")` sobrescreveria. Não encontrei evidência
  de que isso seja intencional ou que tenha sido testado; é uma consequência
  natural de como `@dataclass` avalia defaults, não uma decisão documentada.
- `settings = Settings()` (`config.py:24`) cria a instância única que todo o
  resto do código importa (`from src.config import settings`) — efetivamente
  um singleton por convenção Python (módulo importado uma vez, mesmo objeto
  reaproveitado), não por um padrão de projeto formal (sem metaclasse, sem
  `__new__` sobrescrito).

## Decisão de projeto documentada no próprio código

**[EVIDÊNCIA]** O docstring do módulo (`config.py:7-9`) afirma
explicitamente: "as configurações são lidas de variáveis de ambiente (.env),
não hardcoded, para permitir trocar de modelo/provedor sem alterar
código-fonte" — e remete a `docs/decisoes_arquitetura.md` para mais
contexto, embora essa entrada específica sobre `config.py` não apareça de
forma isolada nesse documento (a decisão sobre Ollama está registrada na
entrada "Camada 2").

## Risco de ordem de import (ver `07_riscos.md`, item 0)

**[FATO — verificado na biblioteca instalada]** `src/layer2_llm_core/core.py:14`
faz `import ollama` **antes** de `core.py:15` (`from src.config import
settings`, que é o que dispara `load_dotenv()`, linha 15 deste arquivo). O
pacote `ollama` cria seu cliente HTTP singleton no próprio momento do
import, lendo `os.getenv('OLLAMA_HOST')` **antes** de `load_dotenv()` ter
rodado. Consequência: um `OLLAMA_HOST` definido só em `.env` nunca chega a
ser efetivamente usado pela chamada real a `ollama.chat()` — só funcionaria
se já fosse uma variável de ambiente real do sistema operacional. Passa
despercebido porque o default em `.env.example` coincide com o default da
própria biblioteca. Detalhado com os caminhos de código exatos em
`07_riscos.md`.

## Quem chama / quem é chamado

- **Chamado por**: `src/layer2_llm_core/core.py:15,20` (único consumidor
  atual).
- **Chama**: apenas a stdlib (`os`) e `python-dotenv`.

## Constantes e valores mágicos

- `"llama3.1"` (default do modelo) e `"http://localhost:11434"` (endereço
  padrão do servidor Ollama local) — ambos coincidem exatamente com os
  valores documentados em `.env.example:2,5`, então não são valores
  arbitrários: são os defaults reais do próprio Ollama e do modelo escolhido
  para o protótipo (ver `README.md:47-57` para a motivação de escolher
  `llama3.1`: equilíbrio entre qualidade e uso de recursos, com suporte a
  tool calling).
