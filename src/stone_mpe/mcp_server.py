"""Servidor MCP (FastMCP). Execução local via stdio:

    python -m stone_mpe.mcp_server

Configuração de um cliente compatível com MCP, em mcpServers:
    "stone-engajamento-mpe": {"command": "<caminho>/.venv/Scripts/python.exe",
                               "args": ["-m", "stone_mpe.mcp_server"]}
"""
from __future__ import annotations

import json
from typing import Literal, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from stone_mpe import config
from stone_mpe.api import run

mcp = FastMCP(
    "stone-engajamento-mpe",
    instructions="Consulta a base de publicações de alto engajamento voltadas a micro e pequenos empreendedores "
                 "e gera recomendações e criativos para o Impulso Stone, sempre com posts reais de referência.",
)


@mcp.tool()
def analisar_engajamento(
    mode: Literal["analisar", "recomendar", "gerar_criativo"],
    query: str,
    segment: Optional[str] = None,
    platform: Optional[Literal["instagram", "youtube"]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    profile_size: Optional[Literal["micro", "medio", "grande"]] = None,
    tipo_post: Optional[Literal["reels", "carrossel", "imagem", "short"]] = None,
    n_creatives: int = 1,
) -> dict:
    """Analisa padrões das publicações de alto engajamento entre MPEs, recomenda características ou gera
    criativos (gancho, roteiro, legenda, CTA). Toda resposta traz os posts reais que a sustentam."""
    filters = {k: v for k, v in dict(platform=platform, date_from=date_from, date_to=date_to,
                                     profile_size=profile_size, tipo_post=tipo_post).items() if v}
    try:
        return run(mode, query, segment=segment, filters=filters or None, n_creatives=n_creatives).model_dump()
    except ValidationError as e:  # entrada fora do contrato: mensagem curta para o cliente, sem traceback
        campos = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
        raise ToolError(f"entrada inválida ({campos})") from None


@mcp.tool()
def resumo_base() -> dict:
    """Estatísticas da base coletada: volume, perfis, período, exclusões e limiar do top 10%."""
    p = config.outputs_dir() / "base_stats.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"erro": "base ainda não construída"}


if __name__ == "__main__":
    mcp.run()
