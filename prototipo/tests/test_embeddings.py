"""
Testes dos modos de recuperação da Camada 5 (v7: bm25, embeddings, hybrid)
— sem LLM, sem Ollama: um cliente de embeddings falso gera vetores a partir
de palavras-chave, sobre uma Gold mínima num diretório temporário.

Uso (de dentro de prototipo/):
    python -m unittest discover -s tests -v
"""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.layer5_knowledge.embeddings import (
    INDICE_EMBEDDINGS_NOME,
    IndiceEmbeddingsInvalido,
    _normalizar,
    codificar_vetor,
    decodificar_vetor,
    gerar_indice,
)
from src.layer5_knowledge.knowledge_base import RRF_K, KnowledgeBase
from src.layer5_knowledge.texto import tokenizar

# Eixos do vetor falso: um por conceito.
_EIXOS = ("defin", "prazo", "consentimento")
_SINONIMOS = {"defin": ("defin", "conceit", "entende"), "prazo": ("prazo", "dias"),
              "consentimento": ("consentimento", "autoriz")}


class ClienteFalso:
    def __init__(self, modelo="falso", digest="d" * 64):
        self.modelo = modelo
        self._digest = digest

    def digest(self):
        return self._digest

    def gerar(self, textos):
        vetores = []
        for texto in textos:
            t = texto.lower()
            vetores.append(_normalizar([sum(t.count(s) for s in _SINONIMOS[e]) + 0.01 for e in _EIXOS]))
        return vetores


_TRECHOS = [
    ("rc#1", "Art. 1º", "[Norma — Art. 1º]\nEsta norma dispõe sobre o sistema financeiro aberto."),
    ("rc#2", "Art. 2º", "[Norma — Art. 2º]\nPara os fins desta norma, entende-se por sistema aberto o compartilhamento."),
    ("rc#3", "Art. 3º", "[Norma — Art. 3º]\nO prazo para revogar o consentimento é de dois dias."),
]


def _montar_gold(diretorio: Path, cliente) -> None:
    trechos = []
    for id_trecho, identificador, texto in _TRECHOS:
        tokens = tokenizar(texto)
        trechos.append({"id": id_trecho, "identificador": identificador, "contexto": [], "anotacoes": [],
                        "texto": texto, "n_tokens": len(tokens), "frequencia_tokens": dict(Counter(tokens))})
    gold = {"titulo": "Norma de Teste nº 1, de 1º de janeiro de 2020", "ementa": "teste",
            "url_oficial": "https://www.bcb.gov.br/teste", "corpus_runtime": True, "trechos": trechos}
    (diretorio / "norma.json").write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
    df = Counter(tok for t in trechos for tok in t["frequencia_tokens"])
    indice = {"arquivos": ["norma.json"], "k1": 1.5, "b": 0.75, "n_trechos": len(trechos),
              "tamanho_medio": sum(t["n_tokens"] for t in trechos) / len(trechos),
              "frequencia_documento": dict(df)}
    (diretorio / "indice_bm25.json").write_text(json.dumps(indice), encoding="utf-8")
    emb = gerar_indice([(i, t) for i, _, t in _TRECHOS], cliente)
    (diretorio / INDICE_EMBEDDINGS_NOME).write_text(json.dumps(emb), encoding="utf-8")


class TestModos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.cliente = ClienteFalso()
        _montar_gold(self.dir, self.cliente)

    def tearDown(self):
        self._tmp.cleanup()

    def _kb(self, modo, **kw):
        return KnowledgeBase(self.dir, modo=modo, cliente_embeddings=self.cliente, **kw)

    def test_embeddings_acha_parafrase_que_o_bm25_perde(self):
        pergunta = "Qual é a definição de sistema aberto?"
        self.assertNotEqual(self._kb("bm25").buscar(pergunta, top_k=1)[0].identificador, "Art. 2º")
        self.assertEqual(self._kb("embeddings").buscar(pergunta, top_k=1)[0].identificador, "Art. 2º")

    def test_rrf_soma_inverso_das_posicoes(self):
        kb = self._kb("hybrid")
        pergunta = "Qual o prazo do consentimento?"
        pos_bm25 = {i: p for p, (_, i) in enumerate(kb._ranking_bm25(pergunta), start=1)}
        pos_emb = {i: p for p, (_, i) in enumerate(kb._ranking_embeddings(pergunta), start=1)}
        for pontuacao, doc in kb.buscar_pontuado(pergunta, top_k=3):
            i = kb.documentos.index(doc)
            esperado = sum(1 / (RRF_K + pos[i]) for pos in (pos_bm25, pos_emb) if i in pos)
            self.assertAlmostEqual(pontuacao, esperado)

    def test_interface_de_buscar_nao_muda(self):
        for modo in ("bm25", "embeddings", "hybrid"):
            docs = self._kb(modo).buscar("sistema aberto e prazo", top_k=2)
            self.assertEqual(len(docs), 2)
            self.assertTrue(all(d.titulo and d.url_oficial and d.trecho for d in docs))

    def test_limiar_cosseno_recusa_tudo_ou_nada(self):
        kb = self._kb("embeddings", limiar_cosseno=1.5)
        self.assertEqual(kb.buscar("sistema financeiro"), [])
        self.assertEqual(len(self._kb("embeddings", limiar_cosseno=-1.0).buscar("sistema financeiro")), 3)

    def test_limiar_bm25_continua_bm25_nos_outros_modos(self):
        # Pergunta sem nenhum token do corpus: BM25 zero, recusa em qualquer modo.
        for modo in ("bm25", "embeddings", "hybrid"):
            self.assertEqual(self._kb(modo).buscar("xyzw qwerty", limiar=0.5), [])

    def test_identificacao(self):
        ident = self._kb("hybrid").identificacao()
        self.assertEqual(ident["modo"], "hybrid")
        self.assertEqual(ident["digest_embeddings"], "d" * 12)
        self.assertRegex(ident["versao_indice"], r"^bm25:[0-9a-f]{12}\+emb:[0-9a-f]{12}$")
        self.assertIsNone(self._kb("bm25").identificacao()["modelo_embeddings"])


class TestIndiceNuncaMisturado(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        _montar_gold(self.dir, ClienteFalso())

    def tearDown(self):
        self._tmp.cleanup()

    def test_digest_diferente_recusa_o_indice(self):
        with self.assertRaises(IndiceEmbeddingsInvalido):
            KnowledgeBase(self.dir, modo="embeddings", cliente_embeddings=ClienteFalso(digest="e" * 64))

    def test_modelo_diferente_recusa_o_indice(self):
        with self.assertRaises(IndiceEmbeddingsInvalido):
            KnowledgeBase(self.dir, modo="embeddings", cliente_embeddings=ClienteFalso(modelo="outro"))

    def test_texto_alterado_recusa_o_indice(self):
        caminho = self.dir / "norma.json"
        gold = json.loads(caminho.read_text(encoding="utf-8"))
        gold["trechos"][1]["texto"] += " Texto novo."
        caminho.write_text(json.dumps(gold, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(IndiceEmbeddingsInvalido):
            KnowledgeBase(self.dir, modo="hybrid", cliente_embeddings=ClienteFalso())

    def test_modo_bm25_nao_exige_indice_de_embeddings(self):
        (self.dir / INDICE_EMBEDDINGS_NOME).unlink()
        self.assertEqual(len(KnowledgeBase(self.dir, modo="bm25").documentos), 3)

    def test_modo_invalido(self):
        with self.assertRaises(ValueError):
            KnowledgeBase(self.dir, modo="vetorial")


class TestCodificacao(unittest.TestCase):
    def test_float32_ida_e_volta(self):
        v = _normalizar([0.1, -0.2, 0.3])
        self.assertTrue(all(abs(a - b) < 1e-7 for a, b in zip(v, decodificar_vetor(codificar_vetor(v)))))


if __name__ == "__main__":
    unittest.main()
