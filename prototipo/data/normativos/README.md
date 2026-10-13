# Base de Conhecimento — Atos Normativos do BACEN

Esta pasta armazena o corpus de documentos públicos usado pela Camada 5
(Integração de Conhecimento / RAG).

## Fontes públicas identificadas

- **Portal de Dados Abertos do Banco Central** —
  https://dadosabertos.bcb.gov.br/ (dados estruturados via API)
- **Atos normativos do Open Finance** —
  https://openfinancebrasil.org.br/atos-normativos/
- **Resoluções, Circulares e Instruções Normativas do BCB** — buscar
  diretamente em https://www.bcb.gov.br/estabilidadefinanceira/buscanormas

## Regra de governança do projeto

Somente fontes públicas e oficiais do Banco Central do Brasil devem ser
adicionadas a esta pasta. Nenhuma informação interna, proprietária ou
confidencial de qualquer instituição financeira deve ser utilizada (ver
Capítulo 1, Seção 3 — Objetivo).

## Status

O corpus é montado pelo pipeline `src/layer5_knowledge/ingest_normativos.py`
a partir das URLs oficiais listadas em `fontes_url.json` (ver
`docs/decisoes_arquitetura.md`, Camada 5, "Ingestão por URL e consumo da
Gold"):

| Normativo | Texto usado | Em runtime |
|---|---|---|
| Resolução Conjunta nº 1/2020 (marco regulatório do Open Finance) | PDF consolidado v9 listado na página | sim |
| Circular nº 4.015/2020 (escopo de dados e serviços) | PDF consolidado v5 listado na página | sim |
| Instrução Normativa BCB nº 759/2026 (Manual de Escopo de Dados e Serviços do Open Finance, v8.0) | HTML da página | sim |
| Resolução BCB nº 1/2020 (Pix) | HTML da página (texto tachado removido) | não — só pipeline |
| Resolução CMN nº 4.753/2019 (abertura, manutenção e encerramento de conta de depósitos) | PDF consolidado v6 listado na página | sim |
| Resolução BCB nº 96/2021 (abertura, manutenção e encerramento de contas de pagamento) | HTML da página (o BCB não publica PDF) | sim |
| Resolução CMN nº 4.595/2017 (política de conformidade — compliance) | PDF consolidado v3 listado na página | sim |
| Resolução BCB nº 65/2021 (política de conformidade das instituições de pagamento e outras) | HTML da página (o BCB não publica PDF) | sim |
| Circular nº 3.978/2020 (PLD/FT: política, procedimentos e controles internos) | PDF consolidado v6 listado na página | sim |
| Carta Circular nº 4.001/2020 (indícios de lavagem de dinheiro) | PDF consolidado v4 listado na página | sim |
| Resolução CMN nº 4.968/2021 (sistemas de controles internos) | HTML da página (o BCB não publica PDF) | sim |
| Resolução BCB nº 260/2022 (controles internos das instituições de pagamento e outras) | HTML da página (o BCB não publica PDF) | sim |
| Resolução BCB nº 142/2021 (prevenção de fraudes em serviços de pagamento) | HTML da página (o BCB não publica PDF) | sim |
| Resolução Conjunta nº 6/2023 (compartilhamento de dados sobre indícios de fraudes) | HTML da página (o BCB não publica PDF) | sim |
| Resolução BCB nº 343/2023 (execução do compartilhamento de dados sobre fraudes) | HTML da página (o BCB não publica PDF) | sim |
| Resolução CMN nº 4.893/2021 (política de segurança cibernética) | HTML da página (o BCB não publica PDF) | sim |
| Resolução BCB nº 85/2021 (segurança cibernética das instituições de pagamento e outras) | HTML da página (o BCB não publica PDF) | sim |
| Resolução CMN nº 5.320/2026 (bloqueio de contas ligadas a apostas sem autorização) | HTML da página (o BCB não publica PDF) | sim |

As catorze últimas (contas, compliance, PLD/FT, fraudes e segurança
cibernética) entraram em 2026-10-12 — ver `docs/decisoes_arquitetura.md`,
Camada 5, "Corpus ampliado: contas e compliance". Com elas, o índice tem
440 trechos de 17 normativos (antes, 141 trechos de 3).

Camadas geradas:

- `1_bronze_raw/`: resposta JSON da página do BCB e, quando existe, o PDF
  consolidado mais recente — dado bruto, sem alteração.
- `2_silver_cleaned/`: texto vigente limpo e estruturado por artigo / seção
  de anexo, com as anotações de alteração separadas do texto.
- `3_gold_indexed/`: trechos prontos para a busca (cabeçalho de contexto +
  frequência de tokens) e `indice_bm25.json`. É a única camada lida por
  `src/layer5_knowledge/knowledge_base.py` em runtime.

Pendentes (ver `PENDENTES.md`): Resolução BCB nº 339/2023 (duplicata
escritural) e Resolução BCB nº 32/2020 (requisitos técnicos). A Resolução
BCB nº 32/2020 fica deliberadamente fora do corpus: é a norma ausente do
cenário "Norma Ausente / Fronteira" do benchmark.
Atenção: três outros casos do grupo `norma_ausente` (Resoluções CMN
4.893 e BCB 96, Circular 3.978) perguntam sobre normas que entraram no
corpus em 2026-10-12.

Para incluir um normativo: adicionar a URL da página em `fontes_url.json`
e rodar `python -m src.layer5_knowledge.ingest_normativos`.
