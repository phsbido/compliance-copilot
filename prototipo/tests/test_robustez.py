"""
Testes da robustez a falhas do Ollama (2026-10-20): cliente da Camada 2,
registro de erro nas Camadas 3/8 e mensagem da CLI (Camada 1). Sem Ollama,
determinísticos.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import src.layer1_interaction.cli as cli
import src.layer2_llm_core.core as core
import src.layer8_observability.observability as observabilidade
from src.layer3_orchestration.orchestrator import Orchestrator


class TestClienteCamada2(unittest.TestCase):
    def setUp(self):
        self._clientes = dict(core._CLIENTES)
        core._CLIENTES.clear()

    def tearDown(self):
        core._CLIENTES.clear()
        core._CLIENTES.update(self._clientes)

    def test_cliente_usa_host_e_timeout_das_settings_e_e_compartilhado(self):
        with mock.patch.object(core.settings, "ollama_host", "http://127.0.0.1:9999"), \
                mock.patch.object(core.settings, "ollama_timeout_s", 12.5), \
                mock.patch.object(core.ollama, "Client") as cliente_cls:
            cliente_cls.return_value.chat.return_value = {"message": {"content": "ok"}, "done_reason": "stop"}
            a, b = core.LLMCore(), core.LLMCore()
            self.assertEqual(a.generate("oi"), "ok")
            self.assertEqual(b.generate("oi"), "ok")
            self.assertEqual(a.ultimo_motivo_parada, "stop")
        cliente_cls.assert_called_once_with(host="http://127.0.0.1:9999", timeout=12.5)
        self.assertEqual(cliente_cls.return_value.chat.call_count, 2)


class _LLMQueFalha:
    def generate(self, prompt, system=None, options=None):
        raise ConnectionError("Ollama fora do ar")

    def identificacao(self):
        raise AssertionError("o registro do erro não deve consultar o Ollama")


class _TmpLog(unittest.TestCase):
    def setUp(self):
        self._log_original = observabilidade.LOG_FILE
        self._tmp = tempfile.TemporaryDirectory()
        observabilidade.LOG_FILE = Path(self._tmp.name) / "interacoes.jsonl"

    def tearDown(self):
        observabilidade.LOG_FILE = self._log_original
        self._tmp.cleanup()


class TestFalhaNoFluxo(_TmpLog):
    def test_relanca_registra_erro_e_nao_grava_na_memoria(self):
        orq = Orchestrator(llm=_LLMQueFalha())
        with self.assertRaises(ConnectionError):
            orq.responder("Qual o prazo de guarda dos consentimentos?")
        self.assertEqual(orq.ultimo_registro.desfecho, "erro")
        self.assertIn("Ollama fora do ar", orq.ultimo_registro.erro)
        self.assertEqual(orq.memoria.contexto_formatado(), "")
        linhas = observabilidade.LOG_FILE.read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(linhas[-1])["desfecho"], "erro")


class TestFalhaNaCLI(_TmpLog):
    def test_mensagem_e_sessao_continua(self):
        class OrquestradorQueFalha:
            ultimo_registro = None

            def responder(self, pergunta):
                raise ConnectionError("recusou")

        saida = io.StringIO()
        with mock.patch.object(cli, "Orchestrator", OrquestradorQueFalha), \
                mock.patch("builtins.input", side_effect=["uma pergunta", "sair"]), \
                contextlib.redirect_stdout(saida):
            cli.main()
        texto = saida.getvalue()
        self.assertIn("Não foi possível gerar a resposta", texto)
        self.assertIn("recusou", texto)
        self.assertIn("Encerrando.", texto)


if __name__ == "__main__":
    unittest.main()
