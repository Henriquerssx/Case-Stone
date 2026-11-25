"""Configuração central: caminhos do projeto, settings.yaml e variáveis de ambiente.

Os caminhos podem ser sobrescritos por variáveis de ambiente (usado nos testes):
STONE_MPE_ROOT, STONE_MPE_DB.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_PKG_ROOT = Path(__file__).resolve().parents[2]


def root() -> Path:
    return Path(os.environ.get("STONE_MPE_ROOT", _PKG_ROOT))


load_dotenv(root() / ".env")


def path(*parts: str) -> Path:
    p = root().joinpath(*parts)
    return p


def db_path() -> Path:
    return Path(os.environ.get("STONE_MPE_DB", path("db", "base.sqlite")))


def data_dir() -> Path:
    return Path(os.environ.get("STONE_MPE_DATA", path("data")))


def raw_dir(platform: str) -> Path:
    d = data_dir() / "raw" / platform
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir(namespace: str) -> Path:
    d = data_dir() / "cache" / namespace
    d.mkdir(parents=True, exist_ok=True)
    return d


def outputs_dir() -> Path:
    d = Path(os.environ.get("STONE_MPE_OUTPUTS", path("outputs")))
    d.mkdir(parents=True, exist_ok=True)
    return d


@lru_cache(maxsize=1)
def settings() -> dict[str, Any]:
    with open(path("config", "settings.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def get(dotted: str, default: Any = None) -> Any:
    """settings via chave pontilhada, ex.: get('ranking.top_percentile')."""
    node: Any = settings()
    for key in dotted.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    return v if v else default
