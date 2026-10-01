"""
Script de validação — Camada 7 (Governança e Segurança).

Mostra, sem LLM, as três frentes da governança (ver docs/decisoes_arquitetura.md,
Camada 7 v2):

- antes da geração: recusa de parecer jurídico, de pergunta fora de escopo e
  de pergunta sem base no corpus;
- depois da geração: `validar_resposta` confere norma, artigo e valor citados
  contra o contexto recuperado, e distingue ausência declarada de citação
  inventada. Os casos reproduzem os achados de docs/evidencias_empiricas.md;
- na ingestão: só fontes de domínios do BCB são aceitas.

Os testes exaustivos ficam em tests/test_governanca.py.

Uso:
    python run_check_governance.py
"""
from src.layer7_governance.governance import (
    recusar_fora_de_escopo,
    recusar_parecer_juridico,
    recusar_sem_base,
    validar_fonte_publica,
    validar_resposta,
)

URL_RC1 = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=1"

CONTEXTO_REAL = (
    f"Fonte: Resolução Conjunta nº 1, de 4 de maio de 2020 ({URL_RC1})\n"
    "[Resolução Conjunta nº 1/2020 — Seção II Da Participação no Open Finance — Art. 6º]\n"
    "Art. 6º São participantes do Open Finance as instituições com número de "
    "clientes superior a cinco milhões."
)

CASOS = [
    # (descrição, resposta simulada do LLM, campo esperado com aviso ou None)
    ("Citação correta (art. 6º e valor presentes no contexto)",
     "Participam as instituições com mais de 5 milhões de clientes (Resolução Conjunta nº 1/2020, art. 6º).",
     None),
    ("Artigo que não está no contexto",
     "Esse requisito está no art. 51 da Resolução Conjunta nº 1.",
     "artigos_nao_verificados"),
    ("Valor distorcido (achado real: 'cinco milhões' -> '3 milhões')",
     "Participam as instituições com mais de 3 milhões de clientes.",
     "valores_nao_verificados"),
    ("Norma inventada (achado real da v1)",
     "Segundo a Resolução BCB nº 32/2020, as interfaces devem ser padronizadas.",
     "normas_nao_verificadas"),
    ("Ausência declarada (comportamento correto, sem aviso)",
     "Não encontrei a Resolução BCB nº 32/2020 no contexto consultado.",
     "normas_declaradas_ausentes"),
]


def _mostrar(descricao: str, resposta: str, campo: str | None) -> None:
    r = validar_resposta(resposta, CONTEXTO_REAL)
    print(f"- {descricao}")
    print(f"  resposta: {resposta}")
    if campo is None:
        assert not r.possui_aviso, "citação correta não deve gerar aviso"
        print("  [OK] sem aviso\n")
    elif campo == "normas_declaradas_ausentes":
        assert not r.possui_aviso and getattr(r, campo), campo
        print(f"  [OK] registrada como ausência declarada: {getattr(r, campo)}\n")
    else:
        assert r.possui_aviso and getattr(r, campo), campo
        print(f"  [OK] aviso em {campo}: {getattr(r, campo)}\n")


if __name__ == "__main__":
    print("1) Antes da geração: recusas\n")
    print(f"- Parecer jurídico:\n  {recusar_parecer_juridico()}\n")
    print(f"- Fora de escopo:\n  {recusar_fora_de_escopo()}\n")
    print(f"- Sem base no corpus:\n  {recusar_sem_base()}\n")

    print("2) Depois da geração: verificação da resposta contra o contexto\n")
    for caso in CASOS:
        _mostrar(*caso)

    print("Texto final entregue ao usuário (caso do artigo inexistente):")
    print(validar_resposta(CASOS[1][1], CONTEXTO_REAL).texto_final)

    print("\n3) Na ingestão: só fontes públicas do BCB\n")
    validar_fonte_publica(URL_RC1)
    print(f"- {URL_RC1}\n  [OK] aceita")
    try:
        validar_fonte_publica("https://blog-qualquer.com/resumo-open-finance")
        raise AssertionError("fonte fora do BCB deveria ser recusada")
    except ValueError as erro:
        print(f"- https://blog-qualquer.com/resumo-open-finance\n  [OK] recusada: {erro}")

    print("\nGovernança validada.")
