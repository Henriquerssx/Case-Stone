"""Painel do projeto: como funciona, base, padrões, perfis e geração de roteiros com métricas.

    streamlit run demo/app.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stone_mpe import config, demo_cache, release, status, storage, storyboard  # noqa: E402
from stone_mpe.analysis import comments, creators, lead_signals, niches, patterns, weighted  # noqa: E402
from stone_mpe.collect.media import thumb_path  # noqa: E402
from stone_mpe.api import run  # noqa: E402

st.set_page_config(page_title="Impulso Stone · Engajamento MPE", page_icon="🟢", layout="wide")
try:  # cores acompanham o tema (claro/escuro) do Streamlit
    _DARK = st.context.theme.type == "dark"
except Exception:
    _DARK = False
# Identidade Impulso Stone / Clube dos Sonhos. Paletas de gráfico validadas (contraste, daltonismo, separação):
# claro = verde Stone + roxo Impulso; escuro = os mesmos matizes mais claros sobre a tinta #03211D.
BRAND = {"sherwood": "#004132", "lime": "#C7F93C", "purple": "#A780FF", "ink": "#03211D", "deep": "#055046",
         "teal": "#32ADA1", "mist": "#E6EAE9", "smoke": "#EFEFEF"}
SERIES_1, SERIES_2 = ("#3FAF55", "#9A78F0") if _DARK else ("#128C4F", "#8A63E6")
SEQ = ([[0, "#06352E"], [0.5, "#1E8A55"], [1, "#C7F93C"]] if _DARK
       else [[0, "#E9F5EE"], [0.5, "#5FBC87"], [1, "#004132"]])
INK, MUTED, GRID = ("#EFEFEF", "#A9BDB7", "#0E4A40") if _DARK else ("#03211D", "#4A615B", "#E6EAE9")
HOVER_BG = "#06352E" if _DARK else "#FFFFFF"

st.markdown(f"""<style>
.brand-hero {{background:{BRAND['sherwood']};color:#FFFFFF;border-radius:1.25rem;padding:1.6rem 1.8rem 1.4rem;margin:0 0 1rem;
  position:relative;overflow:hidden}}
.brand-hero:after {{content:"";position:absolute;right:-60px;top:-60px;width:220px;height:220px;border-radius:50%;
  background:{BRAND['lime']};opacity:.16}}
.brand-hero .eyebrow {{font-family:Outfit,sans-serif;font-weight:600;font-size:.78rem;letter-spacing:.14em;color:{BRAND['lime']};margin:0}}
.brand-hero h1 {{font-family:Outfit,sans-serif;color:#FFFFFF;font-size:2.1rem;line-height:1.15;margin:.35rem 0 .4rem;padding:0}}
.brand-hero p {{color:#D6E4DF;margin:0;max-width:760px;font-size:.98rem}}
.brand-hero .pill {{display:inline-block;margin-top:.9rem;background:{BRAND['lime']};color:{BRAND['sherwood']};font-weight:700;
  border-radius:999px;padding:.3rem .9rem;font-size:.82rem}}
[data-testid="stMetricValue"] {{font-family:Outfit,sans-serif;font-weight:600}}
{'button[kind="primary"] p, button[kind="primary"] {color:' + BRAND['ink'] + ' !important}' if _DARK else ''}
</style>""", unsafe_allow_html=True)  # CSS estático, sem dados externos

LABELS = {"tipo_post": "Tipo de post", "formato_video": "Formato de vídeo", "tipo_hook": "Tipo de gancho",
          "tema_principal": "Tema", "tom": "Tom", "tipo_cta": "Tipo de CTA", "duracao_faixa": "Duração",
          "legenda_tamanho": "Tamanho da legenda", "tem_rosto": "Rosto", "texto_na_tela": "Texto na tela",
          "prova_social": "Prova social", "criador_e_empreendedor_real": "Criador é empreendedor real",
          "tem_cta": "Tem CTA", "oferta_ou_beneficio_explicito": "Oferta explícita", "usa_linguagem_regional": "Linguagem regional"}
STATUS = {"ok": "✅ pronto", "parcial": "◐ em andamento", "pendente": "○ pendente"}



def _layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=INK, size=13), hoverlabel=dict(bgcolor=HOVER_BG, font_color=INK), showlegend=False)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(color=MUTED))
    return fig


def _n(x) -> str:
    return f"{int(x):,}".replace(",", ".") if pd.notna(x) else "—"


def _pct(x, d: int = 2) -> str:
    return f"{x * 100:.{d}f}%".replace(".", ",") if pd.notna(x) else "—"


@st.cache_resource
def agent_llm():
    """Um cliente de LLM por servidor: modelos esgotados ficam em pausa entre um clique e outro."""
    from stone_mpe.llm import get_client
    return get_client("agent")


@st.cache_data(ttl=60)
def base_stats() -> dict:
    p = config.outputs_dir() / "base_stats.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@st.cache_data(ttl=60)
def top_df(segment: str | None, platform: str | None, tipo_post: str | None) -> pd.DataFrame:
    f = {k: v for k, v in dict(platform=platform, tipo_post=tipo_post).items() if v}
    return patterns.load_top(segment, f)


@st.cache_data(ttl=60)
def segments() -> list[str]:
    return sorted(storage.read_sql("SELECT DISTINCT segmento FROM posts")["segmento"].dropna().tolist())


def roteiro_md(cr, refs: pd.DataFrame, meta: dict, followers: int) -> str:
    lines = [f"# {cr.titulo}", "", f"**Formato:** {cr.formato}", f"**Gancho (0–3 s):** {cr.gancho}", "",
             "## Roteiro", cr.roteiro, "", "## Legenda", cr.legenda, "", f"**CTA:** {cr.cta}", ""]
    if cr.justificativa:
        lines += ["## Por quê", cr.justificativa, ""]
    lines += ["## Inspirado em (posts reais)"]
    for r in refs.itertuples():
        lines.append(f"- @{r.handle} · {r.url} · engajamento {_pct(r.engagement_rate)} · {_n(r.views)} views")
    if meta:
        lines += ["", f"## Metas para um perfil com {_n(followers)} seguidores (curtidas + comentários)",
                  f"- mediana da base: {_n(meta['mediana_da_base'])}",
                  f"- entrar no top 10%: {_n(meta['entrar_no_top'])}",
                  f"- mediana do top: {_n(meta['mediana_do_top'])}"]
    lines += ["", "_Padrões observados em publicações reais de alto desempenho; não garantem resultado._"]
    return "\n".join(lines)


def ref_gallery(df: pd.DataFrame, cols: int = 5) -> None:
    """Capas dos posts reais com métricas (o vídeo mais próximo do que se quer gravar)."""
    if df is None or df.empty:
        return
    grid = st.columns(cols)
    for k, r in enumerate(df.itertuples()):
        with grid[k % cols]:
            tp = thumb_path(r.post_id)
            if tp.exists() and tp.stat().st_size > 0:
                st.image(str(tp), width="stretch")
            st.markdown(f"[@{r.handle}]({r.url}) · {r.platform}")
            views = getattr(r, "views", None)
            st.caption(f"engajamento **{_pct(r.engagement_rate)}** · {_n(r.likes)} curtidas · {_n(r.comments)} coment."
                       + (f" · {_n(views)} views" if pd.notna(views) else "") + f" · {_n(r.followers)} seguidores")


def storyboard_grid(cr, key: str, per_row: int = 4) -> None:
    cs = storyboard.scenes(cr)
    for start in range(0, len(cs), per_row):
        cols = st.columns(per_row)
        for k, c in enumerate(cs[start:start + per_row]):
            i = start + k + 1
            with cols[k]:
                st.markdown(storyboard.svg_frame(c, i, uid=key), unsafe_allow_html=True)
                st.caption(f"**{c.tempo or f'cena {i}'}** · {storyboard.PLANO_LABEL.get(c.plano, c.plano)}  \n{c.visual}")


if release.ensure_db():  # clone novo: monta a base pública de data/release/
    st.toast("Base pública carregada de data/release/ (sem legendas e capas).")
if not storage.table_exists("posts"):
    st.error("Base ainda não construída. Rode `python -m stone_mpe.cli build-base`.")
    st.stop()

st.markdown("""<div class="brand-hero"><p class="eyebrow">IMPULSO STONE · STONE × INTELI ACADEMY</p>
<h1>Conteúdo de alto engajamento para MPEs</h1>
<p>Do começo ao crescimento: o que as publicações que mais engajam pequenos empreendedores têm em comum,
e roteiros prontos para o Impulso Stone ligados a posts reais.</p>
<span class="pill">Padrões observados no top 10% · correlação, não garantia</span></div>""", unsafe_allow_html=True)

tab_how, tab_rot, tab_nic, tab_pad, tab_idp, tab_perf, tab_base = st.tabs(
    ["Como funciona", "Gerar roteiro", "Nichos", "Padrões do top", "Métrica ponderada", "Perfis em destaque", "Base"])

# ---------------- Como funciona ----------------
with tab_how:
    steps = status.pipeline()
    st.markdown("**Dados públicos entram, viram uma base ranqueada, cada post de sucesso é descrito por uma rubrica fixa, "
                "e o agente transforma os padrões em roteiros que citam os posts reais de onde vieram.**")
    for row in range(0, len(steps), 3):
        cols = st.columns(3)
        for col, s in zip(cols, steps[row:row + 3]):
            with col.container(border=True):
                st.markdown(f"**{s['etapa']}** · {STATUS[s['status']]}")
                st.markdown(f"<span style='font-size:1.9rem;font-weight:600'>{_n(s['numero'])}</span>", unsafe_allow_html=True)
                st.caption(s["detalhe"])
                st.code(s["comando"], language=None, wrap_lines=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Do volume ao que sustenta os padrões")
        by = {s["etapa"]: s["numero"] for s in steps}
        funnel = pd.DataFrame({"etapa": ["Coletados", "Elegíveis", "Top 10%", "Categorizados (top)", "Rotulados à mão"],
                               "n": [by["2. Coleta"], by["3. Base e métrica"], by["4. Top 10%"], by["5. Categorização"],
                                     by["6. Validação manual"]]})
        fig = go.Figure(go.Bar(x=funnel["n"], y=funnel["etapa"], orientation="h", marker=dict(color=SERIES_1, cornerradius=4),
                               text=[_n(v) for v in funnel["n"]], textposition="outside",
                               hovertemplate="%{y}: %{x:,} publicações<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        fig.update_xaxes(title="publicações", range=[0, funnel["n"].max() * 1.12])
        st.plotly_chart(_layout(fig, 280), width="stretch")
        st.caption("A validação manual usa 50 posts do top, sorteados por faixa de tamanho do perfil.")
    with c2:
        st.subheader("A métrica, num exemplo real")
        ex = storage.read_sql("""SELECT handle, url, likes, comments, followers, views, engagement_rate, percentile
                                 FROM posts WHERE is_top = 1 ORDER BY percentile DESC, engagement_rate DESC LIMIT 1""")
        if not ex.empty:
            e = ex.iloc[0]
            st.markdown(f"[@{e.handle}]({e.url}) tem **{_n(e.followers)} seguidores**. O post teve "
                        f"**{_n(e.likes)} curtidas + {_n(e.comments)} comentários**.")
            st.latex(r"\frac{%s + %s}{%s} = %s" % (_n(e.likes), _n(e.comments), _n(e.followers), _pct(e.engagement_rate, 1).replace(",", "{,}").replace("%", r"\%")))
            bs = base_stats()
            thr = bs.get("er_threshold_by_platform", {})
            st.caption("Entra no top quem passa do percentil 90 da sua plataforma: " +
                       " · ".join(f"{p} ≥ {_pct(v)}" for p, v in thr.items()) +
                       ". Dividir por seguidores permite comparar contas de 3 mil e de 3 milhões.")

    st.subheader("Como um pedido vira roteiro")
    st.markdown(
        "1. **validar_entrada**: confere o pedido e infere segmento e tipo de post pelas palavras usadas.\n"
        "2. **consulta_base**: SQL no top do recorte; conta a frequência de cada característica. Se o recorte tiver "
        f"menos de {config.get('agent.confidence_min_posts', 10)} posts, amplia e marca **confiança baixa**.\n"
        "3. **posts_referencia**: escolhe os posts mais parecidos com o pedido (BM25) e de maior engajamento, "
        f"no máximo {config.get('agent.max_refs_per_creator', 2)} por criador.\n"
        "4. **gerar_criativo**: o LLM só *redige* gancho, roteiro, legenda e CTA a partir desses números e posts.\n"
        "5. **validar_saida**: descarta qualquer `post_id` que não veio da base e pede nova versão (até 2 vezes).\n"
        "6. **registrar**: grava a execução em `outputs/runs.jsonl`. Sem LLM disponível, um template usa os mesmos dados.")

# ---------------- Gerar roteiro ----------------
with tab_rot:
    examples = [q["query"] for q in demo_cache.DEMO_QUERIES]
    c1, c2 = st.columns([1, 3])
    mode = c1.radio("Modo", ["gerar_criativo", "recomendar", "analisar"],
                    format_func={"gerar_criativo": "Roteiro de vídeo", "recomendar": "Recomendação", "analisar": "Análise"}.get)
    offline = c1.toggle("Modo offline (respostas salvas)", value=True, help="Usa respostas pré-computadas: para apresentar sem internet.")
    query = c2.text_area("O que você quer criar?", value=examples[2], height=80)
    c3, c4, c5, c6 = st.columns(4)
    seg_opt = c3.selectbox("Segmento", ["(inferir do pedido)"] + segments())
    segment = None if seg_opt.startswith("(") else seg_opt
    platform = c4.selectbox("Plataforma", ["(todas)", "youtube", "instagram"], key="ag_plat")
    size = c5.selectbox("Tamanho dos perfis de referência", ["(todos)", "micro", "medio", "grande"])
    n_cr = c6.number_input("Roteiros", 1, 3, 1)
    c7, c8 = st.columns([3, 1])
    followers = c7.number_input("Seguidores do perfil que vai publicar (para calcular metas)", min_value=100, value=10000, step=1000)
    pub_plat = c8.selectbox("Onde vai publicar", ["instagram", "youtube"])

    if st.button("Gerar", type="primary"):
        out = None
        if offline:
            out = demo_cache.get(mode, query, segment)
            if not out:
                st.warning("Pedido não está nas respostas salvas; executando ao vivo.")
        if out is None:
            filters = {k: v for k, v in dict(platform=None if platform == "(todas)" else platform,
                                              profile_size=None if size == "(todos)" else size).items() if v}
            with st.spinner("Consultando a base e redigindo..."):
                try:
                    out = run(mode, query, segment=segment, filters=filters or None, n_creatives=int(n_cr), llm=agent_llm())
                except Exception as e:
                    out = demo_cache.get(mode, query, segment)
                    st.error(f"Falha ao vivo ({e}); {'usando resposta salva' if out else 'sem resposta salva para este pedido'}.")
        st.session_state.out = out

    out = st.session_state.get("out")
    if out:
        badge = "⚠️ confiança baixa (recorte pequeno ou ampliado)" if out.confidence_flag else "✅ confiança adequada"
        st.markdown(f"**{badge}** · recorte: `{out.segment_used or 'todos os segmentos'}` · "
                    f"redação: `{out.llm if out.llm != 'none' else 'template (sem LLM)'}` · execução `{out.run_id}`")
        st.markdown(out.explanation)

        nicho = out.segment_used if out.segment_used in segments() else None
        bm = status.benchmarks(pub_plat, nicho) or status.benchmarks(pub_plat)
        meta = status.goals(int(followers), bm)
        all_refs = status.reference_metrics([r.post_id for r in out.reference_posts])

        for i, cr in enumerate(out.creatives, 1):
            refs = all_refs[all_refs.post_id.isin(cr.inspired_by)]
            with st.container(border=True):
                st.markdown(f"### Roteiro {i}: {cr.titulo}")
                st.markdown(f"**Formato:** {cr.formato}")
                st.markdown(f"<div style='font-size:1.35rem;font-weight:600;margin:.4rem 0'>🎬 0–3 s: “{html.escape(cr.gancho)}”</div>",
                            unsafe_allow_html=True)
                t_sb, t_txt, t_ref = st.tabs(["Storyboard ilustrado", "Roteiro e legenda", "Vídeos de referência"])
                with t_sb:
                    storyboard_grid(cr, key=f"{out.run_id}{i}")
                    st.caption("Quadros 9:16: ilustração do tipo de plano, texto na tela como no vídeo e a fala como legenda.")
                with t_txt:
                    a, b = st.columns([3, 2])
                    with a:
                        st.markdown("**Roteiro de gravação**")
                        st.markdown(cr.roteiro)
                        st.markdown(f"**CTA:** {cr.cta}")
                    with b:
                        st.markdown("**Legenda (copiar)**")
                        st.code(cr.legenda, language=None, wrap_lines=True)
                    if cr.justificativa:
                        st.caption(cr.justificativa)
                with t_ref:
                    st.caption("Posts reais de alto desempenho que inspiraram este roteiro: o mais próximo do vídeo a gravar.")
                    ref_gallery(refs, cols=4)
                d1, d2, _ = st.columns([1, 1, 2])
                d1.download_button("Baixar storyboard (.html)",
                                   storyboard.storyboard_html(cr, refs, meta, int(followers), niches.NOMES.get(nicho, nicho) if nicho else None),
                                   file_name=f"storyboard_{out.run_id}_{i}.html", mime="text/html", key=f"sb{i}")
                d2.download_button("Baixar roteiro (.md)", roteiro_md(cr, refs, meta, int(followers)),
                                   file_name=f"roteiro_{out.run_id}_{i}.md", key=f"dl{i}")

        st.subheader("Métricas: de onde vem e aonde mirar")
        if meta:
            m = st.columns(4)
            st.caption(f"Metas no **{pub_plat}**" + (f", nicho **{niches.NOMES.get(nicho, nicho)}**" if nicho else "") + ".")
            m[0].metric("Mediana do nicho" if nicho else "Mediana da base", _n(meta["mediana_da_base"]),
                        help=f"{_pct(bm['mediana_geral'], 3)} dos seguidores")
            m[1].metric("Para entrar no top 10%", _n(meta["entrar_no_top"]), help=f"{_pct(bm['limiar_top'])} dos seguidores")
            m[2].metric("Mediana do top", _n(meta["mediana_do_top"]), help=f"{_pct(bm['mediana_top'])} dos seguidores")
            m[3].metric("Views por seguidor (top)", f"{bm['views_por_seguidor_top']:.1f}".replace(".", ",") if bm.get("views_por_seguidor_top") else "n/d",
                        help="Alcance relativo (fora do ranking). No Instagram, a coleta básica não traz views.")
            st.caption(f"Curtidas + comentários que um post precisaria para um perfil com {_n(followers)} seguidores, "
                       f"calculado sobre {_n(bm['n'])} publicações elegíveis. São referências observadas, não previsões.")
        if not all_refs.empty:
            r = all_refs.sort_values("engagement_rate")
            fig = go.Figure(go.Bar(x=r["engagement_rate"] * 100, y="@" + r["handle"] + " · " + r["post_id"].str[-6:], orientation="h",
                                   marker=dict(color=SERIES_1, cornerradius=4), text=[_pct(v, 1) for v in r["engagement_rate"]],
                                   textposition="outside", customdata=r[["views", "likes", "comments", "followers"]],
                                   hovertemplate="%{y}<br>engajamento %{x:.2f}%<br>%{customdata[0]:,} views · %{customdata[1]:,} curtidas"
                                                 " · %{customdata[2]:,} comentários<br>%{customdata[3]:,} seguidores<extra></extra>"))
            # linhas de referência só quando as referências são de uma plataforma (escalas diferentes)
            rplats = r["platform"].unique()
            bm_r = status.benchmarks(rplats[0], nicho) if len(rplats) == 1 else {}
            lab_med = "mediana do nicho" if nicho else "mediana da base"
            for k, (val, lab) in enumerate([(bm_r.get("mediana_geral"), f"{lab_med} ({rplats[0]})" if bm_r else lab_med),
                                            (bm_r.get("limiar_top"), "entrada no top")]):
                if val:
                    fig.add_vline(x=val * 100, line=dict(color=MUTED, width=1, dash="dot"))
                    fig.add_annotation(x=val * 100, y=1 + 0.09 * (k + 1), yref="paper", text=f"{lab} {_pct(val)}", showarrow=False,
                                       font=dict(color=MUTED, size=11), xanchor="left", xshift=3)
            fig.update_xaxes(title="engajamento (%)", range=[0, r["engagement_rate"].max() * 100 * 1.15])
            fig.update_layout(margin=dict(t=48))
            st.plotly_chart(_layout(fig, 120 + 46 * len(r)).update_layout(margin=dict(t=48)), width="stretch")
            st.dataframe(all_refs.assign(perfil="@" + all_refs.handle)[
                ["perfil", "faixa", "followers", "views", "likes", "comments", "engagement_rate", "percentile", "url"]],
                hide_index=True, column_config={
                    "url": st.column_config.LinkColumn("link"), "followers": st.column_config.NumberColumn("seguidores", format="localized"),
                    "views": st.column_config.NumberColumn(format="localized"), "likes": st.column_config.NumberColumn("curtidas", format="localized"),
                    "comments": st.column_config.NumberColumn("comentários", format="localized"),
                    "engagement_rate": st.column_config.NumberColumn("engajamento", format="percent"),
                    "percentile": st.column_config.NumberColumn("percentil", format="percent")})
        if out.findings:
            st.markdown("**Por que esses elementos:** frequência no top do recorte")
            fd = pd.DataFrame([f.model_dump() for f in out.findings])
            fd = fd[~fd.feature.str.startswith("tipo_post=") & ~fd.feature.str.endswith("=não")]
            fd = fd.sort_values("frequency", ascending=False).head(12).sort_values("frequency")
            fig = go.Figure(go.Bar(x=fd["frequency"] * 100, y=fd["feature"], orientation="h", marker=dict(color=SERIES_1, cornerradius=4),
                                   text=[f"{v * 100:.0f}% ({n}/{t})" for v, n, t in zip(fd["frequency"], fd["n_posts"], fd["total"])],
                                   textposition="outside", hovertemplate="%{y}: %{x:.0f}%<extra></extra>"))
            fig.update_xaxes(title="% dos posts de alto desempenho do recorte", range=[0, 118])
            st.plotly_chart(_layout(fig, 60 + 30 * len(fd)), width="stretch")

# ---------------- Nichos ----------------
with tab_nic:
    st.markdown("**Quanto cada nicho empreendedor engaja, quanto chega ao top e o que o top de cada nicho usa.**")
    n1, n2 = st.columns([1, 3])
    nplat = n1.radio("Plataforma", ["instagram", "youtube", "(ambas)"], key="nic_plat",
                     help="Instagram e YouTube têm escalas diferentes de engajamento: compare nichos dentro da mesma plataforma.")
    pf = None if nplat == "(ambas)" else nplat
    ns = niches.summary(pf)
    if ns.empty:
        st.info("Sem dados para esta plataforma.")
    else:
        with n2:
            r = ns.sort_values("er_mediana")
            fig = go.Figure(go.Bar(x=r["er_mediana"] * 100, y=r["nome"], orientation="h", marker=dict(color=SERIES_1, cornerradius=4),
                                   text=[_pct(v) for v in r["er_mediana"]], textposition="outside",
                                   customdata=r[["posts", "perfis", "er_p90", "taxa_top"]],
                                   hovertemplate="%{y}: mediana %{x:.2f}%<br>p90 %{customdata[2]:.2%} · %{customdata[3]:.0%} dos posts no top"
                                                 "<br>%{customdata[0]} posts de %{customdata[1]} perfis<extra></extra>"))
            fig.update_xaxes(title="engajamento mediano (%): (curtidas + comentários) ÷ seguidores", range=[0, r["er_mediana"].max() * 118])
            st.plotly_chart(_layout(fig, 70 + 40 * len(r)), width="stretch", key="nic_bar")
        tbl = ns.assign(formato=[f"{f} ({p * 100:.0f}%)" if isinstance(f, str) else "ainda não categorizado"
                                 for f, p in zip(ns.formato_top, ns.formato_top_pct)],
                        gancho=ns.gancho_top.fillna("—"), tema=ns.tema_top.fillna("—"), duracao=ns.duracao_top.fillna("—"))
        for c in ("views_por_seguidor", "cta_no_top", "er_mediana_top"):
            tbl[c] = pd.to_numeric(tbl[c], errors="coerce")
        st.dataframe(
            tbl[["nome", "perfis", "posts", "posts_top", "taxa_top", "er_mediana", "er_p90", "er_mediana_top", "views_por_seguidor",
                 "formato", "gancho", "tema", "duracao", "cta_no_top"]],
            hide_index=True, column_config={
                "nome": "nicho", "posts_top": "no top", "taxa_top": st.column_config.NumberColumn("% no top", format="percent"),
                "er_mediana": st.column_config.NumberColumn("engaj. mediano", format="percent"),
                "er_p90": st.column_config.NumberColumn("engaj. p90", format="percent"),
                "er_mediana_top": st.column_config.NumberColumn("mediana do top", format="percent"),
                "views_por_seguidor": st.column_config.NumberColumn("views/seguidor", format="%.2f"),
                "formato": "formato mais comum no top", "gancho": "gancho", "tema": "tema", "duracao": "duração",
                "cta_no_top": st.column_config.NumberColumn("top com CTA", format="percent")})
        st.caption("No Instagram há poucos perfis por nicho: leia como sinal, não como regra. “% no top” usa o limiar da plataforma.")

        st.subheader("Detalhe do nicho")
        d1, d2 = st.columns(2)
        pick = d1.selectbox("Nicho", ns["nicho"].tolist(), format_func=lambda k: niches.NOMES.get(k, k))
        fol = d2.number_input("Seguidores do perfil", min_value=100, value=10000, step=1000, key="nic_fol")
        row = ns.set_index("nicho").loc[pick]
        g = status.goals(int(fol), status.benchmarks(pf, pick))
        k = st.columns(4)
        k[0].metric("Engajamento mediano", _pct(row.er_mediana))
        k[1].metric("Posts que chegam ao top", _pct(row.taxa_top, 0))
        k[2].metric("Meta para entrar no top", _n(g.get("entrar_no_top")) if g else "—", help="curtidas + comentários")
        k[3].metric("Mediana do top no nicho", _n(g.get("mediana_do_top")) if g and g.get("mediana_do_top") is not None else "—",
                    help="curtidas + comentários")
        dt = top_df(pick, pf, None)
        if not dt.empty:
            cc = st.columns(3)
            for col, fld in zip(cc, ["formato_video", "tipo_hook", "tema_principal"]):
                fr = patterns.frequencies(dt, [fld]).head(5).sort_values("freq")
                fig = go.Figure(go.Bar(x=fr["freq"] * 100, y=fr["value"], orientation="h", marker=dict(color=SERIES_1, cornerradius=4),
                                       text=[f"{v * 100:.0f}%" for v in fr["freq"]], textposition="outside",
                                       hovertemplate="%{y}: %{x:.0f}%<extra></extra>"))
                fig.update_xaxes(range=[0, 118], showticklabels=False)
                col.markdown(f"**{LABELS[fld]}** no top ({len(dt)} posts)")
                col.plotly_chart(_layout(fig, 50 + 34 * len(fr)), width="stretch", key=f"nic_{fld}")
        st.markdown("**Posts de maior engajamento do nicho**")
        ref_gallery(niches.top_posts(pick, 5, pf), cols=5)
        if st.button(f"Gerar roteiro para {niches.NOMES.get(pick, pick)}", key="nic_go"):
            with st.spinner("Consultando o nicho e redigindo..."):
                st.session_state.out = run("gerar_criativo", f"Vídeo curto para atrair empreendedores de {niches.NOMES.get(pick, pick).lower()} "
                                           "para o Impulso Stone", segment=pick, filters={"platform": pf} if pf else None,
                                           llm=agent_llm())
            st.success("Roteiro pronto: abra a aba **Gerar roteiro**.")

# ---------------- Padrões ----------------
with tab_pad:
    f1, f2, f3 = st.columns(3)
    seg = f1.selectbox("Segmento", ["(todos)"] + segments())
    plat = f2.selectbox("Plataforma", ["(todas)", "instagram", "youtube"])
    tp = f3.selectbox("Tipo de post", ["(todos)", "reels", "carrossel", "imagem", "short"])
    df = top_df(None if seg == "(todos)" else seg, None if plat == "(todas)" else plat, None if tp == "(todos)" else tp)
    if df.empty:
        st.info("Nenhuma publicação de alto desempenho categorizada neste recorte.")
    else:
        if len(df) < config.get("agent.confidence_min_posts", 10):
            st.warning(f"⚠️ Recorte com apenas {len(df)} publicações: padrões frágeis.")
        conc = patterns.concentration(df)
        if conc:
            st.caption(f"{len(df)} posts de {conc['n_criadores']} criadores · os 4 maiores somam {conc['share_top4'] * 100:.0f}% do recorte. "
                       "Compare “% dos posts” com “% por criador” (cada criador pesa igual) para separar padrão de estilo de um canal.")
        field = st.selectbox("Característica", list(LABELS), format_func=lambda k: LABELS[k], index=1)
        fr = patterns.frequencies(df, [field]).sort_values("freq")
        fig = go.Figure()
        # barras horizontais agrupadas empilham de baixo para cima: a 2ª série entra primeiro para "% dos posts" ficar em cima
        fig.add_trace(go.Bar(x=fr["freq_por_criador"] * 100, y=fr["value"], orientation="h", name="% por criador",
                             marker=dict(color=SERIES_2, cornerradius=4), hovertemplate="%{y}: %{x:.0f}% com cada criador pesando igual<extra></extra>"))
        fig.add_trace(go.Bar(x=fr["freq"] * 100, y=fr["value"], orientation="h", name="% dos posts", marker=dict(color=SERIES_1, cornerradius=4),
                             customdata=fr[["n", "total", "n_criadores"]],
                             hovertemplate="%{y}: %{x:.0f}% dos posts (%{customdata[0]} de %{customdata[1]}) · %{customdata[2]} criadores<extra></extra>"))
        fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
        fig.update_xaxes(title=f"% das {len(df)} publicações de alto desempenho",
                         range=[0, min(100, max(fr["freq"].max(), fr["freq_por_criador"].max()) * 118)])
        _layout(fig, 80 + 56 * len(fr)).update_layout(showlegend=True, legend=dict(orientation="h", y=1.08, x=0, traceorder="reversed"))
        st.plotly_chart(fig, width="stretch")
        st.markdown("**Exemplos reais**")
        m = df.set_index("post_id")
        for r in fr.sort_values("freq", ascending=False).head(4).itertuples():
            links = " · ".join(f"[@{m.at[i, 'handle']}]({m.at[i, 'url']})" for i in r.example_post_ids)
            st.markdown(f"- **{r.value}** ({r.n_criadores} criadores): {links}")
        st.subheader("Tema × formato")
        ct = patterns.crosstab(df)
        if not ct.empty:
            fig = go.Figure(go.Heatmap(z=ct.values, x=ct.columns, y=ct.index, colorscale=SEQ, xgap=2, ygap=2, text=ct.values,
                                       texttemplate="%{text}", hovertemplate="%{y} × %{x}: %{z} posts<extra></extra>", showscale=False))
            st.plotly_chart(_layout(fig, 80 + 34 * len(ct)), width="stretch")
        try:
            lf = patterns.lift(["formato_video", "tipo_hook", "tema_principal", "tipo_cta", "tom"])
            if not lf.empty:
                st.subheader("Top × resto da base (lift)")
                st.caption("lift > 1: mais comum no top do que numa amostra aleatória de fora do top. "
                           "Ajuda a separar o que é do sucesso do que é só do nicho.")
                st.dataframe(lf[["field", "value", "n_top", "freq_top", "freq_rest", "lift"]].round(2), hide_index=True)
        except Exception:
            pass

# ---------------- Métrica ponderada ----------------
with tab_idp:
    st.markdown("**Índice de Desempenho Ponderado (IDP).** A métrica oficial compara todos os posts da plataforma entre si. "
                "O IDP compara cada post com os seus pares e soma os percentis com pesos: o mesmo **nicho**, a mediana do "
                "próprio **perfil** (o post foi acima do normal do criador?), o mesmo **período** (tendência da plataforma) "
                "e contas do mesmo **porte**. É uma leitura complementar: o ranking oficial do case continua sendo o principal.")
    wc = st.columns(4)
    w_in = {
        "nicho": wc[0].slider("Nicho", 0.0, 1.0, 0.35, 0.05, help="percentil dentro do mesmo segmento e plataforma"),
        "perfil": wc[1].slider("Perfil", 0.0, 1.0, 0.30, 0.05, help="engajamento ÷ mediana do próprio criador"),
        "periodo": wc[2].slider("Período", 0.0, 1.0, 0.20, 0.05, help="percentil entre posts do mesmo trimestre"),
        "porte": wc[3].slider("Porte", 0.0, 1.0, 0.15, 0.05, help="percentil entre contas da mesma faixa de seguidores"),
    }
    if sum(w_in.values()) == 0:
        st.warning("Dê peso a pelo menos um componente.")
    else:
        idp_df = weighted.compute(weight_override=w_in)
        summ = weighted.summary(idp_df, weight_override=w_in)
        for plat, d in summ.get("plataformas", {}).items():
            st.markdown(f"**{plat.capitalize()}** · {_n(d['elegiveis'])} posts elegíveis")
            m = st.columns(4)
            m[0].metric("Top em comum com o oficial", _pct(d["sobreposicao"], 0),
                        help=f"{d['em_ambos']} de {d['top_idp']} posts do top do IDP também estão no top oficial")
            m[1].metric("Criadores no top", d["concentracao_idp"]["criadores"],
                        delta=d["concentracao_idp"]["criadores"] - d["concentracao_oficial"]["criadores"],
                        help="criadores diferentes no top; o delta compara com o ranking oficial")
            m[2].metric("4 maiores criadores somam", _pct(d["concentracao_idp"]["top4_share"], 0),
                        delta=f"{(d['concentracao_idp']['top4_share'] - d['concentracao_oficial']['top4_share']) * 100:+.0f} p.p.",
                        delta_color="inverse", help="participação dos 4 criadores com mais posts no top; menor = padrão mais distribuído")
            m[3].metric("Top do IDP já categorizado", _pct(d["idp_categorizados"] / d["top_idp"] if d["top_idp"] else None, 0),
                        help="os padrões abaixo usam só os posts com categorização")
        tp = weighted.top_patterns(idp_df)
        if not tp.empty:
            st.subheader("Os padrões se mantêm?")
            st.caption("Valores mais frequentes no top oficial e no top do IDP. Barras parecidas = o padrão não depende de nicho, "
                       "perfil, época ou porte.")
            f_sel = st.selectbox("Característica", ["tipo_hook", "formato_video", "tema_principal", "tipo_cta", "tom", "duracao_faixa"],
                                 format_func=lambda k: LABELS.get(k, k), key="idp_field")
            g = tp[tp["field"] == f_sel]
            vals = list(dict.fromkeys(g.sort_values("freq", ascending=False)["value"]))[::-1]
            fig = go.Figure()
            for name, color, label in [("idp", SERIES_2, "Top do IDP"), ("oficial", SERIES_1, "Top oficial")]:
                gg = g[g["ranking"] == name].set_index("value").reindex(vals)
                fig.add_trace(go.Bar(x=gg["freq"] * 100, y=vals, orientation="h", name=label, marker=dict(color=color, cornerradius=4),
                                     hovertemplate="%{y}: %{x:.0f}%<extra>" + label + "</extra>"))
            fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
            fig.update_xaxes(title="% dos posts categorizados de cada top")
            _layout(fig, 80 + 60 * len(vals)).update_layout(showlegend=True, legend=dict(orientation="h", y=1.1, x=0, traceorder="reversed"))
            st.plotly_chart(fig, width="stretch")
        st.subheader("Posts com maior IDP")
        show = idp_df.sort_values("idp", ascending=False).head(15).merge(
            storage.read_sql("SELECT post_id, url FROM posts"), on="post_id", how="left")
        st.dataframe(show[["handle", "platform", "segmento", "faixa", "engagement_rate", "c_nicho", "c_perfil", "c_periodo", "c_porte",
                           "idp", "is_top", "url"]]
                     .rename(columns={"engagement_rate": "engajamento", "c_nicho": "nicho", "c_perfil": "perfil", "c_periodo": "período",
                                      "c_porte": "porte", "is_top": "no top oficial"}),
                     hide_index=True, column_config={
                         "engajamento": st.column_config.NumberColumn(format="percent"),
                         "idp": st.column_config.ProgressColumn("IDP", format="%.2f", min_value=0, max_value=1),
                         "url": st.column_config.LinkColumn("link"),
                         "no top oficial": st.column_config.CheckboxColumn()})

# ---------------- Perfis ----------------
with tab_perf:
    df_all = top_df(None, None, None)
    feat = creators.featured(df_all)
    if feat.empty:
        st.info("Sem dados.")
    else:
        st.dataframe(feat[["handle", "platform", "faixa", "segmento", "n_top", "taxa_no_top", "tema_predominante", "formato_predominante"]]
                     .rename(columns={"taxa_no_top": "% dos posts no top"}), hide_index=True,
                     column_config={"% dos posts no top": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})
    lead = lead_signals.cta_summary(df_all)
    cm = comments.summary()
    if lead:
        st.subheader("Sinais de lead")
        c = st.columns(3)
        c[0].metric("Top com CTA explícita", f"{lead['share_com_cta'] * 100:.0f}%")
        c[1].metric("Oferta/benefício explícito", f"{lead['share_oferta_explicita'] * 100:.0f}%")
        c[2].metric("Comentários por curtida (mediana)", f"{lead['mediana_comentarios_por_curtida']:.3f}".replace(".", ","))
        if cm:
            st.caption(f"{cm['comentarios_analisados']} comentários de {cm['posts']} posts: intenção de contato {cm['taxa_contato'] * 100:.1f}% · "
                       f"dúvidas {cm['taxa_duvida'] * 100:.1f}% · objeções {cm['taxa_objecao'] * 100:.1f}%")

# ---------------- Base ----------------
with tab_base:
    s = base_stats()
    c = st.columns(4)
    c[0].metric("Publicações coletadas", _n(s.get("n_posts_raw", 0)))
    c[1].metric("Elegíveis (≥ 14 dias)", _n(s.get("n_posts_eligible", 0)))
    c[2].metric("Alto desempenho (top 10%)", _n(s.get("n_top", 0)))
    c[3].metric("Perfis", s.get("n_profiles", 0))
    st.caption(f"Publicadas de {s.get('posted_from')} a {s.get('posted_to')} · coletadas de {s.get('collected_from')} a {s.get('collected_to')} "
               f"· percentil por {'plataforma' if s.get('ranking_scope') == 'platform' else 'base combinada'}")
    posts = storage.read_sql("SELECT platform, faixa, engagement_rate, is_top FROM posts WHERE eligible = 1 AND engagement_rate > 0")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Taxa de engajamento por plataforma")
        fig = go.Figure()
        for i, (plat, g) in enumerate(posts.groupby("platform")):
            fig.add_trace(go.Box(x=g["engagement_rate"] * 100, name=plat, marker_color=[SERIES_1, SERIES_2][i % 2],
                                 boxpoints=False, line_width=2, hovertemplate="%{x:.2f}%<extra>" + plat + "</extra>"))
            thr = s.get("er_threshold_by_platform", {}).get(plat)
            if thr:
                fig.add_annotation(x=thr * 100, y=plat, text=f"p90 {thr * 100:.1f}%", showarrow=True, arrowhead=0, ax=0, ay=-22,
                                   font=dict(color=MUTED, size=11))
        fig.update_xaxes(title="engajamento (%) — escala log", type="log")
        st.plotly_chart(_layout(fig), width="stretch")
    with col2:
        st.subheader("Perfis por faixa de tamanho")
        prof = storage.read_sql("SELECT faixa, COUNT(*) n FROM profiles GROUP BY faixa")
        prof["faixa"] = pd.Categorical(prof["faixa"], ["micro", "medio", "grande"], ordered=True)
        prof = prof.sort_values("faixa")
        fig = go.Figure(go.Bar(x=prof["n"], y=prof["faixa"], orientation="h", marker=dict(color=SERIES_1, cornerradius=4),
                               text=prof["n"], textposition="outside", hovertemplate="%{y}: %{x} perfis<extra></extra>"))
        st.plotly_chart(_layout(fig, 260), width="stretch")
        st.caption("micro ≤ 10 mil · médio 10–100 mil · grande > 100 mil seguidores")
    with st.expander("Exclusões e limitações"):
        st.json(s.get("exclusions", {}))
        st.markdown("- Seguidores medidos na data de coleta, não na data do post.\n- Impulsionamento pago não é visível publicamente.\n"
                    "- Shorts identificados por duração ≤ 180 s.\n- Poucos canais concentram boa parte do top (ver aba Padrões).")
