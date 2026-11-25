"""Importador de dados do Instagram exportados pela rota definida no kickoff.

Este módulo NÃO faz scraping (fora do escopo, TAP §4.3). Ele recebe o arquivo
(CSV, JSON ou JSONL) produzido pela rota oficial do case e o converte para o
schema único `RawPost`, validando cada registro.

Colunas aceitas (com aliases comuns de exportadores):
  post_id/shortcode/shortCode/code, handle/ownerUsername/username/owner,
  url/permalink, media_type/type/productType, posted_at/timestamp/taken_at/date,
  caption/text, likes/likesCount/like_count, comments/commentsCount/comment_count,
  views/videoViewCount/videoPlayCount/play_count/view_count,
  duration_s/videoDuration/video_duration, thumbnail_url/displayUrl/thumbnail_src,
  followers/followersCount/follower_count
Se `followers` não vier no arquivo, é lido de config/profiles.csv (coluna followers).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from stone_mpe import config
from stone_mpe.collect.schema import RawPost

ALIASES: dict[str, list[str]] = {
    "post_id": ["post_id", "shortcode", "shortCode", "code", "id"],
    "handle": ["handle", "ownerUsername", "username", "owner", "owner_username"],
    "url": ["url", "permalink", "link"],
    "media_type": ["media_type", "type", "productType", "typename", "media"],
    "posted_at": ["posted_at", "timestamp", "taken_at", "date", "date_utc"],
    "caption": ["caption", "text", "description"],
    "likes": ["likes", "likesCount", "like_count"],
    "comments": ["comments", "commentsCount", "comment_count"],
    "views": ["views", "videoViewCount", "videoPlayCount", "play_count", "view_count", "video_view_count"],
    "duration_s": ["duration_s", "videoDuration", "video_duration"],
    "thumbnail_url": ["thumbnail_url", "displayUrl", "thumbnail_src", "display_url", "thumbnailUrl"],
    "followers": ["followers", "followersCount", "follower_count", "owner_followers"],
}

MEDIA_MAP = {
    "reels": "reels", "reel": "reels", "clips": "reels", "video": "reels", "graphvideo": "reels", "igtv": "reels",
    "carrossel": "carrossel", "carousel": "carrossel", "sidecar": "carrossel", "graphsidecar": "carrossel",
    "carousel_album": "carrossel",
    "imagem": "imagem", "image": "imagem", "photo": "imagem", "graphimage": "imagem", "feed": "imagem",
}


_CODE_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")

def _read(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".jsonl":
        return pd.read_json(path, lines=True)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return pd.json_normalize(data if isinstance(data, list) else data.get("items", data.get("data", [])))


def _pick(row: dict, field: str):
    for alias in ALIASES[field]:
        v = row.get(alias)
        if v is not None and not (isinstance(v, float) and pd.isna(v)):
            return v
    return None


def _followers_from_profiles() -> dict[str, int]:
    p = config.path("config", "profiles.csv")
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    if "followers" not in df:
        return {}
    df = df[(df.platform == "instagram") & df.followers.notna()]
    return {str(h).lstrip("@").lower(): int(f) for h, f in zip(df.handle, df.followers)}


def _to_dt(v) -> datetime:
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=timezone.utc)
    return pd.to_datetime(v, utc=True).to_pydatetime()


def import_file(path: str | Path, route_name: str, collected_at: str | None = None,
                only_handles: list[str] | None = None) -> tuple[int, list[str]]:
    """Converte um export da rota do kickoff em data/raw/instagram/<arquivo>.jsonl.

    `collected_at`: data da coleta (ISO). Se o export não trouxer, é obrigatório informar.
    """
    path = Path(path)
    df = _read(path)
    fallback_followers = _followers_from_profiles()
    errors: list[str] = []
    out: list[RawPost] = []
    skipped_other = 0
    keep = {h.lower() for h in only_handles} if only_handles else None
    for i, row in enumerate(df.to_dict(orient="records")):
        if row.get("error") and not (isinstance(row.get("error"), float) and pd.isna(row.get("error"))):
            errors.append(f"linha {i}: {row.get('error')} ({row.get('username') or row.get('inputUrl') or '?'}) — {row.get('errorDescription', '')}")
            continue
        if keep is not None and str(_pick(row, "handle") or "").lstrip("@").lower() not in keep:
            skipped_other += 1  # post de colaboração cujo dono não é um perfil da base
            continue
        try:
            handle = str(_pick(row, "handle") or "").lstrip("@").lower()
            code = str(_pick(row, "post_id"))
            if not _CODE_RE.fullmatch(code):  # vira nome de arquivo (capa): nada de ../ ou separadores
                raise ValueError(f"código de post inválido: {code[:40]!r}")
            url_in = str(_pick(row, "url") or "")
            if url_in and not url_in.startswith("https://www.instagram.com/"):
                url_in = ""
            mt_raw = str(_pick(row, "media_type") or "").replace("_", "").lower()
            media_type = MEDIA_MAP.get(mt_raw, MEDIA_MAP.get(str(_pick(row, "media_type") or "").lower(), "imagem"))
            if _pick(row, "posted_at") is None:
                raise ValueError("data de publicação ausente")
            col = row.get("collected_at") or collected_at
            if not col:
                raise ValueError("collected_at ausente: informe --collected-at")
            followers = _pick(row, "followers")
            if followers is None:
                followers = fallback_followers.get(handle)
            out.append(
                RawPost(
                    post_id=code if code.startswith("ig_") else f"ig_{code}",
                    platform="instagram",
                    handle=handle,
                    url=url_in or f"https://www.instagram.com/p/{code.removeprefix('ig_')}/",
                    media_type=media_type,
                    posted_at=_to_dt(_pick(row, "posted_at")),
                    collected_at=_to_dt(col),
                    caption=str(_pick(row, "caption") or ""),
                    likes=_pick(row, "likes"),
                    comments=_pick(row, "comments"),
                    views=_pick(row, "views"),
                    duration_s=_pick(row, "duration_s"),
                    thumbnail_url=_pick(row, "thumbnail_url"),
                    followers=followers,
                    source_route=route_name,
                )
            )
        except (ValidationError, ValueError, TypeError) as e:
            errors.append(f"linha {i}: {e}")
    if skipped_other:
        errors.append(f"{skipped_other} posts ignorados: dono fora da lista de perfis (colaborações)")
    dest = config.raw_dir("instagram") / f"{path.stem}.jsonl"
    with open(dest, "w", encoding="utf-8") as f:
        for p in out:
            f.write(p.model_dump_json() + "\n")
    return len(out), errors
