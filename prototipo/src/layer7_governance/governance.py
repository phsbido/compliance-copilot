"""
Camada 7 — Governança e Segurança (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: aplicar constraints sobre
o comportamento do sistema (nunca citar norma inexistente, sempre linkar
fonte, recusar parecer jurídico definitivo, usar apenas fontes públicas).

Decisão de projeto (ver docs/decisoes_arquitetura.md): construída
diretamente sobre 3 achados empíricos registrados em
docs/evidencias_empiricas.md (norma citada inexistente; número distorcido
mesmo com contexto correto; artigo citado incorretamente de forma
recorrente). A validação de citação é determinística, por padrão de texto
(regex) — confere se números de artigo e nomes/números de norma citados na
resposta aparecem literalmente no trecho normativo usado como contexto.
Não é verificação semântica: não detecta toda fabricação possível, só
citações que seguem o formato padrão de atos normativos brasileiros
("Art. N", "Resolução/Circular nº N"). A regra de "usar apenas fontes
públicas" não é verificada aqui em runtime — é garantida estruturalmente
pela curadoria do corpus na Camada 5 (só normativos públicos do BACEN são
adicionados a data/normativos/).
"""
import re

_ARTIGO_REGEX = re.compile(r"art(?:igo)?\.?\s*(\d+)", re.IGNORECASE)
_NORMA_REGEX = re.compile(
    r"(Resolução(?:\s+Conjunta|\s+BCB)?|Circular|Instrução Normativa)\s+n[ºo°]\.?\s*(\d+(?:\.\d+)*)",
    re.IGNORECASE,
)

AVISO_VALIDACAO_HUMANA = (
    "\n\n---\nEsta resposta é apoiada em atos normativos públicos do BCB, mas "
    "não constitui parecer jurídico definitivo. Valide com a área jurídica/"
    "compliance antes de qualquer decisão final."
)

RECUSA_PARECER_JURIDICO = (
    "Não posso emitir parecer jurídico definitivo sobre casos concretos. "
    "Posso indicar o que os atos normativos públicos do BACEN dizem sobre o "
    "tema em geral — se for útil, reformule a pergunta nesses termos. A "
    "decisão final sobre o seu caso deve ser validada por um profissional "
    "jurídico/compliance qualificado."
)

RECUSA_FORA_DE_ESCOPO = (
    "Este copiloto responde apenas perguntas sobre requisitos regulatórios "
    "de Open Finance e contas PJ no Brasil, com base em atos normativos "
    "públicos do BACEN. Sua pergunta parece estar fora desse escopo — se "
    "for sobre esse tema, reformule para eu poder ajudar."
)


def recusar_parecer_juridico() -> str:
    return RECUSA_PARECER_JURIDICO


def recusar_fora_de_escopo() -> str:
    return RECUSA_FORA_DE_ESCOPO


def validar_citacao(resposta: str, contexto_normativo: str) -> str:
    avisos = []

    artigos_citados = {m.group(1) for m in _ARTIGO_REGEX.finditer(resposta)}
    artigos_no_contexto = {m.group(1) for m in _ARTIGO_REGEX.finditer(contexto_normativo)}
    artigos_nao_verificados = sorted(artigos_citados - artigos_no_contexto, key=int)
    if artigos_nao_verificados:
        lista = ", ".join(artigos_nao_verificados)
        avisos.append(
            f"Aviso: a resposta cita art. {lista}, que não aparece no trecho "
            f"normativo usado como base para esta resposta — confirme essa "
            f"referência na fonte oficial antes de usá-la."
        )

    normas_citadas = {
        f"{m.group(1).strip()} nº {m.group(2)}" for m in _NORMA_REGEX.finditer(resposta)
    }
    normas_no_contexto = {
        f"{m.group(1).strip()} nº {m.group(2)}" for m in _NORMA_REGEX.finditer(contexto_normativo)
    }
    normas_nao_verificadas = sorted(normas_citadas - normas_no_contexto)
    if normas_nao_verificadas:
        lista = "; ".join(normas_nao_verificadas)
        avisos.append(
            f"Aviso: a resposta cita {lista}, que não consta no trecho "
            f"normativo usado como base para esta resposta — não foi "
            f"possível verificar essa citação no corpus indexado."
        )

    resultado = resposta
    if avisos:
        resultado += "\n\n" + "\n".join(avisos)
    resultado += AVISO_VALIDACAO_HUMANA
    return resultado
