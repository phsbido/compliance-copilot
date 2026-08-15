"""
Script de validação — Camada 7 (Governança e Segurança).

Testa `validar_citacao`, `recusar_parecer_juridico` e `recusar_fora_de_escopo`
isoladamente, com casos construídos a partir dos achados empíricos registrados
em docs/evidencias_empiricas.md: um artigo citado que não está no contexto
(reproduz o achado da Camada 4/6) e uma citação que bate com o contexto
(não deve gerar aviso de citação, só o aviso padrão de validação humana).

Uso:
    python run_check_governance.py
"""
from src.layer7_governance.governance import (
    recusar_fora_de_escopo,
    recusar_parecer_juridico,
    validar_citacao,
)

CONTEXTO_REAL = (
    "Fonte: Resolução Conjunta nº 1, de 4 de maio de 2020 "
    "(https://normativos.bcb.gov.br/Lists/Normativos/Attachments/51028/Res_Conj_0001_v7_L.pdf)\n"
    "Art. 6º São participantes do Open Finance: instituições com número de "
    "clientes superior a cinco milhões."
)

if __name__ == "__main__":
    print("Testando validar_citacao (Camada 7) com citação incorreta de artigo...")
    resposta_com_erro = "Esse requisito está no art. 51 da Resolução Conjunta nº 1."
    resultado = validar_citacao(resposta_com_erro, CONTEXTO_REAL)
    print(resultado)
    assert "art. 51" in resultado and "não aparece no trecho normativo" in resultado
    print("\n[OK] Citação incorreta foi sinalizada.\n")

    print("Testando validar_citacao com citação correta (art. 6º, presente no contexto)...")
    resposta_correta = "Esse requisito está no art. 6º da Resolução Conjunta nº 1."
    resultado2 = validar_citacao(resposta_correta, CONTEXTO_REAL)
    print(resultado2)
    assert "não aparece no trecho normativo" not in resultado2
    assert "não consta no trecho normativo" not in resultado2, (
        "falso positivo: o ponto final da frase não deve ser confundido com "
        "parte do número da norma"
    )
    print("\n[OK] Citação correta não gerou aviso de inconsistência.\n")

    print("Testando recusar_parecer_juridico...")
    print(recusar_parecer_juridico())
    print("\n[OK] Recusa de parecer jurídico funcionando.")

    print("\nTestando recusar_fora_de_escopo...")
    print(recusar_fora_de_escopo())
    print("\n[OK] Recusa de pergunta fora de escopo funcionando.")

    print("\nGovernança validada.")
