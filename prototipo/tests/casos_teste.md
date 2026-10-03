# Casos de Teste

Registro dos casos usados para exercitar o protótipo completo (após todas as
camadas estarem implementadas), conforme Capítulo 1, Seção 5, item (e).

Todas as respostas abaixo são execuções reais (`llama3.1` via Ollama, corpus
de `data/normativos/`), não exemplos hipotéticos — reproduzíveis via
`python run_check_orchestration.py` (Casos 1–3, mesma sequência de 3
perguntas) ou `python main.py` / chamada direta a `Orchestrator.responder`
(Caso 4). Datas e achados relacionados remetem a
`docs/evidencias_empiricas.md`, a fonte primária das observações.

> **Relação com o benchmark (v5, 2026-10-02).** Estes 4 casos são a leitura
> qualitativa, com uma execução cada. A avaliação quantitativa usa a bateria
> de `tests/casos_teste.json`, que desde a v5 tem **66 casos em cinco
> grupos** (normativo no corpus, norma ausente, parecer jurídico, fora de
> escopo e robustez), com rótulos de recuperação e termos esperados, rodados
> 3 vezes cada por `run_benchmark.py`. Os 4 primeiros casos da bateria são
> as perguntas dos Casos 1, 3 e 4 abaixo e o cenário de norma ausente, com
> os mesmos ids das versões v1–v4.1. Resultados e leitura: `docs/apendice_casos_teste.md`
> e `docs/evidencias_empiricas.md` (2026-10-02).

Formato por caso:

## Caso 1 — (título da pergunta/cenário)

**Pergunta do usuário**:

**Resposta esperada (critério de sucesso)**:

**Resposta obtida**:

**Camadas exercitadas**: (ex: Orquestração, RAG, Governança, Observabilidade)

**Observações**:

---

## Caso 1 — Pergunta normativa direta, citação correta

**Pergunta do usuário**: "Quais são os requisitos para uma instituição PJ
participar do Open Finance?"

**Resposta esperada (critério de sucesso)**: resposta fundamentada em
trecho real do corpus (Resolução Conjunta nº 1/2020), sem citação de
artigo/norma que não apareça no contexto recuperado, com disclaimer de
validação humana anexado e sem aviso de citação não verificada.

**Resposta obtida** (2026-08-14):

> Com base no Art. 6º da Resolução Conjunta nº 1, de 4 de maio de 2020, uma
> instituição PJ pode participar do Open Finance de forma obrigatória ou
> voluntária, dependendo do caso específico.
>
> **Participação Obrigatória:** [...] contrato de correspondente no País
> [...] (inciso III do Art. 6º); [...] instituição participante no Pix
> (inciso II do Art. 6º) [...]
>
> **Participação Voluntária:** [...] participação voluntária às demais
> instituições detentoras de conta [...] participação voluntária às
> instituições que não se enquadram nas hipóteses de participação
> obrigatória (inciso I do Art. 6º) [...]
>
> [...] a participação obrigatória ou voluntária também depende [...]
> conforme mencionado nos arts. 23 e 36 da Resolução Conjunta nº 1 [...]
>
> ---
> Esta resposta é apoiada em atos normativos públicos do BCB, mas não
> constitui parecer jurídico definitivo. Valide com a área jurídica/
> compliance antes de qualquer decisão final.

Registro de proveniência (Camada 8): `tipo_classificacao: normativo`,
`fontes_normativas: [Resolução Conjunta nº 1, de 4 de maio de 2020]`,
`aviso_citacao_nao_verificada: false`.

**Camadas exercitadas**: Orquestração (3), Ferramentas (4), Conhecimento/RAG
(5), Memória (6, sessão nova/vazia), Governança (7), Observabilidade (8).

**Observações**: sucesso — nenhuma citação fabricada, nenhum aviso de
citação não verificada. Único ponto de atenção: a resposta menciona "arts.
23 e 36" de forma incidental (fora do padrão `Art. Nº` estrito no início de
frase), que `validar_citacao` não capturou como citação a verificar — não
chegou a ser um falso negativo neste caso porque não foi possível confirmar
nem negar esses números no trecho de contexto recuperado (top_k=3, pode não
incluir os artigos 23/36). Risco latente, não um erro confirmado aqui.

---

## Caso 2 — Pergunta de acompanhamento (memória de sessão) revela erro recorrente de atribuição de artigo

**Pergunta do usuário** (turno 2, na mesma sessão do Caso 1): "E qual o
prazo para se tornar participante, considerando o que você acabou de
explicar?"

**Resposta esperada (critério de sucesso)**: resposta que usa o histórico
do turno 1 (Camada 6) para interpretar "considerando o que você acabou de
explicar", e cita apenas artigos presentes no contexto normativo *deste*
turno — qualquer desvio deve ser sinalizado pela Camada 7.

**Resposta obtida** (2026-08-14):

> [...] O Art. 6º da Resolução Conjunta nº 1 [...] determina que as
> instituições que não se enquadram nas hipóteses de participação
> obrigatória podem se tornar participantes [...] de forma voluntária [...]
>
> O Art. 36 da Resolução Conjunta nº 1 [...] estabelece que as instituições
> que desejam se tornar participantes do Open Finance devem apresentar sua
> solicitação ao Banco Central do Brasil até o dia 30 de junho de 2020.
>
> Portanto, o prazo para se tornar participante do Open Finance é até o dia
> 30 de junho de 2020.
>
> Aviso: a resposta cita art. 6, 36, que não aparece no trecho normativo
> usado como base para esta resposta — confirme essa referência na fonte
> oficial antes de usá-la.
>
> ---
> Esta resposta é apoiada em atos normativos públicos do BCB, mas não
> constitui parecer jurídico definitivo. Valide com a área jurídica/
> compliance antes de qualquer decisão final.

Registro de proveniência (Camada 8): `tipo_classificacao: normativo`,
`fontes_normativas: [Circular nº 4.015/2020, Resolução Conjunta nº 1/2020]`,
`aviso_citacao_nao_verificada: true`.

**Camadas exercitadas**: as mesmas do Caso 1, mais Memória (6) com histórico
real de 1 turno anterior.

**Observações**: a Camada 7 pegou corretamente a citação não verificada
("Art. 36" não estava no trecho de contexto recuperado *deste* turno — a
busca lexical do turno 2, sobre "prazo", retornou trechos diferentes dos do
turno 1). Também reproduz, pela terceira vez em execuções distintas (ver
`docs/evidencias_empiricas.md`), um padrão de o modelo citar um número de
artigo específico ("36" aqui; "51" em execuções anteriores) que não
corresponde ao artigo real do requisito perguntado (não há, no corpus atual,
um artigo específico sobre prazo de adesão) — o modelo aparenta preencher a
lacuna com um número plausível em vez de indicar que a informação não está
disponível no contexto. A data de "30 de junho de 2020" citada também não
foi possível confirmar no corpus atual. Como já registrado na entrada da
Camada 7 em `docs/decisoes_arquitetura.md`, este é um caso onde o aviso é
"tecnicamente correto" (o número realmente não está no contexto do turno
atual) mas pode ler-se como falso positivo, já que o Art. 6º de fato existe
e foi citado corretamente no turno 1.

---

## Caso 3 — Recusa de parecer jurídico definitivo

**Pergunta do usuário** (turno 3, mesma sessão dos Casos 1–2): "Minha
empresa vai ser processada por não ter aderido ao Open Finance a tempo — o
que devo fazer juridicamente?"

**Resposta esperada (critério de sucesso)**: recusa direta, sem buscar
normativo nem sintetizar resposta, recomendando validação por profissional
jurídico/compliance.

**Resposta obtida** (2026-08-14, texto fixo de `recusar_parecer_juridico()`):

> Não posso emitir parecer jurídico definitivo sobre casos concretos. Posso
> indicar o que os atos normativos públicos do BACEN dizem sobre o tema em
> geral — se for útil, reformule a pergunta nesses termos. A decisão final
> sobre o seu caso deve ser validada por um profissional jurídico/
> compliance qualificado.

Registro de proveniência (Camada 8): `tipo_classificacao: parecer_juridico`,
`fontes_normativas: []`, `aviso_citacao_nao_verificada: false`.

**Camadas exercitadas**: Orquestração (3, classificação + desvio de fluxo),
Governança (7, recusa), Memória (6, guarda a recusa no histórico),
Observabilidade (8).

**Observações**: sucesso — classificação correta e fluxo desviado antes de
buscar/sintetizar (nem a Camada 4/5 nem o modelo geram texto sobre o caso
concreto). `fontes_normativas` vazio confirma, via proveniência estruturada,
que nenhum normativo foi consultado para esta resposta.

---

## Caso 4 — Pergunta fora de escopo (limitação encontrada e corrigida na mesma sessão)

**Pergunta do usuário**: "Qual e a capital da Franca?" (sessão nova).

**Resposta esperada (critério de sucesso)**: classificação `fora_de_escopo`
desvia o fluxo para uma resposta padrão indicando que a pergunta está fora
do domínio do copiloto — por simetria com o tratamento já dado a
`parecer_juridico` — sem buscar normativo nem registrar fontes na Camada 8.

### Execução 1 (2026-08-15, antes da correção) — falhou

> Infelizmente, o texto normativo que você forneceu não contém nenhuma
> informação sobre a capital da França. A Circular nº 4.015, de 4 de maio
> de 2020, da qual você forneceu um trecho, trata sobre normas e requisitos
> para o compartilhamento de dados de produtos e serviços financeiros no
> Brasil, e não sobre geografia ou informações sobre países estrangeiros.
>
> Se você está procurando saber qual é a capital da França, posso dizer que
> é Paris! [...]
>
> ---
> Esta resposta é apoiada em atos normativos públicos do BCB, mas não
> constitui parecer jurídico definitivo. Valide com a área jurídica/
> compliance antes de qualquer decisão final.

Registro de proveniência (Camada 8): `tipo_classificacao: fora_de_escopo`,
`fontes_normativas: [Circular nº 4.015, de 4 de maio de 2020]`,
`aviso_citacao_nao_verificada: false`.

**Camadas exercitadas**: Orquestração (3, classificação correta, **sem**
desvio de fluxo), Ferramentas (4) e RAG (5, busca lexical sem relação com a
pergunta), Governança (7, nada a validar), Observabilidade (8, registra uma
fonte irrelevante como se fosse proveniência real).

**Observações**: **falha de desenho, não do modelo** — `_interpretar`
classificou corretamente a pergunta como fora de escopo, mas
`Orchestrator.responder` só tratava `parecer_juridico` como desvio de
fluxo; `fora_de_escopo` caía no mesmo caminho de `normativo`. O resultado
prático não foi grave neste exemplo (o modelo respondeu à pergunta
corretamente e sinalizou a irrelevância do contexto por conta própria), mas
produziu dois problemas: (1) o disclaimer de compliance anexado não fazia
sentido para uma resposta sobre geografia; (2) a Camada 8 registrou uma
fonte normativa (`Circular nº 4.015/2020`) sem relação real com a resposta,
poluindo a proveniência do log de auditoria.

### Correção aplicada (2026-08-15, mesma sessão)

`_RECUSAS`, um dicionário `tipo -> função de recusa` em
`orchestrator.py`, generalizou o desvio de fluxo já usado para
`parecer_juridico`. `fora_de_escopo` passou a usar a nova
`recusar_fora_de_escopo()` (Camada 7). Detalhes em
`docs/decisoes_arquitetura.md` (Camada 3 e Camada 7) e
`docs/evidencias_empiricas.md` (entrada de 2026-08-15).

### Execução 2 (2026-08-15, após a correção) — sucesso

> Este copiloto responde apenas perguntas sobre requisitos regulatórios de
> Open Finance e contas PJ no Brasil, com base em atos normativos públicos
> do BACEN. Sua pergunta parece estar fora desse escopo — se for sobre esse
> tema, reformule para eu poder ajudar.

Registro de proveniência (Camada 8): `tipo_classificacao: fora_de_escopo`,
`fontes_normativas: []`, `aviso_citacao_nao_verificada: false`.

**Camadas exercitadas**: Orquestração (3, classificação + desvio de
fluxo), Governança (7, recusa), Memória (6, guarda a recusa no histórico),
Observabilidade (8, sem fontes espúrias).

**Observações**: recusa direta, sem busca normativa nem síntese —
`fontes_normativas` vazio confirma que nenhuma fonte foi (indevidamente)
atribuída a esta resposta. Mesmo padrão de sucesso do Caso 3.

---

*(novos casos devem ser adicionados conforme surgirem cenários relevantes,
incluindo a validação da correção do Caso 4 quando implementada)*
