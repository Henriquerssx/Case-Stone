"""Indicador indireto de lead (TAP §3): presença/tipo de CTA + comentários com intenção de contato."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

_PATTERNS = [
    r"\bquero\b", r"\bcomo faco\b", r"\bqual (e )?o link\b", r"\bonde (eu )?(compro|acho|encontro)\b",
    r"\bquanto custa\b", r"\bqual o valor\b", r"\bpreco\b", r"\bme (chama|manda)\b", r"\bmanda (o )?link\b",
    r"\bcomo (eu )?(participo|me inscrevo|faco para participar)\b", r"\btem (vaga|inscric)", r"\binteress",
    r"\bpassa (o )?contato\b", r"\bchama no (direct|privado|pv)\b",
]
_RX = re.compile("|".join(_PATTERNS))


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def has_contact_intent(text: str) -> bool:
    return bool(_RX.search(_fold(text or "")))


def comment_intent_rate(comments: list[str]) -> float | None:
    if not comments:
        return None
    return sum(has_contact_intent(c) for c in comments) / len(comments)


def cta_summary(df_top: pd.DataFrame) -> dict:
    if df_top.empty:
        return {}
    return {
        "share_com_cta": float(df_top["tem_cta"].mean()),
        "tipos_cta": df_top.loc[df_top["tem_cta"] == 1, "tipo_cta"].value_counts().to_dict(),
        "share_oferta_explicita": float(df_top["oferta_ou_beneficio_explicito"].mean()),
        # razão comentários/curtidas alta costuma indicar CTA "comenta que eu te mando"
        "mediana_comentarios_por_curtida": float((df_top["comments"] / df_top["likes"].where(df_top["likes"] > 0)).median()),
    }
