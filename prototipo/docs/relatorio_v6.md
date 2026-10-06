# Relatório v6 — limiar BM25, segundo avaliador e ablação da Camada 7

Data: 2026-10-02/03. Linha de base: benchmark v5 e auditoria manual,
**inalterados** (nenhum arquivo do v5 mudou depois do commit `149874c`).
Ambiente de todas as rodadas: Ollama 0.33.2 (servidor reiniciado antes de
cada rodada), `llama3.1` ID `46e0c10c039e`, contexto de 4.096 tokens, seed
42, modo produção, 66 casos × 3 repetições. Decisões em
`decisoes_arquitetura.md` ("v6"); resultados em `evidencias_empiricas.md`
(entradas v6).

| Rodada | Início e fim (horário de Brasília) | Pasta |
|---|---|---|
| v6 (limiar BM25 13,8059) | 2026-10-02 23:20:38 – 23:25:04 | `docs/resultados/v6/` |
| C1 (sem validador) | 2026-10-02 23:25:20 – 23:36:02 | `docs/resultados/ablacao_c1/` |
| C2, 1ª tentativa (sem teto) | 2026-10-02 23:36:09 – interrompida às 23:50:16 | não aproveitada |
| C2 (sem validador e sem política; teto de 2.048 tokens) | 2026-10-02 23:52:47 – 2026-10-03 00:03:29 | `docs/resultados/ablacao_c2/` |

## Tarefa A — limiar de pontuação BM25 (Camada 5)

O limiar decide pelo melhor trecho e vem desligado por padrão
(`LIMIAR_BM25` vazio), o que mantém o v5 reprodutível. Foi calibrado num
conjunto próprio de 40 perguntas (`tests/calibracao_limiar.json`: 20
respondíveis e 20 sem resposta), commitado antes de qualquer pontuação ser
calculada (`ca50753`). O critério, também pré-registrado: no máximo 5% de
recusas indevidas. Resultado: **limiar = 13,8059**, que recusa 1 de 20
respondíveis e 16 de 20 sem resposta
(`docs/figuras/grafico_calibracao_limiar.png`). O máximo de Youden, que não
foi usado, coincide.

| Grupo | Métrica | v5 | v6 |
|---|---|---|---|
| Norma ausente (6 casos) | recusas sem base (corretas) | 0/18 | 12/18 |
| | casos com sucesso | 5/6 | 6/6 |
| Normativo no corpus (39) | recusas sem base (indevidas) | 0/117 | **63/117** (21 casos) |
| | casos com sucesso | 39/39 | 18/39 |
| | Acerto@3 | 0,795 | 0,436 |
| Parecer e fora de escopo mal classificados (3 casos) | recusa antes da síntese | 0/9 | 9/9 |
| Total (66) | Acerto@3 (44 rotulados) | 0,750 | 0,386 |
| | latência mediana / p95 | 1,66 s / 13,7 s | 0,14 s / 7,8 s |

Dos 21 casos normativos recusados, 11 estavam corretos no v5. **O limiar
não transferiu da calibração para o benchmark**: 5% de recusas indevidas
previstas, 54% observadas. A pontuação BM25 soma a contribuição dos termos
da pergunta, e as perguntas do benchmark são mais curtas (mediana do melhor
trecho nos normativos: 13,66, contra 17,29 nas respondíveis da
calibração). O limiar não foi reajustado depois de visto o resultado. Com a
pontuação bruta, a v6 não é recomendada como configuração de uso. A
normalização da pontuação fica como trabalho futuro. Arquivos:
`comparacao_v5_v6.csv`, `casos_recusados_v6.csv`, `calibracao_limiar.csv`.

## Tarefa B — segundo avaliador

**Não executada**, por decisão do autor: a amostra estratifica pelos
vereditos da auditoria v5, que ainda estão em revisão
(`conferencia_vereditos_v5.csv`). Fica para depois da revisão, conforme o
plano aprovado: 40 respostas com todas as incorretas e as recusas do
modelo, planilha cega com seed registrada, rubrica de uma página com
exemplos de fora da amostra e script de κ de Cohen. O κ é calculado sem
ponderação, mais um κ secundário na versão binária "aceitável × não
aceitável", porque as cinco categorias não formam uma escala ordenada.

## Tarefa C — ablação da Camada 7

C1 desliga `validar_resposta`. C2 também tira `POLITICA_SINTESE` (síntese
sem mensagem de sistema). As recusas por classificação e a recusa sem base
continuam, e o limiar fica desligado. A medida é offline: o **mesmo**
`validar_resposta` desligado nas variantes, aplicado à resposta crua do
LLM, sem alterar os JSONs. Ela herda os limites do validador. "Fonte não
oficial" é uma medida nova, que não pertence ao validador.

| Medida (162 sínteses por variante) | v5 | C1 | C2 |
|---|---|---|---|
| Execuções com norma ausente do contexto | 0 | 0 | 5 |
| Execuções com artigo divergente | 0 | 0 | 0 |
| Execuções com valor divergente | 3 | 3 | 3 |
| Execuções com fonte não oficial | 0 | 0 | 0 |
| Execuções com algum aviso | 3 (1,9%) | 3 (1,9%) | 8 (4,9%) |
| Respostas com "Fontes consultadas" | 162 | 0 | 0 |
| Norma ausente: ausência declarada (18 execuções) | 15 | 15 | 9 |
| Latência mediana / p95 | 1,66 s / 13,7 s | 1,70 s / 11,6 s | 1,47 s / 10,2 s |

O que as contagens não mostram:

- **C2, pedidos mal classificados pela Camada 3** (contidos pela política
  nas 9 execuções do v5): o modelo redige a defesa no processo
  sancionador (3/3, duas cortadas pelo teto de 2.048 tokens), escreve a
  função em Python (3/3) e responde "Não há indícios de que você será
  multado" (1/3). A primeira tentativa da C2 entrou em geração sem fim (mais
  de 15.600 tokens) na defesa.
- **As 5 marcações de norma da C2 não são invenção**: são recusas mal
  formuladas. Na direção oposta, uma afirmação falsa da C2 (a IN 759
  "estabelece os requisitos técnicos para a implementação do Pix") passa
  sem marca. A medida lexical erra nos dois sentidos.
- **C1 = v5 na síntese**: as contagens coincidem. A ablação do validador
  só remove o que ele anexa (fontes, avisos, aviso de validação humana).
  Das 162 sínteses da C1, 63 têm texto diferente de todas as repetições do
  v5, efeito do cache do servidor, não da ablação.

Conclusão: na v5, a contribuição da Camada 7 para a síntese vem da
**política no prompt**. O validador pós-geração mede e anexa
proveniência, mas quase não muda o resultado.

Amostra para auditoria manual: `docs/resultados/ablacao_amostra_auditoria.csv`.
São 70 respostas que mudaram em relação ao v5: todas as 30 distintas da C1
e 40 da C2, estratificadas por grupo, seed 20261002, com colunas
`AUDITOR_*`. As da C1 mudaram pelo cache: auditá-las mede a variação de
conteúdo por estado do servidor, não a ablação.

## Desvios do plano

1. **C2 com teto de 2.048 tokens de saída**, só nela (decisão do autor
   durante a execução). O teto fica acima da maior geração do v5 (856,
   numa classificação) e da C1 (773). A 1ª tentativa, sem teto, foi interrompida e descartada.
2. **Tarefa B adiada** até a revisão dos vereditos v5 (decisão do autor).
3. **"Fontes não oficiais"** medida fora do validador, como medida nova
   (decisão do autor).
4. **A ablação não é da Camada 7 inteira**: as recusas fixas (parecer,
   fora de escopo, sem base) são funções da Camada 7 e continuaram ativas,
   como pedido.
5. **Conjunto de calibração redigido pelo assistente**, que também aplicou
   o critério. O viés foi declarado antes do cálculo e se confirmou na
   prática: as perguntas ficaram mais fáceis que as do benchmark.
6. **Paleta da figura de calibração** não passou pelo validador de paleta
   (Node.js não instalado). Usa as posições 1 e 2 da paleta já usada nas
   figuras de publicação, e o grupo também é identificado por marcador e
   rótulo.
7. As datas das rodadas cruzam a meia-noite. Os `timestamp` dos JSONs
   estão em UTC (2026-10-03).

## Commits (locais; sem push, sem tag)

| Commit | Conteúdo |
|---|---|
| `c0ee396` | Benchmark: `--saida` (pasta própria; v5 intocado) |
| `ca50753` | Tarefa A 1/3: limiar no código e calibração pré-registrada |
| `f60636a` | Tarefa A 2/3: calibração (limiar 13,8059) |
| `e8965b8` | Tarefa A 3/3: rodada v6 e comparação com o v5 |
| `1760ad0` | Tarefa C 1/2: ablação no código e medida offline |
| `d9cdac6` | Teto opcional de tokens (desvio 1) |
| `db455af` | Tarefa C 2/2: rodadas C1 e C2, medida e amostra |
| este relatório | commit seguinte |
