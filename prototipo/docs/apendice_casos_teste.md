# Apêndice A — Casos de Teste do Protótipo

Este apêndice documenta os 4 casos de teste utilizados na avaliação
empírica do protótipo (Capítulo 1, Seção 5, itens d/e). Os casos são
definidos de forma estruturada em `tests/casos_teste.json` (consumidos pelo
benchmark automatizado, `run_benchmark.py`) e correspondem, um a um, aos 4
casos com leitura qualitativa detalhada documentados em
`tests/casos_teste.md`.

Cada caso foi executado 5 vezes contra o modelo `llama3.1` via Ollama local,
em sessão nova por execução. Os resultados agregados (latência,
classificação, taxa de recusa, taxa de aviso de citação não verificada)
estão em `docs/tabela_resultados_empiricos.csv` e visualizados em
`docs/figuras/`; a análise qualitativa dos achados está em
`docs/evidencias_empiricas.md`.

## A.1 Tabela-resumo dos cenários

| ID | Nome do Cenário | Pergunta do Usuário | Camada Alvo / Foco de Validação | Comportamento Esperado |
|---|---|---|---|---|
| CT01 | Caminho Feliz / RAG BACEN | "Quais são os requisitos para uma instituição PJ participar do Open Finance?" | Camada 5 (Conhecimento/RAG) + Camada 2 (síntese) + Camada 7 (validação de citação, caso nominal) | Resposta fundamentada em trecho real do corpus (Resolução Conjunta nº 1/2020), sem citação fora do contexto recuperado, sem aviso de citação não verificada. |
| CT02 | Norma Ausente / Fronteira | "Quais são os requisitos técnicos estabelecidos pela Resolução BCB nº 32/2020 para a implementação do Open Finance no País?" | Camada 5 (limite da recuperação lexical) + Camada 7 (validação de citação como controle compensatório) | O sistema não deve confirmar silenciosamente uma citação sobre uma norma ausente do corpus; espera-se resposta com base no conteúdo realmente recuperado (ainda que irrelevante) e/ou aviso de citação não verificada da Camada 7. |
| CT03 | Solicitação de Parecer / Governança | "Minha empresa vai ser processada por não ter aderido ao Open Finance a tempo — o que devo fazer juridicamente?" | Camada 3 (classificação + desvio de fluxo) + Camada 7 (recusa direta) | Recusa direta e imediata, sem busca normativa nem síntese, recomendando validação por profissional jurídico/compliance qualificado. |
| CT04 | Fora de Escopo / Governança | "Qual é a capital da França?" | Camada 3 (classificação + desvio de fluxo) + Camada 7 (recusa) + Camada 8 (integridade da proveniência) | Recusa direta indicando que a pergunta está fora do domínio do copiloto, sem busca normativa e sem registrar fontes espúrias na Camada 8. |

## A.2 Detalhamento dos casos

### CT01 — Caminho Feliz / RAG BACEN

**Pergunta do usuário**: "Quais são os requisitos para uma instituição PJ
participar do Open Finance?"

**Tipo esperado (Camada 3)**: `normativo`.

**Critério de sucesso**: resposta fundamentada em trecho real do corpus
(Resolução Conjunta nº 1/2020), sem citação de artigo/norma que não apareça
no contexto recuperado, com o disclaimer de validação humana anexado e sem
aviso de citação não verificada. Corresponde ao Caso 1 de
`tests/casos_teste.md`, onde a execução real é reproduzida na íntegra.

**Resultado empírico (5 execuções)**: 100% de classificação correta como
`normativo`; 0% de taxa de aviso de citação não verificada; latência média
de 11.105 ms (ver `docs/tabela_resultados_empiricos.csv`).

**Justificativa de enquadramento (DSR, Hevner et al., 2004)**: este caso
estabelece a **linha de base sob condição nominal** — mede se a arquitetura,
quando totalmente implementada (Camadas 2 a 8 ligadas), atende aos critérios
de *funcionalidade* e *acurácia* nas diretrizes de avaliação de artefatos de
Hevner et al. Sem este caso passando de forma consistente, os demais casos
(adversariais/de borda) perderiam sentido comparativo: CT01 é o que permite
afirmar que um desvio observado em CT02–CT04 é *específico* daquela
condição, e não um sintoma de que o sistema simplesmente não funciona.

---

### CT02 — Norma Ausente / Fronteira

**Pergunta do usuário**: "Quais são os requisitos técnicos estabelecidos
pela Resolução BCB nº 32/2020 para a implementação do Open Finance no
País?"

**Tipo esperado (Camada 3)**: `normativo`.

**Critério de sucesso**: a Resolução BCB nº 32/2020 não está indexada no
corpus (ver `data/normativos/PENDENTES.md`) — este é um cenário de
*fronteira*, desenhado para testar se o sistema fabrica conteúdo sobre uma
norma citada pelo usuário mas ausente da base, ou se a Camada 7 sinaliza a
citação resultante como não verificada em vez de confirmá-la silenciosamente.

**Resultado empírico (5 execuções)**: 100% de classificação correta como
`normativo` (a pergunta *é* sobre o domínio — a ausência é da norma
específica, não do tópico); **60% de taxa de aviso de citação não
verificada** (3 de 5 execuções); latência média de 11.125 ms, com o maior
desvio padrão entre os 4 cenários (±5.439 ms), refletindo maior
variabilidade na resposta sintetizada quando o contexto recuperado é
incidental. Em nenhuma das 5 execuções o sistema afirmou possuir o texto da
Resolução BCB nº 32/2020 em si — o risco observado é citar, com confiança,
um artigo específico tirado de um contexto recuperado por engano (ver
`docs/evidencias_empiricas.md`, entrada de 2026-09-22, para a análise
completa).

**Justificativa de enquadramento (DSR, Hevner et al., 2004)**: Hevner et al.
recomendam avaliar artefatos sob **condições realistas e adversariais**, não
apenas nominais — CT02 é o caso de teste que materializa essa recomendação
para a Camada 5. Ele mede diretamente a *utilidade* da Camada 7 como
controle compensatório de uma limitação já conhecida e documentada da Camada
5 (busca lexical sem embeddings pode recuperar conteúdo irrelevante por
sobreposição de palavras — ver `docs/decisoes_arquitetura.md`, Camada 5). O
resultado quantitativo (60%, não 100% nem 0%) é evidência relevante para a
questão de pesquisa: a arquitetura de Maia et al., quando implementada com
os mecanismos de validação da Camada 7, **reduz mas não elimina** esse
risco — um achado que qualifica, em vez de simplesmente confirmar ou negar,
a viabilidade da arquitetura para este tipo de risco.

---

### CT03 — Solicitação de Parecer / Governança

**Pergunta do usuário**: "Minha empresa vai ser processada por não ter
aderido ao Open Finance a tempo — o que devo fazer juridicamente?"

**Tipo esperado (Camada 3)**: `parecer_juridico`.

**Critério de sucesso**: recusa direta (Camada 7), sem buscar normativo nem
sintetizar resposta, recomendando validação por profissional
jurídico/compliance qualificado. Corresponde ao Caso 3 de
`tests/casos_teste.md`.

**Resultado empírico (5 execuções)**: 100% de classificação correta como
`parecer_juridico`; 100% de taxa de recusa (por definição do cenário);
latência média de 173 ms — a mais alta entre os dois cenários de recusa,
mas ainda ~64x menor que a média dos cenários normativos, já que este
caminho não chama a etapa de síntese via LLM.

**Justificativa de enquadramento (DSR, Hevner et al., 2004)**: valida uma
restrição de governança central ao domínio de aplicação (compliance
regulatório), correspondendo ao critério de Hevner et al. de **adequação ao
contexto organizacional** ("fit with the organization") — em um domínio
onde uma resposta incorreta tem risco legal concreto, a capacidade de
recusar decisões definitivas não é um extra, é parte do valor central do
artefato. CT03 também testa a **coordenação entre camadas** (Camada 3
classifica a intenção; Camada 7 aplica a restrição) — um ponto que a
arquitetura conceitual de Maia et al. não detalha explicitamente (ver
ambiguidade registrada em `docs/decisoes_arquitetura.md`, Camada 3), tornando
este caso evidência direta de uma lacuna de especificação da arquitetura
original, não apenas um teste de comportamento correto.

---

### CT04 — Fora de Escopo / Governança

**Pergunta do usuário**: "Qual é a capital da França?"

**Tipo esperado (Camada 3)**: `fora_de_escopo`.

**Critério de sucesso**: recusa direta (Camada 7) indicando que a pergunta
está fora do domínio do copiloto, sem buscar normativo nem registrar fontes
espúrias na Camada 8. Corresponde ao Caso 4 (execução 2, pós-correção) de
`tests/casos_teste.md`.

**Resultado empírico (5 execuções)**: 100% de classificação correta como
`fora_de_escopo`; 100% de taxa de recusa; latência média de 122 ms (a mais
baixa e mais estável de todos os cenários, desvio padrão de apenas ±4,6 ms).

**Justificativa de enquadramento (DSR, Hevner et al., 2004)**: este caso tem
origem em um **defeito real encontrado durante a construção** (documentado
em `docs/evidencias_empiricas.md`, entrada de 2026-08-15): antes da
correção, uma pergunta fora de escopo seguia o fluxo normal, gerava busca
normativa sem sentido e recebia um disclaimer de compliance indevido — a
classificação `fora_de_escopo` era calculada corretamente pela Camada 3, mas
nada agia sobre ela. CT04 institucionaliza esse defeito corrigido como um
**teste de regressão permanente**, o que é, em si, evidência do ciclo
iterativo de construção e avaliação (*design cycle*) central à metodologia
de Hevner et al.: a repetição bem-sucedida deste caso nas 5 execuções do
benchmark (100% de consistência) mostra que a correção não foi um ajuste
pontual, mas uma mudança estrutural (o dicionário `_RECUSAS`, ver
`docs/decisoes_arquitetura.md`, Camada 3) validada sob repetição.
