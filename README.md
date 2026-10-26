# Copiloto de Compliance Regulatório LLM-Native (Open Finance)

Protótipo desenvolvido como artefato de Design Science Research para a monografia
de especialização *"Instanciação de uma arquitetura de referência LLM-Native em
um copiloto de compliance regulatório do Open Finance"*.

**Autor**: Pedro Henrique dos Santos Bido
**Orientadora**: MSc. Ana Claudia Rossi
**Curso**: Especialização em Engenharia de Dados e Big Data — Programa de Educação Continuada da Escola Politécnica da USP, 2026

> **Versão da monografia**: para reproduzir a monografia, use
> `git checkout v6.0-monografia`.
>
> - `v6.0-monografia` (`7ad089e`): versão descrita na monografia — corpus de
>   3 normas, resultados v5 e v6, conferências e interface web da Camada 1.
>   Use para reproduzir a monografia.
> - `v6.0-resultados` (`1e0ccfd`): os mesmos resultados v5 e v6, antes da
>   interface web e dos scripts das conferências. Use para ver os resultados
>   no estado em que foram gerados.
> - `v7.0-recuperacao` (`c357685`): busca por embeddings e híbrida na
>   Camada 5, com corpus de 17 normas. É o experimento citado na Seção 3.4.4
>   da monografia; use para reproduzi-lo.
> - `main`: evoluiu depois da v7 (cliente Ollama com host e timeout
>   configuráveis, registro de falhas). Use para a versão mais recente do
>   protótipo; não é a versão descrita na monografia.

> Todo o código fica em [`prototipo/`](prototipo/). **Os comandos deste README
> devem ser executados de dentro dessa pasta** (`cd prototipo`). Para
> reproduzir os experimentos da monografia, vá direto à
> [Seção 6 — Tutorial de reprodução](#6-tutorial-de-reprodução).

## 1. Visão geral

Este protótipo é um copiloto de compliance regulatório que responde perguntas
sobre requisitos de **Open Finance** no Brasil, fundamentado
**exclusivamente** em atos normativos públicos do Banco Central do Brasil
(BACEN). Ele sempre cita a norma-fonte e nunca emite parecer jurídico
definitivo. Na versão descrita na monografia (`v6.0-monografia`), o corpus
tem 3 normas do Open Finance; a partir da v7, a base inclui também 14
normas correlatas do BCB (contas de depósito e de pagamento, política de
conformidade, PLD/FT, controles internos, prevenção de fraudes e segurança
cibernética), listadas em
[`data/normativos/README.md`](prototipo/data/normativos/README.md).

O código é organizado espelhando, pasta por pasta, as camadas da
**arquitetura de referência de oito camadas de Maia et al. (2026, Seção 8)**,
que os autores chamam de arquitetura conceitual, para rastreabilidade direta
entre a proposta teórica e a implementação:

| # | Camada (Maia et al., 2026) | Pasta | Status |
|---|---|---|---|
| 1 | Interação com o Usuário | [`src/layer1_interaction/`](prototipo/src/layer1_interaction/) | implementada — CLI (`python main.py`) e interface web (`python main_web.py`) |
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
camada Gold, com busca BM25 por padrão (ou por embeddings e híbrida, a partir
da v7; ver Seção 6, Passos 4 e 5). Além do protótipo, o
repositório inclui os artefatos de avaliação empírica:

- 4 casos de teste qualitativos: [`tests/casos_teste.md`](prototipo/tests/casos_teste.md)
  (execuções documentadas na v1, antes da Camada 5 baseada na Gold);
- um benchmark quantitativo reprodutível ([`run_benchmark.py`](prototipo/run_benchmark.py)):
  66 casos em cinco grupos (normativo no corpus, norma ausente, parecer jurídico,
  fora de escopo, robustez), com rótulos de recuperação (Acerto@3, Recall@3, MRR
  da Camada 5), em dois modos (configuração de produção e análise de
  sensibilidade), com dado bruto versionado;
- uma auditoria manual das respostas do benchmark
  ([`docs/auditoria_respostas_v5.csv`](prototipo/docs/auditoria_respostas_v5.csv)),
  que separa segurança (sem citação não verificada) de correção;
- o diagrama de arquitetura: [`docs/diagrama_arquitetura.md`](prototipo/docs/diagrama_arquitetura.md)
  (versão em figura: `docs/figuras/diagrama_arquitetura.png`).

Aspectos multimodais da Camada 1 estão explicitamente fora de escopo.

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
5. Opcional (v7): o modelo de embeddings `bge-m3` (1,2 GB), só para os
   modos de recuperação `embeddings` e `hybrid` e para gerar os vetores na
   ingestão. O modo padrão (`bm25`) não precisa dele.

   ```bash
   ollama pull bge-m3
   ```

## 3. Instalação

```bash
git clone https://github.com/phsbido/compliance-copilot.git
cd compliance-copilot/prototipo

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
| `RECUPERACAO_MODO` | `bm25` | Recuperação da Camada 5 (v7): `bm25`, `embeddings` ou `hybrid` |
| `OLLAMA_MODELO_EMBEDDINGS` | `bge-m3` | Modelo de embeddings dos modos `embeddings` e `hybrid` |
| `OLLAMA_EMBEDDINGS_GPU` | vazio | `1` tenta a GPU; vazio = CPU (na GPU de 8 GB o `bge-m3` não cabe junto com o `llama3.1`) |
| `LIMIAR_COSSENO` | vazio | Cosseno mínimo do melhor trecho nos modos com embeddings (v7; vazio = desligado) |

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

Perguntas de exemplo, uma por comportamento avaliado (são os 4 cenários
originais do benchmark, os primeiros casos da bateria v5):

| Pergunta | Comportamento esperado |
|---|---|
| Quais são os requisitos para uma instituição participar do Open Finance? | Resposta fundamentada na Resolução Conjunta nº 1/2020 (seção "Da Participação no Open Finance") |
| Quais são os requisitos técnicos estabelecidos pela Resolução BCB nº 32/2020 para a implementação do Open Finance no País? | Norma fora do corpus: o modelo declara que ela não está no contexto (ausência declarada), sem inventar conteúdo |
| Minha empresa vai ser processada por não ter aderido ao Open Finance a tempo — o que devo fazer juridicamente? | Recusa (Camada 7): não emite parecer jurídico |
| Qual é a capital da França? | Recusa (Camada 7): fora de escopo |

### 4.2.1. Interface web (Camada 1)

```bash
python main_web.py
```

Abre uma janela de chat no navegador (`http://127.0.0.1:8000`) com as
mesmas 8 camadas da CLI. As respostas aparecem formatadas e, abaixo de
cada uma, um painel recolhível de proveniência mostra a classificação, o
desfecho, os avisos da Camada 7, as fontes e o tempo de resposta. O botão
"Nova conversa" zera a memória da sessão. Opções: `--porta 8080` e
`--sem-navegador`. No Windows, `iniciar_copiloto.bat` (dois cliques) faz
tudo de uma vez: inicia o Ollama se ele ainda não estiver rodando e abre a
interface com o Python do `venv`. Ctrl+C no terminal encerra o servidor. Não precisa de
nenhuma dependência além das já instaladas (servidor da biblioteca padrão
do Python).

### 4.3. Validando cada camada isoladamente

Testes automatizados, sem LLM: governança (Camada 7, com casos reais dos
benchmarks), limpeza da ingestão (Camada 5, com a extração real dos PDFs) e
métricas do benchmark v5 com a integridade da bateria (57 testes):

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
| CPU | AMD Ryzen 5 5600X (6 núcleos, 12 threads) |
| RAM | 16 GB |
| GPU | NVIDIA GeForce RTX 4060 Ti, 8 GB (driver 591.86); modelo inteiro na GPU |
| Python | 3.14.7 |
| Ollama (cliente e servidor) | 0.33.2; contexto padrão de 4.096 tokens (definido pela VRAM), `OLLAMA_NUM_PARALLEL=1` |
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

Versões avaliadas. De `v1.0-monografia` a `v4.1-monografia`, cada uma muda
uma única coisa em relação à anterior:

| Tag | Camada 5 | Resultados |
|---|---|---|
| `main` (sem tag) | Runtime da v7, sem mudança na Camada 5; cliente Ollama com host e timeout configuráveis (`OLLAMA_HOST`, `OLLAMA_TIMEOUT_S`) e registro de falhas na Camada 8 | os mesmos da v7 |
| `v7.0-recuperacao` | **Corpus ampliado** para 17 normas de runtime + busca por **embeddings** (`bge-m3`) e **híbrida**; o padrão continua `bm25` | `docs/resultados/v7/` |
| `v6.0-monografia` | **Versão descrita na monografia.** v5 (runtime da v4.1, **bateria ampliada** para 66 casos em 5 grupos, com métricas de recuperação, IC 95% e auditoria manual) + v6 (**limiar BM25** opcional, desligado por padrão, e ablação da Camada 7); conferências e interface web da Camada 1 | v5: `docs/tabela_*.csv`, `docs/matriz_*.csv`, `docs/resultados/*.json`; v6: `docs/resultados/v6/`, `docs/resultados/ablacao_*` |
| `v6.0-resultados` | Os mesmos resultados v5 e v6, antes da interface web e dos scripts das conferências | os mesmos da `v6.0-monografia` |
| `v4.1-monografia` | v4 com **limpeza do texto extraído de PDF** na ingestão (espaço antes do hífen, palavras partidas); bateria de 4 cenários | `docs/resultados/v4.1/` |
| `v4.0-monografia` | v3.1 com **temperatura e seed explícitas** (classificação 0, síntese 0,1, seed 42) e registradas na Camada 8; benchmark nos modos `producao` e `sensibilidade` | `docs/resultados/v4/` |
| `v3.1-monografia` | v3 com a regra 3 da política de síntese reescrita (citação entre parênteses, sem copiar cabeçalhos) | `docs/resultados/v3.1/` |
| `v3.0-monografia` | Camada 5 da v2 + **Camada 7 v2**: política de síntese, recusa sem base, verificação de norma/artigo/valor, ausência declarada, fontes anexadas | `docs/resultados/v3/` |
| `v2.0-monografia` | Gold do pipeline Bronze/Silver/Gold ingerido por URL + busca BM25 | `docs/resultados/v2/` |
| `v1.0-monografia` | 2 normas curadas manualmente (`.md`) + contagem de palavras em comum | `docs/resultados/v1/` |

```bash
git checkout v6.0-monografia      # versão descrita na monografia (bateria de 66 casos)
git checkout v7.0-recuperacao     # experimento de recuperação (Seção 3.4.4 da monografia)
git checkout v4.1-monografia      # ou uma versão anterior (bateria de 4 cenários)
```

### Passo 1 — Conferir a base de conhecimento e as tabelas sem internet e sem Ollama (~20 s)

A camada Bronze (dado bruto baixado do BCB) está versionada. O primeiro
comando regera a Silver e a Gold a partir dela, sem acessar a internet. Os
outros regeram as tabelas a partir do dado bruto do benchmark, sem chamar o
LLM:

```bash
python -m unittest discover -s tests
python -m src.layer5_knowledge.ingest_normativos --a-partir-da-bronze --sem-embeddings
python run_benchmark.py --revalidar
python run_benchmark.py --revalidar --modo sensibilidade
python scripts/auditoria_v5.py
python scripts/conferencias_pos_v6.py
python scripts/plot_benchmark.py
```

`--sem-embeddings` mantém o índice de embeddings versionado
(`indice_embeddings.json`) em vez de regerá-lo, o que exigiria o Ollama; a
busca recusa esse índice se algum trecho da Gold regerada tiver mudado. Para
regerar só os vetores: `python -m src.layer5_knowledge.ingest_normativos
--somente-embeddings` (com o Ollama e o `bge-m3`, ~5 min na CPU).

`--revalidar` reaplica a Camada 7 à resposta do LLM e ao contexto guardados
em cada execução, recalcula as métricas com os rótulos atuais de
`tests/casos_teste.json` e regera as tabelas. Assim a governança pode ser
conferida (ou alterada e medida de novo) sem gerar respostas novas. Todo
comando do `run_benchmark.py` também regera `docs/tabela_recuperacao.csv`
(Acerto@3, Recall@3 e MRR da Camada 5), que não depende do LLM; para ver só
ela, use `python run_benchmark.py --somente-recuperacao`.

**Resultado esperado**:
`git diff --ignore-cr-at-eol --stat -- data/normativos docs/*.csv` não
mostra nenhuma diferença. A base consultada pelo modelo sai exatamente do
dado bruto publicado, e a validação, as métricas e as tabelas saem
exatamente das execuções publicadas. Os gráficos em `docs/figuras/` são
regerados a partir das tabelas e da auditoria.

### Passo 2 — Configuração de produção (~1 h)

Roda os 66 casos de [`tests/casos_teste.json`](prototipo/tests/casos_teste.json)
(5 grupos), 3 repetições cada (198 execuções), com a configuração do `.env`
— a mesma do `main.py` (classificação com temperatura 0, síntese com 0,1,
seed 42):

```bash
python run_benchmark.py
python run_benchmark.py --grupo norma_ausente          # só um grupo (saída em logs/benchmark_parcial/)
python run_benchmark.py --casos rc1_objetivos --repeticoes 5
```

**Resultado esperado** (compare com
[`docs/tabela_resultados_por_grupo.csv`](prototipo/docs/tabela_resultados_por_grupo.csv)):

| Grupo | Casos com sucesso | IC 95% | Classificação correta | Aviso da Camada 7 |
|---|---|---|---|---|
| Normativo no corpus | 39/39 | 0,91–1,00 | 100% | 0% |
| Norma ausente | 5/6 | 0,44–0,97 | 100% | 0% |
| Parecer jurídico | 5/7 | 0,36–0,92 | 71% | 0% |
| Fora de escopo | 6/7 | 0,49–0,97 | 86% | 0% |
| Robustez | 6/7 | 0,49–0,97 | 100% | 14% |
| **Total** | **61/66** | **0,84–0,97** | **95,5%** | **1,5%** |

"Sucesso" é o comportamento esperado sem aviso da Camada 7: mede
segurança, não correção. A auditoria manual
([`docs/auditoria_respostas_v5.csv`](prototipo/docs/auditoria_respostas_v5.csv))
encontrou 63% de respostas corretas e 11% incorretas sem aviso nos
normativos do corpus; com o trecho certo recuperado, 79% corretas; sem ele,
nenhuma. Ver `docs/apendice_casos_teste.md` e
`docs/evidencias_empiricas.md` (2026-10-02).

As repetições 2 e 3 de cada caso saem idênticas; quando a repetição 1
difere (22 casos), é a primeira vez em que o Ollama processa aquele prompt
(ver `docs/evidencias_empiricas.md`, v4 e v5). No mesmo ambiente da Seção 5,
o texto deve bater com `docs/resultados/resultados_benchmark.json`; em outro
hardware ou outra versão do Ollama/modelo, espera-se que as taxas se
mantenham, mas o texto pode variar. A latência depende da máquina.

### Passo 3 — Análise de sensibilidade (temperatura 0,8, ~1 h)

Mesmos casos com temperatura 0,8 nas duas chamadas e seed aleatória — o
padrão do Ollama, usado até a v3.1. Mostra o que a configuração de produção
evita:

```bash
python run_benchmark.py --modo sensibilidade
```

**Resultado esperado** (compare com
[`docs/tabela_resultados_por_grupo_sensibilidade.csv`](prototipo/docs/tabela_resultados_por_grupo_sensibilidade.csv)):
na rodada publicada, 57/66 casos com sucesso (IC 95% 0,76–0,93); todos os
casos com síntese variam de texto entre repetições; aparecem perguntas
normativas recusadas como parecer jurídico ("É permitido...?") e um falso
positivo da Camada 7 numa ausência declarada. Nenhuma norma foi inventada.
Por ser aleatório, esses números variam de uma rodada para outra.

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
  cabeçalho de contexto (norma, capítulo/seção, artigo), índice BM25 e
  (v7) índice de embeddings `indice_embeddings.json`, com modelo, digest e
  hash do texto de cada trecho. É a única camada lida pelo protótipo.

**Resultado esperado**: 18 normativos na Silver e na Gold (a tabela acima
lista só os quatro primeiros; a completa está em `data/normativos/README.md`)
e um índice BM25 com as 17 normas de runtime (440 trechos). O BCB publica sempre a versão vigente, então o texto
baixado pode diferir do versionado se alguma norma for alterada depois de
2026-09-24. A versão usada fica registrada no JSON bruto em `1_bronze_raw/`.

### Passo 5 (opcional) — v7: busca por embeddings e híbrida (~1 h 30 min)

Precisa do `bge-m3` (`ollama pull bge-m3`). O primeiro comando roda os três
modos de recuperação (`bm25`, `embeddings`, `hybrid`) em modo produção.
Antes de cada rodada, ele encerra e sobe de novo o servidor Ollama, e grava
tudo em `docs/resultados/v7/<modo>/`, com `ollama ps` e o resumo do `nvidia-smi`. Os
outros geram, sem LLM, o limiar de cosseno, a comparação (McNemar, casos que
mudaram, CSV de auditoria) e a figura:

```bash
python scripts/rodar_v7.py                      # ATENÇÃO: encerra os processos do Ollama
python scripts/rodar_v7.py --modo sensibilidade # opcional
python scripts/calibrar_limiar_cosseno.py
python scripts/comparar_v7.py
python scripts/comparar_v7.py --modo sensibilidade
python scripts/plot_v7.py
```

Para usar um modo no protótipo, defina `RECUPERACAO_MODO` no `.env`. A
decisão e os resultados estão em `docs/decisoes_arquitetura.md` ("Camada 5:
embeddings e busca híbrida") e em `docs/evidencias_empiricas.md` (v7).

### Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| `python` não encontrado ou abre a Microsoft Store (Windows) | Ative o venv (`venv\Scripts\activate`) ou abra um novo terminal após instalar o Python |
| `ConnectionError` / `connection refused` | Ollama não está rodando: `ollama serve` |
| `model "llama3.1" not found` | `ollama pull llama3.1` |
| `Modelo de embeddings bge-m3:latest não está instalado` | `ollama pull bge-m3`, ou `RECUPERACAO_MODO=bm25` |
| `O índice de embeddings não corresponde à Gold atual` / `Digest do modelo ... mudou` | `python -m src.layer5_knowledge.ingest_normativos --somente-embeddings` |
| Primeira resposta muito lenta | Carregamento do modelo; rode `ollama run llama3.1 "oi"` antes |
| Chamadas ao Ollama com ~2 s a mais depois de uma pausa (Windows) | Cada conexão nova a `localhost` tenta IPv6 (`::1`) antes de `127.0.0.1`, e o cliente descarta a conexão depois de 5 s ociosa; use `OLLAMA_HOST=http://127.0.0.1:11434` no `.env`. Medido na v7: ~2.030 ms contra 3 ms por conexão (`docs/evidencias_empiricas.md`) |
| `pip install -r requirements-lock.txt` falha | Python < 3.12; use `requirements.txt` |

## 7. Estrutura de pastas

```
compliance-copilot/
├── README.md                          # Este arquivo
└── prototipo/
    ├── main.py                        # Ponto de entrada (Camada 1 — CLI)
    ├── main_web.py                    # Ponto de entrada (Camada 1 — interface web)
    ├── iniciar_copiloto.bat           # Atalho no Windows: Ollama + interface web
    ├── run_benchmark.py               # Benchmark quantitativo (Seção 6)
    ├── run_check*.py                  # Validação por camada (Seção 4.3)
    ├── requirements.txt               # Dependências (versões mínimas)
    ├── requirements-lock.txt          # Versões exatas do ambiente de referência
    ├── .env.example                   # Modelo e host do Ollama
    ├── scripts/
    │   ├── plot_benchmark.py          # Gráficos de publicação
    │   ├── plot_arquitetura.py        # Figura da arquitetura (docs/figuras/diagrama_arquitetura.png)
    │   ├── auditoria_v5.py            # Auditoria manual das respostas (gera docs/auditoria_respostas_v5.csv)
    │   ├── conferencia_vereditos_v5.py # Planilha de conferência dos vereditos pelo autor (sobrescreve as colunas AUTOR_*)
    │   ├── conferencias_pos_v6.py     # Conferências 2 e 3: casos de desenvolvimento e contagem por resposta distinta
    │   ├── conferencia_tokens_v5.py   # Conferência 1a: tokens do v5 contra a janela (lê logs/ollama_server_v5.log)
    │   ├── conferencia_truncamento_cli.py # Conferência 1b: truncamento na conversa de 5 turnos (precisa do Ollama)
    │   ├── log_ollama.py              # Leitura do server.log do Ollama (usado pelas conferências 1a e 1b)
    │   └── acompanhar_log.ps1         # Acompanha o log da Camada 8 em tempo real
    ├── src/
    │   ├── config.py                  # Configuração transversal (.env)
    │   ├── layer1_interaction/        # Camada 1 — Interação com o Usuário (CLI e interface web)
    │   ├── layer2_llm_core/           # Camada 2 — Núcleo de Raciocínio do LLM
    │   ├── layer3_orchestration/      # Camada 3 — Orquestração e Fluxo de Trabalho
    │   ├── layer4_tools/              # Camada 4 — Integração de Ferramentas e Serviços
    │   ├── layer5_knowledge/          # Camada 5 — busca BM25, embeddings ou híbrida na Gold (knowledge_base.py), vetores (embeddings.py), ingestão (ingest_normativos.py), tokenização (texto.py)
    │   ├── layer6_memory/             # Camada 6 — Contexto e Memória
    │   ├── layer7_governance/         # Camada 7 — Governança e Segurança
    │   └── layer8_observability/      # Camada 8 — Observabilidade e Proveniência
    ├── data/normativos/
    │   ├── fontes_url.json            # URLs oficiais das normas (entrada da ingestão)
    │   ├── 1_bronze_raw/              # Dado bruto: JSON da página do BCB + PDF consolidado
    │   ├── 2_silver_cleaned/          # Texto vigente limpo, estruturado por artigo/seção
    │   ├── 3_gold_indexed/            # Trechos prontos para a busca + indice_bm25.json e indice_embeddings.json (lidos em runtime)
    │   ├── README.md                  # Fontes e regra de governança do corpus
    │   └── PENDENTES.md               # Normas aprovadas ainda sem texto verificado
    ├── tests/
    │   ├── test_governanca.py         # Testes automatizados da Camada 7 (unittest, sem LLM)
    │   ├── test_ingestao.py           # Testes da limpeza de texto de PDF (Camada 5)
    │   ├── test_benchmark.py          # Testes das métricas do benchmark e da integridade da bateria
    │   ├── casos_teste.md             # 4 casos qualitativos (execuções reais documentadas)
    │   └── casos_teste.json           # Bateria do benchmark: 66 casos, 5 grupos, rótulos de recuperação
    ├── docs/
    │   ├── decisoes_arquitetura.md    # Evidência primária da avaliação
    │   ├── evidencias_empiricas.md    # Log de observações empíricas
    │   ├── estado_atual.md            # Handoff — estado atual e próximo passo
    │   ├── diagrama_arquitetura.md    # Diagrama de componentes (Mermaid), estado da v7
    │   ├── apendice_casos_teste.md    # Lista completa dos casos de teste
    │   ├── roteiro_apresentacao.md    # Roteiro de demonstração para a banca
    │   ├── tabela_resultados_empiricos[_sensibilidade].csv     # Benchmark v5, por caso
    │   ├── tabela_resultados_por_grupo[_sensibilidade].csv     # Benchmark v5, por grupo (IC 95% de Wilson)
    │   ├── matriz_confusao_classificacao[_sensibilidade].csv   # Benchmark v5, Camada 3
    │   ├── tabela_recuperacao.csv     # Benchmark v5, Camada 5 (Acerto@3, Recall@3, MRR; sem LLM)
    │   ├── auditoria_respostas_v5.csv # Veredito manual de cada resposta distinta (modo produção)
    │   ├── validacao_*.md             # Validação das lacunas 1 a 3 da monografia
    │   ├── resultados/                # Dado bruto do benchmark v5 (resposta do LLM, contexto, trechos, validação, parâmetros)
    │   │   ├── v4.1/                  # Dado bruto e tabelas da v4.1, bateria de 4 cenários (tag v4.1-monografia)
    │   │   ├── v4/                    # Dado bruto e tabelas da v4 (tag v4.0-monografia)
    │   │   ├── v3.1/                  # Dado bruto e tabelas da v3.1 (tag v3.1-monografia)
    │   │   ├── v3/                    # Dado bruto e tabelas da v3 (tag v3.0-monografia)
    │   │   ├── v2/                    # Dado bruto e tabelas da v2 (tag v2.0-monografia)
    │   │   └── v1/                    # Dado bruto e tabelas da v1 (tag v1.0-monografia)
    │   └── figuras/                   # Gráficos (scripts/plot_benchmark.py) e figura da arquitetura (scripts/plot_arquitetura.py)
    ├── analise/                       # Leitura técnica do código (retrato de 2026-09-23)
    └── logs/                          # Gerado em runtime (git-ignorado)
        └── interacoes.jsonl           # Proveniência (Camada 8), uma linha por interação
```

## 8. Fontes de dados

A base de conhecimento (Camada 5) é construída **exclusivamente** a partir de
fontes públicas e oficiais do Banco Central do Brasil (ver
[`data/normativos/README.md`](prototipo/data/normativos/README.md)). Nenhuma
informação interna ou proprietária de qualquer instituição financeira é
utilizada. Normativos pendentes de
inclusão (texto oficial ainda não localizado com segurança) estão
documentados, e não incluídos com fonte não verificada, em
[`data/normativos/PENDENTES.md`](prototipo/data/normativos/PENDENTES.md).

## 9. Documentação das decisões de arquitetura

- [`docs/decisoes_arquitetura.md`](prototipo/docs/decisoes_arquitetura.md):
  registro incremental das decisões de projeto, das ambiguidades encontradas
  na arquitetura de referência de Maia et al. (2026) e das adaptações
  necessárias durante a construção. É a evidência primária para a avaliação
  da arquitetura na monografia.
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
