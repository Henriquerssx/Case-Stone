"""Raw JSONL (IG + YT) -> base limpa: dedupe, idade, elegibilidade, métrica, ranking.

Saídas: data/processed/posts.parquet, tabelas `posts` e `profiles` no SQLite,
e outputs/base_stats.json (estatísticas descritivas para o README).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from stone_mpe import config, storage
from stone_mpe.process.metrics import engagement_rate, faixa
from stone_mpe.process.ranking import rank


def load_raw() -> pd.DataFrame:
    rows = []
    for plat in ("instagram", "youtube"):
        for f in sorted(config.raw_dir(plat).glob("*.jsonl")):
            with open(f, encoding="utf-8") as fh:
                rows += [json.loads(line) for line in fh if line.strip()]
    if not rows:
        raise RuntimeError("Nenhum dado bruto em data/raw/. Rode a coleta/importação primeiro.")
    return pd.DataFrame(rows)


def load_profiles_meta() -> pd.DataFrame:
    p = config.path("config", "profiles.csv")
    df = pd.read_csv(p, dtype=str).fillna("")
    df["handle"] = df["handle"].str.strip().str.lstrip("@").str.lower()
    return df[["platform", "handle", "origem", "segmento", "justificativa"]].drop_duplicates(["platform", "handle"])


def _exclusion(row) -> str:
    if row["age_days"] < config.get("collection.min_age_days", 14):
        return "menos_de_14_dias"
    if pd.isna(row["followers"]) or row["followers"] <= 0:
        return "seguidores_ausentes"
    if pd.isna(row["likes"]):
        return "curtidas_ocultas"
    if pd.isna(row["comments"]):
        return "comentarios_indisponiveis"
    # vídeo agendado/em processamento: duração 0 e nenhuma visualização
    if row.get("platform") == "youtube" and (row.get("duration_s") or 0) < 1 and (row.get("views") or 0) == 0:
        return "video_indisponivel"
    return ""


def build(df: pd.DataFrame | None = None, profiles_meta: pd.DataFrame | None = None) -> pd.DataFrame:
    df = load_raw() if df is None else df.copy()
    meta = load_profiles_meta() if profiles_meta is None else profiles_meta

    df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True, format="ISO8601")
    df["collected_at"] = pd.to_datetime(df["collected_at"], utc=True, format="ISO8601")
    df = df.sort_values("collected_at").drop_duplicates("post_id", keep="last")

    for c in ("likes", "comments", "views", "followers", "duration_s"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["likes_hidden"] = df["likes"].isna()
    df["age_days"] = (df["collected_at"] - df["posted_at"]).dt.total_seconds() / 86400

    # seguidores do perfil = valor da coleta mais recente (registrado em todos os posts)
    df["profile_id"] = df["platform"] + ":" + df["handle"]
    latest = df.sort_values("collected_at").groupby("profile_id")["followers"].last()
    df["followers"] = df["profile_id"].map(latest)

    df["exclusion_reason"] = df.apply(_exclusion, axis=1)
    df["eligible"] = df["exclusion_reason"] == ""
    df["engagement_rate"] = engagement_rate(df["likes"], df["comments"], df["followers"])
    df.loc[~df["eligible"], "engagement_rate"] = float("nan")

    mi, me = config.get("profiles.faixa_micro_max", 10000), config.get("profiles.faixa_medio_max", 100000)
    df["faixa"] = df["followers"].apply(lambda f: faixa(f, mi, me))
    df = df.merge(meta, on=["platform", "handle"], how="left")
    df["segmento"] = df["segmento"].replace("", pd.NA).fillna("geral")
    df["origem"] = df["origem"].replace("", pd.NA).fillna("nao_informada")

    df = rank(df)
    df["tags"] = df["tags"].apply(lambda t: json.dumps(t if isinstance(t, list) else [], ensure_ascii=False))
    return df


def profiles_table(posts: pd.DataFrame) -> pd.DataFrame:
    g = posts.groupby("profile_id")
    return pd.DataFrame(
        {
            "platform": g["platform"].first(),
            "handle": g["handle"].first(),
            "followers": g["followers"].first(),
            "faixa": g["faixa"].first(),
            "origem": g["origem"].first(),
            "segmento": g["segmento"].first(),
            "justificativa": g["justificativa"].first(),
            "n_posts": g.size(),
            "n_eligible": g["eligible"].sum(),
            "n_top": g["is_top"].sum(),
            "followers_collected_at": g["collected_at"].max().astype(str),
        }
    ).reset_index()


def stats(posts: pd.DataFrame, profiles: pd.DataFrame) -> dict:
    el = posts[posts["eligible"]]
    return {
        "n_posts_raw": int(len(posts)),
        "n_posts_eligible": int(len(el)),
        "n_top": int(posts["is_top"].sum()),
        "n_profiles": int(len(profiles)),
        "by_platform": posts.groupby("platform").size().to_dict(),
        "eligible_by_platform": el.groupby("platform").size().to_dict(),
        "profiles_by_faixa": profiles["faixa"].value_counts(dropna=False).to_dict(),
        "exclusions": posts["exclusion_reason"].replace("", "elegivel").value_counts().to_dict(),
        "posted_from": str(posts["posted_at"].min().date()),
        "posted_to": str(posts["posted_at"].max().date()),
        "collected_from": str(posts["collected_at"].min().date()),
        "collected_to": str(posts["collected_at"].max().date()),
        "er_threshold_by_platform": el.groupby("platform")["engagement_rate"].quantile(config.get("ranking.top_percentile", 0.9)).to_dict(),
        "er_median_by_platform": el.groupby("platform")["engagement_rate"].median().to_dict(),
        "ranking_scope": config.get("ranking.scope"),
        "overlap_top_platform_vs_combined": int((posts["is_top_platform"] & posts["is_top_combined"]).sum()),
    }


def run() -> dict:
    posts = build()
    profiles = profiles_table(posts)
    out = config.data_dir() / "processed"
    out.mkdir(parents=True, exist_ok=True)
    posts.to_parquet(out / "posts.parquet", index=False)
    db_posts = posts.copy()
    for c in ("posted_at", "collected_at"):
        db_posts[c] = db_posts[c].astype(str)
    storage.write_table(db_posts, "posts")
    storage.write_table(profiles, "profiles")
    s = stats(posts, profiles)
    Path(config.outputs_dir() / "base_stats.json").write_text(json.dumps(s, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return s
