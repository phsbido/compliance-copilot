"""
Camada 1 — Interação com o Usuário (Maia et al., 2026, Seção 8): interface web.

Segunda interface da Camada 1, ao lado da CLI (`cli.py`), sobre o mesmo
`Orchestrator` (Camada 3). Uma janela de chat no navegador, com as respostas
formatadas e, abaixo de cada uma, um resumo recolhível da proveniência
(Camada 8): classificação da Camada 3, desfecho, avisos da Camada 7, fontes
e latência.

Decisões de projeto (ver docs/decisoes_arquitetura.md, Camada 1 — interface
web):
- Servidor só com a biblioteca padrão (`http.server`), sem framework web —
  mesma regra do resto do protótipo: nenhuma abstração de terceiros
  escondendo uma decisão. Página única (`static/index.html`) com CSS e JS
  embutidos, sem CDN, para funcionar sem internet como o resto (Ollama local).
- Um `Orchestrator` por sessão do navegador (id gerado pela página), pelo
  mesmo motivo da CLI: a memória da Camada 6 acumula a conversa da sessão.
  Uma trava por sessão impede duas perguntas simultâneas sobre a mesma
  memória.
- Sem streaming: `responder()` só devolve o texto depois da validação da
  Camada 7; mostrar a geração aos poucos exibiria texto ainda não validado.
- Escuta só em 127.0.0.1: é uma interface local de demonstração, sem
  autenticação.

API:
    GET  /                     -> página do chat
    POST /api/perguntar        {"sessao", "pergunta"} -> {"resposta", "proveniencia"}
    POST /api/nova-conversa    {"sessao"}             -> {"ok": true}
"""
import json
import re
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.config import settings
from src.layer3_orchestration.orchestrator import Orchestrator

PAGINA = Path(__file__).resolve().parent / "static" / "index.html"

TAMANHO_MAXIMO_CORPO = 64 * 1024
TAMANHO_MAXIMO_PERGUNTA = 4000
_SESSAO_REGEX = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class _Sessao:
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.trava = threading.Lock()


_sessoes: dict[str, _Sessao] = {}
_trava_sessoes = threading.Lock()


def _obter_sessao(sessao_id: str) -> _Sessao:
    with _trava_sessoes:
        if sessao_id not in _sessoes:
            _sessoes[sessao_id] = _Sessao()
        return _sessoes[sessao_id]


def _encerrar_sessao(sessao_id: str) -> None:
    with _trava_sessoes:
        _sessoes.pop(sessao_id, None)


def _proveniencia(registro, latencia_s: float) -> dict:
    """Resumo do registro da Camada 8 para a página — o mesmo recorte que a
    CLI mostra, mais os dados que cabem num painel recolhível."""
    if registro is None:
        return {"latencia_s": round(latencia_s, 1)}
    return {
        "classificacao": registro.tipo_classificacao,
        "desfecho": registro.desfecho,
        "fontes": registro.fontes_normativas,
        "validacao": registro.validacao,
        "modelo": registro.parametros_llm.get("modelo"),
        "id_modelo": registro.parametros_llm.get("id_modelo"),
        "latencia_s": round(latencia_s, 1),
    }


class _Handler(BaseHTTPRequestHandler):
    server_version = "CopilotoCompliance/1.0"

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self._erro(HTTPStatus.NOT_FOUND, "Página não encontrada.")
            return
        corpo = PAGINA.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self):
        dados = self._ler_json()
        if dados is None:
            return
        sessao_id = dados.get("sessao")
        if not isinstance(sessao_id, str) or not _SESSAO_REGEX.match(sessao_id):
            self._erro(HTTPStatus.BAD_REQUEST, "Identificador de sessão inválido.")
            return

        if self.path == "/api/perguntar":
            self._perguntar(sessao_id, dados.get("pergunta"))
        elif self.path == "/api/nova-conversa":
            _encerrar_sessao(sessao_id)
            self._json(HTTPStatus.OK, {"ok": True})
        else:
            self._erro(HTTPStatus.NOT_FOUND, "Rota não encontrada.")

    def _perguntar(self, sessao_id: str, pergunta) -> None:
        if not isinstance(pergunta, str) or not pergunta.strip():
            self._erro(HTTPStatus.BAD_REQUEST, "Digite uma pergunta.")
            return
        pergunta = pergunta.strip()
        if len(pergunta) > TAMANHO_MAXIMO_PERGUNTA:
            self._erro(HTTPStatus.BAD_REQUEST,
                       f"Pergunta longa demais (máximo de {TAMANHO_MAXIMO_PERGUNTA} caracteres).")
            return

        sessao = _obter_sessao(sessao_id)
        if not sessao.trava.acquire(blocking=False):
            self._erro(HTTPStatus.CONFLICT, "Aguarde a resposta anterior terminar.")
            return
        try:
            inicio = time.perf_counter()
            resposta = sessao.orchestrator.responder(pergunta)
            latencia = time.perf_counter() - inicio
            registro = sessao.orchestrator.ultimo_registro
        except Exception as erro:  # em geral, Ollama fora do ar ou modelo ausente
            print(f"[web] erro ao responder: {erro!r}", file=sys.stderr)
            self._erro(
                HTTPStatus.SERVICE_UNAVAILABLE,
                f"Não foi possível gerar a resposta: o Ollama ({settings.ollama_host}) "
                f"está rodando e com o modelo {settings.ollama_model} baixado? "
                f"Detalhe técnico: {erro}",
            )
            return
        finally:
            sessao.trava.release()

        self._json(HTTPStatus.OK, {"resposta": resposta,
                                   "proveniencia": _proveniencia(registro, latencia)})

    def _ler_json(self) -> dict | None:
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            tamanho = -1
        if tamanho <= 0 or tamanho > TAMANHO_MAXIMO_CORPO:
            self._erro(HTTPStatus.BAD_REQUEST, "Requisição inválida.")
            return None
        try:
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._erro(HTTPStatus.BAD_REQUEST, "JSON inválido.")
            return None
        if not isinstance(dados, dict):
            self._erro(HTTPStatus.BAD_REQUEST, "JSON inválido.")
            return None
        return dados

    def _json(self, status: HTTPStatus, dados: dict) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _erro(self, status: HTTPStatus, mensagem: str) -> None:
        self._json(status, {"erro": mensagem})

    def log_message(self, formato, *args):
        print(f"[web] {self.address_string()} {formato % args}", file=sys.stderr)


def main(host: str = "127.0.0.1", porta: int = 8000, abrir_navegador: bool = True) -> None:
    servidor = ThreadingHTTPServer((host, porta), _Handler)
    endereco = f"http://{host}:{porta}"
    print("Copiloto de Compliance Regulatório — interface web")
    print(f"Abra {endereco} no navegador. Ctrl+C para encerrar.\n")
    if abrir_navegador:
        import webbrowser
        threading.Timer(0.5, webbrowser.open, args=(endereco,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando.")
    finally:
        servidor.server_close()
