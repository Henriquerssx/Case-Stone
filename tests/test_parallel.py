import json

from stone_mpe.multimodal import categorize
from tests.conftest import FakeLLM
from tests.test_rubric import BASE


def test_run_paralelo_grava_todos(synthetic_db, monkeypatch):
    monkeypatch.setattr(categorize, "get_client", lambda purpose="categorize": FakeLLM([json.dumps(BASE)]))
    monkeypatch.setattr(categorize, "get_thumbnail", lambda *a, **k: None)
    orig = categorize.config.get
    monkeypatch.setattr(categorize.config, "get", lambda k, d=None: {"categorization.workers": 3,
                        "categorization.min_interval_s": 0}.get(k, orig(k, d)))
    r = categorize.run(rest_sample=6)
    assert r["processed"] == 6 and r["valid"] == 6 and not r["exhausted"]
    n = categorize.storage.read_sql("SELECT COUNT(*) n FROM categorizations WHERE model = 'fake/test'")["n"].iloc[0]
    assert n == 6
