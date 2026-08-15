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

Recorte inicial em andamento. Indexados com texto integral:

- `resolucao_conjunta_1_2020.md` — Resolução Conjunta nº 1/2020 (marco
  regulatório do Open Finance)
- `circular_4015_2020.md` — Circular nº 4.015/2020 (escopo de dados e
  serviços)

Pendentes (ver `PENDENTES.md`): Resolução BCB nº 339/2023 (duplicata
escritural) e Resolução BCB nº 32/2020 (requisitos técnicos) — ementa e
citação confirmadas, texto oficial ainda não localizado com segurança.

Cada arquivo indexado segue o formato: cabeçalho de metadados (título,
ementa, URL oficial, data, versão) + texto integral, consumido por
`src/layer5_knowledge/knowledge_base.py`.
