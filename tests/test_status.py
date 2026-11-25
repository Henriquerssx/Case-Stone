from stone_mpe import status


def test_pipeline_e_metas(synthetic_db):
    steps = status.pipeline()
    assert len(steps) == 9 and all(s["status"] in ("ok", "parcial", "pendente") for s in steps)
    bm = status.benchmarks()
    assert bm["limiar_top"] > bm["mediana_geral"] > 0
    g = status.goals(10000, bm)
    assert g["mediana_da_base"] <= g["entrar_no_top"] <= g["mediana_do_top"]
    top = status.reference_metrics(["x_inexistente"])
    assert top.empty
