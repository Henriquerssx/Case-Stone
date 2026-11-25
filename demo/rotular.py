"""Rotulagem manual da amostra de validação (TAP §6.1). Uso: streamlit run demo/rotular.py

- Mostra um post por vez: vídeo, capa, legenda e link.
- NÃO mostra a categorização do modelo (rotulagem cega).
- Cada "Salvar" grava validation/manual_sample.csv. Pode fechar e voltar: os rótulos ficam salvos.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stone_mpe.analysis import agreement  # noqa: E402
from stone_mpe.multimodal import rubric as R  # noqa: E402

st.set_page_config(page_title="Rotulagem manual", layout="wide")

GUIA = {
    "formato_video": "Estrutura do vídeo. talking head = pessoa falando para a câmera; lista/dicas = '3 erros que...'; trend = áudio/formato viral.",
    "tipo_hook": "Como os primeiros 3 s prendem: pergunta, promessa de resultado, dor do público, número, polêmica ou curiosidade.",
    "tema_principal": "Assunto principal para o dono do negócio.",
    "tom": "Registro predominante da comunicação.",
    "tipo_cta": "Chamada explícita (legenda, fala ou tela). Sem chamada = nenhum.",
    "tem_rosto": "Aparece rosto humano de forma relevante.",
    "criador_e_empreendedor_real": "Quem aparece/fala tem negócio próprio (não só influenciador ou marca).",
    "prova_social": "Depoimento, número de clientes, resultado de terceiros, antes/depois.",
    "texto_na_tela": "Há texto sobreposto ao vídeo.",
    "usa_linguagem_regional": "Gírias ou expressões regionais marcadas.",
    "tem_cta": "Existe alguma chamada para ação explícita.",
    "oferta_ou_beneficio_explicito": "Promete um benefício concreto ou faz uma oferta.",
    "forca_hook_0a10": "0 = abertura genérica; 10 = impossível não continuar assistindo.",
    "clareza_mensagem_0a10": "0 = confuso; 10 = a mensagem é entendida em uma frase.",
}
OPCOES = {"formato_video": R.FormatoVideo, "tipo_hook": R.TipoHook, "tema_principal": R.Tema, "tom": R.Tom, "tipo_cta": R.TipoCta}


def _video_id(url: str) -> str | None:
    m = re.search(r"(?:shorts/|v=|youtu\.be/)([\w-]{11})", str(url))
    return m.group(1) if m else None


def _load() -> pd.DataFrame | None:
    p = agreement.sample_path()
    if not p.exists():
        return None
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")


@st.cache_data
def _captions(ids: tuple[str, ...]) -> dict[str, str]:
    """Legendas vêm do banco local: o CSV versionado não guarda texto de terceiros."""
    from stone_mpe import storage
    try:
        d = storage.read_sql(f"SELECT post_id, caption FROM posts WHERE post_id IN ({','.join('?' * len(ids))})", ids)
    except Exception:
        return {}
    return dict(zip(d["post_id"], d["caption"].fillna("")))


def _done(row: pd.Series) -> bool:
    return all(str(row.get(f, "")).strip() != "" for f in agreement.LABEL_FIELDS if f != "formato_video" or row.get("media_type") in ("short", "reels", "video"))


df = _load()
st.title("Rotulagem manual · amostra de validação")
if df is None:
    st.warning("Amostra ainda não gerada.")
    if st.button("Gerar amostra de 50 posts do top"):
        agreement.make_sample(50)
        st.rerun()
    st.stop()

feitos = df.apply(_done, axis=1)
st.progress(feitos.mean(), text=f"{int(feitos.sum())} de {len(df)} rotulados")

if "i" not in st.session_state:
    pend = [i for i, ok in enumerate(feitos) if not ok]
    st.session_state.i = pend[0] if pend else 0
i = st.session_state.i
row = df.iloc[i]

nav = st.columns([1, 1, 2, 3])
if nav[0].button("◀ Anterior", disabled=i == 0):
    st.session_state.i -= 1
    st.rerun()
if nav[1].button("Próximo ▶", disabled=i == len(df) - 1):
    st.session_state.i += 1
    st.rerun()
if nav[2].button("Próximo pendente"):
    pend = [j for j, ok in enumerate(feitos) if not ok and j != i]
    if pend:
        st.session_state.i = next((j for j in pend if j > i), pend[0])
        st.rerun()
annot = nav[3].text_input("Seu nome (anotador)", value=row.get("annotator", "") or st.session_state.get("annot", ""))
st.session_state.annot = annot

left, right = st.columns([2, 3])
with left:
    st.caption(f"Post {i + 1}/{len(df)} · {row['post_id']} · @{row.get('handle', '')} · {row['platform']} · faixa {row['faixa']}")
    vid = _video_id(row["url"])
    if vid:
        st.video(f"https://www.youtube.com/watch?v={vid}")
    st.markdown(f"[Abrir na plataforma]({row['url']})")
    st.text_area("Legenda", _captions(tuple(df["post_id"])).get(row["post_id"], "(legenda indisponível: rode o pipeline local)"), height=160, disabled=True)
    st.info("Assista ao vídeo inteiro antes de rotular. Não consulte a saída do modelo.")

with right:
    vals = {}
    with st.form(f"f{i}"):
        c1, c2 = st.columns(2)
        for k, f in enumerate(R.CATEGORICAL_FIELDS):
            opts = [""] + list(OPCOES[f].__args__)
            cur = row.get(f, "")
            vals[f] = (c1 if k % 2 == 0 else c2).selectbox(f, opts, index=opts.index(cur) if cur in opts else 0, help=GUIA[f])
        for k, f in enumerate(R.BOOL_FIELDS):
            opts = ["", "sim", "não"]
            cur = {"1": "sim", "0": "não"}.get(row.get(f, ""), row.get(f, ""))
            vals[f] = (c1 if k % 2 == 0 else c2).radio(f, opts, index=opts.index(cur) if cur in opts else 0,
                                                       horizontal=True, help=GUIA[f], format_func=lambda x: x or "—")
        for f in ["forca_hook_0a10", "clareza_mensagem_0a10"]:
            opts = [""] + [str(n) for n in range(11)]
            cur = row.get(f, "")
            vals[f] = st.select_slider(f, opts, value=cur if cur in opts else "", help=GUIA[f], format_func=lambda x: x or "—")
        salvar = st.form_submit_button("Salvar e ir para o próximo", type="primary")
    if salvar:
        if not annot.strip():
            st.error("Preencha seu nome antes de salvar.")
        else:
            for f, v in vals.items():
                df.at[df.index[i], f] = v
            df.at[df.index[i], "annotator"] = annot.strip()
            df.drop(columns=["caption"], errors="ignore").to_csv(agreement.sample_path(), index=False, encoding="utf-8-sig")
            if i < len(df) - 1:
                st.session_state.i = i + 1
            st.rerun()

if feitos.all():
    st.success("Amostra completa. Rode: python -m stone_mpe.cli agreement")
