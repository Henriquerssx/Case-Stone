"""Identidade visual do painel: o mundo do Clube dos Sonhos com as cores do Impulso Stone.

Fundo tinta, títulos Outfit em caixa alta, ações em pílula verde-água, a estrela de quatro pontas como motivo
e o verde-limão reservado ao que "brilha" (o top 10%). Todo texto vindo de dados passa por html.escape.
"""
from __future__ import annotations

import html
import json
import math

import pandas as pd
import plotly.graph_objects as go

INK, INK_SOFT, DEEP, TEAL, MIST, LIME, SHERWOOD = "#03211D", "#06352E", "#055046", "#32ADA1", "#E6EAE9", "#C7F93C", "#004132"
MIST_70 = "rgba(230,234,233,.72)"
HAIR = "rgba(230,234,233,.12)"

FONT_FACES = """
@font-face{font-family:"Outfit";src:url("/app/static/fonts/Outfit-variable-latin.woff2") format("woff2");font-weight:400 800;font-display:swap}
@font-face{font-family:"Manrope";src:url("/app/static/fonts/Manrope-variable-latin.woff2") format("woff2");font-weight:400 800;font-display:swap}
"""


def star_svg(size: int = 22, color: str = LIME, glow: bool = True) -> str:
    """A estrela de quatro pontas (motivo do Clube dos Sonhos), desenhada em SVG."""
    f = ' style="filter:drop-shadow(0 0 6px rgba(230,234,233,.55))"' if glow else ""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true"{f}>'
            f'<path d="M12 0 C12.9 6.6 17.4 11.1 24 12 C17.4 12.9 12.9 17.4 12 24 C11.1 17.4 6.6 12.9 0 12 '
            f'C6.6 11.1 11.1 6.6 12 0 Z" fill="{color}"/></svg>')


def css() -> str:
    return f"""<style>
{FONT_FACES}
:root{{--ink:{INK};--ink-soft:{INK_SOFT};--deep:{DEEP};--teal:{TEAL};--mist:{MIST};--lime:{LIME};--hair:{HAIR}}}
.stApp{{background:
  radial-gradient(900px 420px at 8% -6%, rgba(50,173,161,.16), transparent 60%),
  radial-gradient(700px 380px at 96% 4%, rgba(199,249,60,.07), transparent 60%), var(--ink)}}
.block-container{{padding-top:2.2rem;max-width:1320px}}
h1,h2,h3,[data-testid="stHeading"] *{{font-family:"Outfit",sans-serif !important;text-transform:uppercase;letter-spacing:-.01em;
  line-height:.98 !important}}
h2{{font-weight:800 !important}} h3{{font-weight:700 !important;font-size:1.35rem !important}}
p, li, label, .stMarkdown{{font-family:"Manrope",sans-serif}}
::selection{{background:var(--teal);color:var(--ink)}}
*:focus-visible{{outline:2px solid var(--teal) !important;outline-offset:2px}}
::-webkit-scrollbar{{width:10px;height:10px}} ::-webkit-scrollbar-thumb{{background:#0E4A40;border-radius:99px}}
::-webkit-scrollbar-track{{background:transparent}}
a{{text-underline-offset:3px}}

/* abas = pílulas em caixa alta */
[data-testid="stTabs"] [role="tablist"]{{gap:.5rem;flex-wrap:wrap;border-bottom:1px solid var(--hair);padding-bottom:.9rem;margin-bottom:.4rem}}
[data-testid="stTabs"] [role="tablist"] > :not([role="tab"]){{display:none}}
[data-testid="stTab"]{{border:1px solid var(--hair);border-radius:999px;padding:.5rem 1.05rem !important;margin:0 !important;
  transition:border-color .2s, background .2s}}
[data-testid="stTab"] p{{font-family:"Outfit",sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.08em;font-size:.76rem;
  color:var(--mist)}}
[data-testid="stTab"]:hover{{border-color:var(--teal)}}
[data-testid="stTab"][aria-selected="true"]{{background:var(--teal);border-color:var(--teal)}}
[data-testid="stTab"][aria-selected="true"] p{{color:var(--ink) !important}}

/* botões */
.stButton button, .stDownloadButton button{{font-family:"Outfit",sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  font-size:.8rem;padding:.6rem 1.4rem;border:1px solid var(--hair)}}
.stButton button[kind="primary"]{{background:var(--teal);border-color:var(--teal);color:var(--ink);
  box-shadow:0 10px 30px -12px rgba(50,173,161,.75)}}
.stButton button[kind="primary"] p{{color:var(--ink) !important}}
.stButton button[kind="primary"]:hover{{filter:brightness(1.1)}}
.stButton button:hover, .stDownloadButton button:hover{{border-color:var(--teal)}}

/* métricas */
[data-testid="stMetricLabel"] p{{text-transform:uppercase;letter-spacing:.16em;font-size:.68rem !important;color:{MIST_70};font-weight:700}}
[data-testid="stMetricValue"]{{font-family:"Outfit",sans-serif;font-weight:700}}
[data-testid="stVerticalBlockBorderWrapper"]{{transition:border-color .25s}}
[data-testid="stVerticalBlockBorderWrapper"]:hover{{border-color:rgba(50,173,161,.6) !important}}
.cds-rail{{list-style:none;margin:.2rem 0 1rem;padding:0;border-top:1px solid var(--hair)}}
.cds-rail li{{display:grid;grid-template-columns:1.6rem minmax(9rem,14rem) 6.5rem 1fr;gap:.8rem;align-items:baseline;
  padding:.7rem .2rem;border-bottom:1px solid var(--hair);margin:0 !important}}
.cds-rail .st{{display:flex;align-self:center}}
.cds-rail .nm{{font-family:"Outfit",sans-serif;font-weight:700;text-transform:uppercase;letter-spacing:.04em;font-size:.92rem;color:var(--mist)}}
.cds-rail .nu{{font-family:"Outfit",sans-serif;font-weight:700;font-size:1.5rem;color:var(--mist);text-align:right;letter-spacing:-.02em}}
.cds-rail .dt{{color:{MIST_70};font-size:.86rem}}
.cds-rail li.pend{{background:linear-gradient(90deg,rgba(50,173,161,.12),transparent 60%)}}
.cds-rail li.pend .dt{{color:var(--mist)}}
@media (max-width:640px){{.cds-rail li{{grid-template-columns:1.4rem 1fr auto}} .cds-rail .dt{{grid-column:2 / -1}}}}
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]){{border-color:var(--hair) !important}}

/* hero */
.cds-hero h1{{font-size:clamp(2.4rem,4.6vw,4.4rem) !important;font-weight:800 !important;line-height:.95 !important;
  letter-spacing:-.025em;margin:0 0 1.1rem;color:var(--mist);text-wrap:balance}}
.cds-hero h1 em{{font-style:normal;color:var(--lime);text-shadow:0 0 28px rgba(199,249,60,.35)}}
.cds-hero .lede{{font-size:1.12rem;line-height:1.55;color:{MIST_70};max-width:34rem;margin:0 0 1.4rem}}
.cds-proof{{margin:0;font-size:1.05rem;line-height:1.7;color:{MIST_70};max-width:40rem;text-wrap:pretty}}
.cds-proof b{{font-family:"Outfit",sans-serif;font-size:1.45em;font-weight:700;color:var(--mist);letter-spacing:-.02em;padding:0 .08em}}
.cds-proof b.top{{color:var(--lime);text-shadow:0 0 22px rgba(199,249,60,.35)}}
.cds-note{{margin-top:1.2rem;font-size:.8rem;color:{MIST_70};display:flex;gap:.5rem;align-items:center}}
@keyframes cds-rise{{from{{opacity:0;transform:translateY(18px);filter:blur(6px)}}to{{opacity:1;transform:none;filter:none}}}}
.cds-hero > *{{animation:cds-rise .9s cubic-bezier(.16,1,.3,1) both}}
.cds-hero > *:nth-child(2){{animation-delay:.08s}} .cds-hero > *:nth-child(3){{animation-delay:.16s}} .cds-hero > *:nth-child(4){{animation-delay:.24s}}
@media (prefers-reduced-motion:reduce){{.cds-hero > *{{animation:none}}}}

/* universos (nichos) */
.cds-universes{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:.4rem 0 .4rem}}
.cds-card{{position:relative;aspect-ratio:9/16;border-radius:1.1rem;overflow:hidden;border:1px solid var(--hair);
  background:linear-gradient(160deg,var(--deep),var(--ink-soft));transition:border-color .25s, transform .35s cubic-bezier(.16,1,.3,1)}}
.cds-card:hover{{border-color:var(--teal);transform:translateY(-3px)}}
.cds-card.sel{{border:2px solid var(--teal);box-shadow:0 14px 34px -18px rgba(50,173,161,.9)}}
[data-testid="stMainMenu"]{{display:none}}
.cds-card img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.9}}
.cds-card .shade{{position:absolute;inset:0;background:linear-gradient(to top,rgba(3,33,29,.97) 0%,rgba(3,33,29,.92) 52%,rgba(3,33,29,.25) 82%,rgba(3,33,29,.05) 100%)}}
.cds-card .glyph{{position:absolute;top:14px;right:14px}}
.cds-card .txt{{position:absolute;left:12px;right:12px;bottom:12px}}
.cds-card h4{{font-family:"Outfit",sans-serif;font-weight:800;text-transform:uppercase;font-size:clamp(.92rem,1.15vw,1.15rem);
  overflow-wrap:normal;word-break:keep-all;hyphens:none;line-height:.95;margin:0 0 .5rem;
  color:var(--mist);letter-spacing:-.01em}}
.cds-card p{{margin:0;font-size:.8rem;color:{MIST_70};line-height:1.45}}
.cds-card p b{{color:var(--lime);font-weight:700}}
.cds-card .pill{{display:inline-block;margin-top:.55rem;font-family:"Outfit",sans-serif;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;font-size:.58rem;padding:.22rem .5rem;border-radius:.6rem;background:rgba(230,234,233,.1);color:var(--mist)}}

/* gancho do roteiro */
.cds-hook{{display:flex;gap:.7rem;align-items:flex-start;font-family:"Outfit",sans-serif;font-weight:700;font-size:1.45rem;line-height:1.15;
  margin:.5rem 0 .9rem;color:var(--mist)}}

/* faixa do resultado: confiança + motivo + quem redigiu */
.cds-strip{{display:flex;flex-wrap:wrap;gap:.45rem .9rem;align-items:center;margin:1.2rem 0 1rem;padding:.75rem 1rem;
  border:1px solid var(--hair);border-radius:1rem;background:rgba(6,53,46,.55)}}
.cds-conf{{display:inline-flex;align-items:center;gap:.45rem;font-family:"Outfit",sans-serif;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;font-size:.74rem;padding:.32rem .75rem;border-radius:99px;white-space:nowrap}}
.cds-conf i{{width:.5rem;height:.5rem;border-radius:50%;background:currentColor}}
.cds-conf.alta{{background:var(--teal);color:var(--ink)}}
.cds-conf.media{{border:1px solid var(--teal);color:var(--mist)}}
.cds-conf.baixa{{border:1px dashed {MIST_70};color:var(--mist)}}
.cds-strip .why{{color:var(--mist);font-size:.92rem;flex:1 1 22rem}}
.cds-strip .meta{{color:{MIST_70};font-size:.8rem}}

/* checklist "antes de gravar" */
.cds-check{{list-style:none;margin:.3rem 0 .6rem;padding:0;border-top:1px solid var(--hair)}}
.cds-check li{{display:grid;grid-template-columns:1.4rem 1fr 4.2rem;gap:.15rem .7rem;align-items:center;padding:.6rem .1rem;
  border-bottom:1px solid var(--hair);margin:0 !important}}
.cds-check .ck{{display:flex;color:var(--teal)}}
.cds-check .tx{{color:var(--mist);font-size:.95rem}}
.cds-check .pc{{font-family:"Outfit",sans-serif;font-weight:700;font-size:1.15rem;text-align:right;color:var(--mist)}}
.cds-check .bar{{grid-column:2 / -1;height:4px;border-radius:99px;background:rgba(230,234,233,.08);overflow:hidden}}
.cds-check .bar b{{display:block;height:100%;border-radius:99px;background:var(--teal)}}

/* cabeçalho fixo opaco: o conteúdo não passa por baixo com uma linha cortando o texto */
[data-testid="stHeader"]{{background:rgba(3,33,29,.92) !important;backdrop-filter:blur(10px);box-shadow:none !important;border:0 !important}}

</style>"""


def hero_html(n_posts: int, n_profiles: int, n_top: int, n_creatives: int) -> str:
    f = lambda v: f"{int(v):,}".replace(",", ".")
    return f"""<div class="cds-hero">
<h1>O que faz um pequeno negócio <em>brilhar</em>?</h1>
<p class="lede">Lemos as publicações que mais engajam quem empreende, descobrimos o que elas têm em comum
e transformamos isso em roteiros para o Impulso Stone, cada um ligado aos posts reais em que se apoia.</p>
<p class="cds-proof">De <b>{f(n_posts)}</b> posts de <b>{f(n_profiles)}</b> perfis, <b class="top">{f(n_top)}</b> brilham no
top 10% e viraram <b>{f(n_creatives)}</b> roteiros prontos.</p>
<p class="cds-note">{star_svg(14)} Padrões observados nos dados, não garantia de resultado.</p>
</div>"""


def star3d_html(n_total: int, n_top: int, height: int = 420) -> str:
    """Estrela facetada em 3D (canvas 2D, sem bibliotecas) cercada por partículas: cada uma é um post;
    as verde-limão são o top 10%, na proporção real. Inclina com o ponteiro; respeita movimento reduzido."""
    ratio = n_top / n_total if n_total else 0.1
    cfg = json.dumps({"ratio": round(ratio, 4), "ink": INK, "deep": DEEP, "teal": TEAL, "lime": LIME, "mist": MIST})
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:"Outfit";src:url("/app/static/fonts/Outfit-variable-latin.woff2") format("woff2");font-weight:400 800}}
html,body{{margin:0;height:100%;background:transparent;overflow:hidden}}
canvas{{width:100%;height:{height}px;display:block;cursor:grab}}
.cap{{position:absolute;left:0;right:0;bottom:0;padding:22px 0 6px;text-align:center;font:600 11px/1.3 Outfit,sans-serif;letter-spacing:.14em;
text-transform:uppercase;color:rgba(230,234,233,.7);background:linear-gradient(to top,{INK} 55%,rgba(3,33,29,0))}}
.cap svg{{vertical-align:-1px;margin-right:4px}}
</style></head><body>
<canvas id="c" role="img" aria-label="Estrela 3D cercada por {n_total} pontos; {n_top} em destaque representam o top 10%"></canvas>
<div class="cap"><svg width="8" height="8" aria-hidden="true"><circle cx="4" cy="4" r="4" fill="{LIME}"/></svg>top 10% &nbsp;
<svg width="8" height="8" aria-hidden="true"><circle cx="4" cy="4" r="4" fill="{TEAL}"/></svg>demais posts &nbsp;·&nbsp; arraste para girar</div>
<script>
const C={cfg};
const cv=document.getElementById('c'),cx=cv.getContext('2d');
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
let W=0,H=0,dpr=Math.min(window.devicePixelRatio||1,2);
function size(){{W=cv.clientWidth;H={height};cv.width=W*dpr;cv.height=H*dpr;cx.setTransform(dpr,0,0,dpr,0,0)}}
size();addEventListener('resize',()=>{{size();if(reduce)frame()}});
const hex=h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16));
const mix=(a,b,t)=>a.map((v,i)=>Math.round(v+(b[i]-v)*t));
const DEEP=hex(C.deep),TEAL=hex(C.teal),LIME=hex(C.lime),MIST=hex(C.mist);
// estrela de 4 pontas: contorno de 8 pontos + dois ápices (frente/trás)
const R=1.0,r=0.30,outline=[];
for(let k=0;k<8;k++){{const a=k*Math.PI/4-Math.PI/2,rad=k%2?r:R;outline.push([Math.cos(a)*rad,Math.sin(a)*rad,0])}}
const AF=[0,0,0.42],AB=[0,0,-0.42],tris=[];
for(let k=0;k<8;k++){{const p=outline[k],q=outline[(k+1)%8];tris.push([AF,p,q]);tris.push([AB,q,p])}}
// partículas em anéis inclinados
const N=420,parts=[];
for(let i=0;i<N;i++){{const ring=i%3,rad=1.55+ring*0.32+Math.random()*0.22,a=Math.random()*Math.PI*2;
 parts.push({{a,rad,spd:(0.0018+Math.random()*0.0026)*(ring%2?-1:1),tilt:[0.55,-0.35,0.15][ring],y:(Math.random()-.5)*0.16,
 top:Math.random()<C.ratio,s:0.6+Math.random()*1.1}})}}
let ry=0.6,rx=-0.18,trx=-0.18,dragging=false,lx=0,vy=0.006;
cv.addEventListener('pointerdown',e=>{{dragging=true;lx=e.clientX;cv.setPointerCapture(e.pointerId)}});
cv.addEventListener('pointerup',()=>dragging=false);
cv.addEventListener('pointermove',e=>{{const b=cv.getBoundingClientRect();trx=((e.clientY-b.top)/b.height-.5)*-0.7;
 if(dragging){{ry+=(e.clientX-lx)*0.01;lx=e.clientX}} if(reduce)requestAnimationFrame(frame)}});
function rot(p){{let [x,y,z]=p;let c=Math.cos(ry),s=Math.sin(ry);[x,z]=[x*c+z*s,-x*s+z*c];
 c=Math.cos(rx);s=Math.sin(rx);[y,z]=[y*c-z*s,y*s+z*c];return [x,y,z]}}
function proj(p){{const sc=Math.min(W,H)*0.27,f=3.6/(3.6-p[2]);return [W/2+p[0]*sc*f,H/2-12+p[1]*sc*f,f]}}
function frame(){{
 cx.clearRect(0,0,W,H);
 const items=[];
 for(const t of tris){{const v=t.map(rot);const n=[(v[1][1]-v[0][1])*(v[2][2]-v[0][2])-(v[1][2]-v[0][2])*(v[2][1]-v[0][1]),
  (v[1][2]-v[0][2])*(v[2][0]-v[0][0])-(v[1][0]-v[0][0])*(v[2][2]-v[0][2]),(v[1][0]-v[0][0])*(v[2][1]-v[0][1])-(v[1][1]-v[0][1])*(v[2][0]-v[0][0])];
  const ln=Math.hypot(...n)||1,l=Math.max(0,(n[0]*-0.4+n[1]*0.55+n[2]*0.73)/ln);
  items.push({{z:(v[0][2]+v[1][2]+v[2][2])/3,tri:v.map(proj),l}})}}
 for(const p of parts){{if(!reduce)p.a+=p.spd;const x=Math.cos(p.a)*p.rad,z0=Math.sin(p.a)*p.rad;
  const y=p.y+z0*p.tilt,z=z0*Math.cos(p.tilt);const v=rot([x,y,z]);items.push({{z:v[2],pt:proj(v),p}})}}
 items.sort((a,b)=>a.z-b.z);
 for(const it of items){{
  if(it.tri){{const col=it.l>0.55?mix(TEAL,LIME,(it.l-0.55)/0.45):mix(DEEP,TEAL,it.l/0.55);
   cx.beginPath();cx.moveTo(it.tri[0][0],it.tri[0][1]);cx.lineTo(it.tri[1][0],it.tri[1][1]);cx.lineTo(it.tri[2][0],it.tri[2][1]);cx.closePath();
   cx.fillStyle=`rgb(${{col}})`;cx.shadowColor='rgba(230,234,233,.35)';cx.shadowBlur=18;cx.fill();cx.shadowBlur=0;
   cx.strokeStyle='rgba(3,33,29,.35)';cx.lineWidth=0.6;cx.stroke()}}
  else{{const [px,py,f]=it.pt,p=it.p,a=Math.max(.18,Math.min(1,(it.z+2.2)/3.2));
   cx.beginPath();cx.arc(px,py,(p.top?1.9:1.2)*p.s*f,0,7);
   if(p.top){{cx.fillStyle=`rgba(${{LIME}},${{a}})`;cx.shadowColor='rgba(199,249,60,.9)';cx.shadowBlur=10}}
   else{{cx.fillStyle=`rgba(${{TEAL}},${{a*0.75}})`;cx.shadowBlur=0}}
   cx.fill();cx.shadowBlur=0}}
 }}
 if(!dragging&&!reduce)ry+=vy; rx+=(trx-rx)*0.05;
 if(!reduce)requestAnimationFrame(frame);
}}
document.addEventListener('visibilitychange',()=>{{if(!document.hidden&&!reduce)requestAnimationFrame(frame)}});
frame();
// com movimento reduzido há um quadro só: redesenha quando o iframe ganha tamanho
if(reduce){{setTimeout(()=>{{size();frame()}},250);addEventListener('load',()=>{{size();frame()}})}}
</script></body></html>"""


def galaxy_figure(df: pd.DataFrame, nichos: dict[str, str]) -> go.Figure:
    """Galáxia 3D: cada post é um ponto (nicho × data × engajamento); o top 10% acende em verde-limão."""
    d = df.copy()
    order = sorted(d["segmento"].dropna().unique())
    idx = {s: i for i, s in enumerate(order)}
    rng = pd.Series(range(len(d)), index=d.index).map(lambda i: ((i * 2654435761) % 1000) / 1000 - 0.5)
    d["x"] = d["segmento"].map(idx).astype(float) + rng * 0.7
    d["t"] = pd.to_datetime(d["posted_at"], utc=True, errors="coerce").dt.tz_localize(None)
    d = d.dropna(subset=["t"])
    d["y"] = d["t"].dt.year + (d["t"].dt.dayofyear / 366)
    d["z"] = (d["engagement_rate"].clip(lower=1e-5) * 100).apply(lambda v: math.log10(v))
    fig = go.Figure()
    for top, name, color, size, op in [(0, "Demais posts", TEAL, 2.2, 0.32), (1, "Top 10% (brilham)", LIME, 3.6, 0.95)]:
        g = d[d["is_top"] == top]
        fig.add_trace(go.Scatter3d(
            x=g["x"], y=g["y"], z=g["z"], mode="markers", name=name,
            marker=dict(size=size, color=color, opacity=op, line=dict(width=0)),
            customdata=g[["handle", "segmento", "engagement_rate", "platform"]].assign(
                segmento=g["segmento"].map(lambda s: nichos.get(s, s))).values,
            hovertemplate="@%{customdata[0]} · %{customdata[3]}<br>%{customdata[1]}<br>engajamento %{customdata[2]:.2%}<extra></extra>"))
    axis = dict(backgroundcolor=INK, gridcolor="rgba(230,234,233,.10)", zerolinecolor="rgba(230,234,233,.10)",
                color=MIST_70, showspikes=False)
    tick = [10 ** k for k in range(-3, 3)]
    fig.update_layout(
        height=660, margin=dict(l=0, r=0, t=10, b=56), paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color=MIST),
        legend=dict(orientation="h", y=1.02, x=0, font=dict(size=12), itemsizing="constant"),
        scene=dict(
            xaxis=dict(axis, title="nicho", tickvals=list(idx.values()), ticktext=[nichos.get(s, s) for s in order]),
            yaxis=dict(axis, title="ano de publicação", tickformat="d", nticks=5),
            zaxis=dict(axis, title="engajamento (%)", tickvals=[math.log10(v) for v in tick],
                       ticktext=[f"{v:g}%".replace(".", ",") for v in tick]),
            camera=dict(eye=dict(x=1.5, y=-1.55, z=0.66), center=dict(x=0, y=0, z=-0.12)), aspectmode="manual", aspectratio=dict(x=1.75, y=1.05, z=0.75)))
    return fig


def universe_card(r, cover: str | None, selected: bool = False) -> str:
    """Um cartão de nicho (capa real sob gradiente de tinta)."""
    pic = f'<img src="{cover}" alt="" loading="lazy">' if cover else ""
    er = f"{r.er_mediana * 100:.2f}%".replace(".", ",") if pd.notna(r.er_mediana) else "—"
    taxa = f"{r.taxa_top * 100:.0f}%" if pd.notna(r.taxa_top) else "—"
    fmt = html.escape(str(r.formato_top)) if isinstance(r.formato_top, str) else "ainda não categorizado"
    return (f'<div class="cds-card{" sel" if selected else ""}">{pic}<div class="shade"></div>'
            f'<div class="glyph">{star_svg(16, LIME if (r.taxa_top or 0) >= .1 else MIST)}</div>'
            f'<div class="txt"><h4>{html.escape(str(r.nome))}</h4>'
            f'<p><b>{taxa}</b> chegam ao top · mediana {er}</p>'
            f'<span class="pill">{int(r.posts)} posts · {fmt}</span></div></div>')


def rail_html(steps: list[dict], fmt_n) -> str:
    """As etapas do pipeline numa trilha única (status, etapa, número, detalhe); pendências em destaque."""
    ok = '<svg width="16" height="16" viewBox="0 0 16 16" aria-label="pronto"><circle cx="8" cy="8" r="7" fill="none" stroke="#32ADA1" stroke-width="1.6"/><path d="M4.6 8.2l2.2 2.2 4.6-4.8" fill="none" stroke="#32ADA1" stroke-width="1.8" stroke-linecap="round"/></svg>'
    pend = '<svg width="16" height="16" viewBox="0 0 16 16" aria-label="pendente"><circle cx="8" cy="8" r="7" fill="none" stroke="#E6EAE9" stroke-width="1.6"/></svg>'
    part = '<svg width="16" height="16" viewBox="0 0 16 16" aria-label="em andamento"><circle cx="8" cy="8" r="7" fill="none" stroke="#E6EAE9" stroke-width="1.6" stroke-dasharray="3 3"/></svg>'
    rows = []
    for s in steps:
        icon = {"ok": ok, "parcial": part}.get(s["status"], pend)
        rows.append(f'<li class="{"pend" if s["status"] != "ok" else ""}"><span class="st">{icon}</span>'
                    f'<span class="nm">{html.escape(str(s["etapa"]))}</span><span class="nu">{html.escape(fmt_n(s["numero"]))}</span>'
                    f'<span class="dt">{html.escape(str(s["detalhe"]))}</span></li>')
    return f'<ul class="cds-rail">{"".join(rows)}</ul>'


def universe_cards(summary: pd.DataFrame, covers: dict[str, str | None]) -> str:
    """Cartões de nicho no formato "Escolha o seu universo": capa real do post de maior engajamento + dados."""
    cards = []
    for r in summary.itertuples():
        img = covers.get(r.nicho)
        pic = f'<img src="{img}" alt="" loading="lazy">' if img else ""
        er = f"{r.er_mediana * 100:.2f}%".replace(".", ",") if pd.notna(r.er_mediana) else "—"
        taxa = f"{r.taxa_top * 100:.0f}%" if pd.notna(r.taxa_top) else "—"
        fmt = html.escape(str(r.formato_top)) if isinstance(r.formato_top, str) else "ainda não categorizado"
        cards.append(
            f'<div class="cds-card">{pic}<div class="shade"></div><div class="glyph">{star_svg(18, LIME if (r.taxa_top or 0) >= .1 else MIST)}</div>'
            f'<div class="txt"><h4>{html.escape(str(r.nome))}</h4>'
            f'<p><b>{taxa}</b> dos posts chegam ao top · mediana {er}</p>'
            f'<span class="pill">{int(r.posts)} posts · {fmt}</span></div></div>')
    return f'<div class="cds-universes">{"".join(cards)}</div>'


def hook_html(gancho: str) -> str:
    return f'<div class="cds-hook">{star_svg(22)}<div>“{html.escape(gancho)}”</div></div>'


_CONF = {"alta": "Confiança alta", "media": "Confiança média", "baixa": "Confiança baixa"}


def result_strip_html(level: str, reason: str, scope: str, writer: str) -> str:
    """Uma linha com o que importa antes do roteiro: nível de confiança, por quê, recorte e quem redigiu."""
    lv = level if level in _CONF else "baixa"
    return (f'<div class="cds-strip" role="status"><span class="cds-conf {lv}"><i></i>{_CONF[lv]}</span>'
            f'<span class="why">{html.escape(reason[:1].upper() + reason[1:]) if reason else ""}</span>'
            f'<span class="meta">{html.escape(scope)} · redação: {html.escape(writer)}</span></div>')


_CHECK_SVG = ('<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" '
              'stroke="currentColor" stroke-width="2"/><path d="M7.5 12.5l3 3 6-6.5" fill="none" stroke="currentColor" '
              'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def checklist_html(items: list[tuple[str, float, int, int]]) -> str:
    """Checklist de gravação: cada item é o elemento mais frequente do top em um campo, com a % e uma barra."""
    rows = []
    for text, freq, n, total in items:
        pct = f"{freq * 100:.0f}%"
        rows.append(f'<li title="{n} de {total} posts do top"><span class="ck">{_CHECK_SVG}</span>'
                    f'<span class="tx">{html.escape(text)}</span><span class="pc">{pct}</span>'
                    f'<span class="bar"><b style="width:{min(freq, 1) * 100:.0f}%"></b></span></li>')
    return f'<ul class="cds-check">{"".join(rows)}</ul>'
