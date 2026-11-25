import pandas as pd

from stone_mpe.agent import tools
from stone_mpe.analysis import patterns


def test_freq_por_criador_pesa_cada_criador_igual():
    # criador A: 9 posts "humor"; criador B: 1 post "educativo"
    df = pd.DataFrame({"post_id": [f"p{i}" for i in range(10)], "profile_id": ["yt:a"] * 9 + ["yt:b"],
                       "tom": ["humor"] * 9 + ["educativo"], "engagement_rate": range(10)})
    f = patterns.frequencies(df, ["tom"]).set_index("value")
    assert f.loc["humor", "freq"] == 0.9
    assert f.loc["humor", "freq_por_criador"] == 0.5  # A=1.0, B=0.0
    assert f.loc["humor", "n_criadores"] == 1
    c = patterns.concentration(df)
    assert c["share_top1"] == 0.9 and c["n_criadores"] == 2


def test_referencias_limitadas_por_criador(env):
    df = pd.DataFrame({"post_id": [f"p{i}" for i in range(6)], "url": "u", "platform": "youtube",
                       "handle": ["a"] * 5 + ["b"], "caption": "maquininha vendas loja",
                       "percentile": [0.99, 0.98, 0.97, 0.96, 0.95, 0.91], "engagement_rate": 0.1})
    refs = tools.posts_referencia(df, "maquininha vendas", k=5)
    assert [r.handle for r in refs].count("a") <= 2
    assert "b" in [r.handle for r in refs]
