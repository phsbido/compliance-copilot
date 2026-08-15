"""
Script de validação — Camada 8 (Observabilidade e Proveniência).

Testa `registrar_interacao` isoladamente: um caso com normativo (fonte
extraída corretamente, sem aviso de citação não verificada), um caso com
aviso de citação não verificada (Camada 7 sinalizou), e um caso de recusa de
parecer jurídico (sem fontes). Usa um arquivo de log temporário, não o
`logs/interacoes.jsonl` real, para não poluir o log de uso do protótipo.

Uso:
    python run_check_observability.py
"""
import json
import tempfile
from pathlib import Path

from src.layer8_observability.observability import registrar_interacao

NORMATIVO = (
    "Fonte: Resolução Conjunta nº 1/2020 (https://normativos.bcb.gov.br/exemplo.pdf)\n"
    "Art. 6º São participantes do Open Finance instituições com número de "
    "clientes superior a cinco milhões."
)

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        arquivo = Path(tmp) / "interacoes.jsonl"

        print("Testando registro de interação com normativo (sem aviso)...")
        registrar_interacao(
            pergunta="Quem participa do Open Finance?",
            tipo_classificacao="normativo",
            resposta_final="Participam instituições com mais de 5 milhões de clientes (art. 6º).",
            normativo=NORMATIVO,
            arquivo=arquivo,
        )
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        assert len(linhas) == 1
        registro1 = json.loads(linhas[0])
        assert registro1["fontes_normativas"] == [
            {
                "titulo": "Resolução Conjunta nº 1/2020",
                "url_oficial": "https://normativos.bcb.gov.br/exemplo.pdf",
            }
        ]
        assert registro1["aviso_citacao_nao_verificada"] is False
        assert registro1["tipo_classificacao"] == "normativo"
        print("[OK] Fonte extraída corretamente, sem aviso.\n")

        print("Testando registro com citação não verificada (Camada 7 sinalizou)...")
        registrar_interacao(
            pergunta="Qual artigo trata disso?",
            tipo_classificacao="normativo",
            resposta_final=(
                "Está no art. 51.\n\nAviso: a resposta cita art. 51, que não "
                "aparece no trecho normativo usado como base para esta resposta."
            ),
            normativo=NORMATIVO,
            arquivo=arquivo,
        )
        linhas = arquivo.read_text(encoding="utf-8").splitlines()
        assert len(linhas) == 2
        registro2 = json.loads(linhas[1])
        assert registro2["aviso_citacao_nao_verificada"] is True
        print("[OK] Aviso de citação não verificada foi registrado.\n")

        print("Testando registro de recusa de parecer jurídico (sem fontes)...")
        registro3 = registrar_interacao(
            pergunta="Posso fazer X no meu caso específico?",
            tipo_classificacao="parecer_juridico",
            resposta_final="Não posso emitir parecer jurídico definitivo sobre casos concretos.",
            arquivo=arquivo,
        )
        assert registro3.fontes_normativas == []
        assert registro3.tipo_classificacao == "parecer_juridico"
        print("[OK] Recusa registrada sem fontes normativas.\n")

    print("Observabilidade validada.")
