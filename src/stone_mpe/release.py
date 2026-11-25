"""Base pública sanitizada (data/release/) e reconstrução do banco local a partir dela.

O repositório é público. Por isso ele NÃO versiona texto de terceiros nem dados brutos:
- ficam de fora legendas, títulos, tags e URLs de miniatura (CDN assinada) dos posts;
- ficam de fora o JSON bruto da resposta do modelo e os exemplos de comentários;
- nenhum dado de comentarista ou seguidor é coletado em nenhuma etapa.

Ficam as métricas públicas agregadas (curtidas, comentários, views, seguidores na data da coleta),
o link de cada post, a categorização pela rubrica e os sinais agregados de comentários. Isso basta
para reproduzir o ranking, os padrões, o playbook e o painel (sem legendas e capas).

Uso: `python -m stone_mpe.cli export-release` (quem tem a base completa) e
`python -m stone_mpe.cli bootstrap` (clone novo).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from stone_mpe import config, storage

POSTS_DROP = ["caption", "title", "tags", "thumbnail_url"]
CATEG_DROP = ["raw_json", "error"]
FILES = {
    "posts": "posts.csv.gz",
    "profiles": "profiles.csv",
    "categorizations": "categorizations.csv.gz",
    "comment_signals": "comment_signals.csv",
}


def release_dir() -> Path:
    return Path(os.environ.get("STONE_MPE_RELEASE", config.root() / "data" / "release"))


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _table(name: str) -> pd.DataFrame:
    try:
        return storage.read_sql(f"SELECT * FROM {name}")  # nome vem de FILES, nunca do usuário
    except Exception:
        return pd.DataFrame()


def export() -> dict:
    out = release_dir()
    out.mkdir(parents=True, exist_ok=True)
    frames = {
        "posts": _table("posts").drop(columns=POSTS_DROP, errors="ignore"),
        "profiles": _table("profiles"),
        "categorizations": _table("categorizations").query("valid == 1").drop(columns=CATEG_DROP, errors="ignore")
        if not _table("categorizations").empty else pd.DataFrame(),
        "comment_signals": _table("comment_signals").drop(columns=["exemplos"], errors="ignore"),
    }
    manifest = {"gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "removido": {"posts": POSTS_DROP, "categorizations": CATEG_DROP, "comment_signals": ["exemplos"]},
                "arquivos": {}}
    for name, df in frames.items():
        if df.empty:
            continue
        p = out / FILES[name]
        df.to_csv(p, index=False, encoding="utf-8")
        manifest["arquivos"][FILES[name]] = {"linhas": int(len(df)), "colunas": list(df.columns), "sha256": _sha256(p)}
    (out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {k: v["linhas"] for k, v in manifest["arquivos"].items()}


def _has_posts() -> bool:
    if not config.db_path().exists():
        return False
    try:
        return int(storage.read_sql("SELECT COUNT(*) AS n FROM posts")["n"].iloc[0]) > 0
    except Exception:
        return False


def restore(force: bool = False) -> dict:
    """Monta db/base.sqlite a partir de data/release/. Não sobrescreve uma base existente sem force."""
    src = release_dir()
    if _has_posts() and not force:
        return {"status": "base local já existe; use --force para recriar a partir de data/release/"}
    manifest = json.loads((src / "MANIFEST.json").read_text(encoding="utf-8"))
    for fname, meta in manifest["arquivos"].items():
        if _sha256(src / fname) != meta["sha256"]:
            raise ValueError(f"{fname}: checksum não confere com MANIFEST.json")
    res = {}
    posts = pd.read_csv(src / FILES["posts"], dtype={"post_id": str, "handle": str, "profile_id": str})
    for c in POSTS_DROP:
        posts[c] = ""
    storage.write_table(posts, "posts")
    res["posts"] = len(posts)
    prof = pd.read_csv(src / FILES["profiles"], dtype={"handle": str, "profile_id": str})
    storage.write_table(prof, "profiles")
    res["profiles"] = len(prof)
    if (src / FILES["comment_signals"]).exists():
        cs = pd.read_csv(src / FILES["comment_signals"], dtype={"post_id": str})
        cs["exemplos"] = "{}"
        storage.write_table(cs, "comment_signals")
        res["comment_signals"] = len(cs)
    if (src / FILES["categorizations"]).exists():
        cat = pd.read_csv(src / FILES["categorizations"], dtype={"post_id": str})
        for c in CATEG_DROP:
            cat[c] = None
        with storage.connect() as conn:
            conn.execute("DELETE FROM categorizations")
            cat.to_sql("categorizations", conn, if_exists="append", index=False)
        res["categorizations"] = len(cat)
    return res


def ensure_db() -> bool:
    """Chamado pelo painel: num clone novo, monta a base pública automaticamente."""
    if _has_posts():
        return False
    if (release_dir() / "MANIFEST.json").exists():
        restore()
        return True
    return False
