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
# mundo do painel (Clube dos Sonhos): tinta, verde-água e névoa; verde-limão só como acento de destaque
INK, INK_SOFT, DEEP, WALL, TEAL, TEAL_LT, MIST, LIME = ("#03211D", "#06352E", "#055046", "#0B4A40", "#32ADA1", "#7FCFC5",
                                                       "#E6EAE9", "#C7F93C")
SKIN, SKIN_SH, SKIN2, SKIN2_SH = "#E2B08C", "#C68B66", "#9C6444", "#7A4A30"
HAIR, HAIR2, MOUTH, BLUSH = "#1B2622", "#3B2A20", "#5A1F24", "#E07A6B"
PLANO_LABEL = {"rosto": "Rosto para a câmera", "produto": "Produto em destaque", "maos": "Mãos / processo",
               "tela": "Tela / número", "ambiente": "Ambiente / bastidores", "cliente": "Cliente / atendimento"}
PLANO_CHIP = {"rosto": "CLOSE", "produto": "DETALHE", "maos": "PROCESSO", "tela": "TELA", "ambiente": "AMBIENTE",
              "cliente": "ATENDIMENTO"}
BG = {"rosto": ("#0B4A40", "#06352E"), "produto": ("#06352E", "#03211D"), "maos": ("#0B4A40", "#055046"),
      "tela": ("#055046", "#03211D"), "ambiente": ("#0E5A4E", "#06352E"), "cliente": ("#0B4A40", "#06352E")}


def _star(cx: float, cy: float, r: float, fill: str, op: float = 1) -> str:
    """Estrela de quatro pontas (motivo do Clube dos Sonhos)."""
    k = r * 0.22
    return (f'<path d="M{cx} {cy - r} Q{cx + k} {cy - k} {cx + r} {cy} Q{cx + k} {cy + k} {cx} {cy + r} '
            f'Q{cx - k} {cy + k} {cx - r} {cy} Q{cx - k} {cy - k} {cx} {cy - r} Z" fill="{fill}" opacity="{op}"/>')


def _person(cx: float, cy: float, r: float, skin: str, sh: str, hair: str, shirt: str, apron: str | None = None,
            long_hair: bool = False, bottom: float = 500) -> str:
    """Busto frontal simples: cabelo, rosto com expressão, pescoço, camisa e avental opcional."""
    f = lambda v: f"{v:.1f}"  # noqa: E731
    out = []
    if long_hair:
        out.append(f'<path d="M{f(cx - 1.12 * r)} {f(cy - .2 * r)} Q{f(cx - 1.35 * r)} {f(cy + 1.3 * r)} {f(cx - .85 * r)} {f(cy + 1.55 * r)} '
                   f'L{f(cx + .85 * r)} {f(cy + 1.55 * r)} Q{f(cx + 1.35 * r)} {f(cy + 1.3 * r)} {f(cx + 1.12 * r)} {f(cy - .2 * r)} Z" fill="{hair}"/>')
    out.append(f'<path d="M{f(cx - 2.15 * r)} {bottom} L{f(cx - 2.15 * r)} {f(cy + 2.5 * r)} Q{f(cx - 2.05 * r)} {f(cy + 1.5 * r)} '
               f'{f(cx - .9 * r)} {f(cy + 1.38 * r)} L{f(cx + .9 * r)} {f(cy + 1.38 * r)} Q{f(cx + 2.05 * r)} {f(cy + 1.5 * r)} '
               f'{f(cx + 2.15 * r)} {f(cy + 2.5 * r)} L{f(cx + 2.15 * r)} {bottom} Z" fill="{shirt}"/>')
    out.append(f'<rect x="{f(cx - .3 * r)}" y="{f(cy + .55 * r)}" width="{f(.6 * r)}" height="{f(.95 * r)}" fill="{sh}"/>')
    out.append(f'<path d="M{f(cx - .46 * r)} {f(cy + 1.38 * r)} L{f(cx)} {f(cy + 1.9 * r)} L{f(cx + .46 * r)} {f(cy + 1.38 * r)} Z" fill="{sh}"/>')
    if apron:
        out.append(f'<path d="M{f(cx - 1.02 * r)} {f(cy + 2.05 * r)} L{f(cx + 1.02 * r)} {f(cy + 2.05 * r)} L{f(cx + 1.2 * r)} {bottom} '
                   f'L{f(cx - 1.2 * r)} {bottom} Z" fill="{apron}"/>'
                   f'<path d="M{f(cx - .9 * r)} {f(cy + 2.05 * r)} L{f(cx - .62 * r)} {f(cy + 1.4 * r)} M{f(cx + .9 * r)} {f(cy + 2.05 * r)} '
                   f'L{f(cx + .62 * r)} {f(cy + 1.4 * r)}" stroke="{apron}" stroke-width="{f(.16 * r)}" stroke-linecap="round"/>'
                   f'<rect x="{f(cx - .45 * r)}" y="{f(cy + 2.6 * r)}" width="{f(.9 * r)}" height="{f(.55 * r)}" rx="{f(.12 * r)}" '
                   f'fill="none" stroke="{INK}" stroke-opacity=".35" stroke-width="2"/>')
    out.append(f'<ellipse cx="{f(cx - .98 * r)}" cy="{f(cy + .08 * r)}" rx="{f(.17 * r)}" ry="{f(.25 * r)}" fill="{sh}"/>'
               f'<ellipse cx="{f(cx + .98 * r)}" cy="{f(cy + .08 * r)}" rx="{f(.17 * r)}" ry="{f(.25 * r)}" fill="{sh}"/>')
    out.append(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(r)}" ry="{f(1.12 * r)}" fill="{skin}"/>')
    out.append(f'<path d="M{f(cx - 1.03 * r)} {f(cy + .02 * r)} Q{f(cx - 1.08 * r)} {f(cy - 1.28 * r)} {f(cx)} {f(cy - 1.22 * r)} '
               f'Q{f(cx + 1.08 * r)} {f(cy - 1.28 * r)} {f(cx + 1.03 * r)} {f(cy + .02 * r)} Q{f(cx + .92 * r)} {f(cy - .58 * r)} '
               f'{f(cx + .34 * r)} {f(cy - .62 * r)} Q{f(cx - .3 * r)} {f(cy - .46 * r)} {f(cx - .86 * r)} {f(cy - .18 * r)} Z" fill="{hair}"/>')
    for s in (-1, 1):
        out.append(f'<ellipse cx="{f(cx + s * .36 * r)}" cy="{f(cy + .06 * r)}" rx="{f(.085 * r)}" ry="{f(.12 * r)}" fill="{INK}"/>'
                   f'<path d="M{f(cx + s * .5 * r)} {f(cy - .2 * r)} L{f(cx + s * .22 * r)} {f(cy - .24 * r)}" stroke="{hair}" '
                   f'stroke-width="{f(.07 * r)}" stroke-linecap="round"/>'
                   f'<circle cx="{f(cx + s * .56 * r)}" cy="{f(cy + .38 * r)}" r="{f(.15 * r)}" fill="{BLUSH}" opacity=".28"/>')
    out.append(f'<path d="M{f(cx)} {f(cy + .12 * r)} q{f(-.1 * r)} {f(.22 * r)} {f(.05 * r)} {f(.26 * r)}" stroke="{sh}" '
               f'stroke-width="{f(.06 * r)}" fill="none" stroke-linecap="round"/>')
    out.append(f'<path d="M{f(cx - .3 * r)} {f(cy + .5 * r)} Q{f(cx)} {f(cy + .84 * r)} {f(cx + .3 * r)} {f(cy + .5 * r)} Z" fill="{MOUTH}"/>'
               f'<path d="M{f(cx - .2 * r)} {f(cy + .53 * r)} L{f(cx + .2 * r)} {f(cy + .53 * r)}" stroke="#fff" stroke-width="{f(.08 * r)}" '
               f'stroke-linecap="round" opacity=".9"/>')
    return "".join(out)


def _shelves(y0: int = 160) -> str:
    """Prateleiras desfocadas ao fundo: o negócio aparece atrás de quem fala."""
    out = []
    for k, y in enumerate((y0, y0 + 62)):
        out.append(f'<rect x="-4" y="{y + 40}" width="{W + 8}" height="6" rx="3" fill="{INK}" opacity=".45"/>')
        for j in range(7):
            x = 10 + j * 38 + (k * 14)
            h = 18 + (j * 7 + k * 5) % 20
            col = (TEAL_LT, MIST, TEAL)[(j + k) % 3]
            out.append(f'<rect x="{x}" y="{y + 40 - h}" width="22" height="{h}" rx="4" fill="{col}" opacity=".22"/>')
    return "".join(out)


def _bokeh(seed: int) -> str:
    out = []
    for j in range(7):
        x = (seed * 37 + j * 53) % W
        y = 150 + (seed * 19 + j * 71) % 240
        r = 10 + (j * 13 + seed) % 22
        out.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{(TEAL_LT, MIST, LIME)[j % 3]}" opacity="{.05 + (j % 3) * .025:.3f}"/>')
    return "".join(out)


def _ill_rosto(gid: str) -> str:
    return (f'<circle cx="214" cy="190" r="86" fill="url(#l{gid})"/>' + _shelves(150) +
            _person(135, 262, 44, SKIN, SKIN_SH, HAIR, MIST, apron=TEAL, long_hair=True))


def _ill_produto(gid: str) -> str:
    return (f'<path d="M108 0 L162 0 L238 372 L32 372 Z" fill="url(#l{gid})"/>'
            f'<rect x="-4" y="366" width="{W + 8}" height="130" fill="{INK}" opacity=".55"/>'
            f'<rect x="-4" y="362" width="{W + 8}" height="6" fill="{TEAL}" opacity=".55"/>'
            '<ellipse cx="135" cy="370" rx="96" ry="10" fill="#000" opacity=".28"/>'
            # caixa de presente/embalagem com fita e etiqueta de preço
            f'<rect x="76" y="270" width="118" height="98" rx="6" fill="{TEAL_LT}"/>'
            f'<rect x="76" y="270" width="118" height="22" fill="{TEAL}" opacity=".35"/>'
            f'<rect x="66" y="250" width="138" height="28" rx="5" fill="{TEAL}"/>'
            f'<rect x="127" y="250" width="16" height="118" fill="{MIST}"/>'
            f'<path d="M135 250 C112 224 96 240 110 250 Z M135 250 C158 224 174 240 160 250 Z" fill="{MIST}"/>'
            f'<circle cx="135" cy="249" r="6" fill="{LIME}"/>'
            f'<path d="M194 300 L212 318" stroke="{MIST}" stroke-width="2"/>'
            f'<g transform="rotate(18 222 330)"><rect x="204" y="316" width="42" height="26" rx="5" fill="{LIME}"/>'
            f'<circle cx="210" cy="329" r="3" fill="{INK}"/><text x="230" y="334" font-size="11" font-weight="800" '
            f'text-anchor="middle" fill="{INK}">R$</text></g>'
            + _star(58, 226, 13, LIME, .9) + _star(214, 232, 9, LIME, .7) + _star(196, 186, 6, MIST, .6) + _star(78, 300, 6, MIST, .5))


def _hand(x: float, y: float, rot: float, skin: str, sh: str, mirror: bool = False) -> str:
    sx = -1 if mirror else 1
    fingers = "".join(f'<rect x="{-17 + k * 9.5:.1f}" y="-44" width="9" height="{30 - abs(k - 1.5) * 4:.1f}" rx="4.5" fill="{skin}"/>'
                      for k in range(4))
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({sx} 1)">{fingers}'
            f'<rect x="-19" y="-24" width="42" height="40" rx="15" fill="{skin}"/>'
            f'<ellipse cx="25" cy="-4" rx="7" ry="15" transform="rotate(-28 25 -4)" fill="{sh}"/></g>')


def _ill_maos(gid: str) -> str:
    grain = "".join(f'<path d="M-4 {y} Q135 {y + 8} 274 {y}" stroke="{MIST}" stroke-opacity=".06" stroke-width="2" fill="none"/>'
                    for y in range(300, 480, 22))
    return (f'<rect x="-4" y="286" width="{W + 8}" height="200" fill="{INK_SOFT}"/>{grain}'
            f'<rect x="-4" y="284" width="{W + 8}" height="4" fill="{TEAL}" opacity=".45"/>'
            '<ellipse cx="135" cy="372" rx="84" ry="10" fill="#000" opacity=".25"/>'
            # embalagem sendo fechada: fita e selo
            f'<rect x="78" y="296" width="114" height="76" rx="7" fill="{TEAL_LT}"/>'
            f'<path d="M78 296 L135 318 L192 296" fill="none" stroke="{TEAL}" stroke-width="3" stroke-linejoin="round"/>'
            f'<rect x="78" y="328" width="114" height="12" fill="{MIST}" opacity=".85"/>'
            f'<circle cx="135" cy="334" r="10" fill="{LIME}"/>' + _star(135, 334, 6, INK, .85) +
            f'<path d="M-10 486 L50 392 L84 416 L22 496 Z" fill="{TEAL}"/><path d="M280 486 L220 392 L186 416 L248 496 Z" fill="{TEAL}"/>'
            f'<rect x="42" y="386" width="40" height="12" rx="5" transform="rotate(36 62 392)" fill="{MIST}"/>'
            f'<rect x="188" y="386" width="40" height="12" rx="5" transform="rotate(-36 208 392)" fill="{MIST}"/>'
            + _hand(80, 372, -38, SKIN, SKIN_SH) + _hand(190, 372, 38, SKIN, SKIN_SH, mirror=True) +
            f'<path d="M58 270 q-12 -14 0 -28 M212 270 q12 -14 0 -28" stroke="{MIST}" stroke-opacity=".55" stroke-width="3" '
            'fill="none" stroke-linecap="round"/>')


def _ill_tela(gid: str) -> str:
    bars = "".join(f'<rect x="{99 + k * 15}" y="{338 - h}" width="10" height="{h}" rx="3" fill="{TEAL if k == 4 else TEAL_LT}"/>'
                   for k, h in enumerate((26, 40, 34, 56, 84)))
    return (_bokeh(3) +
            f'<path d="M188 262 Q214 268 214 300 L214 372 Q214 410 186 424 L150 430 L150 262 Z" fill="{SKIN2}"/>'
            f'<rect x="80" y="170" width="110" height="222" rx="18" fill="{INK}" stroke="#1E4A42" stroke-width="3"/>'
            f'<rect x="88" y="184" width="94" height="194" rx="10" fill="{MIST}"/>'
            f'<rect x="120" y="176" width="30" height="5" rx="2.5" fill="#1E4A42"/>'
            f'<text x="96" y="203" font-size="8.5" font-weight="700" letter-spacing=".08em" fill="{DEEP}">VENDAS DO MÊS</text>'
            f'<text x="96" y="225" font-size="14.5" font-weight="800" fill="{INK}">R$ 12,4 mil</text>'
            f'<rect x="96" y="234" width="40" height="16" rx="8" fill="{INK}"/>'
            f'<text x="116" y="246" font-size="10" font-weight="800" text-anchor="middle" fill="{LIME}">+32%</text>'
            f'<path d="M96 338 L176 338" stroke="{DEEP}" stroke-opacity=".3"/>{bars}'
            f'<path d="M104 306 L119 290 L134 296 L149 270 L164 248" fill="none" stroke="{DEEP}" stroke-width="2.5" stroke-linecap="round" '
            'stroke-linejoin="round"/>'
            f'<circle cx="164" cy="248" r="5" fill="{LIME}" stroke="{INK}" stroke-width="2"/>'
            f'<rect x="96" y="352" width="78" height="14" rx="7" fill="{DEEP}" opacity=".15"/>'
            # mão segurando o celular por baixo; polegar à esquerda
            f'<path d="M70 486 L84 360 Q86 344 100 346 L106 392 L150 404 L176 486 Z" fill="{SKIN2}"/>'
            f'<ellipse cx="88" cy="330" rx="9" ry="22" transform="rotate(18 88 330)" fill="{SKIN2_SH}"/>'
            + "".join(f'<rect x="184" y="{276 + k * 26}" width="26" height="16" rx="8" fill="{SKIN2_SH}"/>' for k in range(4)))


def _ill_ambiente(gid: str) -> str:
    stripes = "".join(f'<rect x="{18 + k * 26}" y="198" width="26" height="34" fill="{TEAL if k % 2 else MIST}"/>' for k in range(9))
    scallops = "".join(f'<circle cx="{31 + k * 26}" cy="232" r="13" fill="{TEAL if k % 2 else MIST}"/>' for k in range(9))
    shelf_items = "".join(f'<rect x="{50 + k * 18}" y="{y - 14 - (k % 3) * 4}" width="12" height="{14 + (k % 3) * 4}" rx="2" '
                          f'fill="{(TEAL_LT, LIME, MIST)[(k + i) % 3]}" opacity=".8"/>'
                          for i, y in enumerate((292, 330)) for k in range(5))
    return (f'<circle cx="60" cy="120" r="90" fill="url(#l{gid})"/>'
            f'<rect x="26" y="182" width="218" height="232" fill="{INK_SOFT}"/>'
            f'<rect x="26" y="182" width="218" height="16" fill="{INK}"/>{stripes}{scallops}'
            f'<rect x="40" y="258" width="104" height="96" rx="4" fill="{INK}" stroke="{MIST}" stroke-opacity=".6" stroke-width="2"/>'
            f'<path d="M44 292 L140 292 M44 330 L140 330" stroke="{MIST}" stroke-opacity=".35" stroke-width="2"/>{shelf_items}'
            f'<path d="M52 350 L92 262" stroke="{MIST}" stroke-opacity=".12" stroke-width="8"/>'
            f'<rect x="160" y="258" width="68" height="156" rx="4" fill="{INK}" stroke="{MIST}" stroke-opacity=".6" stroke-width="2"/>'
            f'<rect x="170" y="270" width="48" height="56" rx="3" fill="{TEAL}" opacity=".35"/>'
            f'<circle cx="216" cy="350" r="4" fill="{LIME}"/>'
            f'<g transform="rotate(-4 194 292)"><rect x="172" y="284" width="44" height="18" rx="4" fill="{MIST}"/>'
            f'<text x="194" y="297" font-size="9" font-weight="800" text-anchor="middle" letter-spacing=".06em" fill="{INK}">ABERTO</text></g>'
            f'<path d="M46 414 L58 384 L86 384 L98 414 Z" fill="{TEAL}"/>'
            f'<ellipse cx="62" cy="370" rx="9" ry="18" transform="rotate(-24 62 370)" fill="{TEAL_LT}"/>'
            f'<ellipse cx="82" cy="368" rx="9" ry="18" transform="rotate(24 82 368)" fill="{TEAL_LT}"/>'
            f'<ellipse cx="72" cy="360" rx="8" ry="20" fill="{TEAL}"/>'
            f'<rect x="-4" y="414" width="{W + 8}" height="80" fill="{INK}" opacity=".6"/>'
            f'<path d="M0 432 L270 432" stroke="{MIST}" stroke-opacity=".12" stroke-width="2"/>')


def _ill_cliente(gid: str) -> str:
    return (f'<circle cx="135" cy="200" r="100" fill="url(#l{gid})"/>' + _shelves(140) +
            _person(84, 262, 30, SKIN, SKIN_SH, HAIR, MIST, apron=TEAL, long_hair=True) +
            _person(190, 258, 30, SKIN2, SKIN2_SH, HAIR2, TEAL_LT) +
            f'<rect x="-4" y="346" width="{W + 8}" height="140" fill="{WALL}"/>'
            f'<rect x="-4" y="340" width="{W + 8}" height="10" rx="3" fill="{TEAL}"/>'
            # maquininha (genérica, sem marca) sobre o balcão
            f'<rect x="118" y="300" width="36" height="50" rx="7" fill="{INK}" stroke="{MIST}" stroke-opacity=".5" stroke-width="2"/>'
            f'<rect x="124" y="306" width="24" height="14" rx="3" fill="{LIME}"/>'
            + "".join(f'<circle cx="{127 + (k % 3) * 9}" cy="{328 + (k // 3) * 8}" r="2.4" fill="{MIST}" opacity=".7"/>' for k in range(6)) +
            f'<rect x="110" y="196" width="52" height="34" rx="12" fill="{MIST}"/><path d="M128 230 L124 242 L138 230 Z" fill="{MIST}"/>'
            f'<path d="M136 222 C122 212 124 202 131 202 C134 202 136 205 136 207 C136 205 138 202 141 202 C148 202 150 212 136 222 Z" '
            f'fill="{TEAL}"/>')


_ILLU = {"rosto": _ill_rosto, "produto": _ill_produto, "maos": _ill_maos, "tela": _ill_tela, "ambiente": _ill_ambiente,
         "cliente": _ill_cliente}


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(re.sub(r"\s+", " ", text or "").strip(), width) or []
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        lines[-1] = (last.rsplit(" ", 1)[0] if " " in last and len(last) > width - 2 else last).rstrip(" ,.;:") + "…"
    return lines


def svg_frame(cena: Cena, i: int, uid: str = "", total: int = 0) -> str:
    """Quadro 9:16 de uma cena, como um still do vídeo: ilustração do plano, barra de progresso do Reels,
    texto na tela como apareceria no vídeo e a fala como legenda."""
    plano = cena.plano if cena.plano in _ILLU else "rosto"
    c1, c2 = BG[plano]
    gid = re.sub(r"[^A-Za-z0-9_-]", "", f"g{uid}{i}")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" '
             f'aria-label="Cena {i}: {html.escape(PLANO_LABEL.get(plano, plano))}" style="font-family:Outfit,Manrope,system-ui,sans-serif;display:block">',
             f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c1}"/>'
             f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
             f'<radialGradient id="l{gid}"><stop offset="0" stop-color="{MIST}" stop-opacity=".16"/>'
             f'<stop offset="1" stop-color="{MIST}" stop-opacity="0"/></radialGradient>'
             f'<linearGradient id="f{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INK}" stop-opacity="0"/>'
             f'<stop offset=".45" stop-color="{INK}" stop-opacity=".88"/><stop offset="1" stop-color="{INK}" stop-opacity=".96"/></linearGradient>'
             f'<clipPath id="c{gid}"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>',
             f'<g clip-path="url(#c{gid})"><rect width="{W}" height="{H}" fill="url(#{gid})"/>',
             _ILLU[plano](gid)]
    # barra de progresso do Reels/Shorts: em que ponto do vídeo a cena está
    if total and total > 1:
        gap, x0, w_all = 4, 12, W - 24
        seg = (w_all - gap * (total - 1)) / total
        for k in range(total):
            fill, op = (MIST, ".95") if k < i else (MIST, ".28")
            parts.append(f'<rect x="{x0 + k * (seg + gap):.1f}" y="8" width="{seg:.1f}" height="3" rx="1.5" fill="{fill}" opacity="{op}"/>')
    # selo da cena (esquerda) e tipo de plano (direita)
    badge = f"CENA {i}" + (f" · {cena.tempo}" if cena.tempo else "")
    parts.append(f'<rect x="12" y="18" width="{14 + 6.9 * len(badge):.0f}" height="22" rx="11" fill="{INK}" opacity=".9"/>'
                 f'<text x="21" y="33" font-size="11" font-weight="700" letter-spacing=".06em" fill="{MIST}">{html.escape(badge)}</text>')
    chip = PLANO_CHIP.get(plano, "")
    cw = 22 + 6.6 * len(chip)
    dot = f'<circle cx="{W - 12 - cw + 11}" cy="29" r="3.5" fill="{LIME}"/>' if plano == "rosto" else ""
    parts.append(f'<rect x="{W - 12 - cw:.0f}" y="18" width="{cw:.0f}" height="22" rx="11" fill="{INK}" opacity=".55" '
                 f'stroke="{MIST}" stroke-opacity=".3"/>{dot}'
                 f'<text x="{W - 12 - cw / 2 + (4 if dot else 0):.0f}" y="33" font-size="9.5" font-weight="700" letter-spacing=".1em" '
                 f'text-anchor="middle" fill="{MIST}">{"REC" if plano == "rosto" else chip}</text>')
    # texto na tela (como no vídeo)
    tl = _wrap(cena.texto_tela, 20, 3)
    if tl:
        top, lh = 56, 22
        parts.append(f'<rect x="22" y="{top}" width="226" height="{16 + lh * len(tl)}" rx="10" fill="{MIST}" opacity=".97"/>')
        for k, line in enumerate(tl):
            parts.append(f'<text x="135" y="{top + 26 + k * lh}" font-size="16" font-weight="800" text-anchor="middle" '
                         f'fill="{INK}">{html.escape(line.upper())}</text>')
    # fala como legenda, sobre um degradê (o fundo continua visível)
    fl = _wrap(cena.fala, 36, 3)
    if fl:
        y0 = H - 18 - 17 * len(fl)
        parts.append(f'<rect x="0" y="{y0 - 44}" width="{W}" height="{H - y0 + 44}" fill="url(#f{gid})"/>')
        for k, line in enumerate(fl):
            parts.append(f'<text x="135" y="{y0 + k * 17}" font-size="12.5" font-weight="600" text-anchor="middle" fill="{MIST}">'
                         f'{html.escape(line)}</text>')
    parts.append(f'<rect width="{W}" height="{H}" rx="18" fill="none" stroke="{MIST}" stroke-opacity=".12" stroke-width="2"/></g></svg>')
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
        f'<figure><div class="frame">{svg_frame(c, i, "x", len(cs))}</div><figcaption><b>{html.escape(c.tempo or f"cena {i}")}</b> · '
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
