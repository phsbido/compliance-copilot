# Testes, Configuração e Operação

## O que os testes cobrem (e o que revelam sobre o comportamento esperado)

**[FATO]** Não há suíte de testes automatizados no sentido convencional
(`pytest`/`unittest`) — nenhuma dessas bibliotecas está em
`requirements.txt` nem é importada em lugar nenhum. O que existe é uma
combinação de:

1. **Scripts de validação manual por camada** (`run_check_*.py`) — alguns com
   `assert` (falham com `AssertionError` e stack trace se o comportamento
   mudar), outros só imprimem resultado para inspeção visual. Ver
   `03_modulos/scripts_validacao_e_avaliacao.md` para a tabela completa de
   qual script tem assert e qual não tem.
2. **Casos de teste qualitativos documentados** (`tests/casos_teste.md`) —
   4 execuções **reais**, não hipotéticas, com a resposta completa do modelo
   transcrita e uma seção "Observações" analisando o que aconteceu. Isso é
   evidência de intenção mais rica que um teste automatizado convencional:
   documenta não só "passou/falhou", mas *por que* o comportamento observado
   é ou não aceitável (ex.: Caso 1 nota um "risco latente, não um erro
   confirmado" sobre citações incidentais fora do padrão regex esperado —
   `tests/casos_teste.md:69-75`).
3. **Benchmark quantitativo reprodutível** (`run_benchmark.py` + `tests/casos_teste.json`)
   — os mesmos 4 cenários, agora rodados 5 vezes cada contra o modelo real,
   agregados estatisticamente. É o único mecanismo do projeto que dá um
   número de confiança (ex.: 60% de taxa de aviso, não só "acontece às
   vezes").

**O que os testes revelam sobre comportamento esperado**:

- O sistema é esperado a **nunca dar parecer jurídico definitivo** — testado
  tanto isoladamente (`run_check_governance.py`) quanto ponta a ponta
  (Caso 3 de `tests/casos_teste.md`, CT03 do benchmark).
- É esperado a **recusar perguntas fora de domínio sem poluir a
  proveniência** — Caso 4/CT04, com a versão "antes da correção" e "depois"
  documentada lado a lado, mostrando exatamente o comportamento indesejado
  que motivou a correção.
- É esperado que citações de artigo/norma **sempre sejam checadas contra o
  contexto realmente usado naquela resposta**, e que o sistema **nunca
  afirme silenciosamente** uma citação não verificável — mas é
  explicitamente **não esperado** que essa checagem seja 100% eficaz (CT02
  documenta 60%, não 100%, como resultado aceito e analisado, não como falha
  a corrigir).
- É esperado que a memória de sessão influencie a síntese de resposta, mas
  não a classificação de intenção (`run_check_memory.py` só testa o buffer
  isoladamente, sem tocar em classificação).

## Opções de configuração

Só 2 variáveis de ambiente, ambas lidas em `src/config.py:20-21`:

| Variável | Default | Efeito |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1` | Nome do modelo Ollama usado pela Camada 2 em toda chamada a `ollama.chat` |
| `OLLAMA_HOST` | `http://localhost:11434` | **[FATO — verificado no código-fonte da biblioteca instalada em `venv/Lib/site-packages/ollama/`]**: `Settings.ollama_host` (`config.py:21`) é lido para dentro de `settings`, mas **nenhum ponto de `core.py` passa esse valor para a biblioteca `ollama`** — `core.py:35` chama `ollama.chat(model=self.model, messages=messages)` sem parâmetro de host/cliente. A função de módulo `ollama.chat` usa um cliente singleton (`_client = Client()`, `ollama/__init__.py:44`) construído **no momento do import do pacote `ollama`**; `Client.__init__` resolve o host via `os.getenv('OLLAMA_HOST')` (`ollama/_client.py:113`) **naquele exato momento**. Como `core.py:14` faz `import ollama` **antes** de `core.py:15` (`from src.config import settings`, que é o que dispara `load_dotenv()` em `config.py:15`), **`OLLAMA_HOST` definido só em `.env` é lido tarde demais e é ignorado** — só é efetivo se já estiver definido como variável de ambiente real do sistema operacional antes do processo Python iniciar. Como o valor default em `.env.example` já coincide com o default da própria biblioteca `ollama`, esse bug é invisível no setup documentado — só afetaria quem aponta para um servidor Ollama em outro host/porta usando apenas `.env`. Ver `07_riscos.md`, item 0. |

Sem outras opções de configuração — não há flags de linha de comando
(`argparse` não é usado), não há arquivo de configuração além de `.env`.

## Como construir, implantar e rodar

**[FATO]** Não há build nem deploy no sentido de software de produção — é
sempre execução direta de scripts Python em um ambiente local.

### Instalação (`README.md:59-66`)

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Nota de ambiente Windows específica, registrada tanto no `README.md:167-170`
quanto em `docs/estado_atual.md:46-50`: `python` só resolve corretamente
dentro do venv ativado ou usando o caminho completo do interpretador —
sessões de shell abertas antes da instalação do Python não pegam o `PATH`
atualizado.

### Pré-requisito externo: Ollama

O sistema depende de um processo externo rodando localmente — o servidor
Ollama (`README.md:44-57,73-90`). Não é gerenciado pelo código Python do
projeto: o usuário precisa instalar o Ollama separadamente, baixar o modelo
(`ollama pull llama3.1`) e ter o servidor ativo (`ollama serve`, geralmente
automático após a instalação) antes de rodar qualquer script que use a
Camada 2.

### Execução

Ver `01_mapa.md`, seção "Pontos de entrada", para a lista completa de
comandos. Resumo operacional:

1. Uso interativo: `python main.py`.
2. Validar uma camada isolada (debugging/desenvolvimento): `python
   run_check_<camada>.py`.
3. Reproduzir a avaliação empírica completa: `python run_benchmark.py`
   seguido de `python scripts/plot_benchmark.py`.
4. Gerar o pipeline ilustrativo de ingestão (não afeta o runtime): `python
   -m src.layer5_knowledge.ingest_normativos`.

### CI/CD

**[FATO]** Não existe — sem `.github/workflows`, sem qualquer outro sistema
de integração contínua identificado no repositório.

## Reprodutibilidade científica

**[EVIDÊNCIA]** É um objetivo de projeto explícito, não incidental —
`README.md:238-244`: "Todo o pipeline roda localmente via Ollama — sem
custo, sem chave de API, sem dependência de serviços de terceiros — para que
qualquer pessoa possa clonar e reproduzir os resultados". Isso explica
diretamente a escolha de Ollama local (item 2 de `05_decisoes_de_design.md`)
e por que `pandas`/`matplotlib`/`seaborn` foram aceitos como dependências
(análise de dados determinística a partir de um CSV versionado, não parte do
"non-negotiable" de não usar frameworks de orquestração de LLM).

**Limite real de reprodutibilidade**: `requirements.txt` não trava versões
exatas (`>=`, não `==`), então uma reprodução futura pode obter versões mais
novas das bibliotecas do que as usadas originalmente — não há
`requirements.lock` nem `poetry.lock`. Além disso, o próprio modelo
`llama3.1` via Ollama não é determinístico entre execuções (confirmado
empiricamente pelo próprio benchmark: mesma pergunta, 5 repetições, taxas de
0%/60%/100% variam conforme o cenário) — a reprodutibilidade aqui é "mesmo
método, resultados estatisticamente comparáveis", não "output byte-a-byte
idêntico".
