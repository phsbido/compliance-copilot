"""
Camada 6 — Contexto e Memória (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: manter o estado da
conversa/investigação em andamento, para que o sistema possa considerar
interações anteriores da mesma sessão.

Decisão de projeto (ver docs/decisoes_arquitetura.md): memória em processo
apenas (não persiste em disco entre execuções), limitada às últimas N
interações.
"""
from dataclasses import dataclass


@dataclass
class Interacao:
    pergunta: str
    resposta: str


class Memoria:
    def __init__(self, limite: int = 5):
        self.limite = limite
        self._interacoes: list[Interacao] = []

    def adicionar(self, pergunta: str, resposta: str) -> None:
        self._interacoes.append(Interacao(pergunta, resposta))
        if len(self._interacoes) > self.limite:
            self._interacoes = self._interacoes[-self.limite:]

    def contexto_formatado(self) -> str:
        if not self._interacoes:
            return ""
        blocos = [
            f"Pergunta anterior: {i.pergunta}\nResposta anterior: {i.resposta}"
            for i in self._interacoes
        ]
        return "\n\n".join(blocos)
