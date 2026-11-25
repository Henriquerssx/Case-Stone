"""Proteções do repositório público: segredos, HTML, entradas e arquivos."""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from stone_mpe.agent.schemas import AgentInput, Filters
from stone_mpe.collect import http, instagram
from stone_mpe.storyboard import safe_url


def test_erro_http_nunca_carrega_a_chave():
    e = http.HttpError(0, "Max retries exceeded with url: /youtube/v3/videos?part=x&key=AIzaSECRETO&id=1", "https://h/?token=abc")
    assert "AIzaSECRETO" not in str(e) and "abc" not in str(e)
    assert "key=***" in str(e)


def test_youtube_envia_a_chave_no_cabecalho(monkeypatch):
    from stone_mpe.collect import youtube
    seen = {}

    def fake_fetch(method, url, *, params=None, headers=None, **kw):
        seen.update(params=params, headers=headers)
        return http.FetchResult({"items": []}, False)

    monkeypatch.setattr(youtube, "fetch_json", fake_fetch)
    monkeypatch.setattr(youtube.config, "env", lambda k, d=None: "CHAVE_TESTE")
    youtube._api("channels", {"part": "id"}, youtube.QuotaMeter())
    assert "key" not in seen["params"] and seen["headers"]["X-Goog-Api-Key"] == "CHAVE_TESTE"


@pytest.mark.parametrize("url,ok", [
    ("https://www.youtube.com/shorts/abc", True), ("https://www.instagram.com/p/X/", True),
    ("javascript:alert(1)", False), ("http://www.youtube.com/x", False), ("https://evil.example/x", False)])
def test_links_do_storyboard_so_aceitam_plataformas_conhecidas(url, ok):
    assert (safe_url(url) == url) is ok


def test_entrada_do_agente_tem_limites():
    with pytest.raises(ValidationError):
        AgentInput(mode="recomendar", query="x" * 501)
    with pytest.raises(ValidationError):
        AgentInput(mode="recomendar", query="ok ok", segment="'; DROP TABLE posts;--")
    with pytest.raises(ValidationError):
        Filters(date_from="ontem")
    assert AgentInput(mode="recomendar", query="como atrair lojistas", segment="varejo").segment == "varejo"


def test_import_instagram_recusa_codigo_que_vira_caminho(tmp_path, env):
    rows = [{"shortCode": "../../etc/x", "ownerUsername": "loja", "type": "Video", "timestamp": "2026-10-01T10:00:00Z",
             "likesCount": 10, "commentsCount": 1, "followersCount": 100, "collected_at": "2026-11-20T00:00:00Z"},
            {"shortCode": "Abc_123", "ownerUsername": "loja", "type": "Video", "timestamp": "2026-10-01T10:00:00Z",
             "likesCount": 10, "commentsCount": 1, "followersCount": 100, "url": "javascript:alert(1)",
             "collected_at": "2026-11-20T00:00:00Z"}]
    f = tmp_path / "export.json"
    f.write_text(json.dumps(rows), encoding="utf-8")
    n, errors = instagram.import_file(f, "teste")
    assert n == 1 and any("inválido" in e for e in errors)
    from stone_mpe import config
    saved = [json.loads(line) for line in (config.raw_dir("instagram") / "export.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [p["url"] for p in saved] == ["https://www.instagram.com/p/Abc_123/"]
