"""Métricas de engajamento por nicho empreendedor (segmento do perfil) e por plataforma.

Tudo é contagem sobre a base. Os percentis do top continuam sendo por plataforma; aqui só se
recorta por segmento para comparar nichos (quanto engaja, quanto chega ao top, o que o top usa).
"""
from __future__ import annotations

import pandas as pd

from stone_mpe import storage
from stone_mpe.analysis import patterns

NOMES = {"alimentacao": "Alimentação", "beleza": "Beleza", "varejo": "Varejo", "servicos": "Serviços",
         "financas": "Finanças", "marketing": "Marketing", "geral": "Geral"}


def _eligible(platform: str | None = None) -> pd.DataFrame:
    where, params = "eligible = 1", ()
    if platform:
        where += " AND platform = ?"
        params = (platform,)
    return storage.read_sql(f"""SELECT post_id, platform, handle, profile_id, segmento, faixa, url, likes, comments, views, followers,
                                       engagement_rate, is_top, posted_at FROM posts WHERE {where}""", params)


def _mode(s: pd.Series) -> tuple[str | None, float | None]:
    s = s.dropna()
    if s.empty:
        return None, None
    vc = s.value_counts(normalize=True)
    return str(vc.index[0]), float(vc.iloc[0])


def summary(platform: str | None = None) -> pd.DataFrame:
    """Uma linha por nicho: volume, engajamento (mediana e p90), taxa de chegada ao top e o que o top usa."""
    df = _eligible(platform)
    if df.empty:
        return pd.DataFrame()
    top = patterns.load_top(filters={"platform": platform} if platform else None)
    rows = []
    for seg, g in df.groupby("segmento"):
        t = top[top["segmento"] == seg]
        fmt, fmt_p = _mode(t.get("formato_video", pd.Series(dtype=str)))
        hook, hook_p = _mode(t.get("tipo_hook", pd.Series(dtype=str)))
        tema, tema_p = _mode(t.get("tema_principal", pd.Series(dtype=str)))
        dur, dur_p = _mode(t.get("duracao_faixa", pd.Series(dtype=str)))
        v = g[g["views"].notna() & (g["followers"] > 0)]
        rows.append({
            "nicho": seg, "nome": NOMES.get(seg, seg), "perfis": g["profile_id"].nunique(),
            "plataformas": ", ".join(sorted(g["platform"].unique())),
            "posts": len(g), "posts_top": int(g["is_top"].sum()), "taxa_top": float(g["is_top"].mean()),
            "er_mediana": float(g["engagement_rate"].median()), "er_p90": float(g["engagement_rate"].quantile(0.9)),
            "er_mediana_top": float(g.loc[g["is_top"] == 1, "engagement_rate"].median()) if g["is_top"].any() else None,
            "views_por_seguidor": float((v["views"] / v["followers"]).median()) if len(v) else None,
            "comentarios_por_curtida": float((g["comments"] / g["likes"].where(g["likes"] > 0)).median()),
            "top_categorizados": len(t),
            "formato_top": fmt, "formato_top_pct": fmt_p, "gancho_top": hook, "gancho_top_pct": hook_p,
            "tema_top": tema, "tema_top_pct": tema_p, "duracao_top": dur, "duracao_top_pct": dur_p,
            "cta_no_top": float(t["tem_cta"].mean()) if "tem_cta" in t and len(t) else None,
        })
    return pd.DataFrame(rows).sort_values("er_mediana", ascending=False).reset_index(drop=True)


def by_platform() -> pd.DataFrame:
    """Mediana de engajamento por nicho × plataforma (para comparar Instagram e YouTube no mesmo nicho)."""
    df = _eligible()
    if df.empty:
        return pd.DataFrame()
    return (df.groupby(["segmento", "platform"])
              .agg(posts=("post_id", "size"), perfis=("profile_id", "nunique"), er_mediana=("engagement_rate", "median"),
                   taxa_top=("is_top", "mean"))
              .reset_index())


def top_posts(segment: str, n: int = 6, platform: str | None = None) -> pd.DataFrame:
    df = _eligible(platform)
    df = df[(df["segmento"] == segment) & (df["is_top"] == 1)]
    return df.sort_values("engagement_rate", ascending=False).head(n)
