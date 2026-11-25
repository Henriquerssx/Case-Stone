"""Perfis em destaque: criadores mais presentes no top, com tema e formato predominantes."""
from __future__ import annotations

import pandas as pd

from stone_mpe import storage


def _mode(s: pd.Series):
    s = s.dropna()
    return s.mode().iloc[0] if not s.empty else None


def featured(df_top: pd.DataFrame, min_posts: int = 1) -> pd.DataFrame:
    if df_top.empty:
        return pd.DataFrame()
    prof = storage.read_sql("SELECT profile_id, n_eligible, followers, faixa, origem FROM profiles")
    g = df_top.groupby("profile_id")
    out = pd.DataFrame({
        "platform": g["platform"].first(),
        "handle": g["handle"].first(),
        "segmento": g["segmento"].first(),
        "n_top": g.size(),
        "er_mediana_top": g["engagement_rate"].median(),
        "tema_predominante": g["tema_principal"].agg(_mode),
        "formato_predominante": g["formato_video"].agg(_mode),
        "tipo_post_predominante": g["tipo_post"].agg(_mode),
        "exemplo": g.apply(lambda x: x.sort_values("engagement_rate", ascending=False)["post_id"].iloc[0], include_groups=False),
    }).reset_index()
    out = out.merge(prof, on="profile_id", how="left")
    # taxa de presença: evita que perfis com muitos posts dominem só por volume
    out["taxa_no_top"] = out["n_top"] / out["n_eligible"].where(out["n_eligible"] > 0)
    out = out[out["n_top"] >= min_posts]
    return out.sort_values(["n_top", "taxa_no_top"], ascending=False).reset_index(drop=True)
