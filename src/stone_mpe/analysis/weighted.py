"""Índice de Desempenho Ponderado (IDP): engajamento relativo aos pares.

A métrica oficial do case, (curtidas + comentários) ÷ seguidores, compara todos os posts de uma
plataforma entre si. Ela favorece nichos que engajam mais por natureza, contas pequenas com um
viral e posts de épocas em que a plataforma distribuía mais. O IDP corrige isso comparando cada
post com quatro grupos de referência e somando os percentis com pesos:

| componente     | compara o post com...                                    | peso padrão |
|----------------|----------------------------------------------------------|-------------|
| nicho          | posts do mesmo segmento, na mesma plataforma             | 0,35        |
| perfil         | a mediana do próprio criador (acima do normal dele?)      | 0,30        |
| período        | posts do mesmo trimestre, na mesma plataforma (tendência) | 0,20        |
| porte          | posts de contas da mesma faixa de seguidores             | 0,15        |

Cada componente é um percentil de 0 a 1. Grupos com menos de `min_group` posts caem para o
percentil da plataforma inteira (evita percentil instável em grupo pequeno). O top do IDP é o
percentil 90 do índice por plataforma, como na métrica oficial.

É uma leitura COMPLEMENTAR: o ranking oficial continua sendo o do case. O IDP mostra se os
padrões resistem quando nicho, perfil, época e porte são controlados.
"""
from __future__ import annotations

import pandas as pd

from stone_mpe import config, storage

DEFAULT_WEIGHTS = {"nicho": 0.35, "perfil": 0.30, "periodo": 0.20, "porte": 0.15}


def weights(override: dict[str, float] | None = None) -> dict[str, float]:
    w = {**DEFAULT_WEIGHTS, **(config.get("analysis.weighted_index.weights", {}) or {}), **(override or {})}
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


def _pct(df: pd.DataFrame, value: str, keys: list[str], min_group: int) -> pd.Series:
    """Percentil (0–1) de `value` dentro do grupo; grupos pequenos usam a plataforma inteira."""
    in_group = df.groupby(keys, dropna=False)[value].rank(pct=True)
    size = df.groupby(keys, dropna=False)[value].transform("size")
    platform = df.groupby("platform")[value].rank(pct=True)
    return in_group.where(size >= min_group, platform)


def compute(posts: pd.DataFrame | None = None, min_group: int | None = None, top_q: float = 0.90,
            weight_override: dict[str, float] | None = None) -> pd.DataFrame:
    """Calcula o IDP para os posts elegíveis. Devolve um DataFrame com componentes e flag de top."""
    min_group = min_group or int(config.get("analysis.weighted_index.min_group", 20))
    if posts is None:
        posts = storage.read_sql(
            "SELECT post_id, platform, handle, profile_id, segmento, faixa, posted_at, engagement_rate, is_top "
            "FROM posts WHERE eligible = 1")
    df = posts.dropna(subset=["engagement_rate"]).copy()
    if df.empty:
        return df
    dt = pd.to_datetime(df["posted_at"], utc=True, errors="coerce").dt.tz_localize(None)
    df["periodo"] = dt.dt.to_period("Q").astype(str)
    creator_med = df.groupby(["platform", "profile_id"])["engagement_rate"].transform("median")
    df["er_vs_perfil"] = df["engagement_rate"] / creator_med.where(creator_med > 0)
    df["er_vs_perfil"] = df["er_vs_perfil"].fillna(0.0)

    df["c_nicho"] = _pct(df, "engagement_rate", ["platform", "segmento"], min_group)
    df["c_perfil"] = _pct(df, "er_vs_perfil", ["platform"], min_group)
    df["c_periodo"] = _pct(df, "engagement_rate", ["platform", "periodo"], min_group)
    df["c_porte"] = _pct(df, "engagement_rate", ["platform", "faixa"], min_group)
    w = weights(weight_override)
    df["idp"] = sum(w[k] * df[f"c_{k}"] for k in w)
    cut = df.groupby("platform")["idp"].transform(lambda s: s.quantile(top_q))
    df["is_top_idp"] = (df["idp"] >= cut).astype(int)
    df["is_top"] = df["is_top"].fillna(0).astype(int)
    return df


def _concentration(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"criadores": 0, "top4_share": None}
    counts = df["handle"].value_counts()
    return {"criadores": int(counts.size), "top4_share": round(float(counts.head(4).sum() / counts.sum()), 3)}


def summary(df: pd.DataFrame | None = None, weight_override: dict[str, float] | None = None) -> dict:
    """Compara o top oficial com o top do IDP, por plataforma."""
    df = compute(weight_override=weight_override) if df is None else df
    if df.empty:
        return {}
    categorized = set(storage.read_sql(
        "SELECT DISTINCT post_id FROM categorizations WHERE valid = 1")["post_id"])
    out = {"pesos": {k: round(v, 3) for k, v in weights(weight_override).items()}, "plataformas": {}}
    for plat, g in df.groupby("platform"):
        off, idp = g[g["is_top"] == 1], g[g["is_top_idp"] == 1]
        both = set(off["post_id"]) & set(idp["post_id"])
        out["plataformas"][plat] = {
            "elegiveis": int(len(g)),
            "top_oficial": int(len(off)),
            "top_idp": int(len(idp)),
            "em_ambos": len(both),
            "sobreposicao": round(len(both) / len(idp), 3) if len(idp) else None,
            "concentracao_oficial": _concentration(off),
            "concentracao_idp": _concentration(idp),
            "idp_categorizados": int(idp["post_id"].isin(categorized).sum()),
        }
    return out


def top_patterns(df: pd.DataFrame | None = None, fields: list[str] | None = None) -> pd.DataFrame:
    """Frequência das características no top oficial × top do IDP (só posts categorizados)."""
    from stone_mpe.analysis import patterns

    df = compute() if df is None else df
    fields = fields or ["tipo_hook", "formato_video", "tema_principal", "tipo_cta", "tom", "duracao_faixa"]
    cat = patterns.load_top(include_rest=True)
    if cat.empty or df.empty:
        return pd.DataFrame()
    cat = cat.merge(df[["post_id", "is_top_idp"]], on="post_id", how="inner")
    rows = []
    for name, sub in [("oficial", cat[cat["is_top"] == 1]), ("idp", cat[cat["is_top_idp"] == 1])]:
        for f in fields:
            vc = sub[f].dropna().astype(str).value_counts(normalize=True)
            for value, freq in vc.head(3).items():
                rows.append({"ranking": name, "field": f, "value": value, "freq": round(float(freq), 3),
                             "n": int(len(sub))})
    return pd.DataFrame(rows)


def save() -> dict:
    df = compute()
    if df.empty:
        return {}
    cols = ["post_id", "platform", "handle", "segmento", "faixa", "periodo", "engagement_rate", "er_vs_perfil",
            "c_nicho", "c_perfil", "c_periodo", "c_porte", "idp", "is_top", "is_top_idp"]
    out_dir = config.outputs_dir()
    df[cols].round(4).to_csv(out_dir / "indice_ponderado.csv", index=False)
    s = summary(df)
    tp = top_patterns(df)
    if not tp.empty:
        tp.to_csv(out_dir / "indice_ponderado_padroes.csv", index=False)
    import json
    (out_dir / "indice_ponderado.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    return s
