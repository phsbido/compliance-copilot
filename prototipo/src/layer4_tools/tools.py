"""
Camada 4 — Integração de Ferramentas e Serviços (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: expor ações externas que
o Núcleo de Raciocínio (via Orquestração) pode invocar.

Estágio atual: uma única ferramenta, `buscar_normativo`, que embrulha a
Camada 5 (Conhecimento/RAG) e formata os resultados em texto citável.
Decisão de não criar uma abstração genérica de "ferramenta" ainda (nome,
descrição, registro de múltiplas ferramentas) registrada em
docs/decisoes_arquitetura.md — o BCB expõe outras APIs públicas (ex: dados
cadastrais de instituições autorizadas) que são candidatas naturais a uma
segunda ferramenta futura, momento em que a generalização se justificaria.
"""
from src.layer5_knowledge.knowledge_base import KnowledgeBase

_kb = KnowledgeBase()

# Retorno quando a Camada 5 não acha nenhum trecho — a Camada 3 compara com
# esta constante para desviar para a recusa sem base (Camada 7).
NENHUM_TRECHO_ENCONTRADO = "Nenhum trecho normativo relevante foi encontrado no corpus indexado."


def buscar_normativo(pergunta: str, top_k: int = 3) -> str:
    """Busca trechos normativos relevantes e retorna um texto citável.

    Retorna uma string pronta para ser usada como contexto normativo na
    síntese de resposta (Camada 3), com cada trecho identificado por fonte
    e URL oficial.
    """
    resultados = _kb.buscar(pergunta, top_k=top_k)
    if not resultados:
        return NENHUM_TRECHO_ENCONTRADO

    blocos = []
    for doc in resultados:
        blocos.append(f"Fonte: {doc.titulo} ({doc.url_oficial})\n{doc.trecho}")
    return "\n\n---\n\n".join(blocos)
