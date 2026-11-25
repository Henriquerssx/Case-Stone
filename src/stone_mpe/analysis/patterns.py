"""Levantamento de características das publicações de alto desempenho.

Tudo aqui é contagem sobre a base: o agente e o playbook só leem estes resultados.
Padrões são OBSERVADOS, não causais (TAP §6.4).
"""
from __future__ import annotations

import json
import unicodedata

import pandas as pd

from stone_mpe import config, storage
from stone_mpe.multimodal import rubric as R

PATTERN_FIELDS = ["tipo_post", "formato_video", "tipo_hook", "tema_principal", "tom", "tipo_cta",
                  "duracao_faixa", "legenda_tamanho"] + R.BOOL_FIELDS


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def load_top(segment: str | None = None, filters: dict | None = None, include_rest: bool = False) -> pd.DataFrame:
    """Posts do top com categorização válida (join SQLite), filtrados.

    filters: platform, date_from, date_to, profile_size (micro|medio|grande), tipo_post.
    include_rest=True devolve todos os elegíveis (para comparação top × resto).
    """
    where = "p.eligible = 1" if include_rest else "p.is_top = 1"
    join, params = storage.categ_join()
    df = storage.read_sql(
        f"""SELECT p.post_id, p.platform, p.handle, p.profile_id, p.url, p.media_type, p.posted_at, p.caption,
                   p.likes, p.comments, p.views, p.followers, p.engagement_rate, p.percentile, p.is_top,
                   p.faixa, p.segmento, p.duration_s, c.*
            FROM posts p {join}
            WHERE {where}""",
        params,
    )
    df = df.loc[:, ~df.columns.duplicated()]
    f = filters or {}
    if segment:
        df = df[df["segmento"].map(_fold) == _fold(segment)]
    if f.get("platform"):
        df = df[df["platform"] == f["platform"]]
    if f.get("profile_size"):
        df = df[df["faixa"] == f["profile_size"]]
    if f.get("tipo_post"):
        df = df[df["tipo_post"] == f["tipo_post"]]
    if f.get("date_from"):
        df = df[df["posted_at"] >= str(f["date_from"])]
    if f.get("date_to"):
        df = df[df["posted_at"] <= str(f["date_to"]) + "T23:59:59"]
    return df.reset_index(drop=True)


def frequencies(df: pd.DataFrame, fields: list[str] | None = None, n_examples: int = 3) -> pd.DataFrame:
    """Uma linha por (campo, valor): n, frequência no recorte, exemplos (maior engajamento).

    Como poucos criadores concentram boa parte do top, também calcula:
    - n_criadores: em quantos criadores distintos o valor aparece;
    - freq_por_criador: média das frequências dentro de cada criador (cada criador pesa igual).
    Um padrão com freq alta mas freq_por_criador baixa é estilo de poucos canais, não do top em geral.
    """
    rows = []
    total = len(df)
    if total == 0:
        return pd.DataFrame(columns=["field", "value", "n", "freq", "total", "n_criadores", "freq_por_criador", "example_post_ids"])
    by = df["profile_id"] if "profile_id" in df else pd.Series("all", index=df.index)
    for field in fields or PATTERN_FIELDS:
        if field not in df:
            continue
        col = df[field]
        if field in R.BOOL_FIELDS:
            col = col.map({1: "sim", 0: "não", True: "sim", False: "não"})
        valid = col.dropna()
        for value, n in valid.value_counts().items():
            hit = col == value
            ex = df.loc[hit].sort_values("engagement_rate", ascending=False)["post_id"].head(n_examples).tolist()
            share = hit[col.notna()].groupby(by[col.notna()]).mean()
            rows.append({"field": field, "value": str(value), "n": int(n), "freq": n / total, "total": total,
                         "n_criadores": int(by[hit].nunique()), "freq_por_criador": float(share.mean()), "example_post_ids": ex})
    return pd.DataFrame(rows).sort_values(["field", "n"], ascending=[True, False]).reset_index(drop=True)


def crosstab(df: pd.DataFrame, a: str = "tema_principal", b: str = "formato_video") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return pd.crosstab(df[a].fillna("n/a"), df[b].fillna("n/a"))


def lift(fields: list[str] | None = None, min_n: int = 5, min_rest: int | None = None) -> pd.DataFrame:
    """Nível 3: frequência no top ÷ frequência no resto (exige amostra do resto categorizada).

    Só calcula com pelo menos `min_rest` posts do resto (padrão: analysis.min_rest_sample = 50):
    com poucos posts no resto, qualquer razão é ruído.
    """
    allc = load_top(include_rest=True)
    top, rest = allc[allc["is_top"] == 1], allc[allc["is_top"] == 0]
    min_rest = config.get("analysis.min_rest_sample", 50) if min_rest is None else min_rest
    if top.empty or len(rest) < min_rest:
        return pd.DataFrame()
    ft, fr = frequencies(top, fields), frequencies(rest, fields)
    m = ft.merge(fr[["field", "value", "freq", "n"]], on=["field", "value"], how="left", suffixes=("_top", "_rest"))
    m = m[m["n_top"] >= min_n]
    m["lift"] = m["freq_top"] / m["freq_rest"]
    return m.sort_values("lift", ascending=False)


def concentration(df: pd.DataFrame) -> dict:
    """Quanto do top vem de poucos criadores (lido junto com freq_por_criador)."""
    if df.empty or "profile_id" not in df:
        return {}
    c = df["profile_id"].value_counts()
    return {"n_criadores": int(len(c)), "share_top1": round(float(c.iloc[0] / c.sum()), 3),
            "share_top4": round(float(c.head(4).sum() / c.sum()), 3),
            "maiores": {k.split(":", 1)[-1]: int(v) for k, v in c.head(5).items()}}


def report() -> dict:
    """Gera outputs/patterns.json + CSVs para o README e o playbook."""
    df = load_top()
    out = config.outputs_dir()
    freq = frequencies(df)
    freq.assign(example_post_ids=freq["example_post_ids"].map(json.dumps)).to_csv(out / "frequencias_top.csv", index=False)
    crosstab(df).to_csv(out / "tema_x_formato.csv")
    summary = {"n_top_categorizados": len(df), "concentracao": concentration(df),
               "top_por_campo": {f: g.head(3)[["value", "n", "freq", "n_criadores", "freq_por_criador"]].round(3).to_dict(orient="records")
                                 for f, g in freq.groupby("field")}}
    (out / "patterns.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
