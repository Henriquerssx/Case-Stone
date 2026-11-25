"""Respostas pré-computadas para a demonstração (fallback se a internet/LLM falhar ao vivo)."""
from __future__ import annotations

import json
import time

from stone_mpe import config
from stone_mpe.agent.schemas import AgentOutput

DEMO_QUERIES = [
    {"mode": "analisar", "query": "Quais formatos de vídeo curto mais aparecem entre as publicações de alto desempenho de pequenos negócios de alimentação?", "segment": "alimentacao"},
    {"mode": "recomendar", "query": "Como atrair microempreendedoras de beleza para o programa do Impulso?", "segment": "beleza"},
    {"mode": "gerar_criativo", "query": "Preciso de um vídeo curto para atrair donos de pequenos restaurantes e lanchonetes", "segment": "alimentacao"},
    {"mode": "gerar_criativo", "query": "Vídeo curto sobre precificação para quem está começando a empreender", "segment": None},
    {"mode": "gerar_criativo", "query": "Vídeo curto com humor sobre o dia a dia de quem tem loja ou comércio", "segment": "varejo"},
]


def _key(mode: str, query: str, segment: str | None) -> str:
    return f"{mode}|{query.strip().lower()}|{(segment or '').lower()}"


def path():
    return config.outputs_dir() / "demo_cache.json"


def precompute(attempts: int = 3, wait_s: float = 60) -> int:
    """Gera as respostas da demo. Nunca troca uma resposta com LLM por uma de template:
    se o LLM falhar, tenta de novo (`attempts` vezes) e, no fim, mantém a versão anterior."""
    from stone_mpe.api import run
    cache = load_raw()
    for q in DEMO_QUERIES:
        key = _key(q["mode"], q["query"], q["segment"])
        out = None
        for i in range(attempts):
            out = run(q["mode"], q["query"], segment=q["segment"])
            if out.llm != "none":
                break
            if i < attempts - 1:
                print(f"[demo] LLM indisponível; nova tentativa em {wait_s:.0f}s", flush=True)
                time.sleep(wait_s)
        prev = cache.get(key)
        if out.llm == "none" and prev and prev.get("llm") not in (None, "none"):
            print(f"[demo] {q['mode']}: mantida a versão anterior (llm={prev['llm']})")
            continue
        cache[key] = out.model_dump()
        print(f"[demo] {q['mode']}: {len(out.reference_posts)} refs, {len(out.creatives)} criativos, llm={out.llm}", flush=True)
    path().write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(cache)


def load_raw() -> dict:
    p = path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def get(mode: str, query: str, segment: str | None) -> AgentOutput | None:
    cache = load_raw()
    d = cache.get(_key(mode, query, segment))
    if d is None:  # mesmo pedido com outro segmento
        prefix = _key(mode, query, None).rsplit("|", 1)[0] + "|"
        d = next((v for k, v in cache.items() if k.startswith(prefix)), None)
    return AgentOutput.model_validate(d) if d else None
