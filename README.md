# Copiloto de Compliance Regulatório LLM-Native (Open Finance / Contas PJ)

Protótipo desenvolvido como artefato de Design Science Research para a monografia
de especialização *"Aplicações LLM-Native: Implementação e Avaliação de Viabilidade
da Arquitetura Conceitual de Maia et al. (2026)"*.

**Autor**: Pedro Henrique dos Santos Bido
**Orientadora**: Prof.ª Ana Claudia Rossi

> Todo o código fica em [`prototipo/`](prototipo/). **Os comandos deste README
> devem ser executados de dentro dessa pasta** (`cd prototipo`). Para
> reproduzir os experimentos da monografia, vá direto à
> [Seção 6 — Tutorial de reprodução](#6-tutorial-de-reprodução).

## 1. Visão geral

Este protótipo é um copiloto de compliance regulatório que responde perguntas
sobre requisitos de **Open Finance** e **contas PJ** no Brasil, fundamentado
**exclusivamente** em atos normativos públicos do Banco Central do Brasil
(BACEN). Ele sempre cita a norma-fonte e nunca emite parecer jurídico
definitivo.

O código é organizado espelhando, pasta por pasta, as **oito camadas da
arquitetura conceitual de "Aplicações LLM-Native" de Maia et al. (2026, Seção
8)**, para rastreabilidade direta entre a proposta teórica e a implementação:

| # | Camada (Maia et al., 2026) | Pasta | Status |
|---|---|---|---|
| 1 | Interação com o Usuário | [`src/layer1_interaction/`](prototipo/src/layer1_interaction/) | implementada — CLI (`python main.py`) |
| 2 | Núcleo de Raciocínio do LLM | [`src/layer2_llm_core/`](prototipo/src/layer2_llm_core/) | implementada |
| 3 | Orquestração e Fluxo de Trabalho | [`src/layer3_orchestration/`](prototipo/src/layer3_orchestration/) | implementada |
| 4 | Integração de Ferramentas e Serviços | [`src/layer4_tools/`](prototipo/src/layer4_tools/) | implementada |
| 5 | Integração de Conhecimento (RAG) | [`src/layer5_knowledge/`](prototipo/src/layer5_knowledge/) | implementada |
| 6 | Contexto e Memória | [`src/layer6_memory/`](prototipo/src/layer6_memory/) | implementada |
| 7 | Governança e Segurança | [`src/layer7_governance/`](prototipo/src/layer7_governance/) | implementada |
| 8 | Observabilidade e Proveniência | [`src/layer8_observability/`](prototipo/src/layer8_observability/) | implementada |

Todas as 8 camadas estão implementadas e ligadas ponta a ponta. A base de
conhecimento (Camada 5) é gerada por um pipeline Bronze/Silver/Gold que
ingere as normas a partir das URLs oficiais do BCB; o protótipo consulta a
camada Gold com busca BM25 (ver Seção 6, Passo 4). Além do protótipo, o
repositório inclui os artefatos de avaliação empírica:

- 4 casos de teste qualitativos: [`tests/casos_teste.md`](prototipo/tests/casos_teste.md)
  (execuções documentadas na v1, antes da Camada 5 baseada na Gold);
- um benchmark quantitativo reprodutível ([`run_benchmark.py`](prototipo/run_benchmark.py)),
  em dois modos (configuração de produção e análise de sensibilidade), com dado bruto versionado;
- o diagrama de arquitetura: [`docs/diagrama_arquitetura.md`](prototipo/docs/diagrama_arquitetura.md).

Aspectos multimodais da Camada 1 estão explicitamente fora de escopo (ver
Capítulo 1, Seção 5 — Metodologia).

## 2. Pré-requisitos

1. **Python 3.12+**. O ambiente de referência usa 3.14.7 (ver Seção 5).
   Com Python 3.10 ou 3.11, instale por `requirements.txt` em vez de
   `requirements-lock.txt`, porque as versões fixadas de `numpy`/`contourpy`
   exigem 3.12+.
2. **Git**.
3. **Ollama** instalado localmente: https://ollama.com/download
4. O modelo `llama3.1` baixado localmente (tag padrão = 8B, quantização
   Q4_K_M, cerca de 4,9 GB em disco; recomenda-se ~8 GB de RAM livre):

   ```bash
   ollama pull llama3.1
   ```

## 3. Instalação

```bash
git clone https://github.com/phsbido/prototipo_esqueleto.git
cd prototipo_esqueleto/prototipo

python -m venv venv
# Windows (PowerShell):  venv\Scripts\activate
# Linux/macOS:           source venv/bin/activate

pip install -r requirements-lock.txt   # versões exatas do ambiente de referência
# ou: pip install -r requirements.txt  # versões mínimas, se o lock não instalar

# Windows:      copy .env.example .env
# Linux/macOS:  cp .env.example .env
```

Dependências:

- `ollama` e `python-dotenv` são usadas em runtime pelo protótipo.
- `pypdf` é usada pela ingestão da base de conhecimento
  (`ingest_normativos.py`), para ler os PDFs consolidados do BCB.
- `pandas`, `matplotlib` e `seaborn` são usadas só pelos scripts de avaliação
  empírica (`run_benchmark.py` e `scripts/plot_benchmark.py`), não pelo `main.py`.
- `requirements-lock.txt` é a saída de `pip freeze` do ambiente de referência.

O `.env` define:

| Variável | Padrão | Uso |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1` | Modelo |
| `OLLAMA_HOST` | `http://localhost:11434` | Endereço do servidor Ollama |
| `OLLAMA_TEMPERATURA_CLASSIFICACAO` | `0` | Classificação da pergunta (normativo / parecer / fora de escopo) |
| `OLLAMA_TEMPERATURA_SINTESE` | `0.1` | Síntese da resposta |
| `OLLAMA_SEED` | `42` | Seed (vazio = aleatória) |

Temperatura e seed são explícitas desde a v4 (antes valia o padrão do
Ollama: 0,8 e seed aleatória); a justificativa está em
`docs/decisoes_arquitetura.md`, Camada 2. Cada interação registra modelo, ID
do modelo, temperaturas e seed em `logs/interacoes.jsonl`.

## 4. Usando o protótipo

### 4.1. Subindo o Ollama

O Ollama normalmente inicia um servidor local automaticamente após a
instalação. Se não estiver rodando, suba-o em um terminal separado:

```bash
ollama serve
```

Recomenda-se "aquecer" o modelo antes de usar ou demonstrar o protótipo
(opcional; o protótipo em si chama o modelo via `ollama.chat`, não via este
comando). Assim a primeira resposta não inclui o tempo de carregar o modelo
na memória:

```bash
ollama run llama3.1 "oi"
```

### 4.2. CLI interativa (Camada 1)

```bash
python main.py
```

Todas as 8 camadas estão ligadas em um loop de conversa
(`src/layer1_interaction/cli.py`). O loop mantém a memória da sessão
(Camada 6). Cada resposta sai da Camada 7 com as fontes consultadas (título
e URL), os avisos de norma, artigo ou valor não verificado na fonte e o
aviso de validação humana. Digite `sair`,
`exit` ou `quit` para encerrar. Cada interação é registrada em
`logs/interacoes.jsonl` (Camada 8) para auditoria posterior.

Perguntas de exemplo, uma por comportamento avaliado (são os 4 cenários do
benchmark):

| Pergunta | Comportamento esperado |
|---|---|
| Quais são os requisitos para uma instituição PJ participar do Open Finance? | Resposta fundamentada na Resolução Conjunta nº 1/2020 (seção "Da Participação no Open Finance") |
| Quais são os requisitos técnicos estabelecidos pela Resolução BCB nº 32/2020 para a implementação do Open Finance no País? | Norma fora do corpus: resposta frequentemente acompanhada de aviso de citação não verificada |
| Minha empresa vai ser processada por não ter aderido ao Open Finance a tempo — o que devo fazer juridicamente? | Recusa (Camada 7): não emite parecer jurídico |
| Qual é a capital da França? | Recusa (Camada 7): fora de escopo |

### 4.3. Validando cada camada isoladamente

Testes automatizados da governança (Camada 7) e da limpeza da ingestão
(Camada 5), sem LLM, com casos reais dos benchmarks e da extração dos PDFs:

```bash
python -m unittest discover -s tests -v
```

Scripts de validação por camada:

```bash
python run_check_knowledge.py      # Camada 5 — Conhecimento/RAG (não usa o LLM)
python run_check_tools.py          # Camada 4 — Ferramentas
python run_check_memory.py         # Camada 6 — Memória
python run_check.py                # Camada 2 — Núcleo de Raciocínio
python run_check_orchestration.py  # Camada 3 — Orquestração (fluxo completo, 3 perguntas)
python run_check_governance.py     # Camada 7 — Governança
python run_check_observability.py  # Camada 8 — Observabilidade
```

## 5. Ambiente de referência

Os resultados versionados em `docs/` foram produzidos neste ambiente:

| Item | Versão |
|---|---|
| Sistema operacional | Windows 11 Home (10.0.26200) |
| Python | 3.14.7 |
| Ollama | 0.33.2 |
| Modelo | `llama3.1:latest` — ID `46e0c10c039e`, 8.0B, Q4_K_M |
| Amostragem (produção) | classificação temperatura 0, síntese 0,1, seed 42 |
| Pacotes Python | [`requirements-lock.txt`](prototipo/requirements-lock.txt) |

Para conferir o ID do seu modelo, rode `ollama list`. Se o ID for diferente
(a tag `latest` pode mudar com o tempo), as taxas devem ser parecidas, mas o
texto das respostas pode mudar.

## 6. Tutorial de reprodução

Quatro níveis de reprodução, do mais simples ao mais completo. Todos partem
da instalação da Seção 3, dentro de `prototipo/` e com o venv ativado.

### Passo 0 — Escolher a versão

Versões avaliadas. Cada uma muda uma única coisa em relação à anterior:

| Tag | Camada 5 | Resultados |
|---|---|---|
| `v4.1-monografia` (atual) | v4 com **limpeza do texto extraído de PDF** na ingestão (espaço antes do hífen, palavras partidas) | `docs/tabela_resultados_empiricos*.csv`, `docs/resultados/*.json` |
| `v4.0-monografia` | v3.1 com **temperatura e seed explícitas** (classificação 0, síntese 0,1, seed 42) e registradas na Camada 8; benchmark nos modos `producao` e `sensibilidade` | `docs/resultados/v4/` |
| `v3.1-monografia` | v3 com a regra 3 da política de síntese reescrita (citação entre parênteses, sem copiar cabeçalhos) | `docs/resultados/v3.1/` |
| `v3.0-monografia` | Camada 5 da v2 + **Camada 7 v2**: política de síntese, recusa sem base, verificação de norma/artigo/valor, ausência declarada, fontes anexadas | `docs/resultados/v3/` |
| `v2.0-monografia` | Gold do pipeline Bronze/Silver/Gold ingerido por URL + busca BM25 | `docs/resultados/v2/` |
| `v1.0-monografia` | 2 normas curadas manualmente (`.md`) + contagem de palavras em comum | `docs/resultados/v1/` |

```bash
git checkout v4.1-monografia
```

### Passo 1 — Conferir a base de conhecimento e as tabelas sem internet e sem Ollama (~10 s)

A camada Bronze (dado bruto baixado do BCB) está versionada. O primeiro
comando regera a Silver e a Gold a partir dela, sem acessar a internet. Os
outros regeram as tabelas agregadas a partir do dado bruto do benchmark,
sem chamar o LLM:

```bash
python -m unittest discover -s tests
python -m src.layer5_knowledge.ingest_normativos --a-partir-da-bronze
python run_benchmark.py --revalidar
python run_benchmark.py --revalidar --modo sensibilidade
python scripts/plot_benchmark.py
```

`--revalidar` reaplica a Camada 7 à resposta do LLM e ao contexto guardados
em cada execução, e regera a tabela. Assim a governança pode ser conferida
(ou alterada e medida de novo) sem gerar respostas novas.

**Resultado esperado**:
`git diff --ignore-cr-at-eol --stat -- data/normativos docs/*.csv` não
mostra nenhuma diferença. A base consultada pelo modelo sai exatamente do
dado bruto publicado, e a validação e as tabelas saem exatamente das
execuções publicadas. Os gráficos em `docs/figuras/` são regerados a partir da
tabela do modo produção.

### Passo 2 — Configuração de produção (~5 min)

Roda os 4 cenários de [`tests/casos_teste.json`](prototipo/tests/casos_teste.json),
5 repetições cada, com a configuração do `.env` — a mesma do `main.py`
(classificação com temperatura 0, síntese com 0,1, seed 42):

```bash
python run_benchmark.py
```

**Resultado esperado** (compare com
[`docs/tabela_resultados_empiricos.csv`](prototipo/docs/tabela_resultados_empiricos.csv)):

| Cenário | Classificação correta | Recusa | Ausência declarada | Aviso da Camada 7 | Respostas distintas |
|---|---|---|---|---|---|
| Caminho Feliz / RAG BACEN | 100% | 0% | 0% | 0% | 2 |
| Norma Ausente / Fronteira | 100% | 0% | 100% | 0% | 1 |
| Solicitação de Parecer / Governança | 100% | 100% | 0% | 0% | 1 |
| Fora de Escopo / Governança | 100% | 100% | 0% | 0% | 1 |

No cenário "norma ausente", o modelo responde que a Resolução BCB nº 32/2020
não está no contexto e não descreve o conteúdo dela; a Camada 7 registra
isso como *ausência declarada*, não como citação não verificada.

No caminho feliz, as repetições 2 a 5 saem idênticas e a primeira difere num
trecho acessório (primeira vez em que o Ollama processa aquele prompt —
ver `docs/evidencias_empiricas.md`, v4); na rodada da v4.1, as 5 respostas
da norma ausente saíram idênticas. No mesmo ambiente da Seção 5, o
texto deve bater com `docs/resultados/resultados_benchmark.json`; em outro
hardware ou outra versão do Ollama/modelo, espera-se que as taxas se
mantenham, mas o texto pode variar. A latência depende da máquina.

### Passo 3 — Análise de sensibilidade (temperatura 0,8, ~5 min)

Mesmos cenários com temperatura 0,8 nas duas chamadas e seed aleatória — o
padrão do Ollama, usado até a v3.1. Mostra o que a configuração de produção
evita:

```bash
python run_benchmark.py --modo sensibilidade
```

**Resultado esperado** (compare com
[`docs/tabela_resultados_empiricos_sensibilidade.csv`](prototipo/docs/tabela_resultados_empiricos_sensibilidade.csv)):
classificação correta e recusas em 100%; respostas diferentes a cada
repetição (`n_respostas_distintas` perto de 5). Na rodada publicada (v4.1), 1 das 5
respostas do caminho feliz inventou o limite de clientes ("50 mil") e foi
sinalizada pela Camada 7 como valor não verificado (na v4, 2 de 5: "3,5
milhões" e "100 mil"). Por
ser aleatório, esse número varia de uma rodada para outra.

> A coluna `taxa_aviso_citacao_nao_verificada` usa a régua da v1/v2, que
> conta como aviso qualquer menção a norma fora do contexto — inclusive a
> declaração honesta de que a norma não está no corpus. Ela é mantida só
> para comparar versões; para ler o comportamento atual, use as colunas
> `taxa_norma_nao_verificada`, `taxa_ausencia_declarada`,
> `taxa_artigo_nao_verificado` e `taxa_valor_nao_verificado`. Ver
> `docs/evidencias_empiricas.md`, 2026-09-24 (Camada 7 v2).

> Os passos 2 e 3 sobrescrevem os arquivos versionados em `docs/` com os
> seus resultados. Use `git diff` para comparar e `git checkout -- docs/`
> para restaurar os originais.

### Passo 4 (opcional) — Baixar os normativos de novo pelas URLs oficiais

Refaz a base de conhecimento do zero a partir das páginas do BCB listadas
em [`data/normativos/fontes_url.json`](prototipo/data/normativos/fontes_url.json)
(precisa de internet):

```bash
python -m src.layer5_knowledge.ingest_normativos
```

| Normativo | URL oficial | Em runtime |
|---|---|---|
| Resolução Conjunta nº 1/2020 (marco regulatório do Open Finance) | https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=1 | sim |
| Circular nº 4.015/2020 (escopo de dados e serviços) | https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Circular&numero=4015 | sim |
| Instrução Normativa BCB nº 759/2026 (Manual de Escopo de Dados e Serviços do Open Finance, v8.0) | https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Instru%C3%A7%C3%A3o%20Normativa%20BCB&numero=759 | sim |
| Resolução BCB nº 1/2020 (institui o Pix) | https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=1 | não (só pipeline) |

Como cada camada funciona:

- **Bronze** (`1_bronze_raw/`): o JSON que a própria página consome e,
  quando a página lista versões consolidadas, o PDF consolidado mais recente.
  Para normas anteriores a 2021, o texto em HTML da página é a redação
  original; o texto vigente só existe nesses PDFs.
- **Silver** (`2_silver_cleaned/`): texto vigente limpo (sem texto tachado,
  rodapés e anotações de alteração) e estruturado por artigo ou seção de
  anexo.
- **Gold** (`3_gold_indexed/`): trechos de até 2.500 caracteres com
  cabeçalho de contexto (norma, capítulo/seção, artigo) e índice BM25. É a
  única camada lida pelo protótipo.

**Resultado esperado**: 4 normativos em cada camada e um índice BM25 com as
3 normas de runtime. O BCB publica sempre a versão vigente, então o texto
baixado pode diferir do versionado se alguma norma for alterada depois de
2026-09-24. A versão usada fica registrada no JSON bruto em `1_bronze_raw/`.

### Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| `python` não encontrado ou abre a Microsoft Store (Windows) | Ative o venv (`venv\Scripts\activate`) ou abra um novo terminal após instalar o Python |
| `ConnectionError` / `connection refused` | Ollama não está rodando: `ollama serve` |
| `model "llama3.1" not found` | `ollama pull llama3.1` |
| Primeira resposta muito lenta | Carregamento do modelo; rode `ollama run llama3.1 "oi"` antes |
| `pip install -r requirements-lock.txt` falha | Python < 3.12; use `requirements.txt` |

## 7. Estrutura de pastas

```
prototipo_esqueleto/
├── README.md                          # Este arquivo
└── prototipo/
    ├── main.py                        # Ponto de entrada (Camada 1 — CLI)
    ├── run_benchmark.py               # Benchmark quantitativo (Seção 6)
    ├── run_check*.py                  # Validação por camada (Seção 4.3)
    ├── requirements.txt               # Dependências (versões mínimas)
    ├── requirements-lock.txt          # Versões exatas do ambiente de referência
    ├── .env.example                   # Modelo e host do Ollama
    ├── scripts/
    │   ├── plot_benchmark.py          # Gráficos de publicação
    │   └── acompanhar_log.ps1         # Acompanha o log da Camada 8 em tempo real
    ├── src/
    │   ├── config.py                  # Configuração transversal (.env)
    │   ├── layer1_interaction/        # Camada 1 — Interação com o Usuário (CLI)
    │   ├── layer2_llm_core/           # Camada 2 — Núcleo de Raciocínio do LLM
    │   ├── layer3_orchestration/      # Camada 3 — Orquestração e Fluxo de Trabalho
    │   ├── layer4_tools/              # Camada 4 — Integração de Ferramentas e Serviços
    │   ├── layer5_knowledge/          # Camada 5 — busca BM25 na Gold (knowledge_base.py), ingestão (ingest_normativos.py), tokenização (texto.py)
    │   ├── layer6_memory/             # Camada 6 — Contexto e Memória
    │   ├── layer7_governance/         # Camada 7 — Governança e Segurança
    │   └── layer8_observability/      # Camada 8 — Observabilidade e Proveniência
    ├── data/normativos/
    │   ├── fontes_url.json            # URLs oficiais das normas (entrada da ingestão)
    │   ├── 1_bronze_raw/              # Dado bruto: JSON da página do BCB + PDF consolidado
    │   ├── 2_silver_cleaned/          # Texto vigente limpo, estruturado por artigo/seção
    │   ├── 3_gold_indexed/            # Trechos prontos para a busca + indice_bm25.json (lido em runtime)
    │   ├── README.md                  # Fontes e regra de governança do corpus
    │   └── PENDENTES.md               # Normas aprovadas ainda sem texto verificado
    ├── tests/
    │   ├── test_governanca.py         # Testes automatizados da Camada 7 (unittest, sem LLM)
    │   ├── test_ingestao.py           # Testes da limpeza de texto de PDF (Camada 5)
    │   ├── casos_teste.md             # 4 casos qualitativos (execuções reais documentadas)
    │   └── casos_teste.json           # Os mesmos 4 cenários, estruturados para o benchmark
    ├── docs/
    │   ├── decisoes_arquitetura.md    # Evidência primária da avaliação de viabilidade
    │   ├── evidencias_empiricas.md    # Log de observações empíricas
    │   ├── estado_atual.md            # Handoff — estado atual e próximo passo
    │   ├── diagrama_arquitetura.md    # Diagrama de componentes (Mermaid)
    │   ├── apendice_casos_teste.md    # Apêndice A da monografia
    │   ├── roteiro_apresentacao.md    # Roteiro de demonstração para a banca
    │   ├── tabela_resultados_empiricos.csv                # Benchmark v4.1, modo produção
    │   ├── tabela_resultados_empiricos_sensibilidade.csv  # Benchmark v4.1, modo sensibilidade (0,8)
    │   ├── resultados/                # Dado bruto do benchmark v4.1 (resposta do LLM, contexto, validação, parâmetros)
    │   │   ├── v4/                    # Dado bruto e tabelas da v4 (tag v4.0-monografia)
    │   │   ├── v3.1/                  # Dado bruto e tabelas da v3.1 (tag v3.1-monografia)
    │   │   ├── v3/                    # Dado bruto e tabelas da v3 (tag v3.0-monografia)
    │   │   ├── v2/                    # Dado bruto e tabelas da v2 (tag v2.0-monografia)
    │   │   └── v1/                    # Dado bruto e tabelas da v1 (tag v1.0-monografia)
    │   └── figuras/                   # Gráficos gerados por scripts/plot_benchmark.py
    ├── analise/                       # Leitura técnica do código (retrato de 2026-09-23)
    └── logs/                          # Gerado em runtime (git-ignorado)
        └── interacoes.jsonl           # Proveniência (Camada 8), uma linha por interação
```

## 8. Fontes de dados

A base de conhecimento (Camada 5) é construída **exclusivamente** a partir de
fontes públicas e oficiais do Banco Central do Brasil (ver
[`data/normativos/README.md`](prototipo/data/normativos/README.md)). Nenhuma
informação interna ou proprietária de qualquer instituição financeira é
utilizada (ver Capítulo 1, Seção 3 — Objetivo). Normativos pendentes de
inclusão (texto oficial ainda não localizado com segurança) estão
documentados, e não incluídos com fonte não verificada, em
[`data/normativos/PENDENTES.md`](prototipo/data/normativos/PENDENTES.md).

## 9. Documentação das decisões de arquitetura

- [`docs/decisoes_arquitetura.md`](prototipo/docs/decisoes_arquitetura.md):
  registro incremental das decisões de projeto, das ambiguidades encontradas
  na arquitetura conceitual de Maia et al. (2026) e das adaptações
  necessárias durante a construção. É a evidência primária para a avaliação
  descrita no Capítulo 1, Seção 5 (Metodologia), item (d).
- [`docs/evidencias_empiricas.md`](prototipo/docs/evidencias_empiricas.md):
  observações empíricas feitas ao testar o sistema (comportamentos
  inesperados do modelo, falhas, acertos).
- [`docs/estado_atual.md`](prototipo/docs/estado_atual.md): resumo de
  handoff com o estágio atual e o próximo passo sugerido.

## 10. Licença e reprodutibilidade

Projeto acadêmico, sob a licença MIT (ver `LICENSE`). A licença cobre o
código, a documentação e os resultados do benchmark; os textos normativos
do BCB em `prototipo/data/normativos/` são atos oficiais, que a Lei nº
9.610/1998 (art. 8º, IV) exclui da proteção por direito autoral, e são
reproduzidos a partir das URLs oficiais registradas em `fontes_url.json`.

O protótipo e o benchmark rodam localmente via Ollama:
sem custo, sem chave de API e sem serviços de terceiros. A base de
conhecimento já vem gerada no repositório; só baixá-la de novo (Seção 6,
Passo 4) acessa a internet, e apenas o site público do BCB.
