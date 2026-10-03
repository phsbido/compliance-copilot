"""
Diagnóstico das falhas do benchmark v5 (Fase 1): atribui cada execução com
problema a uma camada de origem, sem alterar o protótipo.

Execuções incluídas, nos dois modos: falha no critério automático, aviso da
Camada 7 ou, no modo produção, veredito "incorreta", "parcial" ou
"abstencao" na auditoria manual (docs/auditoria_respostas_v5.csv; o modo
sensibilidade não foi auditado). A tabela ATRIBUICAO é a fonte: camada
principal, camada contributiva e a evidência lida no JSON bruto
(resposta_sintetizada, contexto_normativo, trechos_recuperados) e nos
prompts do código. Análise e método em docs/diagnostico_falhas_v5.md.

Se um veredito da auditoria mudar, rode de novo: o script falha se uma
execução incluída não tiver atribuição ou tiver mais de uma.

Uso:
    python scripts/diagnostico_v5.py
"""
import collections
import csv
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RESULTADOS = RAIZ / "docs" / "resultados"
AUDITORIA = RAIZ / "docs" / "auditoria_respostas_v5.csv"
CSV_SAIDA = RAIZ / "docs" / "diagnostico_falhas_v5.csv"

C23 = "C2/3 classificação"
C2 = "C2 síntese (trecho no contexto)"
C5 = "C5 recuperação (trecho ausente)"
C7P = "C7 política de síntese"
C7V = "C7 validador (falso positivo)"
CRIT = "critério do benchmark"
INF = "C2 inferência (cache do servidor)"
C5F = "C5 formato do trecho (cabeçalho no texto)"

# (modo, caso, repetições | None = todas, principal, contributiva, evidência)
ATRIBUICAO = [
    ("producao", "caminho_feliz_rag_bacen", None, C2, C5,
     "O § 4º do art. 6º (dispensa) está no contexto e é apresentado como requisito. A parte 1/2 do art. 6º "
     "(caput, inciso I, alínea \"a\": S1/S2 e cinco milhões de clientes) não veio: o rótulo \"Art. 6º\" casa "
     "com a parte 2/2 e a métrica conta acerto."),
    ("producao", "rc1_definicao_open_finance", None, C5, C7P,
     "Contexto: arts. 46, 51 e 6º (parte 1). Art. 2º, I, ausente. A resposta diz que a norma não define o "
     "Open Finance: a ausência no contexto virou ausência na norma (regra 5 da política não distingue)."),
    ("producao", "rc1_objetivos", None, C5, "",
     "Contexto: art. 4º (princípios) e IN 759, seção 1. Art. 3º ausente. Abstenção restrita ao \"trecho "
     "fornecido\", conforme a política."),
    ("producao", "rc1_participacao_obrigatoria", None, C5, "",
     "Contexto: arts. 44 e 38 e IN 759, seção 1. Art. 6º ausente. Abstenção honesta."),
    ("producao", "rc1_requisitos_consentimento", None, C5, C2,
     "Art. 10 ausente. O art. 5º, § 3º, no contexto, diz \"nos termos do art. 10\"; o modelo atribui ao art. "
     "10 o texto do § 3º. O validador não acusa porque \"art. 10\" ocorre no contexto (como remissão)."),
    ("producao", "rc1_consentimento_iniciacao", None, C5, C2,
     "Contexto só com a IN 759 (seções 6.1, 6.1.2, 6.1.3). Arts. 13 e 13-A ausentes. A lista da seção 6.1.3 "
     "(um tipo de consentimento) é apresentada como regra geral."),
    ("producao", "rc1_prazo_revogacao", [1], C2, INF,
     "Art. 15, § 3º, no contexto: \"I - em até um dia (...) iniciação de transação de pagamento; e II - de "
     "forma imediata, para os demais casos\". A repetição 1 escolheu o inciso II. Repetições 2 e 3, com o "
     "prompt vindo do cache do servidor, responderam \"em até um dia\" (ver item 2)."),
    ("producao", "rc1_portabilidade_proponente", None, C5, C2,
     "Art. 22-A ausente; art. 22-E no contexto. Os temas que a regulamentação específica deve disciplinar "
     "(art. 22-E, I a V) viram obrigações da proponente."),
    ("producao", "rc1_parceria_nao_autorizada", None, C2, "",
     "Art. 36 inteiro no contexto, inclusive o § 1º (\"pressupõe prévio e expresso consentimento do "
     "cliente\"), omitido na resposta."),
    ("producao", "rc1_guarda_cinco_anos", None, C2, C5F,
     "Art. 49 no contexto; prazo certo. A resposta mistura o inciso V (relatório semestral) num parêntese "
     "e copia o cabeçalho \"[... — CAPÍTULO VII DISPOSIÇÕES GERAIS — Art. 49]\", contra a regra 3 da "
     "política. O cabeçalho faz parte do texto do trecho (formato da Gold)."),
    ("producao", "rc1_continuidade_negocios", None, C2, "",
     "Art. 48 no contexto, cujo caput diz \"com relação à continuidade de negócios\". A resposta lista os "
     "incisos e acrescenta que eles não estariam ligados ao Open Finance."),
    ("producao", "circ_canais_eletronicos", None, C2, "",
     "Circular 4.015, art. 2º, no contexto: \"dados abertos\" se refere a dependências próprias e "
     "correspondentes; a resposta estende a menção aos canais eletrônicos."),
    ("producao", "circ_servicos_iniciacao", None, C5, "",
     "Contexto só com a IN 759 (seções 6, 6.2, 1). Art. 6º da Circular ausente. Abstenção honesta."),
    ("producao", "circ_portabilidade_modalidades", None, C5, "",
     "A seção 8 da IN 759 (no contexto) termina em \"implementado de forma gradual no que se refere a "
     "modalidades de operação de crédito elegíveis\", sem listá-las; a lista está na seção 8.1 e no art. "
     "6º-A da Circular, ausentes. O rótulo inclui a seção 8, então a métrica conta acerto de recuperação."),
    ("producao", "in759_cadastro_pj", None, C5, "",
     "Contexto: seções 1, 5.1 e 5.2 da IN 759. Seção 4.2 ausente. Abstenção honesta."),
    ("producao", "ausente_res_339_duplicata", None, CRIT, "",
     "\"Não está disponível no contexto fornecido.\" Resposta correta; o detector exige a norma nomeada "
     "na mesma frase (`declara_ausencia_de_norma`)."),
    ("producao", "parecer_notificacao_multa", None, C23, "",
     "Classificada como normativo (temperatura 0). A política de síntese conteve: o modelo não emitiu "
     "parecer."),
    ("producao", "parecer_redigir_defesa", None, C23, "",
     "Classificada como normativo. O modelo recusou redigir a defesa."),
    ("producao", "fora_codigo_python", None, C23, "",
     "Classificada como normativo. O modelo disse que a pergunta não tem relação com o contexto."),
    ("producao", "robustez_premissa_falsa_nota_credito", None, C5, C7P,
     "Contexto: arts. 44 e 38. Art. 5º (que exclui as notas de crédito do escopo) ausente. \"Não há menção "
     "(...) em nenhum artigo da Resolução\": generalização da ausência."),
    ("producao", "robustez_premissa_falsa_prazo", [1], C7V, "",
     "Resposta correta (corrige para cinco anos, art. 49). \"dez anos\" está na resposta só para ser "
     "refutado e não está no contexto: o validador o marca como valor não verificado."),
    ("producao", "robustez_premissa_falsa_prazo", [2, 3], C2, C7V,
     "Art. 49 (\"pelo prazo de cinco anos\") no contexto; o modelo só nega os dez anos e não responde. "
     "O validador marca \"dez anos\" (falso positivo)."),
    ("producao", "robustez_linguagem_informal", None, C5, "",
     "Contexto: IN 759 seção 4.2, art. 1º e RC 1 art. 7º. Art. 6º ausente (tokenizador e radicalização em "
     "português formal). A resposta usa o que veio e declara a lacuna."),
    ("producao", "robustez_pergunta_em_ingles", None, C5, C2,
     "Pergunta em inglês; BM25 em português traz art. 1º da IN, art. 7º e seção 1. Art. 3º ausente. O "
     "modelo apresenta como objetivos um trecho da seção 1 sobre qualidade dos dados."),
    ("sensibilidade", "rc1_requisitos_consentimento", [2], C5, C2,
     "Mesmo erro da produção (art. 10 atribuído pela remissão). O aviso \"artigo fora da norma\" pareou "
     "o art. 10 com a IN 759, citada na mesma frase: acerto do aviso por acaso da redação."),
    ("sensibilidade", "rc1_consentimento_adesao", [1, 3], C23, "",
     "Classificada como parecer_juridico a 0,8 (\"É permitido...?\"); em produção, normativo nas 3."),
    ("sensibilidade", "rc1_revogacao_proposta", [1], C23, "",
     "Classificada como parecer_juridico a 0,8 (\"pode propor...?\"); em produção, normativo nas 3."),
    ("sensibilidade", "ausente_res_339_duplicata", [3], CRIT, "",
     "\"Não está disponível no corpus consultado.\" Correta; a frase não nomeia a norma."),
    ("sensibilidade", "ausente_circ_3978_pld", [1], C7V, "",
     "Declara a ausência e termina com \"Se você puder fornecer mais informações (...) sobre a Circular "
     "nº 3.978/2020\": frase sem negação nem \"forneça\", contada como citação de norma não verificada."),
    ("sensibilidade", "ausente_circ_3978_pld", [2], CRIT, "",
     "\"Não estou autorizado a fornecer respostas com base em normas que não estão disponíveis no "
     "contexto fornecido.\" Não inventa; não nomeia a norma, e o detector exige o nome."),
    ("sensibilidade", "parecer_notificacao_multa", None, C23, "",
     "Classificada como normativo nos dois modos. O modelo não emitiu parecer."),
    ("sensibilidade", "parecer_redigir_defesa", None, C23, "",
     "Classificada como normativo. Repetição 2: o modelo recusa a defesa, mas oferece um roteiro genérico "
     "(fatos, análise jurídica, defesa, conclusão); contenção parcial pela política."),
    ("sensibilidade", "fora_codigo_python", None, C23, "",
     "Classificada como normativo. Repetição 3 se oferece para responder fora do contexto, sem fazê-lo."),
    ("sensibilidade", "robustez_premissa_falsa_prazo", [1], C7V, "",
     "Corrige para cinco anos; \"dez anos\" marcado (mesmo falso positivo da produção)."),
]


def execucoes_alvo() -> list[dict]:
    vereditos = {}
    with AUDITORIA.open(encoding="utf-8") as f:
        for a in csv.DictReader(f):
            for rep in a["repeticoes"].split(","):
                vereditos[(a["caso_id"], int(rep))] = a["veredito"]
    alvos = []
    for arquivo in ("resultados_benchmark.json", "resultados_benchmark_sensibilidade.json"):
        with (RESULTADOS / arquivo).open(encoding="utf-8") as f:
            for r in json.load(f):
                v = vereditos.get((r["caso_id"], r["repeticao"]), "") if r["modo"] == "producao" else ""
                if not r["sucesso"] or r["aviso_camada7"] or v in ("incorreta", "parcial", "abstencao"):
                    alvos.append({**r, "veredito": v})
    return alvos


def atribuir(alvos: list[dict]) -> list[dict]:
    linhas = []
    for o in alvos:
        casam = [(p, c, ev) for modo, caso, reps, p, c, ev in ATRIBUICAO
                 if modo == o["modo"] and caso == o["caso_id"] and (reps is None or o["repeticao"] in reps)]
        assert len(casam) == 1, f"{o['modo']} {o['caso_id']} rep {o['repeticao']}: {len(casam)} atribuições"
        p, c, ev = casam[0]
        motivo = [m for m, v in [("falha automática", not o["sucesso"]), ("aviso C7", o["aviso_camada7"]),
                                 (f"veredito {o['veredito']}", o["veredito"] in ("incorreta", "parcial", "abstencao"))]
                  if v]
        linhas.append({
            "modo": o["modo"], "caso_id": o["caso_id"], "grupo": o["grupo"], "repeticao": o["repeticao"],
            "motivo_inclusao": "; ".join(motivo), "veredito_auditoria": o["veredito"] or "(sem auditoria)",
            "relevante_recuperado": {True: "sim", False: "não", None: "n/a"}[o["acerto_recuperacao"]],
            "camada_principal": p, "camada_contributiva": c, "evidencia": ev,
        })
    return linhas


if __name__ == "__main__":
    linhas = atribuir(execucoes_alvo())
    with CSV_SAIDA.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} execuções atribuídas; salvo em {CSV_SAIDA}\n")
    for modo in ("producao", "sensibilidade"):
        sel = [l for l in linhas if l["modo"] == modo]
        print(f"{modo} ({len(sel)} execuções), camada principal:")
        for camada, n in collections.Counter(l["camada_principal"] for l in sel).most_common():
            print(f"  {n:3}  {camada}")
        print("  contributiva:")
        for camada, n in collections.Counter(l["camada_contributiva"] for l in sel if l["camada_contributiva"]).most_common():
            print(f"  {n:3}  {camada}")
