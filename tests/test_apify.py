import json

from stone_mpe.collect import apify


def _fake_posts():
    return [
        {"shortCode": "ABC1", "ownerUsername": "Loja_X", "type": "Video", "productType": "clips", "caption": "dica #mei",
         "likesCount": 120, "commentsCount": 8, "videoViewCount": 3000, "videoDuration": 22.5,
         "timestamp": "2026-08-01T12:00:00.000Z", "url": "https://www.instagram.com/p/ABC1/", "displayUrl": None},
        {"shortCode": "ABC2", "ownerUsername": "loja_x", "type": "Sidecar", "caption": "carrossel", "likesCount": -1,
         "commentsCount": 3, "timestamp": "2026-07-01T12:00:00.000Z", "url": "https://www.instagram.com/p/ABC2/"},
    ]


def test_collect_monta_export_e_importa(env, monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "x")
    calls = []

    def fake_run(actor, actor_input, max_charge_usd, max_items, **kw):
        calls.append((actor, actor_input, max_charge_usd, max_items))
        if actor == apify.PROFILE_ACTOR:
            return [{"username": "loja_x", "followersCount": 5000}]
        return _fake_posts()

    monkeypatch.setattr(apify, "run_actor", fake_run)
    monkeypatch.setattr(apify, "get_thumbnail", lambda *a, **k: None)
    out = apify.collect(handles=["loja_x", "sumiu"], posts_per_profile=10, max_charge_usd=1.0)
    assert out["importados"] == 2 and out["sem_posts"] == ["sumiu"] and out["sem_seguidores"] == ["sumiu"]
    post_input = calls[1][1]
    assert post_input["dataDetailLevel"] == "basicData" and post_input["resultsLimit"] == 10
    assert calls[1][2] == 1.0 and calls[1][3] == 20  # teto de gasto e de itens repassados
    rows = [json.loads(l) for l in open(apify.config.raw_dir("instagram") / (out["export"].split("\\")[-1].split("/")[-1].replace(".json", ".jsonl")), encoding="utf-8")]
    by = {r["post_id"]: r for r in rows}
    assert by["ig_ABC1"]["media_type"] == "reels" and by["ig_ABC1"]["followers"] == 5000
    assert by["ig_ABC2"]["media_type"] == "carrossel" and by["ig_ABC2"]["likes"] is None  # curtidas ocultas
    assert by["ig_ABC1"]["source_route"] == "apify/instagram-post-scraper"


def test_teto_de_custo_bloqueia(env, monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "x")
    import pytest
    with pytest.raises(ValueError):
        apify.collect(handles=["a"] * 100, posts_per_profile=100, max_charge_usd=1.0)
    assert apify.collect(handles=["a"] * 21, posts_per_profile=60, dry_run=True)["custo_estimado_usd"] == 2.2
