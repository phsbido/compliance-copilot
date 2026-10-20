# `src/layer5_knowledge/` — Camada 5 (Integração de Conhecimento / RAG)

> **Retrato histórico (2026-09-23, v1).** Esta análise descreve o código da v1 e não reflete as mudanças da v2 em diante (Gold e BM25, Camada 7 v2, v4 a v7). Para o estado atual, ver `docs/estado_atual.md`.

Este diretório tem **dois módulos com propósitos muito diferentes** — é
essencial não confundi-los:

| Módulo | Papel | Usado em runtime? |
|---|---|---|
| `knowledge_base.py` | Implementação **real** da Camada 5, validada em todos os testes/benchmark | **Sim** — importado por `layer4_tools/tools.py` |
| `ingest_normativos.py` | Pipeline **ilustrativo/paralelo** Bronze/Silver/Gold | **Não** — nenhum outro módulo do projeto o importa |

Essa distinção não é uma interpretação minha — está documentada de forma
explícita e repetida no próprio docstring de `ingest_normativos.py:1-16` e em
`docs/decisoes_arquitetura.md:472-509` ("Benchmark Empírico", extensão
2026-09-23): o pipeline medalhão foi pedido pelo usuário depois que a Camada
5 real já estava validada em 4 casos de teste e 20 execuções de benchmark; o
risco de reescrever `knowledge_base.py` para consumir o índice Gold foi
levantado, e o usuário optou por manter o runtime intocado.

---

## `knowledge_base.py` — a Camada 5 real

### Responsabilidade

**[EVIDÊNCIA]** Docstring (`knowledge_base.py:1-13`): manter e disponibilizar
o corpus de atos normativos do BACEN. Decisão de projeto explícita: "indexação
e busca lexical simples (contagem de sobreposição de palavras), sem
embeddings e sem biblioteca de vector DB" — cada normativo é um Markdown com
frontmatter de metadados seguido do texto integral, dividido em trechos por
artigo.

### Constantes de módulo

- `DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "normativos"`
  (`knowledge_base.py:19`) — caminho calculado relativo à localização do
  próprio arquivo fonte (`parents[2]` sobe de
  `src/layer5_knowledge/knowledge_base.py` até a raiz do projeto), não ao
  diretório de trabalho do processo. **[INFERÊNCIA]** Isso torna o módulo
  robusto a partir de qual diretório o script é chamado (`python main.py` da
  raiz vs. de outro lugar), desde que a estrutura de pastas do repositório
  não mude.
- `_STOPWORDS` (`knowledge_base.py:21-26`) — conjunto de ~30 palavras
  funcionais do português (artigos, preposições, conjunções, pronomes
  interrogativos) excluídas da tokenização. Sem acentuação nas chaves
  (`"é"`, `"são"`, `"à"`, `"às"` são as únicas com acento) — coerente com
  `_normalizar` removendo acentos antes da comparação (ver abaixo), mas
  **[FATO]** essas 4 entradas acentuadas na lista nunca vão bater com nada,
  porque `_tokenizar` sempre chama `_normalizar` antes, que já removeu os
  acentos — são entradas mortas na prática (redundantes, não incorretas: a
  versão sem acento de cada uma, ex. `"e"`, já está na lista separadamente
  para `"é"`... na verdade não, `"e"` já cobre a conjunção "e", mas "é"
  (verbo ser) sem acento vira "e" também, colidindo com a conjunção — ver
  `07_riscos.md` para essa observação com mais detalhe).

### `@dataclass Documento` (`knowledge_base.py:29-34`)

`titulo`, `ementa`, `url_oficial`, `trecho` — a unidade indexável. Note que
**um `Documento` é um trecho (um artigo), não um normativo inteiro** — um
único arquivo `.md` de origem gera múltiplos objetos `Documento` (um por
artigo encontrado).

### `_normalizar(texto: str) -> str` (`knowledge_base.py:37-40`)

```python
sem_acento = unicodedata.normalize("NFKD", texto)
sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
return sem_acento.lower()
```
Técnica padrão para remover acentuação: decompõe caracteres acentuados em
base + diacrítico (forma NFKD), filtra os diacríticos (`unicodedata.combining`
identifica marcas combinantes), depois normaliza para minúsculas.

### `_tokenizar(texto: str) -> set[str]` (`knowledge_base.py:43-45`)

```python
palavras = re.findall(r"\w+", _normalizar(texto))
return {p for p in palavras if p not in _STOPWORDS and len(p) > 2}
```
`\w+` inclui dígitos e underscore, não só letras — então números de artigo
("6", "31") também viram tokens, o que é relevante: significa que a busca
lexical pode, incidentalmente, favorecer trechos que contenham o mesmo
número mencionado na pergunta, mesmo que o número apareça em contextos
semanticamente diferentes (ex.: "artigo 6" vs. "6 meses de prazo"). Filtro de
comprimento mínimo 3 caracteres (`len(p) > 2`) descarta ruído como "de",
"da" mesmo que não estivessem em `_STOPWORDS`.

### `_parse_frontmatter(conteudo: str) -> tuple[dict, str]` (`knowledge_base.py:48-62`)

Parser manual e minimalista de um cabeçalho YAML-like delimitado por `---`:

1. Se o conteúdo não começa com `"---"`, não há frontmatter — retorna
   `({}, conteudo)` inteiro como corpo.
2. Procura o próximo `"\n---"` após a posição 3 — se não achar, mesmo
   fallback.
3. Extrai o bloco entre os delimitadores, faz split por `:` em cada linha
   (`partition`, que garante exatamente 3 partes mesmo se não houver `:`),
   monta um dicionário `chave -> valor`, removendo aspas do valor
   (`.strip('"')`).

**[INFERÊNCIA]** Não é um parser YAML real (não usa `PyYAML`) — é uma
escolha deliberada de manter zero dependências extras para uma tarefa
simples (metadados de uma linha cada, sem aninhamento, sem listas). Isso
funciona bem para o formato usado, mas quebraria silenciosamente se um valor
contivesse `:` sem estar entre aspas de forma que o `partition` cortasse no
lugar errado, ou se houvesse uma estrutura YAML mais complexa.

### `_dividir_em_trechos(corpo: str) -> list[str]` (`knowledge_base.py:65-71`)

```python
partes = re.split(r"\n(?=Art\.\s*\d)", corpo)
return [p.strip() for p in partes if p.strip()]
```
Divide o texto por *lookahead* antes de cada ocorrência de `"Art. N"` no
início de uma linha (o `\n` é consumido pelo split, o "Art." permanece no
início do próximo trecho, porque é um *positive lookahead* `(?=...)`, não
consumido). Comentário no código (`knowledge_base.py:66-69`) explica a
motivação (artigo é a unidade natural de citação em atos normativos
brasileiros) e a limitação conhecida: a extração de PDF pode introduzir
quebras/espaçamento irregulares em "Art. N", afetando a precisão da divisão
— achado empírico documentado em `docs/decisoes_arquitetura.md:224-237`
("Art. 3 1." em vez de "Art. 31.").

### `class KnowledgeBase`

#### `__init__(self, diretorio: Path | None = None)` (`knowledge_base.py:75-78`)

Injeção de dependência opcional de diretório (para testes com corpus
customizado). `self.documentos: list[Documento] = []` inicializado antes de
`self._carregar()` ser chamado no próprio construtor — **[FATO]** significa
que instanciar `KnowledgeBase()` já faz I/O de disco imediatamente, não é
lazy.

#### `_carregar(self) -> None` (`knowledge_base.py:80-94`)

```python
for arquivo in sorted(self.diretorio.glob("*.md")):
    conteudo = arquivo.read_text(encoding="utf-8")
    metadados, corpo = _parse_frontmatter(conteudo)
    if not metadados:
        continue  # sem cabeçalho -> não é normativo indexável (ex: PENDENTES.md)
    for trecho in _dividir_em_trechos(corpo):
        self.documentos.append(Documento(...))
```
- `Path.glob("*.md")` — **não recursivo**, só o nível raiz de
  `data/normativos/`. É por isso que os `.md` gerados em
  `1_bronze_raw/`/`2_silver_cleaned/`/`3_gold_indexed/` (subpastas) nunca são
  vistos por esta classe — confirmado tanto pelo comportamento do `glob`
  quanto pela documentação explícita em `ingest_normativos.py:9-10`.
- `sorted(...)` garante ordem determinística de carregamento (por nome de
  arquivo) — relevante para reprodutibilidade dos resultados de busca
  (embora a pontuação por interseção de conjuntos não dependa de ordem de
  inserção, a ordem de desempate entre trechos com pontuação igual em
  `sorted(key=..., reverse=True)` de Python é estável, preservando a ordem
  original em empates).
- `if not metadados: continue` (`knowledge_base.py:84-85`) é o mecanismo que
  faz `README.md` e `PENDENTES.md` (que também são `.md` no mesmo
  diretório) serem ignorados: eles não têm frontmatter `---`, então
  `_parse_frontmatter` retorna `{}` para eles.
- Cada trecho de cada arquivo vira um `Documento` separado, todos com os
  mesmos `titulo`/`ementa`/`url_oficial` (do frontmatter do arquivo) mas
  `trecho` diferente.

#### `buscar(self, pergunta: str, top_k: int = 3) -> list[Documento]` (`knowledge_base.py:96-105`)

```python
tokens_pergunta = _tokenizar(pergunta)
pontuados = []
for doc in self.documentos:
    tokens_trecho = _tokenizar(doc.trecho)
    pontuacao = len(tokens_pergunta & tokens_trecho)
    if pontuacao > 0:
        pontuados.append((pontuacao, doc))
pontuados.sort(key=lambda par: par[0], reverse=True)
return [doc for _, doc in pontuados[:top_k]]
```
Algoritmo: para cada documento indexado, calcula o tamanho da interseção
entre o conjunto de tokens da pergunta e o conjunto de tokens do trecho.
Descarta documentos com pontuação 0. Ordena decrescente, retorna os `top_k`
primeiros. **[FATO]** `_tokenizar(doc.trecho)` é recalculado a cada chamada
de `buscar` para cada documento — não há cache/pré-computação dos tokens de
cada trecho no momento do carregamento; para um corpus pequeno (67
documentos/trechos no estado atual, ver `docs/estado_atual.md:169`) isso não
é um problema de performance perceptível, mas escalaria mal com um corpus
muito maior (complexidade O(n) tokenizações repetidas a cada busca). Ver
`07_riscos.md`.

### Quem chama / quem é chamado

- **Chamado por**: `src/layer4_tools/tools.py:15,17,27` e
  `run_check_knowledge.py:10,16,23`.
- **Chama**: só stdlib (`re`, `unicodedata`, `dataclasses`, `pathlib`).

---

## `ingest_normativos.py` — pipeline ilustrativo Bronze/Silver/Gold

### Responsabilidade e por que existe (contexto crucial)

**[EVIDÊNCIA]** O próprio docstring do módulo declara, na primeira frase,
que é um "artefato ILUSTRATIVO/PARALELO, não ligado ao runtime do
protótipo" (`ingest_normativos.py:2-3`). O histórico completo do pedido está
em `docs/decisoes_arquitetura.md:472-536`: o usuário pediu inicialmente para
implementar de fato uma arquitetura Bronze/Silver/Gold *substituindo*
`knowledge_base.py`; isso foi identificado como um risco de invalidar
evidência empírica já coletada (4 casos de teste + 20 execuções de benchmark
já rodados contra a implementação anterior); a decisão final foi manter
`knowledge_base.py` intocado e implementar o pipeline como um artefato
paralelo que só lê os `.md` curados (nunca escreve neles) e gera saída em
subpastas que `KnowledgeBase` não enxerga.

### Duas fontes de entrada tratadas de forma assimetricamente honesta

**[FATO]**, confirmado por leitura de `etapa_bronze()` (`ingest_normativos.py:223-258`):

1. **`.md` já curados** (`data/normativos/*.md`): copiados **verbatim** para
   `1_bronze_raw/` — nenhum reprocessamento, nenhuma heurística.
2. **`.pdf` brutos** (`data/normativos/*.pdf` — hoje, 2 arquivos reais:
   `normativoOpenFinance.pdf` e `normativoPix.pdf`, confirmados presentes no
   diretório): o PDF é copiado sem alteração **e** um `.md` irmão é gerado
   com texto extraído via `pypdf` e metadados obtidos por heurística de
   regex — sempre marcado `fonte_confirmada: "false"` e `url_oficial: ""`
   no frontmatter gerado (`_heuristica_metadados`, `ingest_normativos.py:167-202`).
   **[EVIDÊNCIA]** Esse cuidado de nunca apresentar dado inferido como
   curado é explicitamente comparado, no próprio docstring, ao mesmo
   princípio de transparência de `data/normativos/PENDENTES.md`
   (`ingest_normativos.py:29-30`).

### Regex de título de norma brasileira (`ingest_normativos.py:89-94`)

```python
_TITULO_PDF_REGEX = re.compile(
    r"^(INSTRUÇÃO NORMATIVA|RESOLUÇÃO CONJUNTA|RESOLUÇÃO|CIRCULAR)"
    r"(\s+BCB)?\s+N[ºO°]\.?\s*(\d+(?:\.\d+)*)\s*,?\s*DE\s+"
    r"(\d{1,2})\s+DE\s+(\w+)\s+DE\s+(\d{4})",
    re.IGNORECASE,
)
```
Casa linhas como "INSTRUÇÃO NORMATIVA BCB Nº 759, DE 9 DE JULHO DE 2026" —
comentário no código (`ingest_normativos.py:82-88`) explica por que exige
palavras completas: a primeira página de PDFs oficiais do BCB costuma ter
uma linha de cabeçalho corrompida (artefato de fonte/watermark) antes da
linha de título real, e exigir o match completo evita casar a linha
corrompida por engano. **[EVIDÊNCIA verificada por mim]**: li o arquivo
`data/normativos/3_gold_indexed/normativoPix.json` gerado por este pipeline
e confirmei que a corrupção de fonte documentada realmente ocorre — a
ligadura "ti" foi sistematicamente substituída por `�` (ex.: "Institui" →
"Ins�tui", "instituições" → "ins�tuições"), exatamente como descrito em
`docs/decisoes_arquitetura.md:537-550`.

### `_heuristica_metadados(texto_completo, nome_arquivo) -> dict` (`ingest_normativos.py:167-202`)

Lê só as primeiras 20 linhas não-vazias (`ingest_normativos.py:172`),
procura a linha de título com a regex acima, extrai tipo/número/data,
constrói um título formatado (`ingest_normativos.py:182`), converte o mês
por extenso (removendo acento via `_sem_acento`, `ingest_normativos.py:103-105`)
para número via o dicionário `_MESES` (`ingest_normativos.py:96-100`), e
pega as 2 linhas seguintes ao título como candidatas a ementa
(`ingest_normativos.py:190-192`) — heurística posicional simples (ementa
normalmente vem logo depois do título em atos normativos brasileiros), sem
NLP. Retorna sempre `url_oficial: ""` e `fonte_confirmada: "false"`
(`ingest_normativos.py:198,201`) — nunca inferidos.

### `_extrair_texto_pdf(caminho) -> str` (`ingest_normativos.py:162-164`)

```python
leitor = pypdf.PdfReader(str(caminho))
return "\n\n".join(pagina.extract_text() or "" for pagina in leitor.pages)
```
`pagina.extract_text() or ""` trata o caso de `extract_text()` retornar
`None` (páginas sem texto extraível, ex.: imagens escaneadas) — evita
`TypeError` ao juntar com `"\n\n".join`.

### `_dividir_paragrafos` / `_dividir_artigos` (`ingest_normativos.py:148-159`, `205-215`)

Mesma técnica de regex por lookahead já vista em `knowledge_base.py`, mas
uma etapa mais fina: primeiro divide por artigo
(`_ARTIGO_SPLIT_REGEX = re.compile(r"\n(?=Art\.\s*\d)")`), depois, dentro de
cada artigo, divide por parágrafo/inciso
(`_PARAGRAFO_SPLIT_REGEX = re.compile(r"\n(?=§\s*\d|Parágrafo único)")`).
`_dividir_artigos` (`ingest_normativos.py:205-215`) descarta explicitamente
qualquer trecho antes do primeiro "Art." (preâmbulo/cabeçalho) — comentário
inline documenta essa escolha.

### As três etapas (`etapa_bronze`, `etapa_silver`, `etapa_gold`)

| Etapa | Função | Entrada | Saída |
|---|---|---|---|
| Bronze | `etapa_bronze()` (`ingest_normativos.py:223-258`) | `.md`/`.pdf` de `data/normativos/` | `.md` (+ `.pdf` cópia) em `1_bronze_raw/` |
| Silver | `etapa_silver(arquivos_bronze)` (`ingest_normativos.py:261-281`) | arquivos Bronze | 1 JSON por normativo em `2_silver_cleaned/`, estrutura `{titulo, artigos: [{identificador, texto, paragrafos}]}` |
| Gold | `etapa_gold(arquivos_bronze, arquivos_silver)` (`ingest_normativos.py:284-318`) | Bronze (metadados) + Silver (estrutura) | 1 JSON por normativo em `3_gold_indexed/`, combinando metadados regulatórios completos + artigos estruturados + `gerado_em` (timestamp UTC) |

Nota sobre `etapa_gold` (`ingest_normativos.py:305-310`, comentário inline):
a lógica de `fonte_confirmada` é assimétrica por design — ausência do campo
no frontmatter (corpus curado manualmente) vira `True` (já verificado
manualmente); presença explícita como `"false"` (gerado por
`_heuristica_metadados`) vira `False`. `metadados.get("fonte_confirmada",
"true") == "true"` é a linha que implementa essa lógica.

### `executar()` (`ingest_normativos.py:321-354`)

Função de orquestração do script: valida que `FONTE_DIR` existe, conta PDFs
brutos e avisa, roda as 3 etapas em sequência, imprime estatísticas
(incluindo quantidade de artigos no Silver e lista de normativos com fonte
não confirmada no Gold), e termina com um lembrete explícito impresso no
terminal (`ingest_normativos.py:350-353`) de que `knowledge_base.py`
**não** consome esta saída.

### Quem chama / quem é chamado

- **Chamado por**: ninguém — só executado diretamente (`if __name__ ==
  "__main__":`, `ingest_normativos.py:357-358`), via `python -m
  src.layer5_knowledge.ingest_normativos` ou caminho direto.
- **Chama**: só stdlib + `pypdf`. Não importa nenhum outro módulo `src/`.
