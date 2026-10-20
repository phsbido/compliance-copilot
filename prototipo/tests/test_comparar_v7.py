"""
Testes do teste de McNemar exato e do ajuste de Holm de
scripts/comparar_v7.py — sem LLM, sem Ollama, com dados sintéticos.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import math
import unittest

import pandas as pd

from scripts.comparar_v7 import mcnemar, mcnemar_exato


def _dados(acertos: dict[str, list[bool]]) -> dict[str, pd.DataFrame]:
    return {
        m: pd.DataFrame({"caso_id": [f"c{i}" for i in range(len(v))], "grupo": "normativo_corpus",
                         "acerto_recuperacao": v})
        for m, v in acertos.items()
    }


class TestMcNemarExato(unittest.TestCase):
    def test_sem_discordantes(self):
        self.assertEqual(mcnemar_exato(0, 0), 1.0)

    def test_tres_contra_zero(self):
        # n = 3 discordantes, todos para o mesmo lado: 2 × (1/2)^3 = 0,25.
        self.assertAlmostEqual(mcnemar_exato(0, 3), 0.25)
        self.assertAlmostEqual(mcnemar_exato(3, 0), 0.25)

    def test_simetrico_e_limitado_a_um(self):
        self.assertAlmostEqual(mcnemar_exato(2, 3), mcnemar_exato(3, 2))
        self.assertEqual(mcnemar_exato(4, 4), 1.0)

    def test_confere_com_binomial(self):
        b, c = 1, 9
        n = b + c
        esperado = 2 * sum(math.comb(n, i) for i in range(b + 1)) / 2 ** n
        self.assertAlmostEqual(mcnemar_exato(b, c), esperado)
        self.assertLess(mcnemar_exato(b, c), 0.05)


class TestHolm(unittest.TestCase):
    def test_ajuste_monotonico_e_contagens(self):
        dados = _dados({
            "bm25":       [True] * 5 + [False] * 10,
            "embeddings": [True] * 15,
            "hybrid":     [True] * 6 + [False] * 9,
        })
        df = mcnemar(dados).set_index("comparacao")
        self.assertEqual(df.loc["bm25 x embeddings", "so_b_acerta"], 10)
        self.assertEqual(df.loc["bm25 x embeddings", "so_a_acerta"], 0)
        # Holm: p ajustado >= p bruto e na mesma ordem dos p brutos.
        self.assertTrue((df["p_holm"] >= df["p_exato"] - 1e-12).all())
        ordem_bruta = df["p_exato"].sort_values().index.tolist()
        self.assertTrue(df.loc[ordem_bruta, "p_holm"].is_monotonic_increasing)
        self.assertAlmostEqual(df.loc["bm25 x embeddings", "p_holm"],
                               min(1.0, 3 * df.loc["bm25 x embeddings", "p_exato"]), places=3)


if __name__ == "__main__":
    unittest.main()
