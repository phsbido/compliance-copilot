# Visão Geral — Copiloto de Compliance Regulatório (Open Finance / Contas PJ)

> **Nota (2026-09-24):** esta pasta `analise/` é um retrato do código em 2026-09-23. Depois dela: o pipeline `ingest_normativos.py` passou a ingerir por URL oficial do BCB (`data/normativos/fontes_url.json`) em vez de PDFs locais (os artefatos `normativoPix*`/`normativoOpenFinance*` viraram `resolucao_bcb_1_2020*`/`instrucao_normativa_bcb_759_2026*`); `_openfinance_limpo.md` foi removido do repositório (papel coberto pela camada silver); o benchmark ganhou o modo determinístico e o dado bruto passou para `docs/resultados/`. Ver `docs/decisoes_arquitetura.md`, seção "Reprodutibilidade". Também em 2026-09-24, a Camada 5 foi refeita (runtime lê a camada Gold com BM25; os `.md` curados saíram de `data/normativos/`): tudo o que esta pasta descreve sobre `knowledge_base.py` refere-se à v1 (tag `v1.0-monografia`). Em 2026-10-02, o benchmark passou à bateria v5 (66 casos, cinco grupos, 3 repetições, métricas de recuperação e de sucesso por caso): o que esta pasta diz sobre "4 cenários x 5 repetições" refere-se às versões v1–v4.1 (ver a nota em `06_testes_config_operacao.md`).

## O que é, em uma frase

Um chatbot de linha de comando que responde perguntas sobre **Open Finance**
e **contas PJ** no Brasil, fundamentando cada resposta em textos oficiais do
Banco Central do Brasil (BACEN) já carregados em disco, e que recusa
ativamente dar "parecer jurídico" ou responder fora desse tema.

## Para quem nunca viu o projeto

Não é um produto — é um **protótipo acadêmico** (artefato de pesquisa DSR —
*Design Science Research* — para uma monografia de especialização, ver
`README.md:3-9`). O objetivo da pesquisa não é "construir um copiloto de
compliance", é **testar se uma arquitetura conceitual de 8 camadas** (proposta
por Maia et al., 2026) é viável de implementar na prática, usando esse
copiloto como caso de uso concreto.

Por isso duas coisas saltam aos olhos ao ler o código pela primeira vez:

1. **A estrutura de pastas espelha a teoria, não o domínio.** `src/` não tem
   pastas como `chat/`, `search/`, `api/` — tem `layer1_interaction/` até
   `layer8_observability/`, uma por camada da arquitetura de Maia et al.
   (`README.md:22-31`). Isso é proposital: o objetivo é rastreabilidade
   direta entre teoria e implementação, não um design de software "natural"
   para o problema.
2. **Cada decisão de projeto está documentada, com data, em
   `docs/decisoes_arquitetura.md`, e cada observação de comportamento do
   modelo está documentada, com data, em `docs/evidencias_empiricas.md`.**
   Esses dois arquivos são, em si, o principal produto de pesquisa do
   projeto — mais importantes para a monografia do que o código em si.

## O que o sistema faz, na prática

1. Usuário roda `python main.py` e digita uma pergunta em português.
2. O sistema classifica a pergunta em um de três tipos: `normativo` (sobre
   requisito regulatório), `parecer_juridico` (pede decisão jurídica sobre
   caso concreto) ou `fora_de_escopo` (não é sobre Open Finance/PJ).
3. Se for `parecer_juridico` ou `fora_de_escopo`, recusa direto, com uma
   frase fixa — sem gastar tempo nem custo computacional de mais nenhuma
   camada.
4. Se for `normativo`, busca trechos relevantes em um corpus local de atos
   normativos do BACEN (2 normas com texto integral: Resolução Conjunta nº
   1/2020 e Circular nº 4.015/2020 — `data/normativos/README.md:24-29`),
   monta um prompt com esses trechos + histórico da conversa, pede ao
   modelo de linguagem (`llama3.1`, rodando localmente via Ollama) para
   sintetizar uma resposta, e então **audita a própria resposta**: confere
   se todo artigo/norma citado pelo modelo realmente aparece no trecho que
   foi dado como contexto. Se não aparecer, anexa um aviso visível.
5. Sempre anexa um disclaimer fixo dizendo que a resposta não é parecer
   jurídico definitivo.
6. Registra cada interação em `logs/interacoes.jsonl` — uma linha JSON por
   pergunta, com a classificação, as fontes usadas e se houve aviso de
   citação não verificada.

## Por que isso é interessante como pesquisa (não só como produto)

Os autores documentaram, ao testar o próprio sistema, que o modelo de
linguagem **inventa citações normativas plausíveis mas falsas** quando não
tem uma base de conhecimento real (`docs/evidencias_empiricas.md:19-51`,
entrada de 2026-08-14), e que **mesmo recebendo o texto certo como contexto,
ainda distorce números e atribui trechos ao artigo errado**
(`docs/evidencias_empiricas.md:85-129`). O sistema de checagem por regex da
Camada 7 (Governança) foi desenhado especificamente para pegar essas duas
classes de erro — e o benchmark quantitativo (`docs/tabela_resultados_empiricos.csv`)
mostra que ele pega, mas não sempre: no cenário de "norma citada pelo usuário
mas ausente do corpus", o aviso de citação não verificada dispara em 60% das
execuções, não 100% (ver `docs/apendice_casos_teste.md:70-80`). Essa é a
descoberta central do projeto: **RAG + validação por regex reduz, mas não
elimina, o risco de citação incorreta em domínio regulatório.**

## O que o sistema explicitamente NÃO faz

- Não tem interface web, API HTTP nem multimodalidade — é CLI de texto puro,
  por decisão explícita de escopo (`README.md:41-42`).
- Não usa embeddings nem vector database — a busca no corpus é por
  sobreposição literal de palavras (`src/layer5_knowledge/knowledge_base.py:96-105`).
- Não persiste memória entre execuções — cada sessão de `python main.py`
  começa com histórico vazio (`src/layer6_memory/memory.py:8-10`).
- Não usa nenhum framework de orquestração de agentes (CrewAI, LangGraph
  etc.) — todo o fluxo é uma classe Python simples com 4 métodos privados
  chamados em sequência fixa (ver `05_decisoes_de_design.md`).
- Não paga por nenhuma API — tudo roda localmente via Ollama, sem chave de
  API (`README.md:240-243`), decisão motivada por reprodutibilidade
  científica, não por limitação técnica.

## Mapa de leitura desta análise

- `01_mapa.md` — estrutura de pastas, dependências, pontos de entrada.
- `02_fluxo_execucao.md` — o que acontece, passo a passo, ao rodar `python
  main.py` e fazer uma pergunta (com diagrama).
- `03_modulos/` — um arquivo por módulo/camada, com detalhamento função a
  função.
- `04_dados_e_estado.md` — como os dados se transformam, onde o estado vive.
- `05_decisoes_de_design.md` — o "porquê" de cada decisão não óbvia.
- `06_testes_config_operacao.md` — como rodar, testar e reproduzir os
  experimentos.
- `07_riscos.md` — bugs prováveis, limitações conhecidas, código órfão.
- `08_glossario.md` — termos de domínio e nomes internos.
- `09_perguntas_em_aberto.md` — o que não consegui determinar com certeza.
