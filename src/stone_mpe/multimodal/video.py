"""Nível 2 (TAP §6.3): mídia de vídeo das publicações de alto desempenho.

Para cada post do top com vídeo acessível:
- download em baixa resolução (yt-dlp — recomendado no TAP §8 para mídia de vídeos públicos);
- frames: 3 no gancho (0,5 s · 1,5 s · 2,5 s) + 3 distribuídos no restante;
- ritmo de cortes DETERMINÍSTICO: trocas de cena por segundo (filtro `scene` do ffmpeg);
- transcrição PT-BR com faster-whisper (CPU, int8), com o texto dos primeiros 3 s separado.

Tudo é cacheado em data/media/. Falha em qualquer etapa -> o post cai para o Nível 1.
A mídia baixada é usada só para análise e não é redistribuída.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from stone_mpe import config


def _dir(kind: str) -> Path:
    d = config.data_dir() / "media" / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def ffmpeg_bin() -> str | None:
    return shutil.which("ffmpeg")


def download(post_id: str, url: str) -> Path | None:
    dest = _dir("video") / f"{post_id}.mp4"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        import yt_dlp
    except ImportError:
        return None
    opts = {
        "format": "worst[ext=mp4][height>=240]/worst[ext=mp4]/worst",
        "outtmpl": str(dest.with_suffix(".%(ext)s")),
        "quiet": True, "no_warnings": True, "noplaylist": True, "retries": 3,
        "max_filesize": 60 * 1024 * 1024,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:  # yt-dlp levanta várias classes próprias
        print(f"[video] download falhou {post_id}: {str(e)[:150]}")
        return None
    if dest.exists():
        return dest
    found = list(dest.parent.glob(f"{post_id}.*"))
    return found[0] if found else None


def _run(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")


def probe_duration(video: Path) -> float | None:
    ff = ffmpeg_bin()
    if not ff:
        return None
    out = _run([ff, "-hide_banner", "-i", str(video)]).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else None


def frames(post_id: str, video: Path, duration: float | None) -> list[Path]:
    """Frames em JPG (largura 512). Retorna os existentes, em ordem temporal."""
    ff = ffmpeg_bin()
    if not ff:
        return []
    d = _dir("frames") / post_id
    d.mkdir(exist_ok=True)
    dur = duration or 30.0
    times = [0.5, 1.5, 2.5] + [round(dur * f, 2) for f in (0.35, 0.6, 0.85) if dur * f > 3]
    paths = []
    for i, t in enumerate(times):
        p = d / f"f{i:02d}_{t:.1f}s.jpg"
        if not p.exists():
            _run([ff, "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1",
                  "-vf", "scale=512:-2", "-q:v", "4", "-y", str(p)])
        if p.exists() and p.stat().st_size > 0:
            paths.append(p)
    return paths


def cuts_per_second(video: Path, duration: float | None, threshold: float = 0.3) -> float | None:
    ff = ffmpeg_bin()
    if not ff or not duration:
        return None
    out = _run([ff, "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"], timeout=300).stderr
    n = out.count("pts_time:")
    return round(n / duration, 3)


def cut_score_0a10(cps: float | None) -> int | None:
    """Mapeia cortes/segundo para 0–10 (0 = plano único; 10 = ≥ 1 corte/s). Escala declarada no README."""
    if cps is None:
        return None
    return int(min(10, round(cps * 10)))


@lru_cache(maxsize=1)
def _whisper():
    from faster_whisper import WhisperModel
    size = config.get("level2.whisper_model", "small")
    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe(post_id: str, video: Path) -> dict | None:
    cache = _dir("transcripts") / f"{post_id}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        segments, info = _whisper().transcribe(str(video), language="pt", vad_filter=True, beam_size=1)
        segs = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    except Exception as e:
        print(f"[video] transcrição falhou {post_id}: {str(e)[:150]}")
        return None
    result = {
        "text": " ".join(s["text"] for s in segs),
        "first_3s": " ".join(s["text"] for s in segs if s["start"] < 3.0),
        "segments": segs,
        "has_speech": bool(segs),
    }
    cache.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def media_bundle(post: dict) -> dict:
    """Prepara tudo o que o Nível 2 usa. Campos ausentes = etapa indisponível."""
    out: dict = {"frames": [], "transcript": None, "cuts_per_s": None, "modalities": []}
    if post.get("media_type") not in ("reels", "short", "video"):
        return out
    video = download(post["post_id"], post["url"])
    if not video:
        return out
    dur = post.get("duration_s") or probe_duration(video)
    out["frames"] = frames(post["post_id"], video, dur)
    if out["frames"]:
        out["modalities"].append("frames")
    out["cuts_per_s"] = cuts_per_second(video, dur)
    tr = transcribe(post["post_id"], video)
    if tr:
        out["transcript"] = tr
        out["modalities"].append("transcript")
    return out
