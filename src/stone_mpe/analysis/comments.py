"""Comentários das publicações do top: intenção de contato (lead), dúvidas, objeções.

Fontes: YouTube `commentThreads` (1 unidade/chamada, até 100 comentários por post) ou
um arquivo de comentários exportado pela rota do Instagram (colunas post_id/shortcode + text).

Privacidade (minimização, LGPD): nada de autor/username. Guardamos só contagens por post e
até 3 exemplos curtos por classe, truncados, para o playbook.

Classificador por regras (transparente e reprodutível), classes não exclusivas:
  contato   — "quero", "como faço", "qual o link", "quanto custa", "como participo" ...
  duvida    — perguntas (?, como, onde, qual, quando, funciona pra ...)
  objecao   — "caro", "taxa", "não funciona", "golpe", "difícil", "não tenho tempo" ...
  elogio    — "amei", "top", "ótimo", "obrigad", "ajudou" ...
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

from stone_mpe import storage
from stone_mpe.analysis.lead_signals import has_contact_intent

_DUVIDA = re.compile(r"\?|\b(como|onde|qual|quais|quando|quanto|funciona (pra|para)|serve (pra|para)|da pra|posso)\b")
_OBJECAO = re.compile(r"\b(caro|cara demais|taxa|taxas|nao funciona|golpe|dificil|nao tenho tempo|nao da|mentira|nao acredito|enganacao|juros)\b")
_ELOGIO = re.compile(r"\b(amei|amo|top|otimo|otima|excelente|obrigad|ajudou|maravilh|parabens|incrivel|show)\b")


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def classify(text: str) -> set[str]:
    t = _fold(text)
    out = set()
    if has_contact_intent(text):
        out.add("contato")
    if _DUVIDA.search(t):
        out.add("duvida")
    if _OBJECAO.search(t):
        out.add("objecao")
    if _ELOGIO.search(t):
        out.add("elogio")
    return out


def aggregate(post_id: str, texts: list[str], source: str) -> dict:
    counts = {"contato": 0, "duvida": 0, "objecao": 0, "elogio": 0}
    examples: dict[str, list[str]] = {k: [] for k in counts}
    for t in texts:
        for c in classify(t):
            counts[c] += 1
            if len(examples[c]) < 3 and 10 <= len(t) <= 220:
                examples[c].append(t.strip()[:160])
    n = len(texts)
    return {"post_id": post_id, "source": source, "n_sampled": n,
            **{f"n_{k}": v for k, v in counts.items()},
            **{f"taxa_{k}": (v / n if n else None) for k, v in counts.items()},
            "exemplos": json.dumps(examples, ensure_ascii=False)}


def _upsert(rows: list[dict]) -> None:
    if not rows:
        return
    new = pd.DataFrame(rows)
    if storage.table_exists("comment_signals"):
        old = storage.read_sql("SELECT * FROM comment_signals")
        new = pd.concat([old[~old["post_id"].isin(new["post_id"])], new])
    storage.write_table(new, "comment_signals")


def collect_youtube_top(max_per_post: int = 100) -> dict:
    from stone_mpe.collect.youtube import QuotaMeter, fetch_comments
    posts = storage.read_sql("SELECT post_id, comments FROM posts WHERE is_top = 1 AND platform = 'youtube'")
    meter, rows, fails = QuotaMeter(), [], 0
    for r in posts.itertuples():
        if not r.comments:
            continue
        try:
            texts = fetch_comments(r.post_id[3:], meter, max_per_post)
        except Exception as e:  # comentários desativados etc.
            fails += 1
            print(f"[comments] {r.post_id}: {str(e)[:120]}")
            continue
        rows.append(aggregate(r.post_id, texts, "youtube_commentThreads"))
    _upsert(rows)
    return {"posts": len(rows), "falhas": fails, "quota_units": meter.total}


def import_file(path: str | Path) -> dict:
    """Arquivo de comentários do Instagram (rota do kickoff): colunas post_id|shortcode e text|comment."""
    p = Path(path)
    df = pd.read_csv(p) if p.suffix == ".csv" else pd.read_json(p, lines=p.suffix == ".jsonl")
    idc = next(c for c in ("post_id", "shortcode", "shortCode", "postId") if c in df)
    txc = next(c for c in ("text", "comment", "texto") if c in df)
    df["pid"] = df[idc].astype(str).map(lambda s: s if s.startswith("ig_") else f"ig_{s}")
    rows = [aggregate(pid, g[txc].astype(str).tolist(), "instagram_" + p.stem) for pid, g in df.groupby("pid")]
    _upsert(rows)
    return {"posts": len(rows)}


def summary() -> dict:
    if not storage.table_exists("comment_signals"):
        return {}
    df = storage.read_sql("SELECT * FROM comment_signals")
    tot = df["n_sampled"].sum()
    if not tot:
        return {}
    ex: dict[str, list[str]] = {}
    for e in df.sort_values("n_contato", ascending=False)["exemplos"]:
        for k, v in json.loads(e).items():
            ex.setdefault(k, [])
            ex[k] += [x for x in v if len(ex[k]) < 4]
    return {"posts": int(len(df)), "comentarios_analisados": int(tot),
            **{f"taxa_{k}": float(df[f"n_{k}"].sum() / tot) for k in ("contato", "duvida", "objecao", "elogio")},
            "exemplos": ex}
