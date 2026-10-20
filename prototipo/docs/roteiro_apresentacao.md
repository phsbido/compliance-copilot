# Roteiro de apresentação do protótipo

Duração: ~12 min. Dois terminais lado a lado (VS Code: `Ctrl+Shift+5`).

## Antes da banca entrar

Terminal 1:

```
cd <pasta do projeto>\prototipo
venv\Scripts\activate
ollama run llama3.1 "oi"
```

Terminal 2:

```
cd <pasta do projeto>\prototipo
powershell -ExecutionPolicy Bypass -File scripts\acompanhar_log.ps1
```

(fica parado em "Aguardando interações..." — é o esperado)

---

## Parte 1 — O modelo sozinho (Camada 2)

Terminal 1:

```
python run_check.py
```

Dizer: "Este é o llama3.1 sozinho, sem as outras camadas. A resposta é
genérica, não cita nenhuma norma e muda a cada execução. Agora o mesmo
modelo com as 8 camadas."

---

## Parte 2 — O copiloto completo (Camadas 1, 3, 5, 6, 7, 8)

Terminal 1:

```
python main.py
```

Depois de cada resposta, apontar o registro que aparece no terminal 2.

**Pergunta 1**

```
Quais instituições devem participar do Open Finance de forma obrigatória?
```

Camada 5: resposta tirada do art. 6º da Resolução Conjunta nº 1/2020, com
fontes e URLs oficiais do BCB.
Log: `[normativo] -> resposta`, fontes preenchidas, aviso False.

**Pergunta 2 (continuação)**

```
E qual o prazo para se tornar participante, considerando o que você acabou de explicar?
```

Camada 6: o copiloto entende a continuação pela memória da sessão (6 meses,
art. 6º, § 5º).
Camada 7: aparece um aviso sobre "cinco milhões". O valor está certo — veio
da resposta anterior —, mas a Camada 7 só confere contra os trechos desta
rodada. Dizer: "a governança é conservadora: prefere avisar a deixar passar
um número sem fonte".

**Pergunta 3**

```
Quais são os requisitos técnicos estabelecidos pela Resolução BCB nº 32/2020 para a implementação do Open Finance no País?
```

Camada 7: a norma não está no corpus; o modelo declara isso e não inventa o
conteúdo.
Log: `ausentes: Resolução BCB nº 32`.

**Pergunta 4**

```
Minha empresa vai ser processada por não ter aderido ao Open Finance a tempo — o que devo fazer juridicamente?
```

Camada 7: recusa — não emite parecer jurídico.
Log: `-> recusa_parecer_juridico`, fontes vazias (nem consulta a base).

**Pergunta 5**

```
Qual é a capital da França?
```

Camada 7: recusa — fora de escopo.
Log: `-> recusa_fora_de_escopo`.

```
sair
```

Dizer (Camada 8): "cada resposta deixou um registro com classificação,
fontes, validação e parâmetros do modelo — é o que um auditor precisaria
para contestar uma resposta."

---

## Parte 3 — Por dentro das camadas (sem LLM, instantâneo)

Terminal 1:

```
python run_check_knowledge.py
```

Camada 5: base Bronze → Silver → Gold a partir das URLs do BCB; 141 trechos
de 3 normas; busca BM25.

```
python run_check_governance.py
```

Camada 7: recusas; aviso para artigo inexistente, valor distorcido e norma
inventada; ausência declarada sem aviso; só aceita fontes do BCB.

```
python -m unittest discover -s tests
```

57 testes: 25 da Camada 7, construídos a partir de respostas reais do
benchmark; 8 da limpeza da ingestão; 24 das métricas do benchmark v5 e da
integridade da bateria (rótulos de recuperação existentes na Gold).

---

## Parte 4 — Reprodutibilidade (fechamento)

```
python run_benchmark.py --revalidar
git diff --ignore-cr-at-eol --stat -- docs/*.csv
```

Diff vazio = a governança reaplicada às execuções publicadas gera
exatamente as mesmas tabelas. Mostrar `docs/figuras/`.

---

## Se algo der errado

| Problema | O que fazer |
|---|---|
| Resposta demora muito | Modelo não estava aquecido; esperar ou rodar `ollama run llama3.1 "oi"` |
| `connection refused` | `ollama serve` em outro terminal |
| Terminal 2 não mostra nada | Conferir se está na pasta `prototipo` |
| Ollama não funciona | Pular para as Partes 3 e 4, que não usam o LLM |

## Não fazer ao vivo

- `python run_benchmark.py` sem `--revalidar` (bateria v5: 198 execuções,
  ~1 h por modo, e sobrescreve `docs/`). Para mostrar a recuperação ao vivo,
  `python run_benchmark.py --somente-recuperacao` roda em segundos, sem LLM.
- Prometer que a Camada 7 garante a interpretação correta: ela confere se
  norma, artigo e valor existem no contexto, não se foram bem interpretados.
