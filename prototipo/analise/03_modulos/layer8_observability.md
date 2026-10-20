# `src/layer8_observability/observability.py` — Camada 8 (Observabilidade e Proveniência)

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`observability.py:1-17`): registrar, para cada
interação, o que fundamentou a resposta — normativo(s) usados, classificação
da Camada 3, se a Camada 7 sinalizou citação não verificada — para
rastreabilidade/auditoria completa. Persistência em disco é o próprio
propósito desta camada (contraste explícito com a Camada 6, onde a
não-persistência é igualmente deliberada — ver `layer6_memory.md`).

## Constantes de módulo

- `LOG_DIR = Path(__file__).resolve().parents[2] / "logs"` e `LOG_FILE =
  LOG_DIR / "interacoes.jsonl"` (`observability.py:25-26`) — mesma técnica
  de caminho relativo ao arquivo-fonte já vista em `knowledge_base.py`.
- `_FONTE_REGEX = re.compile(r"^Fonte:\s*(.+?)\s*\((https?://[^\s)]+)\)",
  re.MULTILINE)` (`observability.py:28`) — casa linhas que começam com
  `"Fonte: "` seguidas de um título (non-greedy, `.+?`) e uma URL entre
  parênteses. `re.MULTILINE` faz `^` casar o início de **cada linha**, não
  só do texto inteiro — essencial porque o texto de `buscar_normativo` tem
  múltiplos blocos "Fonte: ..." separados por `"\n\n---\n\n"`
  (`tools.py:34`). **[FATO]** Este regex depende do formato de string exato
  produzido em `tools.py:33` — acoplamento implícito já sinalizado em
  `layer4_tools.md` e detalhado em `07_riscos.md`.

## `@dataclass RegistroInteracao` (`observability.py:31-38`)

```python
@dataclass
class RegistroInteracao:
    timestamp: str
    pergunta: str
    tipo_classificacao: str
    fontes_normativas: list[dict] = field(default_factory=list)
    aviso_citacao_nao_verificada: bool = False
    resposta_final: str = ""
```
Uso de `field(default_factory=list)` (não `= []`) para o default de
`fontes_normativas` — **[FATO]** correto: um `@dataclass` com um `list`
mutável como valor default direto (`= []`) compartilharia a **mesma** lista
entre todas as instâncias (armadilha clássica de mutáveis como default em
Python); `default_factory` evita isso corretamente, criando uma lista nova
por instância.

## `_extrair_fontes(normativo: str) -> list[dict]` (`observability.py:41-53`)

```python
vistos: set[tuple[str, str]] = set()
fontes = []
for titulo, url in _FONTE_REGEX.findall(normativo):
    chave = (titulo, url)
    if chave not in vistos:
        vistos.add(chave)
        fontes.append({"titulo": titulo, "url_oficial": url})
return fontes
```
Deduplica por par `(titulo, url)`, preservando a ordem da primeira
ocorrência (usa uma lista de saída + um `set` auxiliar só para checagem de
pertencimento, não para a ordenação final). Comentário inline
(`observability.py:42-45`) explica por quê: `top_k > 1` trechos retornados
pela Camada 5 podem vir do mesmo documento normativo (mesmo título/URL,
trechos diferentes) — a proveniência deve listar **documentos** distintos
usados, não **trechos**.

## `registrar_interacao(pergunta, tipo_classificacao, resposta_final, normativo="", arquivo=None) -> RegistroInteracao` (`observability.py:56-75`)

1. Monta um `RegistroInteracao` com `timestamp` em UTC ISO 8601
   (`datetime.now(timezone.utc).isoformat()`), `fontes_normativas` extraídas
   via `_extrair_fontes(normativo)` (lista vazia se `normativo` for a string
   vazia default — o caso dos ramos de recusa), e
   `aviso_citacao_nao_verificada` calculado por **[FATO — heurística de
   substring]**: `"Aviso:" in resposta_final` (`observability.py:68`) — não
   inspeciona a estrutura de `validar_citacao`, apenas procura a substring
   literal `"Aviso:"` na resposta final. Funciona porque essa é exatamente a
   palavra que `governance.py:69,84` usa para prefixar cada aviso gerado —
   outro ponto de acoplamento textual implícito entre camadas (ver
   `07_riscos.md`).
2. `destino = arquivo or LOG_FILE` (`observability.py:71`) — parâmetro
   `arquivo` opcional permite redirecionar a escrita para um caminho
   diferente do log real, usado por `run_check_observability.py` para não
   poluir `logs/interacoes.jsonl` durante validação.
3. `destino.parent.mkdir(parents=True, exist_ok=True)` (`observability.py:72`)
   — cria o diretório `logs/` se não existir, antes da primeira escrita
   (relevante porque `logs/` é git-ignorado e não versionado, então em um
   clone novo do repositório o diretório simplesmente não existe até a
   primeira execução).
4. `with destino.open("a", encoding="utf-8") as f: f.write(json.dumps(asdict(registro), ensure_ascii=False) + "\n")`
   (`observability.py:73-74`) — modo append (`"a"`), uma linha JSON por
   chamada (formato JSON Lines / JSONL). `ensure_ascii=False` preserva
   caracteres acentuados em português legíveis no arquivo, em vez de
   escapá-los como `\uXXXX`.
5. Retorna o `RegistroInteracao` construído — é esse valor de retorno que
   `Orchestrator` guarda em `self.ultimo_registro` (`orchestrator.py:64,76`).

## Quem chama / quem é chamado

- **Chamado por**: `src/layer3_orchestration/orchestrator.py:30,64,76` e
  `run_check_observability.py:17,30-36,51-59,68-73` (3 cenários testados com
  `assert`: interação normal, aviso de citação não verificada, recusa sem
  fontes).
- **Chama**: só stdlib (`json`, `re`, `dataclasses`, `datetime`, `pathlib`).
