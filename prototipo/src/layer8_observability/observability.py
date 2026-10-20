"""
Camada 8 — Observabilidade e Proveniência (Maia et al., 2026, Seção 8).

Responsabilidade segundo a arquitetura conceitual: registrar, para cada
interação, o que fundamentou a resposta — normativo(s) usados, classificação
da Camada 3, e se a Camada 7 sinalizou citação não verificada — para
rastreabilidade/auditoria completa.

Decisão de projeto (ver docs/decisoes_arquitetura.md): registro estruturado
em JSON Lines, um objeto por interação, anexado a um arquivo em disco
(`logs/interacoes.jsonl`) — ao contrário da Camada 6 (memória em processo,
sem persistência), aqui a persistência é o propósito da camada. As fontes
normativas usadas são extraídas do texto já formatado que a Camada 4
(`buscar_normativo`) produz ("Fonte: título (url)"), via regex
determinístico — mesmo padrão de parsing já usado na Camada 7 — em vez de
alterar a assinatura de `buscar_normativo` para retornar dados estruturados,
sem um segundo consumidor que justifique essa mudança.

Camada 7 v2 (2026-09-24): o registro passa a guardar o `desfecho` da
interação (resposta ou qual recusa) e as categorias da validação da Camada 7
(`validacao`: normas/artigos/valores não verificados, normas declaradas
ausentes). `aviso_citacao_nao_verificada` continua existindo com o critério
da v1/v2, para comparar versões com a mesma régua.

v4 (2026-09-24): `parametros_llm` registra modelo, ID do modelo (digest),
temperaturas de classificação e de síntese e seed — sem isso, não é possível
saber depois com que configuração uma resposta foi gerada.

v7 (2026-10-20): `recuperacao` registra o modo de recuperação da Camada 5
(bm25, embeddings ou hybrid), o modelo e o digest de embeddings e a versão
do(s) índice(s). A Camada 8 pede essa identificação diretamente à Camada 5
(`identificacao_recuperacao()`), em vez de recebê-la da Camada 3: assim a
orquestração não muda, ao custo de uma dependência da Camada 8 (transversal)
para a Camada 5 — trade-off registrado em docs/decisoes_arquitetura.md,
"Camada 5: embeddings e busca híbrida".

Robustez (2026-10-20): `desfecho="erro"` e o campo `erro` registram a
interação em que uma etapa falhou (Ollama fora do ar, timeout), para que a
falha apareça na auditoria; registros antigos, sem `erro`, continuam
válidos. Ver docs/decisoes_arquitetura.md, Camada 2, "Robustez".
"""
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.layer5_knowledge.knowledge_base import identificacao_recuperacao

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "interacoes.jsonl"

_FONTE_REGEX = re.compile(r"^Fonte:\s*(.+?)\s*\((https?://[^\s)]+)\)", re.MULTILINE)


@dataclass
class RegistroInteracao:
    timestamp: str
    pergunta: str
    tipo_classificacao: str
    fontes_normativas: list[dict] = field(default_factory=list)
    aviso_citacao_nao_verificada: bool = False
    resposta_final: str = ""
    # "resposta" | "recusa_parecer_juridico" | "recusa_fora_de_escopo" |
    # "recusa_sem_base" | "erro" (falha de uma etapa; ver `erro`)
    desfecho: str = "resposta"
    validacao: dict = field(default_factory=dict)
    parametros_llm: dict = field(default_factory=dict)
    recuperacao: dict = field(default_factory=dict)
    erro: str = ""  # mensagem da exceção quando desfecho == "erro" (2026-10-20)


def _extrair_fontes(normativo: str) -> list[dict]:
    # dedup preservando ordem: vários trechos retornados pela Camada 5 podem
    # vir do mesmo normativo (top_k > 1 trechos de um único documento), e a
    # proveniência deve listar quais documentos embasaram a resposta, não
    # quantos trechos foram usados.
    vistos: set[tuple[str, str]] = set()
    fontes = []
    for titulo, url in _FONTE_REGEX.findall(normativo):
        chave = (titulo, url)
        if chave not in vistos:
            vistos.add(chave)
            fontes.append({"titulo": titulo, "url_oficial": url})
    return fontes


def registrar_interacao(
    pergunta: str,
    tipo_classificacao: str,
    resposta_final: str,
    normativo: str = "",
    arquivo: Path | None = None,
    validacao: dict | None = None,
    desfecho: str = "resposta",
    parametros_llm: dict | None = None,
    erro: str = "",
) -> RegistroInteracao:
    registro = RegistroInteracao(
        timestamp=datetime.now(timezone.utc).isoformat(),
        pergunta=pergunta,
        tipo_classificacao=tipo_classificacao,
        fontes_normativas=_extrair_fontes(normativo),
        aviso_citacao_nao_verificada=(
            validacao["aviso_legado"] if validacao else "Aviso:" in resposta_final
        ),
        resposta_final=resposta_final,
        desfecho=desfecho,
        validacao=validacao or {},
        parametros_llm=parametros_llm or {},
        recuperacao=identificacao_recuperacao(),
        erro=erro,
    )
    destino = arquivo or LOG_FILE
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(registro), ensure_ascii=False) + "\n")
    return registro
