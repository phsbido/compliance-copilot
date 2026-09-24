# `src/layer4_tools/tools.py` — Camada 4 (Integração de Ferramentas e Serviços)

## Responsabilidade e por que existe separada

**[EVIDÊNCIA]** Docstring (`tools.py:1-14`): expor ações externas que o
Núcleo de Raciocínio pode invocar. Hoje só uma ferramenta existe,
`buscar_normativo`, que "embrulha" a Camada 5 e formata os resultados em
texto citável. O docstring registra explicitamente a decisão de **não**
criar ainda uma abstração genérica de "ferramenta" (nome, descrição, registro
de múltiplas ferramentas), remetendo a `docs/decisoes_arquitetura.md:170-184`
para a justificativa completa: só existe um caso de uso real; o BCB expõe
outras APIs públicas (Portal de Dados Abertos, dados cadastrais) que seriam
candidatas naturais a uma segunda ferramenta futura — a generalização fica
adiada até essa segunda ferramenta existir de fato.

## Variável de módulo `_kb` (`tools.py:17`)

```python
_kb = KnowledgeBase()
```

**[FATO]** Instanciada **no import do módulo**, não dentro de
`buscar_normativo`. Consequência: `KnowledgeBase._carregar()`
(que lê todos os `.md` de `data/normativos/` do disco) roda uma única vez
por processo, na primeira vez que algo importa `src.layer4_tools.tools`
(direta ou indiretamente, via `orchestrator.py:23`). Ver `02_fluxo_execucao.md`
Seção 1 para a cadeia completa de imports que dispara isso, e
`04_dados_e_estado.md` para as implicações desse cache implícito (o corpus
não é recarregado se os arquivos mudarem em disco enquanto o processo roda).

**[INFERÊNCIA]** Não há um método público para "recarregar" o índice —
consistente com o uso pretendido (um processo CLI de vida curta, uma sessão
por execução), mas seria uma limitação real se o sistema precisasse rodar
como um serviço de longa duração com atualização de corpus em runtime.

## `buscar_normativo(pergunta: str, top_k: int = 3) -> str` (`tools.py:20-34`)

- Assinatura: único parâmetro obrigatório é a pergunta; `top_k` tem default
  3, repassado direto para `_kb.buscar(pergunta, top_k=top_k)`.
- `tools.py:27`: delega toda a lógica de busca/pontuação à Camada 5.
- `tools.py:28-29`: **caso de borda tratado explicitamente** — se
  `resultados` é uma lista vazia (nenhum trecho teve interseção de tokens >
  0 com a pergunta), retorna uma string fixa: `"Nenhum trecho normativo
  relevante foi encontrado no corpus indexado."`. Essa string se torna o
  "contexto normativo" passado ao LLM na síntese (Camada 3) — o modelo
  recebe uma frase claramente dizendo que nada foi encontrado, em vez de uma
  string vazia (que poderia ser mal interpretada como "sem restrições").
- `tools.py:31-34`: para cada `Documento` retornado, monta um bloco `"Fonte:
  {titulo} ({url_oficial})\n{trecho}"` e junta todos os blocos com
  `"\n\n---\n\n"` como separador. **[FATO]** Este formato de texto
  específico (`"Fonte: "` seguido de título entre parênteses e URL) é um
  contrato implícito: tanto `src/layer7_governance/governance.py` (indireta,
  via regex de artigo/norma) quanto `src/layer8_observability/observability.py:28`
  (`_FONTE_REGEX`) dependem desse formato exato de string para extrair
  proveniência via regex. Uma mudança no formato de `tools.py:33` sem
  atualizar `observability.py:28` quebraria silenciosamente a extração de
  fontes na Camada 8 — acoplamento textual não tipado entre camadas. Ver
  `07_riscos.md`.

## Docstring da função (`tools.py:21-26`)

Documenta explicitamente o propósito do formato de retorno: "string pronta
para ser usada como contexto normativo na síntese de resposta (Camada 3)".

## Quem chama / quem é chamado

- **Chamado por**: `src/layer3_orchestration/orchestrator.py:23,96` e
  diretamente por `run_check_tools.py:11,17-19`.
- **Chama**: `src.layer5_knowledge.knowledge_base.KnowledgeBase` (só essa
  dependência).
