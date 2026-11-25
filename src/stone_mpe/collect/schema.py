"""Schema único de registro bruto (Instagram + YouTube). Validado por Pydantic na entrada."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MediaType = Literal["reels", "carrossel", "imagem", "short", "video"]


class RawPost(BaseModel):
    post_id: str                      # "ig_<shortcode>" | "yt_<videoId>"
    platform: Literal["instagram", "youtube"]
    handle: str
    url: str
    media_type: MediaType
    posted_at: datetime
    collected_at: datetime
    caption: str = ""
    title: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    likes: Optional[int] = None       # None = oculto/indisponível
    comments: Optional[int] = None    # None = desativado/indisponível
    views: Optional[int] = None
    duration_s: Optional[float] = None
    thumbnail_url: Optional[str] = None
    followers: Optional[int] = None   # seguidores/inscritos NA DATA DE COLETA
    source_route: str                 # ex.: "youtube_data_api_v3", rota do kickoff

    @field_validator("handle")
    @classmethod
    def _strip_at(cls, v: str) -> str:
        return v.strip().lstrip("@").lower()

    @field_validator("posted_at", "collected_at")
    @classmethod
    def _tz(cls, v: datetime) -> datetime:
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)

    @field_validator("likes", "comments", "views", "followers", mode="before")
    @classmethod
    def _neg_is_hidden(cls, v):
        if v is None or v == "":
            return None
        try:
            v = int(float(v))
        except (TypeError, ValueError):
            return None
        return None if v < 0 else v
