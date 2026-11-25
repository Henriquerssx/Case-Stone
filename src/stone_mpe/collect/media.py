"""Download de thumbnails (Nível 1) com cache em disco. Mídia baixada não é redistribuída."""
from __future__ import annotations

from pathlib import Path

from stone_mpe import config
from stone_mpe.collect.http import HttpError, fetch_bytes


def thumb_path(post_id: str) -> Path:
    d = config.data_dir() / "media" / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{post_id}.jpg"


def get_thumbnail(post_id: str, url: str | None) -> bytes | None:
    """Retorna bytes da thumbnail ou None (URL ausente/expirada — cai para só legenda)."""
    p = thumb_path(post_id)
    if p.exists() and p.stat().st_size > 0:
        return p.read_bytes()
    if not url:
        return None
    try:
        data = fetch_bytes(url)
    except HttpError:
        return None
    p.write_bytes(data)
    return data
