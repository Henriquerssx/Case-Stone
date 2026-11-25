"""Índice de Desempenho Ponderado e base pública sanitizada."""
from __future__ import annotations

import pandas as pd
import pytest

from stone_mpe import release, storage
from stone_mpe.analysis import weighted


def _posts() -> pd.DataFrame:
    rows = []
    # nicho A engaja 10x mais que o nicho B; cada nicho tem um post muito acima do normal do criador
    for seg, base, handle in [("a", 0.10, "perfil_a"), ("b", 0.01, "perfil_b")]:
        for i in range(40):
            er = base * (5 if i == 0 else 1 + (i % 5) / 10)
            rows.append({"post_id": f"{seg}{i}", "platform": "instagram", "handle": handle, "profile_id": handle,
                         "segmento": seg, "faixa": "medio", "posted_at": f"2026-0{1 + i % 9}-10", "engagement_rate": er,
                         "is_top": 1 if seg == "a" and i < 8 else 0})
    return pd.DataFrame(rows)


def test_componentes_em_0_1_e_top_de_10_porcento():
    df = weighted.compute(_posts(), min_group=5)
    for c in ["c_nicho", "c_perfil", "c_periodo", "c_porte", "idp"]:
        assert df[c].between(0, 1).all(), c
    assert df["is_top_idp"].sum() == pytest.approx(len(df) * 0.10, abs=2)


def test_ponderado_reconhece_o_destaque_de_um_nicho_que_engaja_menos():
    df = weighted.compute(_posts(), min_group=5).set_index("post_id")
    raw = df["engagement_rate"].rank(pct=True)
    idp = df["idp"].rank(pct=True)
    # no ranking bruto o melhor post do nicho B fica no meio da tabela; no IDP ele sobe para o quintil de cima
    assert raw["b0"] <= 0.55
    assert idp["b0"] >= 0.80
    assert df.at["b0", "c_nicho"] == 1.0 and df.at["b0", "c_perfil"] > 0.9


def test_pesos_sao_normalizados_e_aceitam_override():
    w = weighted.weights({"nicho": 2, "perfil": 0, "periodo": 0, "porte": 0})
    assert w["nicho"] == pytest.approx(1.0) and sum(w.values()) == pytest.approx(1.0)
    df = weighted.compute(_posts(), min_group=5, weight_override={"nicho": 1, "perfil": 0, "periodo": 0, "porte": 0})
    assert (df["idp"] == df["c_nicho"]).all()


def test_grupo_pequeno_cai_para_percentil_da_plataforma():
    df = weighted.compute(_posts(), min_group=1000)
    plat = df["engagement_rate"].rank(pct=True)
    assert (df["c_nicho"] == plat).all()


def test_summary_compara_com_top_oficial(synthetic_db):
    s = weighted.summary()
    for d in s["plataformas"].values():
        assert d["top_idp"] > 0 and 0 <= d["sobreposicao"] <= 1
        assert d["concentracao_idp"]["criadores"] >= 1


def test_release_nao_exporta_texto_de_terceiros_e_restaura(synthetic_db, tmp_path, monkeypatch):
    monkeypatch.setenv("STONE_MPE_RELEASE", str(tmp_path / "release"))
    counts = release.export()
    assert counts["posts.csv.gz"] == len(storage.read_sql("SELECT post_id FROM posts"))
    pub = pd.read_csv(tmp_path / "release" / "posts.csv.gz")
    assert not set(release.POSTS_DROP) & set(pub.columns)
    cat = pd.read_csv(tmp_path / "release" / "categorizations.csv.gz")
    assert "raw_json" not in cat.columns

    monkeypatch.setenv("STONE_MPE_DB", str(tmp_path / "novo.sqlite"))
    res = release.restore()
    assert res["posts"] == counts["posts.csv.gz"] and res["categorizations"] == counts["categorizations.csv.gz"]
    assert storage.read_sql("SELECT caption FROM posts")["caption"].fillna("").eq("").all()
    assert "já existe" in release.restore()["status"]  # não sobrescreve sem --force


def test_release_recusa_arquivo_adulterado(synthetic_db, tmp_path, monkeypatch):
    monkeypatch.setenv("STONE_MPE_RELEASE", str(tmp_path / "release"))
    release.export()
    with open(tmp_path / "release" / "profiles.csv", "a", encoding="utf-8") as f:
        f.write("x\n")
    monkeypatch.setenv("STONE_MPE_DB", str(tmp_path / "novo.sqlite"))
    with pytest.raises(ValueError, match="checksum"):
        release.restore()
