from stone_mpe import storyboard
from stone_mpe.agent.schemas import Cena, Creative, guess_plano
from stone_mpe.analysis import niches

ROTEIRO = ("1. [0-3s] [Vídeo] Empreendedora olhando para a câmera na cozinha. Texto na tela: 'Cadê o lucro?'. "
           "Fala: 'Vendeu muito e o caixa não bate?'\n"
           "2. [3-15s] Mãos anotando custos numa planilha no celular. Fala: 'Anota cada custo.'")


def _cr(**kw):
    base = dict(titulo="t", formato="Reels 30s", gancho="Cadê o lucro?", roteiro=ROTEIRO, legenda="l", cta="c", inspired_by=["p1"])
    return Creative(**{**base, **kw})


def test_cenas_extraidas_do_texto_do_roteiro():
    cs = storyboard.scenes(_cr())
    assert len(cs) == 2
    assert cs[0].tempo == "0-3s" and cs[0].texto_tela == "Cadê o lucro?" and cs[0].fala.startswith("Vendeu muito")
    assert cs[1].plano in ("maos", "tela")


def test_cenas_do_modelo_tem_prioridade_e_plano_normalizado():
    cr = _cr(cenas=[{"tempo": "0-3s", "plano": "Produto", "visual": "bolo", "fala": "f", "texto_tela": "x"}])
    assert storyboard.scenes(cr)[0].plano == "produto"
    assert guess_plano("valor inventado") == "rosto"


def test_svg_e_html_autocontido():
    svg = storyboard.svg_frame(Cena(tempo="0-3s", plano="tela", fala="a" * 300, texto_tela="Texto <com> & especial"), 1)
    assert svg.startswith("<svg") and "&lt;com&gt;" in svg and "…" in svg
    html = storyboard.storyboard_html(_cr(), metas={"mediana_da_base": 4, "entrar_no_top": 128, "mediana_do_top": 345}, followers=10000)
    assert html.startswith("<!doctype html>") and html.count("<svg") == 2 and "128" in html


def test_resumo_por_nicho(synthetic_db):
    s = niches.summary()
    assert not s.empty and {"nicho", "er_mediana", "taxa_top", "formato_top"} <= set(s.columns)
    assert (s["taxa_top"].between(0, 1)).all()
    assert not niches.by_platform().empty


def test_concordancia_entre_modelos(synthetic_db, monkeypatch):
    import json

    from stone_mpe.analysis import agreement
    from stone_mpe.multimodal import categorize
    from tests.conftest import FakeLLM
    from tests.test_rubric import BASE
    monkeypatch.setattr(categorize, "get_thumbnail", lambda *a, **k: None)
    agreement.make_sample(5)
    res = agreement.cross_model("fake", gap_s=0, client=FakeLLM([json.dumps(BASE)]))
    assert not res.empty and set(res["campo"]) >= {"tema_principal", "tem_rosto", "forca_hook_0a10"}
    assert res["concordancia"].between(0, 1).all()
