"""
Testes automatizados da Camada 7 (Governança) — sem LLM, determinísticos.

Os casos principais vêm de respostas reais dos benchmarks (docs/resultados/)
e de trechos reais da camada Gold, para que cada regra da governança fique
presa a um comportamento observado (ver docs/evidencias_empiricas.md).

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import json
import unittest
from pathlib import Path

from src.layer4_tools.tools import NENHUM_TRECHO_ENCONTRADO, buscar_normativo
from src.layer7_governance.governance import (
    AVISO_VALIDACAO_HUMANA,
    _aviso_legado,
    _frases,
    validar_fonte_publica,
    validar_resposta,
)

RAIZ = Path(__file__).resolve().parents[1]
PERGUNTA_NORMA_AUSENTE = (
    "Quais são os requisitos técnicos estabelecidos pela Resolução BCB nº 32/2020 "
    "para a implementação do Open Finance no País?"
)

URL_RC1 = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20Conjunta&numero=1"
URL_CIRC = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Circular&numero=4015"
URL_IN = "https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Instru%C3%A7%C3%A3o%20Normativa%20BCB&numero=759"

CTX_RC1_CIRC = (
    f"Fonte: Resolução Conjunta nº 1, de 4 de maio de 2020 ({URL_RC1})\n"
    "[Resolução Conjunta nº 1/2020 — Seção II Da Participação no Open Finance — Art. 6º]\n"
    "Art. 6º São participantes do Open Finance as instituições com número de clientes "
    "superior a cinco milhões. O prazo de adequação é de 12 (doze) meses.\n\n---\n\n"
    f"Fonte: Resolução Conjunta nº 1, de 4 de maio de 2020 ({URL_RC1})\n"
    "[Resolução Conjunta nº 1/2020 — CAPÍTULO VI DA CONVENÇÃO — Art. 44]\n"
    "Art. 44. As instituições participantes devem celebrar convenção.\n\n---\n\n"
    f"Fonte: Circular nº 4.015, de 4 de maio de 2020 ({URL_CIRC})\n"
    "[Circular nº 4.015/2020 — Art. 7º]\nArt. 7º Esta Circular entra em vigor na data de sua publicação."
)

CTX_IN = (
    f"Fonte: Instrução Normativa BCB nº 759, de 9 de julho de 2026 ({URL_IN})\n"
    "[Instrução Normativa BCB nº 759/2026 — Art. 1º]\n"
    "Art. 1º Esta Instrução Normativa divulga a versão 8.0 do Manual de Escopo de Dados e "
    "Serviços do Open Finance, de que trata o art. 44, § 1º, da Resolução Conjunta nº 1, "
    "de 4 de maio de 2020."
)


def _resposta_do_llm(texto_final: str) -> str:
    """Resposta do LLM antes dos avisos da Camada 7 (dados da v1/v2 guardam
    só o texto final)."""
    for marcador in ("\n\nAviso:", "\n\n---\n"):
        texto_final = texto_final.split(marcador)[0]
    return texto_final


def _resposta_benchmark(versao: str, caso_id: str) -> str:
    pasta = RAIZ / "docs" / "resultados" / versao
    registros = json.loads((pasta / "resultados_benchmark_deterministico.json").read_text(encoding="utf-8"))
    return _resposta_do_llm(next(r["resposta"] for r in registros if r["caso_id"] == caso_id))


class TestNormaAusente(unittest.TestCase):
    """Achado de 2026-09-24: o aviso de norma disparava também quando o
    modelo dizia, corretamente, que a norma não estava no corpus."""

    @classmethod
    def setUpClass(cls):
        cls.contexto = buscar_normativo(PERGUNTA_NORMA_AUSENTE)

    def test_norma_inventada_na_v1_gera_aviso(self):
        # v1 determinística: "De acordo com a Resolução BCB nº 32/2020, os
        # requisitos técnicos ... incluem: 1. ..." — conteúdo inventado.
        resposta = _resposta_benchmark("v1", "norma_ausente_fronteira")
        r = validar_resposta(resposta, self.contexto)
        self.assertIn("Resolução BCB nº 32", r.normas_nao_verificadas)
        self.assertTrue(r.possui_aviso)

    def test_ausencia_declarada_na_v2_nao_gera_aviso_de_norma(self):
        # v2 determinística: "Não encontrei a Resolução BCB nº 32/2020. ..."
        resposta = _resposta_benchmark("v2", "norma_ausente_fronteira")
        r = validar_resposta(resposta, self.contexto)
        self.assertEqual(r.normas_nao_verificadas, [])
        self.assertIn("Resolução BCB nº 32", r.normas_declaradas_ausentes)

    def test_ausencia_declarada_e_depois_usada_como_fonte_gera_aviso(self):
        resposta = ("Não encontrei a Resolução BCB nº 32/2020 no contexto. "
                    "Segundo a Resolução BCB nº 32/2020, as interfaces devem ser padronizadas.")
        r = validar_resposta(resposta, self.contexto)
        self.assertIn("Resolução BCB nº 32", r.normas_nao_verificadas)

    def test_outras_formas_de_declarar_ausencia_no_benchmark_v3(self):
        # Frases reais do benchmark v3 (modo livre) que a primeira lista
        # fechada de marcadores não cobria — falsos positivos corrigidos.
        for resposta in (
            "Não foi encontrado na consulta normativa o número da Resolução BCB nº 32/2020. "
            "Portanto, não é possível determinar os requisitos técnicos estabelecidos pela "
            "Resolução BCB nº 32/2020 para a implementação do Open Finance no País.",
            "Não estou com os requisitos técnicos da Resolução BCB nº 32/2020 disponíveis. "
            "Apenas tenho acesso a informações da Resolução Conjunta nº 1/2020.",
            "Não há menção à Resolução BCB nº 32/2020 no contexto fornecido.",
        ):
            r = validar_resposta(resposta, self.contexto)
            self.assertEqual(r.normas_nao_verificadas, [], resposta)
            self.assertIn("Resolução BCB nº 32", r.normas_declaradas_ausentes)

    def test_negacao_sobre_conteudo_nao_e_ausencia(self):
        # Negar algo sobre o conteúdo da norma é usá-la como fonte.
        r = validar_resposta("A Resolução BCB nº 32/2020 não exige certificação das interfaces.", self.contexto)
        self.assertIn("Resolução BCB nº 32", r.normas_nao_verificadas)

    def test_metrica_legada_continua_igual_a_v1(self):
        # O validador antigo sinaliza as duas respostas (é o que fazia v1/v2).
        for versao in ("v1", "v2"):
            resposta = _resposta_benchmark(versao, "norma_ausente_fronteira")
            self.assertTrue(_aviso_legado(resposta, self.contexto))


class TestNormas(unittest.TestCase):
    def test_instrucao_normativa_bcb_e_reconhecida(self):
        # Na v1/v2 a regex não reconhecia "Instrução Normativa BCB nº":
        # 13 menções nas respostas, nenhuma verificada.
        ok = validar_resposta("Conforme a Instrução Normativa BCB nº 759, o manual está na versão 8.0.", CTX_IN)
        self.assertEqual(ok.normas_nao_verificadas, [])
        inventada = validar_resposta("Conforme a Instrução Normativa BCB nº 999, há novos requisitos.", CTX_IN)
        self.assertEqual(inventada.normas_nao_verificadas, ["Instrução Normativa BCB nº 999"])

    def test_normalizacao_de_caixa_e_milhar(self):
        r = validar_resposta("A CIRCULAR Nº 4015 trata do escopo de dados.", CTX_RC1_CIRC)
        self.assertEqual(r.normas_nao_verificadas, [])

    def test_resolucao_sem_orgao_casa_com_resolucao_qualificada(self):
        r = validar_resposta("A Resolução nº 1 regula o tema.", CTX_RC1_CIRC)
        self.assertEqual(r.normas_nao_verificadas, [])


class TestArtigos(unittest.TestCase):
    def test_artigo_existente_na_norma_certa(self):
        r = validar_resposta("O art. 44 da Resolução Conjunta nº 1 trata da convenção.", CTX_RC1_CIRC)
        self.assertEqual((r.artigos_nao_verificados, r.artigos_fora_da_norma), ([], []))

    def test_artigo_atribuido_a_norma_errada(self):
        r = validar_resposta("O art. 44 da Circular nº 4.015 trata da convenção.", CTX_RC1_CIRC)
        self.assertEqual(r.artigos_fora_da_norma, ["art. 44 (Circular nº 4015)"])

    def test_remissao_no_contexto_atesta_o_par(self):
        # A IN 759 remete ao "art. 44, § 1º, da Resolução Conjunta nº 1".
        r = validar_resposta("O art. 44 da Resolução Conjunta nº 1 prevê a estrutura de governança.", CTX_IN)
        self.assertEqual((r.artigos_nao_verificados, r.artigos_fora_da_norma), ([], []))

    def test_lista_de_artigos_no_plural(self):
        r = validar_resposta("Ver os arts. 6º e 99 da Resolução Conjunta nº 1.", CTX_RC1_CIRC)
        self.assertEqual(r.artigos_nao_verificados, ["99"])

    def test_cabecalho_inventado_pelo_modelo(self):
        # Benchmark v3 (livre, caminho feliz, rep. 3): o modelo imitou o
        # cabeçalho da Gold para artigos que não estavam no contexto.
        resposta = ("[Resolução Conjunta nº 1/2020 — Seção II Da Participação no Open Finance — Art. 2º]\n"
                    "O art. 2º não está disponível no contexto fornecido.")
        r = validar_resposta(resposta, CTX_RC1_CIRC)
        self.assertEqual(r.artigos_nao_verificados, ["2"])

    def test_artigo_sem_norma_na_frase(self):
        r = validar_resposta("Isso está no art. 51.", CTX_RC1_CIRC)
        self.assertEqual(r.artigos_nao_verificados, ["51"])


class TestValores(unittest.TestCase):
    """Achado recorrente (2026-08-14 e 2026-09-24): com o trecho certo no
    contexto, o modelo distorce números ("cinco milhões" -> "3 milhões")."""

    def test_valor_distorcido_gera_aviso(self):
        r = validar_resposta("Participam instituições com mais de 3 milhões de clientes.", CTX_RC1_CIRC)
        self.assertEqual(len(r.valores_nao_verificados), 1)
        self.assertIn("3 milhões", r.valores_nao_verificados[0])

    def test_valor_em_digitos_casa_com_extenso(self):
        r = validar_resposta("Participam instituições com mais de 5 milhões de clientes.", CTX_RC1_CIRC)
        self.assertEqual(r.valores_nao_verificados, [])

    def test_prazo_por_extenso_e_prazo_errado(self):
        self.assertEqual(validar_resposta("O prazo é de doze meses.", CTX_RC1_CIRC).valores_nao_verificados, [])
        self.assertEqual(len(validar_resposta("O prazo é de 30 dias.", CTX_RC1_CIRC).valores_nao_verificados), 1)

    def test_periodos_em_trimestres(self):
        ctx = CTX_RC1_CIRC + " Considera-se superado o limite após dois trimestres consecutivos."
        self.assertEqual(validar_resposta("Acima do limite por 2 trimestres.", ctx).valores_nao_verificados, [])
        self.assertEqual(len(validar_resposta("Acima do limite por três trimestres.", ctx).valores_nao_verificados), 1)

    def test_numeros_sem_unidade_sao_ignorados(self):
        r = validar_resposta("A Resolução Conjunta nº 1/2020, art. 6º, inciso I, de 2020.", CTX_RC1_CIRC)
        self.assertEqual(r.valores_nao_verificados, [])


class TestTextoFinalEFontes(unittest.TestCase):
    def test_fontes_e_validacao_humana_sempre_anexadas(self):
        r = validar_resposta("Resposta sem nenhuma citação.", CTX_RC1_CIRC)
        self.assertIn("Fontes consultadas:", r.texto_final)
        self.assertIn(URL_RC1, r.texto_final)
        self.assertIn(URL_CIRC, r.texto_final)
        self.assertEqual(r.texto_final.count(URL_RC1), 1)  # fonte repetida aparece uma vez
        self.assertTrue(r.texto_final.endswith(AVISO_VALIDACAO_HUMANA))

    def test_frase_nao_quebra_depois_de_art(self):
        frases = [f for _, f in _frases("Conforme o Art. 6º. A instituição deve participar.")]
        self.assertEqual(len(frases), 2)
        self.assertIn("Art. 6º", frases[0])


class TestFontesPublicasESemBase(unittest.TestCase):
    def test_apenas_dominios_do_bcb(self):
        validar_fonte_publica(URL_RC1)
        validar_fonte_publica("https://normativos.bcb.gov.br/Lists/Normativos/Attachments/51028/x.pdf")
        for url in ("https://example.com/norma", "http://www.bcb.gov.br/x", "https://bcb.gov.br.evil.com/x"):
            with self.assertRaises(ValueError):
                validar_fonte_publica(url)

    def test_busca_sem_resultado_devolve_marcador_de_recusa(self):
        # A Camada 3 compara com esta constante para dar a recusa sem base.
        self.assertEqual(buscar_normativo("xyzzy qwrtp zzkx"), NENHUM_TRECHO_ENCONTRADO)


if __name__ == "__main__":
    unittest.main()
