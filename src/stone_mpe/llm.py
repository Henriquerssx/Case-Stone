"""Clientes de LLM/VLM com fallback em cadeia (TAP §6.4: tratar 429 + alternativa local).

Ordem definida em LLM_PROVIDERS (.env): gemini, openrouter, ollama, none.
- Todas as chamadas passam por collect.http (cache em disco + backoff).
- Cada chamada é registrada em outputs/llm_calls.jsonl.
- "none" não é um modelo: sinaliza ao chamador para usar o modo template/offline.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from typing import Protocol

from stone_mpe import config
from stone_mpe.collect.http import HttpError, fetch_json


class LLMUnavailable(Exception):
    """Nenhum provedor disponível — o chamador deve usar o modo template."""


class LLMClient(Protocol):
    name: str
    model: str

    def complete(self, prompt: str, images: list[bytes] | None = None, json_mode: bool = True) -> str: ...


def _http_opts() -> dict:
    # LLM: poucas tentativas por modelo (o fallback cobre o resto) e timeout maior (modelos com "thinking")
    return {"max_retries": config.get("http.llm_max_retries", 3), "timeout": config.get("http.llm_timeout_s", 120)}


def _models(key: str) -> list[str]:
    """Aceita um modelo ou uma lista separada por vírgula (tentados em ordem)."""
    v = config.get(key) or ""
    return [m.strip() for m in (v if isinstance(v, list) else str(v).split(",")) if m.strip()]


def _log(provider: str, model: str, purpose: str, latency_ms: int, cached: bool, error: str | None, retries: int = 0) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "provider": provider, "model": model, "purpose": purpose,
           "latency_ms": latency_ms, "cached": cached, "retries": retries, "error": error}
    with open(config.outputs_dir() / "llm_calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


class GeminiClient:
    name = "gemini"

    def __init__(self, model: str, purpose: str):
        self.model, self.purpose = model, purpose
        self.key = config.env("GEMINI_API_KEY")

    def complete(self, prompt: str, images: list[bytes] | None = None, json_mode: bool = True) -> str:
        parts: list[dict] = [{"text": prompt}]
        for img in images or []:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}})
        body: dict = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": 0.2}}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        t0 = time.time()
        res = fetch_json("POST", url, json_body=body, headers={"x-goog-api-key": self.key}, namespace="llm", **_http_opts())
        cand = (res.data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
        _log(self.name, self.model, self.purpose, int((time.time() - t0) * 1000), res.from_cache, None, res.retries)
        if not text:
            raise HttpError(200, f"resposta vazia (finishReason={cand.get('finishReason')})", url)
        return text


class OpenAICompatClient:
    """OpenRouter e Ollama expõem a API de chat no formato OpenAI."""

    def __init__(self, name: str, base_url: str, key: str | None, model: str, purpose: str):
        self.name, self.base_url, self.key, self.model, self.purpose = name, base_url.rstrip("/"), key, model, purpose

    def complete(self, prompt: str, images: list[bytes] | None = None, json_mode: bool = True) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images or []:
            content.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}})
        body: dict = {"model": self.model, "messages": [{"role": "user", "content": content}], "temperature": 0.2}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.key}"} if self.key else {}
        t0 = time.time()
        res = fetch_json("POST", f"{self.base_url}/chat/completions", json_body=body, headers=headers, namespace="llm", **_http_opts())
        text = res.data["choices"][0]["message"]["content"] or ""
        _log(self.name, self.model, self.purpose, int((time.time() - t0) * 1000), res.from_cache, None, res.retries)
        return text


class FallbackClient:
    """Tenta cada provedor em ordem; erro esgotado (429 após retries, 5xx, bloqueio) passa ao próximo."""

    def __init__(self, clients: list[LLMClient], purpose: str):
        self.clients, self.purpose = clients, purpose
        self.last_used: LLMClient | None = None
        # disjuntor: modelo que falhou fica fora por `cooldown` segundos (evita pagar o timeout a cada post)
        self.cooldown = config.get("http.llm_cooldown_s", 90)
        self._down_until: dict[int, float] = {}

    @property
    def model(self) -> str:
        c = self.last_used or (self.clients[0] if self.clients else None)
        return f"{c.name}/{c.model}" if c else "none"

    def complete(self, prompt: str, images: list[bytes] | None = None, json_mode: bool = True) -> str:
        if not self.clients:
            raise LLMUnavailable("nenhum provedor configurado")
        errors = []
        now = time.time()
        up = [c for c in self.clients if self._down_until.get(id(c), 0) <= now]
        # se todos estão em pausa, tenta mesmo assim (o chamador decide esperar)
        for c in up or self.clients:
            try:
                out = c.complete(prompt, images, json_mode)
                self.last_used = c
                self._down_until.pop(id(c), None)
                return out
            except (HttpError, KeyError, IndexError) as e:
                _log(c.name, c.model, self.purpose, 0, False, str(e)[:300])
                errors.append(f"{c.name}/{c.model}: {str(e)[:160]}")
                # 429 de cota DIÁRIA (quotaId ...PerDay...) tira o modelo por 1 h; limite por minuto só pelo cooldown curto
                daily = isinstance(e, HttpError) and e.status == 429 and "perday" in str(getattr(e, "body", "")).lower()
                self._down_until[id(c)] = time.time() + (config.get("http.llm_quota_cooldown_s", 3600) if daily else self.cooldown)
        raise LLMUnavailable(" | ".join(errors))


def get_client(purpose: str = "agent") -> FallbackClient:
    """purpose: 'categorize' (VLM, com imagem) ou 'agent' (texto)."""
    order = [p.strip() for p in (config.env("LLM_PROVIDERS", "gemini,openrouter,none") or "").split(",") if p.strip()]
    clients: list[LLMClient] = []
    for p in order:
        if p == "none":
            break
        if p == "gemini" and config.env("GEMINI_API_KEY"):
            clients += [GeminiClient(m, purpose) for m in _models(f"models.gemini_{purpose}")]
        elif p == "openrouter" and config.env("OPENROUTER_API_KEY"):
            clients += [OpenAICompatClient("openrouter", "https://openrouter.ai/api/v1", config.env("OPENROUTER_API_KEY"), m, purpose)
                        for m in _models(f"models.openrouter_{purpose}")]
        elif p == "ollama" and str(config.env("OLLAMA_BASE_URL") or "").startswith("http"):
            clients += [OpenAICompatClient("ollama", config.env("OLLAMA_BASE_URL"), None, m, purpose)
                        for m in _models(f"models.ollama_{purpose}")]
    return FallbackClient(clients, purpose)


def parse_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON (tolera cercas ```json)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("nenhum objeto JSON na resposta")
    return json.loads(t[start : end + 1])
