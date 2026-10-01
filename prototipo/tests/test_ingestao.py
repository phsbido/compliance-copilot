"""
Testes da limpeza de texto de PDF na ingestão (Camada 5) — sem LLM, sem
internet.

Os casos vêm da extração real dos PDFs consolidados do BCB pelo pypdf (ver
docs/evidencias_empiricas.md, v4.1).

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import json
import unittest
from pathlib import Path

from src.layer5_knowledge.ingest_normativos import _limpar_artefatos_pdf
from src.layer7_governance.governance import validar_resposta

RAIZ = Path(__file__).resolve().parents[1]
GOLD_RC1 = RAIZ / "data" / "normativos" / "3_gold_indexed" / "resolucao_conjunta_1_2020.json"


class TestHifen(unittest.TestCase):
    def test_pronome_enclitico(self):
        self.assertEqual(_limpar_artefatos_pdf("§ 2º Excetuam -se as instituições"),
                         "§ 2º Excetuam-se as instituições")

    def test_identificador_de_artigo(self):
        self.assertEqual(_limpar_artefatos_pdf("Art. 22 -A. Art. 6º -A"), "Art. 22-A. Art. 6º-A")

    def test_inciso_com_travessao_nao_muda(self):
        texto = "I - no caso do compartilhamento"
        self.assertEqual(_limpar_artefatos_pdf(texto), texto)


class TestPalavraPartida(unittest.TestCase):
    def test_junta_quando_a_palavra_inteira_aparece_no_documento(self):
        texto = "escopo de implem entação definido. A implementação ocorre."
        self.assertIn("escopo de implementação definido", _limpar_artefatos_pdf(texto))

    def test_palavras_frequentes_lado_a_lado_nao_sao_juntadas(self):
        # "de" e "mais" são frequentes; "demais" existir no texto não basta.
        texto = "as demais instituições; de mais de um tipo; de mais clientes; mais dados; mais prazo"
        self.assertEqual(_limpar_artefatos_pdf(texto), texto)

    def test_residuo_conhecido_sem_forma_inteira_no_documento(self):
        # "referem" não aparece em outro ponto da Resolução Conjunta nº 1:
        # resíduo documentado, não corrigido.
        texto = "os serviços a que se refere m os dados"
        self.assertEqual(_limpar_artefatos_pdf(texto), texto)


class TestGoldSemArtefatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gold = json.loads(GOLD_RC1.read_text(encoding="utf-8"))

    def test_gold_nao_tem_espaco_antes_do_hifen(self):
        textos = " ".join(t["texto"] for t in self.gold["trechos"])
        for artefato in ("22 -A", "Excetuam -se", "considera -se", "implem entação"):
            self.assertNotIn(artefato, textos)

    def test_citacao_correta_de_artigo_com_letra_nao_gera_aviso(self):
        # Na v4, "Art. 22 -A" na Gold fazia a Camada 7 sinalizar a citação
        # correta "art. 22-A" como não verificada.
        trecho = next(t for t in self.gold["trechos"] if t["identificador"] == "Art. 22-A")
        contexto = f"Fonte: {self.gold['titulo']} ({self.gold['url_oficial']})\n{trecho['texto']}"
        r = validar_resposta("Conforme o art. 22-A da Resolução Conjunta nº 1/2020, há requisitos.", contexto)
        self.assertEqual((r.artigos_nao_verificados, r.artigos_fora_da_norma), ([], []))


if __name__ == "__main__":
    unittest.main()
