# `src/layer7_governance/governance.py` — Camada 7 (Governança e Segurança)

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`governance.py:1-21`) — o mais denso do projeto em
termos de justificativa: esta camada foi "construída diretamente sobre 3
achados empíricos" registrados em `docs/evidencias_empiricas.md` (norma
citada inexistente; número distorcido mesmo com contexto correto; artigo
citado incorretamente de forma recorrente). Não é uma camada especulativa —
seu desenho é uma resposta direta a comportamentos observados do modelo
`llama3.1` ao testar as camadas anteriores isoladamente, antes de a Camada 7
existir.

O docstring também documenta o limite consciente da abordagem: validação
"não é verificação semântica: não detecta toda fabricação possível, só
citações que seguem o formato padrão de atos normativos brasileiros" — e que
a regra "usar apenas fontes públicas" **não** é verificada aqui em runtime,
é garantida estruturalmente pela curadoria do corpus na Camada 5
(`governance.py:16-20`).

## Regexes de módulo

```python
_ARTIGO_REGEX = re.compile(r"art(?:igo)?\.?\s*(\d+)", re.IGNORECASE)
_NORMA_REGEX = re.compile(
    r"(Resolução(?:\s+Conjunta|\s+BCB)?|Circular|Instrução Normativa)\s+n[ºo°]\.?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)
```
(`governance.py:24-28`)

- `_ARTIGO_REGEX` casa "art. N", "artigo N", "Art N" (o `\.?` torna o ponto
  opcional), capturando só o número em `group(1)`.
- `_NORMA_REGEX` casa nomes de norma seguidos de "nº" (aceitando `º`, `o`,
  `°` como variantes de indicador ordinal) e um número que pode ter pontos
  de milhar (`\d+(?:\.\d+)*`, ex. "4.015"). Captura o tipo de norma em
  `group(1)` e o número em `group(2)`.

## Textos fixos de módulo

`AVISO_VALIDACAO_HUMANA`, `RECUSA_PARECER_JURIDICO`, `RECUSA_FORA_DE_ESCOPO`
(`governance.py:30-49`) — strings multilinhas constantes, em português,
redigidas com tom de assistente de compliance (recomenda validação
profissional, nunca afirma ter autoridade jurídica). São as únicas
"personalidades" fixas do sistema — todo o resto do texto que o usuário vê é
gerado dinamicamente pelo LLM.

## `recusar_parecer_juridico() -> str` / `recusar_fora_de_escopo() -> str` (`governance.py:52-57`)

Funções triviais, cada uma retorna sua constante de texto correspondente —
existem como funções (não as constantes usadas diretamente) para que
`_RECUSAS` em `orchestrator.py:37-38` possa mapear `tipo -> callable` de
forma uniforme.

## `validar_citacao(resposta: str, contexto_normativo: str) -> str` (`governance.py:60-93`)

Função central da camada. Passo a passo:

1. **Verificação de artigos** (`governance.py:63-72`):
   ```python
   artigos_citados = {m.group(1) for m in _ARTIGO_REGEX.finditer(resposta)}
   artigos_no_contexto = {m.group(1) for m in _ARTIGO_REGEX.finditer(contexto_normativo)}
   artigos_nao_verificados = sorted(artigos_citados - artigos_no_contexto, key=int)
   ```
   Extrai todos os números de artigo citados na **resposta do modelo** e
   todos os citados no **contexto normativo fornecido** (o texto retornado
   pela Camada 4), como conjuntos de strings numéricas. A diferença de
   conjuntos (`-`) dá os números citados na resposta que **não aparecem em
   lugar nenhum** do contexto. `sorted(..., key=int)` ordena numericamente
   (não lexicograficamente — importante para não ordenar "10" antes de "2").
   Se houver algum, monta um aviso listando os números
   (`governance.py:66-72`).
2. **Verificação de normas** (`governance.py:74-87`): mesma lógica, mas
   compondo uma string `"{tipo} nº {numero}"` para cada citação encontrada
   (ex. "Resolução Conjunta nº 1"), e comparando o conjunto de strings
   compostas. `sorted(...)` sem `key=int` aqui, porque o valor é uma string
   composta, não um número puro — ordenação alfabética padrão.
3. **Montagem do resultado** (`governance.py:89-93`): concatena a resposta
   original + os avisos encontrados (se houver, cada um em uma linha, `"\n"`
   entre eles) + o disclaimer fixo `AVISO_VALIDACAO_HUMANA`, **sempre**
   anexado, independentemente de haver avisos de citação ou não.

### Por que é regex e não uma segunda chamada ao LLM

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:326-336`: a escolha por
verificação determinística (regex) em vez de "auto-verificação" via LLM foi
deliberada — mais previsível, sem custo computacional adicional, e sem o
risco de o próprio verificador alucinar. Trade-off assumido conscientemente:
só pega citações no formato padrão de atos normativos brasileiros, não é
verificação semântica.

### Limitação documentada e não corrigida: escopo de validação por turno

**[EVIDÊNCIA]** `docs/decisoes_arquitetura.md:337-348`: `validar_citacao` só
valida contra o contexto normativo *da pergunta atual*, nunca contra o que
está guardado na memória de turnos anteriores. Em teste real (`tests/casos_teste.md`,
Caso 2), uma resposta de turno 2 citou "Art. 36", que tinha aparecido no
contexto do turno 1 mas não no do turno 2 — gerou um aviso "tecnicamente
correto" (não estava *naquele* contexto) mas que pode soar como falso
positivo para quem lê a conversa inteira. Decisão registrada: manter o
comportamento atual e documentar a lacuna, em vez de expandir o escopo da
validação para toda a memória sem um caso de uso concreto que justifique a
complexidade adicional.

## Quem chama / quem é chamado

- **Chamado por**: `src/layer3_orchestration/orchestrator.py:25-29,37-38,62,115`
  e `run_check_governance.py:13-17,29,36` (com `assert`, incluindo um teste
  explícito contra falso positivo — ver `06_testes_config_operacao.md`).
- **Chama**: só `re` (stdlib).
