"""Ranking e critério de alto desempenho (top 10% pela métrica normalizada).

Calcula sempre as duas versões (por plataforma e combinada) para análise de
sensibilidade; `is_top` segue `ranking.scope` do settings.yaml.
"""
from __future__ import annotations

import pandas as pd

from stone_mpe import config


def _flag_top(er: pd.Series, q: float) -> tuple[pd.Series, pd.Series]:
    pct = er.rank(pct=True, method="average")
    thr = er.quantile(q)
    return pct, er >= thr


def rank(df: pd.DataFrame, q: float | None = None, scope: str | None = None) -> pd.DataFrame:
    q = config.get("ranking.top_percentile", 0.9) if q is None else q
    scope = config.get("ranking.scope", "platform") if scope is None else scope
    df = df.copy()
    df["percentile_platform"] = float("nan")
    df["is_top_platform"] = False
    df["percentile_combined"] = float("nan")
    df["is_top_combined"] = False

    ok = df["eligible"] & df["engagement_rate"].notna()
    if ok.any():
        pct, top = _flag_top(df.loc[ok, "engagement_rate"], q)
        df.loc[ok, "percentile_combined"] = pct
        df.loc[ok, "is_top_combined"] = top
        for plat, idx in df[ok].groupby("platform").groups.items():
            pct, top = _flag_top(df.loc[idx, "engagement_rate"], q)
            df.loc[idx, "percentile_platform"] = pct
            df.loc[idx, "is_top_platform"] = top

    df["is_top"] = df["is_top_platform"] if scope == "platform" else df["is_top_combined"]
    df["percentile"] = df["percentile_platform"] if scope == "platform" else df["percentile_combined"]
    df["is_top"] = df["is_top"].astype(bool)
    return df
