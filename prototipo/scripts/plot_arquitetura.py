"""
Gera a figura da arquitetura do protótipo (Capítulo 3): as 8 camadas de
Maia et al. (2026, Seção 8, numeração do texto) mapeadas aos módulos reais
de src/layerN_*/, e o fluxo de uma interação (`Orchestrator.responder()`).

Saída em docs/figuras/: diagrama_arquitetura.png (300 DPI) e
diagrama_arquitetura.pdf (vetorial, para o LaTeX).

Os números exibidos (modelo, temperaturas, seed, top_k, tamanho da memória,
k1 e b do BM25, modelo de embeddings, k do RRF, modo de recuperação padrão,
trechos e normas do índice) são lidos do código e dos dados, não fixados aqui — a figura acompanha o protótipo se ele mudar.

Convenção de cores (a mesma de grafico_latencia_cenarios.png):
  laranja = fluxo normativo; azul tracejado = desvio para recusa;
  cinza = chamada de apoio entre camadas.

Uso:
    python scripts/plot_arquitetura.py
"""
import inspect
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src.config import settings  # noqa: E402
from src.layer4_tools.tools import buscar_normativo  # noqa: E402
from src.layer5_knowledge.knowledge_base import RRF_K  # noqa: E402
from src.layer6_memory.memory import Memoria  # noqa: E402

GOLD_DIR = RAIZ / "data" / "normativos" / "3_gold_indexed"
DIR_FIGURAS = RAIZ / "docs" / "figuras"

AZUL = "#2a78d6"
LARANJA = "#eb6834"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
CINZA = "#8a8984"
BORDA = "#c9c8c2"
FUNDO_CAMADA = "#f6f5f2"
FUNDO_BANDA = "#fdf1eb"
SUPERFICIE = "#ffffff"


def _num(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def coletar_parametros() -> dict:
    indice = json.loads((GOLD_DIR / "indice_bm25.json").read_text(encoding="utf-8"))
    amostragem = settings.amostragem
    return {
        "modelo": settings.ollama_model,
        "t_classif": _num(amostragem.temperatura_classificacao),
        "t_sintese": _num(amostragem.temperatura_sintese),
        "seed": amostragem.seed,
        "top_k": inspect.signature(buscar_normativo).parameters["top_k"].default,
        "limite_memoria": inspect.signature(Memoria.__init__).parameters["limite"].default,
        "k1": _num(indice["k1"]),
        "b": _num(indice["b"]),
        "n_trechos": indice["n_trechos"],
        "n_normas": len(indice["arquivos"]),
        "modelo_embeddings": settings.modelo_embeddings,
        "rrf_k": RRF_K,
        "modo": settings.recuperacao_modo,
    }


# --------------------------------------------------------------------------
# Primitivas de desenho
# --------------------------------------------------------------------------

def caixa(ax, x, y, w, h, titulo, corpo="", *, fundo=FUNDO_CAMADA, borda=BORDA,
          estilo="-", tam_corpo=8.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8",
                                facecolor=fundo, edgecolor=borda, linewidth=1.2,
                                linestyle=estilo, zorder=1))
    ax.text(x + 0.9, y + h - 0.9, titulo, ha="left", va="top", fontsize=10.5,
            fontweight="bold", color=TINTA, zorder=3)
    if corpo:
        ax.text(x + 0.9, y + h - 3.3, corpo, ha="left", va="top", fontsize=tam_corpo,
                color=TINTA_SECUNDARIA, linespacing=1.35, zorder=3)


def passo(ax, x, y, w, h, numero, nome, funcao):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.6",
                                facecolor=SUPERFICIE, edgecolor=LARANJA, linewidth=1.6, zorder=2))
    ax.text(x + w / 2, y + h * 0.66, f"{numero}  {nome}", ha="center", va="center",
            fontsize=10, fontweight="bold", color=TINTA, zorder=3)
    ax.text(x + w / 2, y + h * 0.28, funcao, ha="center", va="center", fontsize=8.3,
            family="monospace", color=TINTA_SECUNDARIA, zorder=3)


def seta(ax, a, b, *, cor=CINZA, estilo="-", largura=1.4, rotulo="", pos_rotulo=0.5,
         desloc=(0, 0), ha="center", duas_pontas=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if duas_pontas else "-|>",
                                 mutation_scale=11, color=cor, linewidth=largura,
                                 linestyle=estilo, shrinkA=2, shrinkB=2, zorder=4))
    if rotulo:
        mx = a[0] + (b[0] - a[0]) * pos_rotulo + desloc[0]
        my = a[1] + (b[1] - a[1]) * pos_rotulo + desloc[1]
        ax.text(mx, my, rotulo, ha=ha, va="center", fontsize=8.3, color=TINTA,
                linespacing=1.25, zorder=5,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=SUPERFICIE, edgecolor="none"))


def linha(ax, pontos, *, cor, estilo="-", largura=1.4):
    xs, ys = zip(*pontos)
    ax.plot(xs, ys, color=cor, linestyle=estilo, linewidth=largura, zorder=4,
            solid_capstyle="round")


def rotulo_livre(ax, x, y, texto, *, cor=TINTA, ha="left", negrito=False, tam=8.0):
    ax.text(x, y, texto, ha=ha, va="center", fontsize=tam, color=cor, zorder=5,
            fontweight="bold" if negrito else "normal")


# --------------------------------------------------------------------------
# Figura
# --------------------------------------------------------------------------

def desenhar(p: dict) -> plt.Figure:
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(16, 11.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 71)
    ax.axis("off")

    ax.text(0.5, 70.5, "Arquitetura do protótipo: as 8 camadas de Maia et al. (2026) "
            "mapeadas aos módulos de src/", ha="left", va="top", fontsize=14,
            fontweight="bold", color=TINTA)

    # ---- Linha de cima: usuário, Camadas 1, 2 e 8 ------------------------
    topo_y, topo_h = 55.5, 10.5
    ax.add_patch(FancyBboxPatch((0.5, 58), 9.5, 5.5, boxstyle="round,pad=0,rounding_size=2.7",
                                facecolor=SUPERFICIE, edgecolor=TINTA_SECUNDARIA, linewidth=1.2))
    ax.text(5.25, 60.75, "Usuário", ha="center", va="center", fontsize=10.5,
            fontweight="bold", color=TINTA)
    caixa(ax, 13.5, topo_y, 21.5, topo_h, "Camada 1 · Interação",
          "cli.py: main(), laço de linha de comando\nweb.py: interface web (127.0.0.1)\n"
          "ambas exibem resposta, fontes e avisos", tam_corpo=8.4)
    caixa(ax, 38, topo_y, 24.5, topo_h, "Camada 2 · Núcleo LLM",
          "layer2_llm_core/core.py\nLLMCore.generate()\n"
          f"Ollama local · {p['modelo']} · seed {p['seed']}\n"
          f"temperatura {p['t_classif']} (classificação),\n{p['t_sintese']} (síntese)")
    caixa(ax, 65.5, topo_y, 34, topo_h, "Camada 8 · Observabilidade e Proveniência",
          "layer8_observability/observability.py\nregistrar_interacao() → logs/interacoes.jsonl\n"
          "um registro por interação: classificação, desfecho,\n"
          "fontes, validação, modelo e parâmetros, recuperação")
    seta(ax, (10, 61.9), (13.5, 61.9), cor=TINTA_SECUNDARIA)
    seta(ax, (13.5, 59.6), (10, 59.6), cor=TINTA_SECUNDARIA)

    # ---- Banda da Camada 3 ----------------------------------------------
    by, bh = 37.5, 14.5
    ax.add_patch(FancyBboxPatch((13.5, by), 86, bh, boxstyle="round,pad=0,rounding_size=0.8",
                                facecolor=FUNDO_BANDA, edgecolor=LARANJA, linewidth=1.2, zorder=1))
    ax.text(68.5, by + bh - 0.9, "Camada 3 · Orquestração", ha="left", va="top",
            fontsize=10.5, fontweight="bold", color=TINTA, zorder=3)
    ax.text(68.5, by + bh - 3.1, "layer3_orchestration/orchestrator.py",
            ha="left", va="top", fontsize=8.3, color=TINTA_SECUNDARIA, zorder=3)

    py, ph, pw = 39.5, 7.0, 16.8
    xs = [16.0, 37.5, 59.0, 80.5]
    passo(ax, xs[0], py, pw, ph, "①", "Interpretar", "_interpretar()")
    passo(ax, xs[1], py, pw, ph, "②", "Buscar normativo", "_buscar_normativo()")
    passo(ax, xs[2], py, pw, ph, "③", "Sintetizar", "_sintetizar_resposta()")
    passo(ax, xs[3], py, pw, ph, "④", "Validar", "_validar_resposta()")
    for a, b in zip(xs, xs[1:]):
        seta(ax, (a + pw, py + ph / 2), (b, py + ph / 2), cor=LARANJA, largura=2)
    for a, texto in zip(xs, ["normativo", "trechos", "resposta"]):
        rotulo_livre(ax, a + pw + (xs[1] - xs[0] - pw) / 2, py + ph / 2 + 1.5, texto,
                     cor=LARANJA, ha="center", negrito=True, tam=7.0)

    # Camada 1 ↔ Camada 3
    seta(ax, (19, topo_y), (19, py + ph), cor=TINTA_SECUNDARIA, largura=1.5,
         rotulo="pergunta", pos_rotulo=0.4)
    seta(ax, (30, by + bh), (30, topo_y), cor=TINTA_SECUNDARIA, largura=1.5)
    rotulo_livre(ax, 29.3, by + bh + 1.75, "resposta final\n+ registro", ha="right")
    # ① e ③ chamam a Camada 2
    seta(ax, (32, py + ph), (43, topo_y), duas_pontas=True, rotulo="classificação",
         pos_rotulo=0.55)
    seta(ax, (64, py + ph), (57, topo_y), duas_pontas=True, rotulo="síntese", pos_rotulo=0.55)
    # Todo desfecho (resposta e as três recusas) é registrado na Camada 8:
    # a seta sai da borda da Camada 3, não de ④.
    seta(ax, (96, by + bh), (96, topo_y), cor=TINTA_SECUNDARIA, largura=1.5)
    rotulo_livre(ax, 95.3, by + bh + 1.75, "registra todos os desfechos\n(resposta e recusas)",
                 ha="right")

    # ---- Linha do meio: legenda, Camadas 4, 6, 7 -------------------------
    cy, ch = 18.0, 15.0
    caixa(ax, 37, cy, 19.5, ch, "Camada 4 · Ferramentas",
          f"layer4_tools/tools.py\nbuscar_normativo(top_k={p['top_k']})\n"
          "formata cada trecho com\n\"Fonte: título (URL)\"")
    caixa(ax, 58.5, cy, 19.5, ch, "Camada 6 · Memória",
          f"layer6_memory/memory.py\nMemoria: últimas {p['limite_memoria']}\n"
          "interações da sessão,\nem processo (sem disco);\n"
          "guarda a síntese ou a recusa,\nsem avisos")
    caixa(ax, 80, 5.0, 19.5, 28.0, "Camada 7 · Governança",
          "layer7_governance/governance.py\n\n"
          "Recusas com texto fixo:\n  recusar_parecer_juridico()\n  recusar_fora_de_escopo()\n"
          "  recusar_sem_base()\n\n"
          "POLITICA_SINTESE: regras\n  injetadas no prompt de ③\n\n"
          "validar_resposta(): norma,\n  artigo e valor citados vs.\n"
          "  trechos; anexa fontes e\n  aviso de validação humana\n\n"
          "validar_fonte_publica():\n  na ingestão, só HTTPS\n  do bcb.gov.br", tam_corpo=8.3)

    canal = 35.5
    seta(ax, (52, py), (52, cy + ch), duas_pontas=True)
    seta(ax, (68, py), (68, cy + ch), duas_pontas=True)
    rotulo_livre(ax, 67.2, 34.2, "histórico / grava turno", ha="right")
    # Camada 7 → ③: a política de síntese entra no prompt
    seta(ax, (81, cy + ch), (75.8, py))
    rotulo_livre(ax, 78.4, 37.6, "política", ha="center")
    seta(ax, (92, py), (92, cy + ch), duas_pontas=True)
    rotulo_livre(ax, 92.8, 34.2, "validação")

    # Desvios para recusa (azul tracejado): ① e ② → Camada 7
    linha(ax, [(18.5, py), (18.5, canal), (86, canal)], cor=AZUL, estilo="--", largura=1.8)
    linha(ax, [(39.5, py), (39.5, canal)], cor=AZUL, estilo="--", largura=1.8)
    seta(ax, (86, canal), (86, cy + ch), cor=AZUL, estilo="--", largura=1.8)
    rotulo_livre(ax, 29, canal + 1.0, "parecer_juridico / fora_de_escopo", cor=AZUL,
                 ha="center", negrito=True, tam=7.8)
    rotulo_livre(ax, 45.6, canal + 1.0, "nenhum trecho", cor=AZUL, ha="center",
                 negrito=True, tam=7.8)

    # Legenda
    caixa(ax, 0.5, cy, 34, ch, "Legenda", fundo=SUPERFICIE)
    itens = [
        (LARANJA, "-", "fluxo normativo de responder(): ① → ④"),
        (AZUL, "--", "desvio para recusa da Camada 7:\nsem busca nem síntese"),
        (CINZA, "-", "chamada entre camadas"),
        (CINZA, ":", "verificação da URL na ingestão"),
    ]
    for i, (cor, estilo, texto) in enumerate(itens):
        y = cy + ch - 4.6 - i * 2.9
        ax.plot([1.6, 5.2], [y, y], color=cor, linestyle=estilo, linewidth=1.8)
        ax.text(6.0, y, texto, ha="left", va="center", fontsize=8.3, color=TINTA,
                linespacing=1.2)

    # ---- Linha de baixo: ingestão offline e Camada 5 ---------------------
    ly, lh = 3.0, 13.0
    caixa(ax, 37, ly, 41, lh, "Camada 5 · Conhecimento (RAG)",
          "layer5_knowledge/knowledge_base.py · KnowledgeBase.buscar()\n"
          f"BM25 (k1 = {p['k1']}, b = {p['b']}) · embeddings ({p['modelo_embeddings']}, cosseno)\n"
          f"híbrida (RRF, k = {p['rrf_k']}) · modo padrão: {p['modo']}\n"
          f"{p['n_trechos']} trechos de {p['n_normas']} normas\n"
          "Temas: Open Finance, contas de depósito e de pagamento,\n"
          "conformidade, PLD/FT, controles internos, fraudes e\n"
          "segurança cibernética", tam_corpo=8.4)
    seta(ax, (46.5, cy), (46.5, ly + lh), duas_pontas=True)
    rotulo_livre(ax, 47.3, (cy + ly + lh) / 2, "consulta / trechos")

    caixa(ax, 0.5, ly, 34, lh, "Ingestão offline (Camada 5)",
          "layer5_knowledge/ingest_normativos.py", fundo=SUPERFICIE, borda=CINZA, estilo="--")
    etapas = [("BCB", "URL oficial"), ("Bronze", "bruto"), ("Silver", "limpo e\nestruturado"),
              ("Gold", "trechos +\níndices BM25\ne embeddings")]
    ex, ew, eg = 1.5, 6.6, 1.6
    for i, (nome, desc) in enumerate(etapas):
        x = ex + i * (ew + eg)
        ax.add_patch(FancyBboxPatch((x, ly + 0.8), ew, 6.2, boxstyle="round,pad=0,rounding_size=0.5",
                                    facecolor=FUNDO_CAMADA, edgecolor=BORDA, linewidth=1, zorder=2))
        ax.text(x + ew / 2, ly + 5.6, nome, ha="center", va="center", fontsize=9,
                fontweight="bold", color=TINTA, zorder=3)
        ax.text(x + ew / 2, ly + 2.8, desc, ha="center", va="center", fontsize=7.6,
                color=TINTA_SECUNDARIA, linespacing=1.2, zorder=3)
        if i:
            seta(ax, (x - eg, ly + 3.9), (x, ly + 3.9), largura=1.1)
    seta(ax, (34.5, ly + 3.9), (37, ly + 3.9), largura=1.4)

    # Camada 7 verifica a URL de origem (contorna a figura por baixo)
    linha(ax, [(89.75, 5.0), (89.75, 1.6), (4.8, 1.6)], cor=CINZA, estilo=":", largura=1.4)
    seta(ax, (4.8, 1.6), (4.8, ly + 0.8), cor=CINZA, estilo=":", largura=1.4)
    ax.text(47, 1.6, "validar_fonte_publica(): só baixa normativo de HTTPS do bcb.gov.br",
            ha="center", va="center", fontsize=7.8, color=TINTA_SECUNDARIA, zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", facecolor=SUPERFICIE, edgecolor="none"))

    return fig


if __name__ == "__main__":
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    parametros = coletar_parametros()
    fig = desenhar(parametros)
    for ext in ("png", "pdf"):
        destino = DIR_FIGURAS / f"diagrama_arquitetura.{ext}"
        fig.savefig(destino, dpi=300, bbox_inches="tight", facecolor=SUPERFICIE)
        print(f"Figura salva: {destino}")
    print(f"Parâmetros lidos do código e dos dados: {parametros}")
