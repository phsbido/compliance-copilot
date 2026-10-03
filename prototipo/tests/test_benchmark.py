"""
Testes das métricas do benchmark v5 (run_benchmark.py) e da integridade da
bateria tests/casos_teste.json — sem LLM, determinísticos.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import json
import unittest
from pathlib import Path

from run_benchmark import (
    ORDEM_GRUPOS,
    RESULTADOS_DIR,
    TABELA_RECUPERACAO,
    caminhos_saida,
    avaliar_sucesso,
    cobertura_termos,
    declara_ausencia_de_norma,
    metricas_recuperacao,
    recuperar,
    wilson,
)

RAIZ = Path(__file__).resolve().parents[1]
GOLD_DIR = RAIZ / "data" / "normativos" / "3_gold_indexed"
CASOS = json.loads((RAIZ / "tests" / "casos_teste.json").read_text(encoding="utf-8"))["casos"]

RC1 = "Resolução Conjunta nº 1, de 4 de maio de 2020"
CIRC = "Circular nº 4.015, de 4 de maio de 2020"


def _execucao(**campos) -> dict:
    base = {
        "classificacao_correta": True, "desfecho": "resposta", "recusou": False,
        "aviso_camada7": False, "ausencia_declarada": False, "resposta_declara_ausencia": False,
        "comportamento_esperado": "resposta_fundamentada",
    }
    base.update(campos)
    return base


class TestWilson(unittest.TestCase):
    def test_valores_de_referencia(self):
        # 8/10: IC de Wilson 95% = [0,490; 0,943] (valor tabelado).
        inf, sup = wilson(8, 10)
        self.assertAlmostEqual(inf, 0.490, places=3)
        self.assertAlmostEqual(sup, 0.943, places=3)

    def test_extremos_ficam_no_intervalo_unitario(self):
        self.assertEqual(wilson(0, 5)[0], 0.0)
        self.assertEqual(wilson(5, 5)[1], 1.0)
        self.assertLess(wilson(5, 5)[0], 1.0)  # 5/5 não dá certeza

    def test_n_zero(self):
        inf, sup = wilson(0, 0)
        self.assertNotEqual(inf, inf)  # NaN


class TestCoberturaTermos(unittest.TestCase):
    def test_ignora_acento_e_caixa(self):
        self.assertEqual(cobertura_termos("Prazo de CINCO anos e relatório semestral.",
                                          [["cinco anos", "5 anos"], ["semestral"]]), 1.0)

    def test_cobertura_parcial(self):
        self.assertEqual(cobertura_termos("Objetivos: inovação.", [["inovacao"], ["concorrencia"]]), 0.5)

    def test_sem_termos_ou_sem_resposta(self):
        self.assertIsNone(cobertura_termos("texto", []))
        self.assertIsNone(cobertura_termos("", [["x"]]))


class TestMetricasRecuperacao(unittest.TestCase):
    relevantes = [{"norma": "Resolução Conjunta nº 1", "trecho": "Art. 6º"}]

    def test_relevante_na_segunda_posicao(self):
        recuperados = [{"norma": RC1, "trecho": "Art. 7º"}, {"norma": RC1, "trecho": "Art. 6º"},
                       {"norma": CIRC, "trecho": "Art. 1º"}]
        m = metricas_recuperacao(recuperados, self.relevantes)
        self.assertEqual(m, {"acerto_recuperacao": True, "recall_recuperacao": 1.0, "rr_recuperacao": 0.5})

    def test_nao_recuperado(self):
        m = metricas_recuperacao([{"norma": RC1, "trecho": "Art. 44"}], self.relevantes)
        self.assertEqual(m, {"acerto_recuperacao": False, "recall_recuperacao": 0.0, "rr_recuperacao": 0.0})

    def test_mesmo_identificador_em_outra_norma_nao_conta(self):
        m = metricas_recuperacao([{"norma": CIRC, "trecho": "Art. 6º"}], self.relevantes)
        self.assertFalse(m["acerto_recuperacao"])

    def test_numero_de_norma_nao_casa_por_prefixo(self):
        # "Resolução Conjunta nº 1" não pode casar com uma hipotética nº 10.
        m = metricas_recuperacao([{"norma": "Resolução Conjunta nº 10, de 2022", "trecho": "Art. 6º"}],
                                 self.relevantes)
        self.assertFalse(m["acerto_recuperacao"])

    def test_recall_com_varios_rotulos(self):
        relevantes = self.relevantes + [{"norma": "Circular nº 4.015", "trecho": "Art. 1º"}]
        m = metricas_recuperacao([{"norma": RC1, "trecho": "Art. 6º"}], relevantes)
        self.assertEqual(m["recall_recuperacao"], 0.5)

    def test_caso_sem_rotulo(self):
        self.assertIsNone(metricas_recuperacao([], [])["acerto_recuperacao"])

    def test_recuperacao_real_e_deterministica(self):
        pergunta = "Por quanto tempo as instituições devem manter as informações sobre consentimentos?"
        self.assertEqual(recuperar(pergunta), recuperar(pergunta))
        self.assertEqual(len(recuperar(pergunta)), 3)


class TestAvaliarSucesso(unittest.TestCase):
    def test_resposta_fundamentada(self):
        self.assertTrue(avaliar_sucesso(_execucao()))
        self.assertFalse(avaliar_sucesso(_execucao(aviso_camada7=True)))
        self.assertFalse(avaliar_sucesso(_execucao(desfecho="recusa_sem_base", recusou=True)))
        self.assertFalse(avaliar_sucesso(_execucao(classificacao_correta=False)))

    def test_ausencia_declarada(self):
        caso = dict(comportamento_esperado="ausencia_declarada")
        self.assertTrue(avaliar_sucesso(_execucao(**caso, ausencia_declarada=True)))
        self.assertTrue(avaliar_sucesso(_execucao(**caso, desfecho="recusa_sem_base", recusou=True)))
        self.assertTrue(avaliar_sucesso(_execucao(**caso, resposta_declara_ausencia=True)))
        self.assertFalse(avaliar_sucesso(_execucao(**caso)))  # respondeu sem declarar ausência
        self.assertFalse(avaliar_sucesso(_execucao(**caso, ausencia_declarada=True, aviso_camada7=True)))

    def test_recusa(self):
        caso = dict(comportamento_esperado="recusa")
        self.assertTrue(avaliar_sucesso(_execucao(**caso, desfecho="recusa_parecer_juridico", recusou=True)))
        self.assertFalse(avaliar_sucesso(_execucao(**caso)))

    def test_sem_alucinacao_aceita_qualquer_desfecho(self):
        caso = dict(comportamento_esperado="sem_alucinacao", classificacao_correta=False)
        self.assertTrue(avaliar_sucesso(_execucao(**caso, desfecho="recusa_fora_de_escopo", recusou=True)))
        self.assertFalse(avaliar_sucesso(_execucao(**caso, aviso_camada7=True)))


class TestDeclaraAusenciaDeNorma(unittest.TestCase):
    def test_resposta_real_do_teste_de_fumaca(self):
        # Resposta real (v5, caso ausente_res_bcb_1_pix): a Res. BCB 1/2020 é
        # mencionada pela IN 759 no contexto, então a Camada 7 não a lista
        # como ausente — o benchmark precisa reconhecer a ausência declarada.
        resposta = ("Infelizmente, não está disponível no contexto fornecido a informação sobre a "
                    "Resolução BCB nº 1/2020 e a devolução de transações Pix.")
        self.assertTrue(declara_ausencia_de_norma(resposta))

    def test_citacao_afirmativa_nao_conta(self):
        self.assertFalse(declara_ausencia_de_norma(
            "A Resolução Conjunta nº 1/2020 exige consentimento do cliente."))

    def test_ausencia_sem_norma_nao_conta(self):
        self.assertFalse(declara_ausencia_de_norma("Não encontrei essa informação no contexto."))


class TestBateria(unittest.TestCase):
    def test_ids_unicos_e_casos_originais_preservados(self):
        ids = [c["id"] for c in CASOS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[:4], ["caminho_feliz_rag_bacen", "norma_ausente_fronteira",
                                   "solicitacao_parecer_governanca", "fora_de_escopo_governanca"])

    def test_campos_validos(self):
        tipos = {"normativo", "parecer_juridico", "fora_de_escopo"}
        comportamentos = {"resposta_fundamentada", "ausencia_declarada", "recusa", "sem_alucinacao"}
        for c in CASOS:
            with self.subTest(c["id"]):
                self.assertIn(c["grupo"], ORDEM_GRUPOS)
                self.assertIn(c["tipo_esperado"], tipos)
                self.assertTrue(set(c.get("tipos_aceitos", [])) <= tipos)
                self.assertIn(c["comportamento_esperado"], comportamentos)
                for grupo in c.get("termos_esperados", []):
                    # Termos já normalizados (sem acento, minúsculas), como a comparação.
                    for termo in grupo:
                        self.assertEqual(termo, termo.lower())
                        self.assertTrue(termo.isascii(), termo)

    def test_rotulos_de_recuperacao_existem_na_gold(self):
        existentes = set()
        indice = json.loads((GOLD_DIR / "indice_bm25.json").read_text(encoding="utf-8"))
        for arquivo in indice["arquivos"]:
            gold = json.loads((GOLD_DIR / arquivo).read_text(encoding="utf-8"))
            existentes |= {(gold["titulo"].split(",")[0], t["identificador"]) for t in gold["trechos"]}
        for c in CASOS:
            for r in c.get("relevantes", []):
                with self.subTest(c["id"], rotulo=r):
                    self.assertIn((r["norma"], r["trecho"]), existentes)

    def test_normativos_do_corpus_tem_rotulo(self):
        for c in CASOS:
            if c["grupo"] == "normativo_corpus":
                with self.subTest(c["id"]):
                    self.assertTrue(c.get("relevantes"))


class TestLimiarBM25(unittest.TestCase):
    """Limiar da Camada 5 (v6): decide pelo melhor trecho; desligado = v5."""
    PERGUNTA = "Quais são os fatores de autenticação do cliente no Open Finance?"

    @classmethod
    def setUpClass(cls):
        from src.layer5_knowledge.knowledge_base import KnowledgeBase
        cls.kb = KnowledgeBase()
        cls.melhor = cls.kb.buscar_pontuado(cls.PERGUNTA, top_k=1)[0][0]

    def test_desligado_igual_a_v5(self):
        self.assertEqual(self.kb.buscar(self.PERGUNTA, limiar=None), self.kb.buscar(self.PERGUNTA))
        self.assertEqual(len(self.kb.buscar(self.PERGUNTA)), 3)

    def test_no_limiar_devolve_os_tres(self):
        self.assertEqual(self.kb.buscar(self.PERGUNTA, limiar=self.melhor), self.kb.buscar(self.PERGUNTA))

    def test_acima_do_melhor_nao_devolve_nada(self):
        self.assertEqual(self.kb.buscar(self.PERGUNTA, limiar=self.melhor + 0.001), [])

    def test_camada_4_devolve_a_constante_de_recusa(self):
        from src.layer4_tools.tools import NENHUM_TRECHO_ENCONTRADO, buscar_normativo
        self.assertEqual(buscar_normativo(self.PERGUNTA, limiar=self.melhor + 0.001), NENHUM_TRECHO_ENCONTRADO)

    def test_recuperacao_vazia_conta_como_erro(self):
        recuperados = recuperar(self.PERGUNTA, limiar=self.melhor + 0.001)
        self.assertEqual(recuperados, [])
        m = metricas_recuperacao(recuperados, [{"norma": "Resolução Conjunta nº 1", "trecho": "Art. 17"}])
        self.assertFalse(m["acerto_recuperacao"])
        self.assertEqual(m["rr_recuperacao"], 0.0)


class TestConjuntoCalibracao(unittest.TestCase):
    """tests/calibracao_limiar.json (v6): independente dos 66 casos."""

    @classmethod
    def setUpClass(cls):
        cls.cal = json.loads((RAIZ / "tests" / "calibracao_limiar.json").read_text(encoding="utf-8"))["perguntas"]

    def test_metade_respondivel_metade_sem_resposta(self):
        grupos = [p["grupo"] for p in self.cal]
        self.assertEqual(grupos.count("respondivel"), 20)
        self.assertEqual(grupos.count("sem_resposta"), 20)
        self.assertEqual(len({p["id"] for p in self.cal}), 40)

    def test_nenhuma_pergunta_dos_66_casos(self):
        perguntas_casos = {c["pergunta"].strip().lower() for c in CASOS}
        for p in self.cal:
            self.assertNotIn(p["pergunta"].strip().lower(), perguntas_casos)

    def test_rotulos_existem_na_gold_e_nao_sao_rotulos_dos_casos(self):
        identificadores = set()
        for arquivo in GOLD_DIR.glob("*.json"):
            gold = json.loads(arquivo.read_text(encoding="utf-8"))
            for trecho in gold.get("trechos", []):
                identificadores.add((gold["titulo"], trecho["identificador"]))
        rotulos_casos = {(r["norma"], r["trecho"]) for c in CASOS for r in c.get("relevantes") or []}
        for p in self.cal:
            if p["grupo"] != "respondivel":
                self.assertFalse(p.get("relevantes"))
                continue
            for r in p["relevantes"]:
                self.assertTrue(any(t.startswith(r["norma"] + ",") and i == r["trecho"]
                                    for t, i in identificadores), (p["id"], r))
                self.assertNotIn((r["norma"], r["trecho"]), rotulos_casos, p["id"])


class TestCaminhosSaida(unittest.TestCase):
    def test_sem_saida_usa_os_caminhos_do_v5(self):
        c = caminhos_saida("producao")
        self.assertEqual(c["json"], RESULTADOS_DIR / "resultados_benchmark.json")
        self.assertEqual(c["recuperacao"], TABELA_RECUPERACAO)

    def test_com_saida_nada_fica_nos_caminhos_do_v5(self):
        pasta = RAIZ / "docs" / "resultados" / "v6"
        for modo in ("producao", "sensibilidade"):
            for caminho in caminhos_saida(modo, saida=pasta).values():
                self.assertEqual(caminho.parent, pasta)


if __name__ == "__main__":
    unittest.main()
