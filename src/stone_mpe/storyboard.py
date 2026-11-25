"""Storyboard ilustrado de um criativo: um quadro 9:16 por cena (SVG, sem custo nem API de imagem).

Cada quadro mostra uma ilustração do tipo de plano (rosto, produto, mãos, tela, ambiente, cliente),
o texto na tela como apareceria no vídeo e a fala como legenda. Ao lado, a capa do post real de
referência mais próximo (o vídeo que mais se parece com o que se quer gravar).

`storyboard_html()` gera um arquivo autocontido para levar para a gravação.
"""
from __future__ import annotations

import base64
import html
import re
import textwrap

import pandas as pd

from stone_mpe.agent.schemas import Cena, Creative, guess_plano
from stone_mpe.collect.media import thumb_path

W, H = 270, 480
# identidade Impulso Stone: verde Stone, verde Sherwood, verde claro, névoa e roxo de destaque
BLUE, BLUE_DK, BLUE_LT, BLUE_XL, ORANGE = "#128C4F", "#004132", "#8FD1AA", "#E9F5EE", "#8A63E6"
PLANO_LABEL = {"rosto": "Rosto para a câmera", "produto": "Produto em destaque", "maos": "Mãos / processo",
               "tela": "Tela / número", "ambiente": "Ambiente / bastidores", "cliente": "Cliente / atendimento"}
BG = {"rosto": ("#EEF8F2", "#D3EEDD"), "produto": ("#F6FBE6", "#E6F5BE"), "maos": ("#EAF6F4", "#CBE9E4"),
      "tela": ("#EFF2F1", "#DCE3E1"), "ambiente": ("#F3F7EE", "#DDEBCF"), "cliente": ("#F3EFFC", "#E0D6F8")}

_ILLU = {
    "rosto": f"""<path d="M48 410 Q135 292 222 410 Z" fill="{BLUE}"/><circle cx="135" cy="262" r="50" fill="{BLUE_LT}"/>
        <path d="M95 250 Q135 196 175 250 Q160 226 135 224 Q110 226 95 250 Z" fill="{BLUE_DK}"/>
        <circle cx="232" cy="150" r="6" fill="{ORANGE}"/><text x="216" y="154" font-size="10" text-anchor="end" fill="{BLUE_DK}">REC</text>""",
    "produto": f"""<rect x="28" y="362" width="214" height="12" rx="6" fill="{BLUE_DK}"/>
        <rect x="80" y="296" width="110" height="66" rx="10" fill="{BLUE_LT}"/><rect x="92" y="262" width="86" height="38" rx="8" fill="{BLUE}"/>
        <rect x="133" y="236" width="4" height="26" fill="{BLUE_DK}"/><circle cx="135" cy="232" r="6" fill="{ORANGE}"/>
        <path d="M60 230 l6 -14 l6 14 l-6 14 z M204 250 l5 -11 l5 11 l-5 11 z" fill="{ORANGE}" opacity=".8"/>""",
    "maos": f"""<rect x="44" y="300" width="182" height="84" rx="12" fill="{BLUE_LT}"/>
        <rect x="95" y="318" width="80" height="44" rx="8" fill="{BLUE_XL}" stroke="{BLUE_DK}" stroke-width="3"/>
        <path d="M0 268 Q60 280 92 312 Q100 324 86 330 Q60 318 0 312 Z" fill="{BLUE}"/>
        <path d="M270 268 Q210 280 178 312 Q170 324 184 330 Q210 318 270 312 Z" fill="{BLUE}"/>""",
    "tela": f"""<rect x="78" y="186" width="114" height="212" rx="18" fill="{BLUE_DK}"/><rect x="87" y="202" width="96" height="178" rx="8" fill="#ffffff"/>
        <text x="135" y="232" font-size="18" font-weight="700" text-anchor="middle" fill="{BLUE_DK}">R$</text>
        <rect x="100" y="320" width="16" height="44" rx="3" fill="{BLUE_LT}"/><rect x="127" y="296" width="16" height="68" rx="3" fill="{BLUE}"/>
        <rect x="154" y="270" width="16" height="94" rx="3" fill="{ORANGE}"/>""",
    "ambiente": f"""<rect x="40" y="252" width="190" height="150" fill="#ffffff" stroke="{BLUE_DK}" stroke-width="3"/>
        <path d="M34 252 L236 252 L226 222 L44 222 Z" fill="{BLUE}"/>
        <path d="M44 222 l20 30 l20 -30 l20 30 l20 -30 l20 30 l20 -30 l20 30 l20 -30 l20 30" fill="none" stroke="{BLUE_XL}" stroke-width="5"/>
        <rect x="58" y="282" width="72" height="56" rx="4" fill="{BLUE_LT}"/><rect x="152" y="290" width="54" height="112" rx="4" fill="{BLUE_DK}"/>
        <circle cx="196" cy="350" r="4" fill="{ORANGE}"/>""",
    "cliente": f"""<circle cx="92" cy="262" r="30" fill="{BLUE_LT}"/><path d="M42 400 Q92 300 142 400 Z" fill="{BLUE}"/>
        <circle cx="182" cy="270" r="28" fill="#f3c6a6"/><path d="M134 400 Q182 308 230 400 Z" fill="{ORANGE}"/>
        <rect x="120" y="330" width="34" height="30" rx="4" fill="{BLUE_DK}"/><path d="M128 330 q9 -14 18 0" fill="none" stroke="{BLUE_DK}" stroke-width="3"/>""",
}


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(re.sub(r"\s+", " ", text or "").strip(), width) or []
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        lines[-1] = (last.rsplit(" ", 1)[0] if " " in last and len(last) > width - 2 else last).rstrip(" ,.;:") + "…"
    return lines


def svg_frame(cena: Cena, i: int, uid: str = "") -> str:
    """Quadro 9:16 ilustrado de uma cena."""
    c1, c2 = BG.get(cena.plano, BG["rosto"])
    gid = f"g{uid}{i}"
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" '
             f'aria-label="Cena {i}: {html.escape(PLANO_LABEL.get(cena.plano, cena.plano))}" style="font-family:system-ui,Segoe UI,sans-serif">',
             f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}"/>'
             f'<stop offset="1" stop-color="{c2}"/></linearGradient><clipPath id="c{gid}"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>',
             f'<g clip-path="url(#c{gid})"><rect width="{W}" height="{H}" fill="url(#{gid})"/>',
             _ILLU.get(cena.plano, _ILLU["rosto"])]
    # selo da cena
    badge = f"CENA {i}" + (f" · {cena.tempo}" if cena.tempo else "")
    parts.append(f'<rect x="12" y="12" width="{12 + 7.2 * len(badge):.0f}" height="24" rx="12" fill="#0b0b0b" opacity=".78"/>'
                 f'<text x="22" y="28" font-size="12" font-weight="600" fill="#fff">{html.escape(badge)}</text>')
    # texto na tela (como no vídeo)
    tl = _wrap(cena.texto_tela, 20, 3)
    if tl:
        top, lh = 64, 22
        parts.append(f'<rect x="22" y="{top}" width="226" height="{16 + lh * len(tl)}" rx="10" fill="#ffffff" opacity=".96"/>')
        for k, line in enumerate(tl):
            parts.append(f'<text x="135" y="{top + 26 + k * lh}" font-size="17" font-weight="800" text-anchor="middle" '
                         f'fill="#0b0b0b">{html.escape(line)}</text>')
    # fala como legenda
    fl = _wrap(cena.fala, 36, 3)
    if fl:
        y0 = H - 18 - 17 * len(fl)
        parts.append(f'<rect x="0" y="{y0 - 18}" width="{W}" height="{H - y0 + 18}" fill="#0b0b0b" opacity=".72"/>')
        for k, line in enumerate(fl):
            parts.append(f'<text x="135" y="{y0 + k * 17}" font-size="12.5" text-anchor="middle" fill="#ffffff">{html.escape(line)}</text>')
    parts.append("</g></svg>")
    return "".join(parts)


_TEMPO = re.compile(r"\[?\(?\s*(\d+\s*[-–a]\s*\d+\s*s)\s*\)?\]?", re.I)
_FALA = re.compile(r"fala\s*:\s*['\"“‘](.+?)['\"”’](?=\s|$|[.)\]])", re.I | re.S)
_TELA = re.compile(r"texto(?: na tela)?\s*:\s*['\"“‘](.+?)['\"”’](?=\s|$|[.)\]])", re.I | re.S)


def scenes(cr: Creative) -> list[Cena]:
    """Cenas do criativo; se o modelo não as preencheu, extrai do texto do roteiro."""
    if cr.cenas:
        return cr.cenas
    items = [x.strip() for x in re.split(r"\n+|(?=(?:^|\s)\d+[.)]\s*\[)", cr.roteiro or "") if x and x.strip()]
    out = []
    for it in items:
        it = re.sub(r"^\d+[.)]\s*", "", it)
        m = _TEMPO.search(it)
        fala, tela = _FALA.search(it), _TELA.search(it)
        visual = _TELA.sub("", _FALA.sub("", _TEMPO.sub("", it, count=1)))
        visual = re.sub(r"\[(?:cena|vídeo|video)\s*:?\s*|\]|\(|\)", " ", visual, flags=re.I)
        visual = re.sub(r"^\s*cena\s*\d+\s*:?", " ", visual, flags=re.I)
        fala_txt = fala.group(1).strip() if fala else ""
        if not fala_txt:  # fala entre aspas sem o rótulo "Fala:" (ex.: "... no balcão: 'Quer crescer?'")
            q = re.search(r"['\"“‘]([^'\"“”‘’]{8,})['\"”’]", visual)
            if q:
                fala_txt = q.group(1).strip()
                visual = visual.replace(q.group(0), " ")
        visual = re.sub(r"\s+", " ", visual).strip(" .;:-")
        out.append(Cena(tempo=m.group(1).replace(" ", "") if m else "", plano=guess_plano(visual), visual=visual[:220],
                        fala=fala_txt, texto_tela=tela.group(1).strip() if tela else ""))
    if out and not out[0].texto_tela and cr.gancho:
        out[0].texto_tela = cr.gancho
    return out or [Cena(tempo="0-3s", plano="rosto", fala=cr.gancho, texto_tela=cr.gancho)]


_SAFE_HOSTS = ("www.instagram.com", "instagram.com", "www.youtube.com", "youtube.com", "youtu.be")


def safe_url(url: str) -> str:
    """Aceita só https:// de Instagram/YouTube; qualquer outra coisa vira '#' (evita javascript: no HTML exportado)."""
    from urllib.parse import urlparse
    u = urlparse(str(url or ""))
    return str(url) if u.scheme == "https" and u.hostname in _SAFE_HOSTS else "#"


def thumb_data_uri(post_id: str) -> str | None:
    p = thumb_path(post_id)
    if p.exists() and p.stat().st_size > 0:
        return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()
    return None


def _pct(x) -> str:
    return f"{x * 100:.2f}%".replace(".", ",") if pd.notna(x) else "—"


def _n(x) -> str:
    return f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"


def storyboard_html(cr: Creative, refs: pd.DataFrame | None = None, metas: dict | None = None, followers: int | None = None,
                    nicho: str | None = None) -> str:
    """Documento HTML autocontido: storyboard ilustrado + roteiro + legenda + referências e métricas."""
    cs = scenes(cr)
    frames = "".join(
        f'<figure><div class="frame">{svg_frame(c, i, "x")}</div><figcaption><b>{html.escape(c.tempo or f"cena {i}")}</b> · '
        f'{html.escape(PLANO_LABEL.get(c.plano, c.plano))}<br>{html.escape(c.visual)}'
        + (f'<br><i>“{html.escape(c.fala)}”</i>' if c.fala else "") + "</figcaption></figure>"
        for i, c in enumerate(cs, 1))
    ref_html = ""
    if refs is not None and not refs.empty:
        cards = []
        for r in refs.itertuples():
            img = thumb_data_uri(r.post_id)
            pic = f'<img src="{img}" alt="capa do post de @{html.escape(r.handle)}">' if img else '<div class="noimg">sem capa</div>'
            cards.append(f'<a class="ref" href="{html.escape(safe_url(r.url))}" target="_blank" rel="noopener">{pic}<div><b>@{html.escape(r.handle)}</b><br>'
                         f'{_n(r.views)} views · {_n(r.likes)} curtidas · {_n(r.comments)} coment.<br>'
                         f'{_n(r.followers)} seguidores · engajamento <b>{_pct(r.engagement_rate)}</b></div></a>')
        ref_html = f'<h2>Vídeos reais de referência (os mais próximos do roteiro)</h2><div class="refs">{"".join(cards)}</div>'
    metas_html = ""
    if metas:
        metas_html = (f'<h2>Metas para um perfil com {_n(followers)} seguidores{f" · nicho {html.escape(nicho)}" if nicho else ""}</h2>'
                      f'<div class="kpis"><div><span>{_n(metas.get("mediana_da_base"))}</span>mediana da base</div>'
                      f'<div><span>{_n(metas.get("entrar_no_top"))}</span>para entrar no top 10%</div>'
                      f'<div><span>{_n(metas.get("mediana_do_top"))}</span>mediana do top</div></div>'
                      '<p class="muted">Curtidas + comentários. São referências observadas em publicações reais, não previsões.</p>')
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(cr.titulo or "Storyboard")}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700&family=Outfit:wght@600;700&display=swap"><style>
:root{{--ink:#03211D;--muted:#4A615B;--line:#DCE3E1;--bg:#FFFFFF;--card:#EFF2F1;--accent:#004132;--lime:#C7F93C}}
@media (prefers-color-scheme:dark){{:root{{--ink:#EFEFEF;--muted:#A9BDB7;--line:#0E4A40;--bg:#03211D;--card:#06352E;--accent:#C7F93C}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 Manrope,system-ui,Segoe UI,sans-serif}}
h1,h2{{font-family:Outfit,Manrope,system-ui,sans-serif}}
.brandbar{{background:#004132;color:#fff;border-radius:16px;padding:14px 18px;margin-bottom:18px}}
.brandbar b{{color:var(--lime);letter-spacing:.12em;font-size:.75rem}}
main{{max-width:1100px;margin:0 auto;padding:24px 16px 48px}} h1{{font-size:1.7rem;margin:.2rem 0}} h2{{font-size:1.15rem;margin:2rem 0 .8rem}}
.hook{{font-size:1.25rem;font-weight:700;margin:.6rem 0 1rem}} .muted{{color:var(--muted);font-size:.9rem}}
.board{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}}
figure{{margin:0}} .frame{{border-radius:18px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.15)}}
figcaption{{font-size:.85rem;color:var(--muted);margin-top:8px}}
pre{{white-space:pre-wrap;background:var(--card);padding:14px;border-radius:10px;border:1px solid var(--line);font:inherit}}
.refs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.ref{{display:flex;gap:10px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:12px;color:inherit;text-decoration:none;font-size:.85rem}}
.ref img,.noimg{{width:72px;height:72px;object-fit:cover;border-radius:8px;background:var(--card);flex:none}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
.kpis div{{border:1px solid var(--line);border-radius:12px;padding:12px;color:var(--muted);font-size:.85rem}}
.kpis span{{display:block;font-size:1.6rem;font-weight:700;color:var(--ink)}}
</style></head><body><main>
<div class="brandbar"><b>IMPULSO STONE · STORYBOARD</b><br>{html.escape(cr.formato)}</div><h1>{html.escape(cr.titulo)}</h1>
<div class="hook">0–3 s: “{html.escape(cr.gancho)}”</div>
<h2>Storyboard</h2><div class="board">{frames}</div>
<h2>Legenda</h2><pre>{html.escape(cr.legenda)}</pre><p><b>CTA:</b> {html.escape(cr.cta)}</p>
{f'<h2>Por que assim</h2><p>{html.escape(cr.justificativa)}</p>' if cr.justificativa else ''}
{ref_html}{metas_html}
<p class="muted">Padrões observados em publicações reais de alto desempenho; não garantem resultado.</p>
</main></body></html>"""
