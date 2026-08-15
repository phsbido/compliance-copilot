# Copiloto de Compliance Regulatório LLM-Native (Open Finance / Contas PJ)

Protótipo desenvolvido como artefato de Design Science Research para a monografia
de especialização *"Aplicações LLM-Native: Implementação e Avaliação de Viabilidade
da Arquitetura Conceitual de Maia et al. (2026)"*.

**Autor**: Pedro Henrique dos Santos Bido
**Orientadora**: Prof.ª Ana Claudia Rossi

## O que este sistema faz

Responde perguntas sobre requisitos regulatórios de Open Finance e contas PJ,
fundamentado exclusivamente em atos normativos públicos do Banco Central do
Brasil (BACEN) — sempre citando a norma-fonte, nunca emitindo parecer jurídico
definitivo.

## Estrutura do código

O código é organizado espelhando as oito camadas da arquitetura conceitual de
Maia et al. (2026, Seção 8), para rastreabilidade direta entre a proposta
teórica e a implementação:

| Pasta | Camada | Status |
|---|---|---|
| `src/layer1_interaction/` | Interação com o Usuário | implementada — CLI (`python main.py`) |
| `src/layer2_llm_core/` | Núcleo de Raciocínio do LLM | implementada |
| `src/layer3_orchestration/` | Orquestração e Fluxo de Trabalho | implementada |
| `src/layer4_tools/` | Integração de Ferramentas e Serviços | implementada |
| `src/layer5_knowledge/` | Integração de Conhecimento (RAG) | implementada |
| `src/layer6_memory/` | Contexto e Memória | implementada |
| `src/layer7_governance/` | Governança e Segurança | implementada |
| `src/layer8_observability/` | Observabilidade e Proveniência | implementada |

Todas as 8 camadas estão implementadas e ligadas ponta a ponta. 4 casos de
teste formais em `tests/casos_teste.md`. Ver `docs/estado_atual.md` para o
estado detalhado e o próximo passo sugerido.

Aspectos multimodais da Camada 1 estão explicitamente fora de escopo (ver
Capítulo 1, Seção 5 — Metodologia).

## Pré-requisitos

1. **Python 3.10+**
2. **Ollama** instalado localmente: https://ollama.com/download
3. Um modelo com suporte a tool calling baixado localmente. Recomendado para
   começar (equilíbrio entre qualidade e uso de recursos):

   ```bash
   ollama pull llama3.1
   ```

   Se sua máquina tiver recursos limitados, `llama3.1:8b` (padrão do comando
   acima) já é suficiente para o protótipo. Modelos maiores (ex: `llama3.1:70b`)
   têm melhor raciocínio, mas exigem muito mais RAM/GPU.

## Instalação

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Validar a base (Estágio 1 do plano de construção)

Antes de implementar qualquer camada além do Núcleo de Raciocínio, valide que
a base está funcionando. Confirme que o Ollama está rodando (geralmente inicia
automaticamente após a instalação; se não, rode `ollama serve` em um terminal
separado) e então:

```bash
python run_check.py
```

Se retornar uma resposta em texto do modelo, a base está validada e podemos
seguir para as próximas camadas.

## Validar a orquestração (Camada 3)

Com a Camada 2 validada, a Camada 3 (Orquestração) já tem um esqueleto
inicial coordenando 4 etapas (interpretar, buscar normativo, sintetizar
resposta, validar citação) — as etapas de busca de normativo e validação de
citação ainda são stubs, pois dependem das Camadas 4/5 e 7. Para testar o
fluxo de ponta a ponta:

```bash
python run_check_orchestration.py
```

## Validar a base de conhecimento (Camada 5)

O corpus inicial (`data/normativos/`) tem 2 normativos com texto integral
indexado e 2 pendentes (ver `data/normativos/PENDENTES.md`). A busca é
lexical simples (sem embeddings). Para testar:

```bash
python run_check_knowledge.py
```

## Validar as ferramentas (Camada 4)

`buscar_normativo` (`src/layer4_tools/tools.py`) embrulha a Camada 5 e já
está ligada à Camada 3 (`Orchestrator._buscar_normativo` não é mais stub).
Para testar a ferramenta isoladamente:

```bash
python run_check_tools.py
```

## Validar a memória (Camada 6)

`Memoria` (`src/layer6_memory/memory.py`) guarda as últimas N interações da
sessão e já está ligada à Camada 3 — `run_check_orchestration.py` simula 2
perguntas em sequência para comprovar o efeito. Para testar a classe
isoladamente:

```bash
python run_check_memory.py
```

## Validar a governança (Camada 7)

`validar_citacao` e `recusar_parecer_juridico`
(`src/layer7_governance/governance.py`) já estão ligadas à Camada 3: citação
de artigo/norma não verificada no contexto gera aviso, e perguntas
classificadas como pedido de parecer jurídico definitivo são recusadas sem
buscar/sintetizar. Para testar isoladamente:

```bash
python run_check_governance.py
```

## Validar a observabilidade (Camada 8)

`registrar_interacao` (`src/layer8_observability/observability.py`) grava
um registro JSON por interação em `logs/interacoes.jsonl` (fontes
normativas usadas, classificação da Camada 3, se a Camada 7 sinalizou
citação não verificada, resposta final) e já está ligada ao `Orchestrator`
— rode `python run_check_orchestration.py` e depois confira
`logs/interacoes.jsonl` para ver os registros reais. Para testar a função
isoladamente (com arquivo de log temporário, sem tocar no log real):

```bash
python run_check_observability.py
```

## Usar o protótipo (Camada 1 — CLI)

Com o Ollama rodando, todas as camadas já estão ligadas em um loop de
conversa (`src/layer1_interaction/cli.py`), que mantém a memória da sessão
(Camada 6) e mostra, após cada resposta, as fontes normativas usadas e
eventuais avisos de citação não verificada (Camadas 7/8):

```bash
python main.py
```

Digite `sair`, `exit` ou `quit` para encerrar. Cada interação também é
registrada em `logs/interacoes.jsonl` (Camada 8) para auditoria posterior.

## Fontes de dados

A base de conhecimento (Camada 5) é construída **exclusivamente** a partir de
fontes públicas e oficiais do Banco Central do Brasil — ver
`data/normativos/README.md`. Nenhuma informação interna ou proprietária de
qualquer instituição financeira é utilizada (ver Capítulo 1, Seção 3 —
Objetivo).

## Documentação das decisões de arquitetura

Ver `docs/decisoes_arquitetura.md` — registro incremental das decisões de
projeto, ambiguidades encontradas na arquitetura conceitual de Maia et al.
(2026) e adaptações necessárias durante a construção. Este documento é a
evidência primária para a avaliação descrita no Capítulo 1, Seção 5
(Metodologia), item (d) — **deve ser atualizado a cada camada implementada**,
não escrito retroativamente ao final.

Observações empíricas feitas ao testar o sistema (comportamentos
inesperados do modelo, falhas, acertos) são registradas separadamente em
`docs/evidencias_empiricas.md`, para compilação posterior na análise da
monografia.

Para retomar o trabalho rapidamente em uma nova sessão, ver
`docs/estado_atual.md` — resumo de handoff com o estágio atual da
construção, como validar cada camada, e o próximo passo sugerido.

## Licença e reprodutibilidade

Projeto acadêmico. Todo o pipeline roda localmente via Ollama — sem custo,
sem chave de API, sem dependência de serviços de terceiros — para que
qualquer pessoa possa clonar e reproduzir os resultados.
