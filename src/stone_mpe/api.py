"""Ponto único de entrada (função Python documentada — TAP §4.1).

Exemplo:
    >>> from stone_mpe.api import run
    >>> out = run("gerar_criativo", "Preciso de um Reels para atrair donos de pequenos restaurantes",
    ...           segment="alimentacao", filters={"platform": "instagram"})
    >>> out.creatives[0].gancho, out.creatives[0].inspired_by
"""
from __future__ import annotations

from typing import Optional

from stone_mpe.agent.graph import invoke
from stone_mpe.agent.schemas import AgentInput, AgentOutput, Filters
from stone_mpe.llm import FallbackClient


def run(
    mode: str | AgentInput,
    query: str | None = None,
    segment: Optional[str] = None,
    filters: Optional[dict | Filters] = None,
    n_creatives: int = 1,
    llm: FallbackClient | None = None,
) -> AgentOutput:
    """Analisa, recomenda ou gera criativos a partir das publicações de alto desempenho da base.

    Args:
        mode: "analisar" | "recomendar" | "gerar_criativo" (ou um AgentInput pronto).
        query: pergunta, objetivo ou pedido de criativo, em linguagem natural.
        segment: recorte do empreendedor (alimentacao, beleza, varejo, servicos, ...). Opcional;
            se ausente, é inferido do texto quando possível.
        filters: {"platform", "date_from", "date_to", "profile_size", "tipo_post"} — todos opcionais.
        n_creatives: quantidade de criativos (1–5) no modo gerar_criativo.
        llm: cliente LLM alternativo (testes). Padrão: cadeia de LLM_PROVIDERS do .env.

    Returns:
        AgentOutput com findings (frequências da base), reference_posts (links reais), creatives
        (cada um com `inspired_by` = post_ids existentes), confidence_flag e explanation.
        A execução é registrada em outputs/runs.jsonl.

    Raises:
        pydantic.ValidationError: entrada fora do contrato.
    """
    if isinstance(mode, AgentInput):
        inp = mode
    else:
        inp = AgentInput(mode=mode, query=query or "", segment=segment,
                         filters=Filters.model_validate(filters) if isinstance(filters, dict) else filters,
                         n_creatives=n_creatives)
    return invoke(inp, llm)
