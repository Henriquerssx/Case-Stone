"""Coleta de YouTube Shorts pela YouTube Data API v3 (rota oficial).

Custo de cota por canal (TAP §5 recomenda playlist em vez de search):
  channels.list       1 unidade  (inscritos + playlist de uploads)
  playlistItems.list  1 unidade por página de 50
  videos.list         1 unidade por lote de 50
Um canal com 300 uploads custa ~1 + 6 + 6 = 13 unidades. `search.list` (100) nunca é usado.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Iterable

import requests

from stone_mpe import config
from stone_mpe.collect.http import fetch_json
from stone_mpe.collect.schema import RawPost

API = "https://www.googleapis.com/youtube/v3"
COST = {"channels": 1, "playlistItems": 1, "videos": 1, "commentThreads": 1}


class QuotaMeter:
    def __init__(self) -> None:
        self.units: Counter[str] = Counter()

    def add(self, endpoint: str, from_cache: bool) -> None:
        if not from_cache:
            self.units[endpoint] += COST[endpoint]

    @property
    def total(self) -> int:
        return sum(self.units.values())


def _api(endpoint: str, params: dict, meter: QuotaMeter) -> dict:
    key = config.env("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY ausente no .env")
    # chave no cabeçalho (não na URL): mensagens de erro de rede trazem a URL completa
    res = fetch_json("GET", f"{API}/{endpoint}", params=params, headers={"X-Goog-Api-Key": key}, namespace="youtube")
    meter.add(endpoint, res.from_cache)
    return res.data


_DUR = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(iso: str | None) -> float | None:
    if not iso:
        return None
    m = _DUR.fullmatch(iso)
    if not m:
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return float(d * 86400 + h * 3600 + mi * 60 + s)


def resolve_channel(handle_or_id: str, meter: QuotaMeter) -> dict:
    h = handle_or_id.strip()
    params = {"part": "snippet,statistics,contentDetails"}
    if h.startswith("UC") and len(h) == 24:
        params["id"] = h
    else:
        params["forHandle"] = h if h.startswith("@") else f"@{h}"
    items = _api("channels", params, meter).get("items", [])
    if not items:
        raise LookupError(f"canal não encontrado: {handle_or_id}")
    c = items[0]
    stats = c.get("statistics", {})
    return {
        "channel_id": c["id"],
        "title": c["snippet"]["title"],
        "custom_url": c["snippet"].get("customUrl", ""),
        "subscribers": None if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0)),
        "uploads_playlist": c["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def list_upload_ids(playlist_id: str, max_items: int, meter: QuotaMeter) -> list[str]:
    ids: list[str] = []
    token = None
    while len(ids) < max_items:
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = _api("playlistItems", params, meter)
        ids += [it["contentDetails"]["videoId"] for it in data.get("items", [])]
        token = data.get("nextPageToken")
        if not token:
            break
    return ids[:max_items]


def get_videos(ids: list[str], meter: QuotaMeter) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(ids), 50):
        batch = ids[i : i + 50]
        data = _api("videos", {"part": "snippet,contentDetails,statistics", "id": ",".join(batch)}, meter)
        out += data.get("items", [])
    return out


def is_short_url(video_id: str) -> bool | None:
    """Confirma Short: youtube.com/shorts/{id} responde 200 para Shorts e redireciona para os demais."""
    try:
        r = requests.head(f"https://www.youtube.com/shorts/{video_id}", allow_redirects=False, timeout=15)
        return r.status_code == 200
    except requests.RequestException:
        return None


def _thumb(snippet: dict) -> str | None:
    th = snippet.get("thumbnails", {})
    for k in ("maxres", "standard", "high", "medium", "default"):
        if k in th:
            return th[k]["url"]
    return None


def to_raw(video: dict, handle: str, subscribers: int | None, collected_at: datetime) -> RawPost:
    sn, st, cd = video["snippet"], video.get("statistics", {}), video.get("contentDetails", {})
    dur = parse_duration(cd.get("duration"))
    max_short = config.get("collection.youtube.shorts_max_duration_s", 180)
    is_short = dur is not None and dur <= max_short
    vid = video["id"]
    return RawPost(
        post_id=f"yt_{vid}",
        platform="youtube",
        handle=handle,
        url=f"https://www.youtube.com/shorts/{vid}" if is_short else f"https://www.youtube.com/watch?v={vid}",
        media_type="short" if is_short else "video",
        posted_at=sn["publishedAt"],
        collected_at=collected_at,
        caption=(sn.get("title", "") + "\n\n" + sn.get("description", "")).strip(),
        title=sn.get("title"),
        tags=sn.get("tags", []),
        likes=st.get("likeCount"),       # ausente quando o canal oculta curtidas
        comments=st.get("commentCount"),  # ausente quando comentários estão desativados
        views=st.get("viewCount"),
        duration_s=dur,
        thumbnail_url=_thumb(sn),
        followers=subscribers,
        source_route="youtube_data_api_v3",
    )


def collect_channel(handle_or_id: str, meter: QuotaMeter) -> list[RawPost]:
    ch = resolve_channel(handle_or_id, meter)
    handle = handle_or_id.strip().lstrip("@").lower()  # mesmo identificador do profiles.csv
    ids = list_upload_ids(ch["uploads_playlist"], config.get("collection.youtube.max_videos_per_channel", 300), meter)
    now = datetime.now(timezone.utc)
    posts = [to_raw(v, handle, ch["subscribers"], now) for v in get_videos(ids, meter)]
    if config.get("collection.youtube.verify_shorts_url", False):
        for p in posts:
            if p.media_type == "short" and is_short_url(p.post_id[3:]) is False:
                p.media_type = "video"
                p.url = f"https://www.youtube.com/watch?v={p.post_id[3:]}"
    if config.get("collection.youtube.only_shorts", True):
        posts = [p for p in posts if p.media_type == "short"]
    return posts


def collect_many(handles: Iterable[str]) -> tuple[int, QuotaMeter, list[str]]:
    """Coleta canais e grava data/raw/youtube/<handle>.jsonl (checkpoint por canal)."""
    meter = QuotaMeter()
    total, failures = 0, []
    outdir = config.raw_dir("youtube")
    for h in handles:
        try:
            posts = collect_channel(h, meter)
        except Exception as e:  # registra e segue: um canal ruim não derruba a coleta
            failures.append(f"{h}: {e}")
            print(f"[youtube] FALHA {h}: {e}")
            continue
        fname = outdir / f"{h.lstrip('@').lower()}.jsonl"
        with open(fname, "w", encoding="utf-8") as f:
            for p in posts:
                f.write(p.model_dump_json() + "\n")
        total += len(posts)
        print(f"[youtube] {h}: {len(posts)} shorts · cota acumulada {meter.total} unidades")
    _log_quota(meter)
    return total, meter, failures


def fetch_comments(video_id: str, meter: QuotaMeter, max_results: int = 100) -> list[str]:
    """Textos de comentários (sem autor — minimização de dados pessoais). 1 unidade por chamada."""
    data = _api(
        "commentThreads",
        {"part": "snippet", "videoId": video_id, "maxResults": min(max_results, 100), "textFormat": "plainText"},
        meter,
    )
    return [it["snippet"]["topLevelComment"]["snippet"]["textDisplay"] for it in data.get("items", [])]


def _log_quota(meter: QuotaMeter) -> None:
    with open(config.outputs_dir() / "youtube_quota.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "units": dict(meter.units), "total": meter.total}) + "\n")
