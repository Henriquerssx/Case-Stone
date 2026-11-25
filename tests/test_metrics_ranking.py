import math

import pandas as pd

from stone_mpe.process.metrics import engagement_rate, faixa
from stone_mpe.process.ranking import rank


def test_exemplo_didatico_conta_b_vence_conta_a():
    a = engagement_rate(10_000, 0, 1_000_000)
    b = engagement_rate(500, 0, 5_000)
    assert math.isclose(a, 0.01) and math.isclose(b, 0.10) and b > a


def test_seguidores_zero_ou_ausente_vira_nan():
    assert math.isnan(engagement_rate(10, 1, 0))
    s = engagement_rate(pd.Series([10, 10]), pd.Series([1, 1]), pd.Series([0, None]))
    assert s.isna().all()


def test_faixas():
    assert faixa(10_000, 10_000, 100_000) == "micro"
    assert faixa(10_001, 10_000, 100_000) == "medio"
    assert faixa(100_001, 10_000, 100_000) == "grande"


def test_top10_por_plataforma_e_combinado():
    df = pd.DataFrame({
        "platform": ["instagram"] * 100 + ["youtube"] * 100,
        "engagement_rate": [i / 100 for i in range(100)] + [i / 1000 for i in range(100)],
        "eligible": True,
    })
    r = rank(df, q=0.9, scope="platform")
    assert r.groupby("platform")["is_top"].sum().tolist() == [10, 10]
    c = rank(df, q=0.9, scope="combined")
    assert c["is_top"].sum() == 20 and set(c.loc[c.is_top, "platform"]) == {"instagram"}


def test_inelegiveis_nao_entram_no_top():
    df = pd.DataFrame({"platform": ["instagram"] * 20, "engagement_rate": [1.0] + [0.01] * 19,
                       "eligible": [False] + [True] * 19})
    assert not rank(df, q=0.9)["is_top"].iloc[0]


def test_normalize_filtra_14_dias(synthetic_db):
    posts = synthetic_db
    assert (posts.loc[posts["eligible"], "age_days"] >= 14).all()
    assert not posts.loc[posts["age_days"] < 14, "is_top"].any()
    assert set(posts["faixa"]) == {"micro", "medio", "grande"}
