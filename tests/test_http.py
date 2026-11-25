import pytest

from stone_mpe.collect import http


class FakeResp:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload or {}, headers or {}
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0

    def request(self, *a, **k):
        self.calls += 1
        return self.responses.pop(0)


@pytest.fixture
def no_sleep(monkeypatch, env):
    monkeypatch.setattr(http, "_sleep", lambda s: None)


def test_429_duas_vezes_depois_sucesso_e_cache(monkeypatch, no_sleep):
    s = FakeSession([FakeResp(429), FakeResp(429), FakeResp(200, {"ok": 1})])
    monkeypatch.setattr(http, "_session", s)
    r = http.fetch_json("GET", "https://api.test/x", params={"q": 1, "key": "SECRET"})
    assert r.data == {"ok": 1} and r.retries == 2 and not r.from_cache
    r2 = http.fetch_json("GET", "https://api.test/x", params={"q": 1, "key": "OUTRA"})  # chave não entra no cache key
    assert r2.from_cache and s.calls == 3


def test_quota_exceeded_nao_insiste(monkeypatch, no_sleep):
    body = {"error": {"errors": [{"reason": "quotaExceeded"}]}}
    s = FakeSession([FakeResp(403, body)])
    monkeypatch.setattr(http, "_session", s)
    with pytest.raises(http.QuotaExceeded):
        http.fetch_json("GET", "https://api.test/q")
    assert s.calls == 1


def test_401_bloqueio_para(monkeypatch, no_sleep):
    monkeypatch.setattr(http, "_session", FakeSession([FakeResp(401)]))
    with pytest.raises(http.BlockedError):
        http.fetch_json("GET", "https://api.test/b")


def test_esgota_retries(monkeypatch, no_sleep):
    monkeypatch.setattr(http, "_session", FakeSession([FakeResp(503)] * 3))
    with pytest.raises(http.HttpError):
        http.fetch_json("GET", "https://api.test/z", max_retries=2)
