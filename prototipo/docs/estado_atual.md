# Estado Atual do Protótipo (para retomar em outra sessão)

**Última atualização**: 2026-08-15 (Camadas 8 e 1 implementadas, e casos de
teste documentados, nesta sessão).

Este documento é um resumo de handoff — para o histórico completo de
decisões e evidências, ver `docs/decisoes_arquitetura.md` e
`docs/evidencias_empiricas.md`, que são as fontes primárias. Este arquivo
só resume o estado para retomar o trabalho rapidamente, em nova sessão.

## Onde estamos na sequência de construção (ver README.md)

1. ✅ Esqueleto do repo + Camada 2 (Núcleo de Raciocínio)
2. ✅ `run_check.py` validado pelo usuário
3. ✅ Camada 3 (Orquestração) — `src/layer3_orchestration/orchestrator.py`
4. ✅ Camada 5 (Conhecimento/RAG) — `src/layer5_knowledge/knowledge_base.py`
5. ✅ Camada 4 (Ferramentas) — `src/layer4_tools/tools.py`
6. ✅ Camada 6 (Memória) — `src/layer6_memory/memory.py`
7. ✅ Camada 7 (Governança) — `src/layer7_governance/governance.py`
8. ✅ Camada 8 (Observabilidade) — `src/layer8_observability/observability.py`
9. ✅ Camada 1 (Interação/CLI) — `src/layer1_interaction/cli.py` (`python main.py`)
10. ✅ Casos de teste documentados em `tests/casos_teste.md` (4 casos)

Cada camada implementada tem: código em `src/layerN_*/`, script de
validação `run_check_*.py` na raiz, entrada em
`docs/decisoes_arquitetura.md`, e (quando relevante) entrada em
`docs/evidencias_empiricas.md`.

## Como validar o que já existe

```bash
python run_check.py                # Camada 2
python run_check_orchestration.py  # Camada 3, fluxo completo (3 perguntas: normativa, acompanhamento, parecer jurídico)
python run_check_knowledge.py      # Camada 5
python run_check_tools.py          # Camada 4
python run_check_memory.py         # Camada 6
python run_check_governance.py     # Camada 7
python run_check_observability.py  # Camada 8
```

Nota de ambiente: neste ambiente Windows, `python` só resolve corretamente
dentro do venv do projeto (`venv\Scripts\activate`) ou usando o caminho
completo `C:\Users\pedro\AppData\Local\Programs\Python\Python314\python.exe`
— sessões de shell abertas antes da instalação do Python não pegam o PATH
atualizado.

## Corpus atual (Camada 5) — `data/normativos/`

Indexados com texto integral:
- `resolucao_conjunta_1_2020.md` — Resolução Conjunta nº 1/2020 (marco do Open Finance)
- `circular_4015_2020.md` — Circular nº 4.015/2020 (escopo de dados e serviços)

Pendentes (ver `data/normativos/PENDENTES.md`) — ementa/citação confirmadas,
texto oficial ainda não localizado com segurança:
- Resolução BCB nº 339/2023 (duplicata escritural) — há uma página oficial
  de referência confirmada (`bcb.gov.br/estabilidadefinanceira/duplicatas-escriturais`),
  mas não o PDF direto.
- Resolução BCB nº 32/2020 (requisitos técnicos) — nem página nem PDF confirmados.

## Principais achados empíricos até agora (ver `docs/evidencias_empiricas.md` para detalhes)

1. Sem Camada 5/7: o modelo citou uma norma inventada ("Resolução do CPM 4.665/2021").
2. Com Camada 5 (contexto real), o modelo ainda distorceu um número presente no próprio contexto (disse "50 mil clientes" onde o texto dizia "cinco milhões").
3. Erro de atribuição de artigo ("art. 51" em vez do correto Art. 6º) apareceu em execuções independentes — padrão recorrente, não isolado.
4. Camada 7 pegou corretamente uma citação de artigo não presente no contexto em teste controlado.
5. Bug de implementação encontrado e corrigido: memória guardava a resposta já com o disclaimer de governança anexado, causando eco/duplicação do disclaimer em turnos seguintes.
6. Limitação conhecida, não corrigida: `validar_citacao` só valida contra o contexto normativo do turno atual, não contra o que está na memória de turnos anteriores — pode gerar aviso "tecnicamente correto" mas que soa como falso positivo ao ler a conversa inteira.
7. `logs/interacoes.jsonl` (Camada 8), gerado ao rodar `run_check_orchestration.py` com as 3 perguntas de teste, confirma em registro estruturado o padrão do achado 3: a segunda pergunta tem `aviso_citacao_nao_verificada: true`, citando "art. 6, 36" fora do trecho normativo daquele turno — mesma classe de erro de atribuição de artigo, agora capturada também na proveniência, não só no texto da resposta.
8. Gap encontrado ao formalizar `tests/casos_teste.md` (Caso 4): a classificação `fora_de_escopo` (Camada 3) era calculada corretamente, mas — diferente de `parecer_juridico` — não desviava o fluxo, causando busca normativa sem sentido e disclaimer de compliance indevido. **Corrigido na mesma sessão** — `_RECUSAS` generalizou o desvio já usado para `parecer_juridico`; ver `tests/casos_teste.md`, Caso 4 (execução 2, após a correção).

## Convenções de trabalho estabelecidas nesta sessão (aplicar nas próximas)

- Propor o plano de cada camada e aguardar aprovação antes de implementar — camada por camada, não tudo de uma vez.
- Atualizar `docs/decisoes_arquitetura.md` a cada camada (decisão, motivação, ambiguidade, adaptação).
- Registrar observações de teste (comportamento do modelo, bugs encontrados) em `docs/evidencias_empiricas.md`, separado das decisões de projeto.
- Fontes do corpus: só atos normativos públicos e oficiais do BACEN — nunca conhecimento interno/proprietário de instituição financeira (o usuário trabalha em fintech PJ — conflito de interesse a evitar).
- Preferir decisões de implementação mínimas e explícitas (funções simples em vez de abstrações genéricas) até haver um segundo caso de uso real que justifique generalizar — aplicado nas Camadas 4 e 6.

## Próximo passo sugerido

Todos os itens da sequência de construção original (README.md) estão
concluídos: 8 camadas implementadas e ligadas ponta a ponta, 4 casos de
teste formais documentados em `tests/casos_teste.md` — incluindo o gap de
`fora_de_escopo` encontrado e corrigido na mesma sessão (Caso 4).

Com o protótipo completo, o próximo passo de mais alto nível passa a ser de
síntese para a monografia, não mais de construção: revisar
`docs/decisoes_arquitetura.md` e `docs/evidencias_empiricas.md` como um
todo para compilar a análise de viabilidade (Capítulo 1, Seção 5, itens d/e).
