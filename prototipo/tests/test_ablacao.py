"""
Testes da ablação da Camada 7 (v6, Tarefa C) no Orchestrator, com um LLM
falso: sem Ollama, determinísticos.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path

import src.layer8_observability.observability as observabilidade
from src.layer3_orchestration.orchestrator import Orchestrator
from src.layer7_governance.governance import AVISO_VALIDACAO_HUMANA, POLITICA_SINTESE, RECUSA_PARECER_JURIDICO

SINTESE = "Segundo a Resolução Conjunta nº 1/2020, art. 49, o prazo é de cinco anos."


class LLMFalso:
    """Classifica com o tipo pedido e sintetiza um texto fixo, guardando o
    system prompt de cada chamada de síntese."""

    def __init__(self, tipo: str = "normativo"):
        self.tipo = tipo
        self.systems_sintese = []

    def generate(self, prompt, system=None, options=None):
        if prompt.startswith("Contexto normativo:") or "Pergunta:" in prompt:
            self.systems_sintese.append(system)
            return SINTESE
        return self.tipo

    def identificacao(self):
        return {"modelo": "falso", "id_modelo": "0"}


class TestAblacaoCamada7(unittest.TestCase):
    PERGUNTA = "Por quanto tempo as informações sobre consentimentos devem ser mantidas?"

    def setUp(self):
        self._log_original = observabilidade.LOG_FILE
        self._tmp = tempfile.TemporaryDirectory()
        observabilidade.LOG_FILE = Path(self._tmp.name) / "interacoes.jsonl"

    def tearDown(self):
        observabilidade.LOG_FILE = self._log_original
        self._tmp.cleanup()

    def test_sem_ablacao_valida_e_anexa_aviso(self):
        llm = LLMFalso()
        resposta = Orchestrator(llm=llm).responder(self.PERGUNTA)
        self.assertIn(AVISO_VALIDACAO_HUMANA.strip(), resposta)
        self.assertEqual(llm.systems_sintese, [POLITICA_SINTESE])

    def test_c1_devolve_a_sintese_crua_com_a_politica(self):
        llm = LLMFalso()
        orq = Orchestrator(llm=llm, ablacao="c1")
        self.assertEqual(orq.responder(self.PERGUNTA), SINTESE)
        self.assertEqual(llm.systems_sintese, [POLITICA_SINTESE])
        self.assertEqual(orq.ultimo_registro.validacao, {})
        self.assertEqual(orq.ultimo_registro.parametros_llm["ablacao_camada7"], "c1")

    def test_c2_tira_tambem_a_politica(self):
        llm = LLMFalso()
        self.assertEqual(Orchestrator(llm=llm, ablacao="c2").responder(self.PERGUNTA), SINTESE)
        self.assertEqual(llm.systems_sintese, [None])

    def test_recusa_por_classificacao_continua_na_ablacao(self):
        for ablacao in ("c1", "c2"):
            llm = LLMFalso(tipo="parecer_juridico")
            self.assertEqual(Orchestrator(llm=llm, ablacao=ablacao).responder("Vou ser multado?"),
                             RECUSA_PARECER_JURIDICO)
            self.assertEqual(llm.systems_sintese, [])

    def test_variante_desconhecida(self):
        with self.assertRaises(ValueError):
            Orchestrator(llm=LLMFalso(), ablacao="c3")


if __name__ == "__main__":
    unittest.main()
