"""Métrica principal (TAP §6.1): (curtidas + comentários) ÷ seguidores."""
from __future__ import annotations

import numpy as np
import pandas as pd


def engagement_rate(likes, comments, followers):
    """Escalar ou vetorizado. Retorna NaN quando seguidores <= 0 ou métricas ausentes."""
    if np.ndim(followers) == 0:
        l, c, f = (pd.to_numeric(x, errors="coerce") for x in (likes, comments, followers))
        if pd.isna(l) or pd.isna(c) or pd.isna(f) or f <= 0:
            return float("nan")
        return float((l + c) / f)
    likes = pd.to_numeric(likes, errors="coerce")
    comments = pd.to_numeric(comments, errors="coerce")
    followers = pd.to_numeric(followers, errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        er = (likes + comments) / followers
    return er.where(followers > 0)


def faixa(followers: float | None, micro_max: int, medio_max: int) -> str | None:
    if followers is None or pd.isna(followers):
        return None
    if followers <= micro_max:
        return "micro"
    if followers <= medio_max:
        return "medio"
    return "grande"
