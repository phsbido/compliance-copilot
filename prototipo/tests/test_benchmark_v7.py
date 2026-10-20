"""
Testes das mudanças da v7 em run_benchmark.py — sem LLM, sem Ollama:
gravação do JSON bruto (temporário + substituição, com novas tentativas) e
latência mediana da busca na tabela por grupo.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import run_benchmark
from run_benchmark import salvar_resultados_json, tabela_por_caso, tabela_por_grupo


class TestSalvarResultadosJson(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.destino = Path(self._tmp.name) / "sub" / "resultados_benchmark.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_grava_sem_deixar_temporario(self):
        salvar_resultados_json([{"caso_id": "a", "texto": "ação"}], self.destino)
        self.assertEqual(json.loads(self.destino.read_text(encoding="utf-8")), [{"caso_id": "a", "texto": "ação"}])
        self.assertEqual([p.name for p in self.destino.parent.iterdir()], [self.destino.name])

    def test_tenta_de_novo_depois_de_oserror(self):
        substituir = run_benchmark.os.replace
        chamadas = []

        def falha_uma_vez(origem, destino):
            chamadas.append(1)
            if len(chamadas) == 1:
                raise OSError(22, "Invalid argument")
            substituir(origem, destino)

        with mock.patch.object(run_benchmark.os, "replace", side_effect=falha_uma_vez), \
                mock.patch.object(run_benchmark.time, "sleep"):
            salvar_resultados_json([{"x": 1}], self.destino)
        self.assertEqual(len(chamadas), 2)
        self.assertEqual(json.loads(self.destino.read_text(encoding="utf-8")), [{"x": 1}])

    def test_desiste_depois_das_tentativas(self):
        with mock.patch.object(run_benchmark.os, "replace", side_effect=OSError(22, "Invalid argument")), \
                mock.patch.object(run_benchmark.time, "sleep"):
            with self.assertRaises(OSError):
                salvar_resultados_json([{"x": 1}], self.destino, tentativas=3)


def _execucoes(com_busca: bool) -> pd.DataFrame:
    linhas = []
    for i, (grupo, ms) in enumerate([("normativo_corpus", 100.0), ("normativo_corpus", 300.0),
                                     ("norma_ausente", 2000.0)]):
        r = {"caso_id": f"c{i}", "grupo": grupo, "categoria": "x", "tipo_esperado": "normativo",
             "comportamento_esperado": "resposta_fundamentada", "repeticao": 1, "sucesso": True,
             "classificacao_correta": True, "recusou": False, "aviso_citacao_nao_verificada": False,
             "cobertura_termos": None, "acerto_recuperacao": True, "recall_recuperacao": 1.0,
             "rr_recuperacao": 1.0, "latencia_ms": 1000.0, "resposta": "r",
             **{c: False for c in run_benchmark.COLUNAS_CAMADA7}}
        if com_busca:
            r["latencia_busca_ms"] = ms
        linhas.append(r)
    return pd.DataFrame(linhas)


class TestLatenciaBusca(unittest.TestCase):
    def test_mediana_da_busca_por_grupo(self):
        df = _execucoes(com_busca=True)
        g = tabela_por_grupo(df, tabela_por_caso(df)).set_index("grupo")
        self.assertEqual(g.loc["normativo_corpus", "latencia_busca_mediana_ms"], 200.0)
        self.assertEqual(g.loc["total", "latencia_busca_mediana_ms"], 300.0)

    def test_json_anterior_a_v7_nao_ganha_a_coluna(self):
        # --revalidar/--somente-tabela sobre JSON da v5/v6 regeram as mesmas colunas.
        df = _execucoes(com_busca=False)
        self.assertNotIn("latencia_busca_mediana_ms", tabela_por_grupo(df, tabela_por_caso(df)).columns)


if __name__ == "__main__":
    unittest.main()
