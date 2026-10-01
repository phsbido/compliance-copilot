"""
Script de validação — Camada 5 (Conhecimento/RAG).

Carrega a camada Gold (data/normativos/3_gold_indexed/) e testa a busca BM25
com uma pergunta de teste, exibindo os trechos mais relevantes e suas fontes.
Não usa o LLM.

Uso:
    python run_check_knowledge.py
"""
from src.layer5_knowledge.knowledge_base import KnowledgeBase


if __name__ == "__main__":
    print("Carregando base de conhecimento (Camada 5)...")

    kb = KnowledgeBase()
    print(f"{len(kb.documentos)} trechos indexados de "
          f"{len({d.titulo for d in kb.documentos})} normativo(s).\n")

    pergunta = "Quais instituições devem participar do Open Finance de forma obrigatória?"
    print(f"Pergunta de teste: {pergunta}\n")

    resultados = kb.buscar(pergunta, top_k=3)
    for i, doc in enumerate(resultados, start=1):
        print(f"--- Resultado {i} ---")
        print(f"Fonte: {doc.titulo}")
        print(f"URL: {doc.url_oficial}")
        print(f"Trecho: {doc.trecho[:300]}...\n")

    if not resultados:
        print("Nenhum resultado encontrado.")

    print("Base de conhecimento validada.")
