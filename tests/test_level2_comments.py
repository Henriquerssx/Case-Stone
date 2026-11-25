import json
import shutil
import subprocess

import pytest

from stone_mpe import storage
from stone_mpe.analysis import comments, patterns
from stone_mpe.multimodal import categorize, video
from stone_mpe.multimodal import rubric as R
from tests.conftest import FakeLLM

GOOD = json.dumps(dict(formato_video="Lista / Dicas", hook_primeiros_3s="3 erros", tipo_hook="numero", forca_hook_0a10=7,
                       tema_principal="financas", tem_rosto=True, criador_e_empreendedor_real=False, prova_social=False,
                       texto_na_tela=True, ritmo_cortes_0a10=None, tom="informal", usa_linguagem_regional=False,
                       clareza_mensagem_0a10=8, tem_cta=True, tipo_cta="salvar", oferta_ou_beneficio_explicito=False,
                       elementos_top5=["a", "b", "c", "d", "e"]))


def test_classificador_de_comentarios():
    assert comments.classify("Quero participar! Como faço?") >= {"contato", "duvida"}
    assert "objecao" in comments.classify("muito caro essa taxa")
    assert comments.classify("amei, ajudou demais") == {"elogio"}
    agg = comments.aggregate("yt_x", ["quero!", "qual o link?", "top"], "teste")
    assert agg["n_contato"] == 2 and agg["n_sampled"] == 3 and "username" not in json.dumps(agg)


def test_categorize_post_json_invalido_depois_valido(env):
    fake = FakeLLM(["isto não é json", GOOD])
    post = {"post_id": "ig_1", "platform": "instagram", "handle": "h", "media_type": "reels", "caption": "x" * 200,
            "duration_s": 40.0, "thumbnail_url": None}
    res, meta = categorize.categorize_post(post, fake)
    assert res.formato_video == "lista/dicas" and res.duracao_faixa == "30-60s" and res.legenda_tamanho == "média"
    assert len(fake.prompts) == 2 and "inválida" in fake.prompts[1] and meta["input_modalities"] == ["caption"]


def test_nivel2_tem_prioridade_sobre_nivel1(synthetic_db):
    top = patterns.load_top()
    pid = top["post_id"].iloc[0]
    rub = R.Rubric(**{**json.loads(GOOD), "tema_principal": "história de empreendedor", "formato_video": "depoimento",
                      "tipo_hook": "dor", "tipo_cta": "DM"}, tipo_post="reels", legenda_tamanho="curta")
    categorize.save(pid, rub, {"raw_json": "{}", "input_modalities": ["caption", "frames"], "error": None}, "fake", "v1-n2")
    top2 = patterns.load_top()
    assert len(top2) == len(top)  # sem duplicar o post
    assert top2.set_index("post_id").at[pid, "tema_principal"] == "história de empreendedor"


def test_amostra_do_resto_para_lift(synthetic_db):
    rest = categorize.pending_posts(rest_sample=20)
    assert 15 <= len(rest) <= 25 and not rest["is_top"].astype(bool).any() and rest["eligible"].astype(bool).all()
    for p in rest.to_dict(orient="records"):
        rub = R.Rubric(**json.loads(GOOD), tipo_post=R.tipo_post(p["media_type"]), legenda_tamanho="curta")
        categorize.save(p["post_id"], rub, {"raw_json": "{}", "input_modalities": ["caption"], "error": None}, "fake")
    lf = patterns.lift(["tema_principal"], min_n=1, min_rest=10)
    assert not lf.empty and {"freq_top", "freq_rest", "lift"} <= set(lf.columns)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg ausente")
def test_frames_e_cortes_com_video_sintetico(env, tmp_path):
    # 6 s: 3 cenas de cor sólida de 2 s cada -> 2 cortes
    src = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2",
                    "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2", "-f", "lavfi", "-i", "color=c=green:s=320x240:d=2",
                    "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0", "-y", str(src)], check=True)
    dur = video.probe_duration(src)
    assert 5.5 < dur < 6.5
    fr = video.frames("test_post", src, dur)
    assert len(fr) >= 3 and all(p.stat().st_size > 0 for p in fr)
    cps = video.cuts_per_second(src, dur)
    assert 0.2 <= cps <= 0.5  # ~2 cortes / 6 s
    assert video.cut_score_0a10(cps) in (2, 3, 4, 5) and video.cut_score_0a10(2.0) == 10
