"""HTTP com cache em disco + retry exponencial com jitter (TAP §6.4).

- 429 / 5xx / erro de rede  -> backoff exponencial com jitter (respeita Retry-After)
- 403 quotaExceeded (YouTube) -> QuotaExceeded (não insiste; esperar reset diário)
- 401 / challenge             -> BlockedError (para a rota, não insiste)
- respostas 200 são cacheadas; re-execuções não refazem chamadas
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from stone_mpe import config

RETRY_STATUS = {429, 500, 502, 503, 504}
SECRET_PARAMS = {"key", "api_key", "access_token"}

# injetáveis nos testes
_sleep: Callable[[float], None] = time.sleep
_session = requests.Session()


_SECRET_RE = re.compile(r"((?:[?&]|\b)(?:key|api_key|access_token|token)=)[^&\s'\"]+", re.IGNORECASE)


def redact(text: str) -> str:
    """Mascara valores de parâmetros secretos (key=, token=...) em qualquer texto de erro ou log."""
    return _SECRET_RE.sub(r"\1***", str(text))


class HttpError(Exception):
    def __init__(self, status: int, body: str, url: str = ""):
        body, url = redact(body), redact(url)
        super().__init__(f"HTTP {status} em {url}: {body[:300]}")
        self.status = status
        self.body = body
        self.url = url


class QuotaExceeded(HttpError):
    pass


class BlockedError(HttpError):
    pass


@dataclass
class FetchResult:
    data: Any
    from_cache: bool
    retries: int = 0


def _cache_key(method: str, url: str, params: dict | None, body: Any) -> str:
    clean = {k: v for k, v in (params or {}).items() if k not in SECRET_PARAMS}
    raw = json.dumps([method.upper(), url, clean, body], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_file(namespace: str, key: str):
    d = config.cache_dir(namespace) / key[:2]
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def _delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), config.get("http.max_delay_s", 120.0))
        except ValueError:
            pass
    base = config.get("http.base_delay_s", 2.0)
    cap = config.get("http.max_delay_s", 120.0)
    return min(cap, base * (2 ** attempt)) * (0.5 + random.random() / 2)


def _classify_403(resp: requests.Response) -> str:
    try:
        reasons = {e.get("reason") for e in resp.json().get("error", {}).get("errors", [])}
    except Exception:
        reasons = set()
    if reasons & {"quotaExceeded", "dailyLimitExceeded"}:
        return "quota"
    if reasons & {"rateLimitExceeded", "userRateLimitExceeded"}:
        return "retry"
    return "fatal"


def fetch_json(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json_body: Any = None,
    headers: dict | None = None,
    namespace: str = "http",
    use_cache: bool = True,
    max_retries: int | None = None,
    timeout: float | None = None,
) -> FetchResult:
    key = _cache_key(method, url, params, json_body)
    cfile = _cache_file(namespace, key)
    if use_cache and cfile.exists():
        return FetchResult(json.loads(cfile.read_text(encoding="utf-8")), True)

    max_retries = config.get("http.max_retries", 6) if max_retries is None else max_retries
    timeout = config.get("http.timeout_s", 60) if timeout is None else timeout
    attempt = 0
    while True:
        try:
            resp = _session.request(method, url, params=params, json=json_body, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt >= max_retries:
                raise HttpError(0, str(e), url) from None  # sem traceback encadeado (traria a URL crua)
            _sleep(_delay(attempt, None))
            attempt += 1
            continue

        if 200 <= resp.status_code < 300:  # 201 Created (ex.: Apify ao iniciar um run)
            data = resp.json()
            if use_cache:
                cfile.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return FetchResult(data, False, attempt)

        if resp.status_code == 401:
            raise BlockedError(401, resp.text, url)
        if resp.status_code == 403:
            kind = _classify_403(resp)
            if kind == "quota":
                raise QuotaExceeded(403, resp.text, url)
            if kind == "fatal":
                raise HttpError(403, resp.text, url)
        elif resp.status_code not in RETRY_STATUS:
            raise HttpError(resp.status_code, resp.text, url)
        elif resp.status_code == 429 and "perday" in resp.text.lower():
            raise HttpError(429, resp.text, url)  # cota diária esgotada: tentar de novo não adianta

        if attempt >= max_retries:
            raise HttpError(resp.status_code, resp.text, url)
        _sleep(_delay(attempt, resp.headers.get("Retry-After")))
        attempt += 1


def fetch_bytes(url: str, *, max_retries: int = 3) -> bytes:
    """Download simples (thumbnails) com retry. Sem cache aqui: quem chama salva o arquivo."""
    attempt = 0
    while True:
        try:
            resp = _session.get(url, timeout=config.get("http.timeout_s", 60))
            if resp.status_code == 200:
                return resp.content
            if resp.status_code not in RETRY_STATUS or attempt >= max_retries:
                raise HttpError(resp.status_code, resp.text[:200], url)
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt >= max_retries:
                raise HttpError(0, str(e), url) from None
        _sleep(_delay(attempt, None))
        attempt += 1
