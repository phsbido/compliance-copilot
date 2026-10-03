"""
Camada 3 — Orquestração e Fluxo de Trabalho (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: coordenar as etapas do
fluxo de resposta a uma pergunta do usuário.

Fluxo implementado (ver README.md): interpretar -> buscar normativo ->
sintetizar resposta -> validar citação.

Estágio atual: a busca de normativo usa as Camadas 4/5 (ver
`_buscar_normativo`), a síntese de resposta considera o histórico da sessão
via Camada 6 (ver `_sintetizar_resposta`), e a validação de citação usa a
Camada 7 (ver `_validar_resposta`). As classificações `parecer_juridico` e
`fora_de_escopo` desviam o fluxo (Camada 7) para uma recusa direta, sem
buscar/sintetizar — `fora_de_escopo` só passou a ter esse tratamento depois
de um teste ter mostrado que, sem ele, a pergunta seguia o fluxo normal e
recebia uma busca normativa sem sentido (ver docs/evidencias_empiricas.md,
2026-08-15). Na Camada 7 v2 (2026-09-24), a política de síntese passou a
vir da Camada 7 (`POLITICA_SINTESE`), e uma busca sem nenhum trecho também
desvia para recusa (`recusar_sem_base`), em vez de deixar o LLM responder
sem base. Decisões registradas em docs/decisoes_arquitetura.md.

Ablação da Camada 7 (v6, Tarefa C; só para avaliação, nunca em uso real):
`ablacao="c1"` não chama `validar_resposta` (a resposta sai como o LLM a
gerou, sem avisos, fontes anexadas nem aviso de validação humana);
`ablacao="c2"` também tira `POLITICA_SINTESE` do prompt de síntese (sem
mensagem de sistema). As recusas por classificação (parecer, fora de
escopo) e a recusa sem base continuam, para isolar o efeito da Camada 7
sobre a síntese.
"""
from dataclasses import dataclass

from src.config import ParametrosAmostragem, settings
from src.layer2_llm_core.core import LLMCore
from src.layer4_tools.tools import NENHUM_TRECHO_ENCONTRADO, buscar_normativo
from src.layer6_memory.memory import Memoria
from src.layer7_governance.governance import (
    POLITICA_SINTESE,
    ResultadoValidacao,
    recusar_fora_de_escopo,
    recusar_parecer_juridico,
    recusar_sem_base,
    validar_resposta,
)
from src.layer8_observability.observability import RegistroInteracao, registrar_interacao

TIPOS_INTERPRETACAO = {"normativo", "parecer_juridico", "fora_de_escopo"}
ABLACOES = {None, "c1", "c2"}

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
    def __init__(
        self,
        llm: LLMCore | None = None,
        memoria: Memoria | None = None,
        amostragem: ParametrosAmostragem | None = None,
        limiar_bm25: float | None = None,
        ablacao: str | None = None,
    ):
        if ablacao not in ABLACOES:
            raise ValueError(f"ablacao deve ser uma de {ABLACOES}, não {ablacao!r}")
        self.ablacao = ablacao
        self.llm = llm or LLMCore()
        # Temperaturas de classificação e de síntese e seed (v4). Padrão:
        # os valores do .env (src/config.py); o benchmark passa outros para
        # a análise de sensibilidade.
        self.amostragem = amostragem or settings.amostragem
        # Limiar de pontuação da Camada 5 (v6). Padrão: o do .env
        # (LIMIAR_BM25; ausente = desligado); o benchmark passa outro valor.
        self.limiar_bm25 = limiar_bm25 if limiar_bm25 is not None else settings.limiar_bm25
        self.memoria = memoria or Memoria()
        # Registro de proveniência (Camada 8) da última chamada a
        # responder() — exposto para camadas superiores (ex: Camada 1)
        # mostrarem fontes/avisos sem precisar reabrir o log em disco nem
        # mudar o tipo de retorno de responder(), usado por outros scripts.
        self.ultimo_registro: RegistroInteracao | None = None
        # Entradas da validação da Camada 7 na última chamada (resposta do
        # LLM antes dos avisos e contexto normativo), expostas para que o
        # benchmark possa revalidar offline com outra versão da Camada 7.
        self.ultima_sintese: str = ""
        self.ultimo_contexto: str = ""

    def responder(self, pergunta: str) -> str:
        interpretacao = self._interpretar(pergunta)

        if interpretacao.tipo in _RECUSAS:
            resposta = _RECUSAS[interpretacao.tipo]()
            self.memoria.adicionar(pergunta, resposta)
            self.ultimo_registro = registrar_interacao(
                pergunta, interpretacao.tipo, resposta,
                parametros_llm=self._parametros_llm(), desfecho=f"recusa_{interpretacao.tipo}"
            )
            return resposta

        self.ultima_sintese, self.ultimo_contexto = "", ""
        normativo = self._buscar_normativo(interpretacao)
        if normativo == NENHUM_TRECHO_ENCONTRADO:
            resposta = recusar_sem_base()
            self.memoria.adicionar(pergunta, resposta)
            self.ultimo_registro = registrar_interacao(
                pergunta, interpretacao.tipo, resposta,
                parametros_llm=self._parametros_llm(), desfecho="recusa_sem_base"
            )
            return resposta

        resposta_sintetizada = self._sintetizar_resposta(pergunta, normativo)
        self.ultima_sintese, self.ultimo_contexto = resposta_sintetizada, normativo
        # A memória guarda a resposta sintetizada, sem os avisos de
        # governança anexados por _validar_resposta — do contrário, o
        # disclaimer de validação humana entra no histórico e o modelo passa
        # a ecoá-lo nas respostas seguintes (observado em teste, ver
        # docs/evidencias_empiricas.md).
        self.memoria.adicionar(pergunta, resposta_sintetizada)
        if self.ablacao:
            # Ablação: a validação pós-geração da Camada 7 não roda.
            self.ultimo_registro = registrar_interacao(
                pergunta, interpretacao.tipo, resposta_sintetizada, normativo,
                parametros_llm=self._parametros_llm(),
            )
            return resposta_sintetizada
        validacao = self._validar_resposta(resposta_sintetizada, normativo)
        self.ultimo_registro = registrar_interacao(
            pergunta, interpretacao.tipo, validacao.texto_final, normativo,
            validacao=validacao.categorias(), parametros_llm=self._parametros_llm(),
        )
        return validacao.texto_final

    def _interpretar(self, pergunta: str) -> Interpretacao:
        system = (
            "Você classifica perguntas de um copiloto de compliance regulatório "
            "de Open Finance e contas PJ no Brasil. Responda apenas com uma "
            "destas palavras, sem mais nada: 'normativo' (pergunta sobre "
            "requisito normativo), 'parecer_juridico' (pede uma decisão "
            "jurídica definitiva sobre um caso concreto), ou 'fora_de_escopo' "
            "(não é sobre Open Finance/PJ)."
        )
        tipo = self.llm.generate(
            prompt=pergunta, system=system,
            options=self.amostragem.opcoes(self.amostragem.temperatura_classificacao),
        ).strip().lower()
        if tipo not in TIPOS_INTERPRETACAO:
            tipo = "normativo"  # fallback conservador
        return Interpretacao(pergunta_original=pergunta, tipo=tipo)

    def _buscar_normativo(self, interpretacao: Interpretacao) -> str:
        return buscar_normativo(interpretacao.pergunta_original, limiar=self.limiar_bm25)

    def _sintetizar_resposta(self, pergunta: str, normativo: str) -> str:
        # A política vem da Camada 7: a governança define as regras, a
        # orquestração só as injeta. O aviso de validação humana não é mais
        # pedido ao modelo — a Camada 7 o anexa de forma determinística.
        system = None if self.ablacao == "c2" else POLITICA_SINTESE
        historico = self.memoria.contexto_formatado()
        partes = []
        if historico:
            partes.append(f"Histórico da conversa nesta sessão:\n{historico}")
        partes.append(f"Contexto normativo: {normativo}")
        partes.append(f"Pergunta: {pergunta}")
        prompt = "\n\n".join(partes)
        return self.llm.generate(
            prompt=prompt, system=system,
            options=self.amostragem.opcoes(self.amostragem.temperatura_sintese),
        )

    def _parametros_llm(self) -> dict:
        # Proveniência (Camada 8): com que modelo e parâmetros a resposta
        # foi gerada.
        parametros = {**self.llm.identificacao(), **self.amostragem.como_dict()}
        if self.ablacao:
            parametros["ablacao_camada7"] = self.ablacao
        return parametros

    def _validar_resposta(self, resposta: str, normativo: str) -> ResultadoValidacao:
        return validar_resposta(resposta, normativo)
