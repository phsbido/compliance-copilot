"""
Camada 3 — Orquestração e Fluxo de Trabalho (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: coordenar as etapas do
fluxo de resposta a uma pergunta do usuário.

Fluxo implementado (ver README.md): interpretar -> buscar normativo ->
sintetizar resposta -> validar citação.

Estágio atual: a busca de normativo usa as Camadas 4/5 (ver
`_buscar_normativo`), a síntese de resposta considera o histórico da sessão
via Camada 6 (ver `_sintetizar_resposta`), e a validação de citação usa a
Camada 7 (ver `_validar_citacao`). As classificações `parecer_juridico` e
`fora_de_escopo` desviam o fluxo (Camada 7) para uma recusa direta, sem
buscar/sintetizar — `fora_de_escopo` só passou a ter esse tratamento depois
de um teste ter mostrado que, sem ele, a pergunta seguia o fluxo normal e
recebia uma busca normativa sem sentido (ver docs/evidencias_empiricas.md,
2026-08-15). Decisões registradas em docs/decisoes_arquitetura.md.
"""
from dataclasses import dataclass

from src.layer2_llm_core.core import LLMCore
from src.layer4_tools.tools import buscar_normativo
from src.layer6_memory.memory import Memoria
from src.layer7_governance.governance import (
    recusar_fora_de_escopo,
    recusar_parecer_juridico,
    validar_citacao,
)
from src.layer8_observability.observability import RegistroInteracao, registrar_interacao

TIPOS_INTERPRETACAO = {"normativo", "parecer_juridico", "fora_de_escopo"}

# Classificações que desviam o fluxo para uma recusa direta (Camada 7),
# sem buscar normativo nem sintetizar resposta.
_RECUSAS = {
    "parecer_juridico": recusar_parecer_juridico,
    "fora_de_escopo": recusar_fora_de_escopo,
}


@dataclass
class Interpretacao:
    pergunta_original: str
    tipo: str  # "normativo" | "parecer_juridico" | "fora_de_escopo"


class Orchestrator:
    def __init__(self, llm: LLMCore | None = None, memoria: Memoria | None = None):
        self.llm = llm or LLMCore()
        self.memoria = memoria or Memoria()
        # Registro de proveniência (Camada 8) da última chamada a
        # responder() — exposto para camadas superiores (ex: Camada 1)
        # mostrarem fontes/avisos sem precisar reabrir o log em disco nem
        # mudar o tipo de retorno de responder(), usado por outros scripts.
        self.ultimo_registro: RegistroInteracao | None = None

    def responder(self, pergunta: str) -> str:
        interpretacao = self._interpretar(pergunta)

        if interpretacao.tipo in _RECUSAS:
            resposta = _RECUSAS[interpretacao.tipo]()
            self.memoria.adicionar(pergunta, resposta)
            self.ultimo_registro = registrar_interacao(pergunta, interpretacao.tipo, resposta)
            return resposta

        normativo = self._buscar_normativo(interpretacao)
        resposta_sintetizada = self._sintetizar_resposta(pergunta, normativo)
        # A memória guarda a resposta sintetizada, sem os avisos de
        # governança anexados por _validar_citacao — do contrário, o
        # disclaimer de validação humana entra no histórico e o modelo passa
        # a ecoá-lo nas respostas seguintes (observado em teste, ver
        # docs/evidencias_empiricas.md).
        self.memoria.adicionar(pergunta, resposta_sintetizada)
        resposta_validada = self._validar_citacao(resposta_sintetizada, normativo)
        self.ultimo_registro = registrar_interacao(
            pergunta, interpretacao.tipo, resposta_validada, normativo
        )
        return resposta_validada

    def _interpretar(self, pergunta: str) -> Interpretacao:
        system = (
            "Você classifica perguntas de um copiloto de compliance regulatório "
            "de Open Finance e contas PJ no Brasil. Responda apenas com uma "
            "destas palavras, sem mais nada: 'normativo' (pergunta sobre "
            "requisito normativo), 'parecer_juridico' (pede uma decisão "
            "jurídica definitiva sobre um caso concreto), ou 'fora_de_escopo' "
            "(não é sobre Open Finance/PJ)."
        )
        tipo = self.llm.generate(prompt=pergunta, system=system).strip().lower()
        if tipo not in TIPOS_INTERPRETACAO:
            tipo = "normativo"  # fallback conservador
        return Interpretacao(pergunta_original=pergunta, tipo=tipo)

    def _buscar_normativo(self, interpretacao: Interpretacao) -> str:
        return buscar_normativo(interpretacao.pergunta_original)

    def _sintetizar_resposta(self, pergunta: str, normativo: str) -> str:
        system = (
            "Você é um copiloto de compliance regulatório de Open Finance e "
            "contas PJ no Brasil. Use o contexto normativo fornecido para "
            "responder. Nunca dê parecer jurídico definitivo — sempre recomende "
            "validação humana."
        )
        historico = self.memoria.contexto_formatado()
        partes = []
        if historico:
            partes.append(f"Histórico da conversa nesta sessão:\n{historico}")
        partes.append(f"Contexto normativo: {normativo}")
        partes.append(f"Pergunta: {pergunta}")
        prompt = "\n\n".join(partes)
        return self.llm.generate(prompt=prompt, system=system)

    def _validar_citacao(self, resposta: str, normativo: str) -> str:
        return validar_citacao(resposta, normativo)
