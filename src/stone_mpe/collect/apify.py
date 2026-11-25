"""Coleta do Instagram via Apify, a rota definida no kickoff (Aula 1 cita Apify/HikerAPI).

Atenção: o Apify é um serviço de terceiros que extrai dados públicos do Instagram. Ele está em
tensão com o TAP §4.3 (scraping fora do escopo). Usamos porque foi a rota acordada no kickoff,
e isso fica declarado no README. Nada aqui acessa o Instagram diretamente.

Fluxo (2 execuções de ator, ambas com teto de gasto `maxTotalChargeUsd`):
1. apify/instagram-profile-scraper → seguidores de cada perfil, na data da coleta.
2. apify/instagram-post-scraper (basicData) → posts com curtidas, comentários, legenda, tipo e data.
3. Junta seguidores aos posts, salva o export bruto em data/raw/instagram_export/ e chama
   `instagram.import_file` com route="apify" (o mesmo caminho de qualquer export).

Custo no plano gratuito (conferido em 23/11/2026): US$ 0,0026/perfil + US$ 0,0017/post.
O plano gratuito dá US$ 5/mês sem cartão; sem créditos, o Apify recusa a execução.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from stone_mpe import config
from stone_mpe.collect import instagram
from stone_mpe.collect.http import HttpError, fetch_json
from stone_mpe.collect.media import get_thumbnail

API = "https://api.apify.com/v2"
PROFILE_ACTOR = "apify~instagram-profile-scraper"
POST_ACTOR = "apify~instagram-post-scraper"
PRICE_PROFILE, PRICE_POST = 0.0026, 0.0017


def _token() -> str:
    t = config.env("APIFY_TOKEN")
    if not t:
        raise RuntimeError("Defina APIFY_TOKEN no .env (console.apify.com > Settings > API & Integrations)")
    return t


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


def estimate_cost(n_profiles: int, posts_per_profile: int) -> float:
    return round(n_profiles * PRICE_PROFILE + n_profiles * posts_per_profile * PRICE_POST, 2)


def account() -> dict:
    """Plano e uso do mês (para checar créditos antes de rodar)."""
    me = fetch_json("GET", f"{API}/users/me", headers=_headers(), use_cache=False).data["data"]
    lim = fetch_json("GET", f"{API}/users/me/limits", headers=_headers(), use_cache=False).data["data"]
    cur = lim.get("current", {})
    mx = lim.get("limits", {})
    return {"plan": (me.get("plan") or {}).get("id"), "usage_usd": cur.get("monthlyUsageUsd"),
            "limit_usd": mx.get("maxMonthlyUsageUsd")}


def _recent_run(actor: str, actor_input: dict, max_age_h: float = 24) -> dict | None:
    """Run do mesmo ator, com a mesma entrada, nas últimas `max_age_h` horas (evita pagar duas vezes)."""
    try:
        runs = fetch_json("GET", f"{API}/acts/{actor}/runs", params={"desc": 1, "limit": 5},
                          headers=_headers(), use_cache=False).data["data"]["items"]
    except HttpError:
        return None
    for r in runs:
        if r["status"] not in ("READY", "RUNNING", "SUCCEEDED"):
            continue
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(r["startedAt"].replace("Z", "+00:00"))).total_seconds() / 3600
        if age_h > max_age_h:
            continue
        try:
            inp = fetch_json("GET", f"{API}/key-value-stores/{r['defaultKeyValueStoreId']}/records/INPUT",
                             headers=_headers(), use_cache=False).data
        except HttpError:
            continue
        if all(inp.get(k) == v for k, v in actor_input.items()):
            return fetch_json("GET", f"{API}/actor-runs/{r['id']}", headers=_headers(), use_cache=False).data["data"]
    return None


def run_actor(actor: str, actor_input: dict, max_charge_usd: float, max_items: int, poll_s: float = 10,
              timeout_s: float = 1800) -> list[dict]:
    """Inicia o ator, espera terminar e devolve os itens do dataset."""
    run = _recent_run(actor, actor_input)
    if run:
        print(f"[apify] reaproveitando run {run['id']} ({run['status']}) com a mesma entrada; sem novo custo", flush=True)
    else:
        params = {"maxTotalChargeUsd": max_charge_usd, "maxItems": max_items}
        run = fetch_json("POST", f"{API}/acts/{actor}/runs", params=params, json_body=actor_input,
                         headers=_headers(), use_cache=False, max_retries=2).data["data"]
    print(f"[apify] {actor} iniciado (run {run['id']}, teto US$ {max_charge_usd})", flush=True)
    t0 = time.time()
    while run["status"] in ("READY", "RUNNING"):
        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"{actor} passou de {timeout_s}s; veja o run {run['id']} no console do Apify")
        time.sleep(poll_s)
        run = fetch_json("GET", f"{API}/actor-runs/{run['id']}", headers=_headers(), use_cache=False).data["data"]
    if run["status"] != "SUCCEEDED":
        raise HttpError(0, f"run {run['id']} terminou como {run['status']}: {run.get('statusMessage')}", actor)
    items = fetch_json("GET", f"{API}/datasets/{run['defaultDatasetId']}/items", params={"format": "json", "clean": "true"},
                       headers=_headers(), use_cache=False).data
    cost = (run.get("usageTotalUsd") or 0)
    print(f"[apify] {actor}: {len(items)} itens em {time.time() - t0:.0f}s · custo informado US$ {cost:.3f}", flush=True)
    return items


def collect(handles: list[str] | None = None, posts_per_profile: int | None = None, newer_than: str | None = None,
            max_charge_usd: float | None = None, dry_run: bool = False) -> dict:
    if handles is None:
        prof = pd.read_csv(config.path("config", "profiles.csv"), dtype=str)
        handles = prof.loc[prof.platform == "instagram", "handle"].str.lstrip("@").str.lower().tolist()
    n = posts_per_profile or config.get("collection.instagram.posts_per_profile", 60)
    months = config.get("collection.instagram.months_back", 18)
    newer_than = newer_than or (date.today() - timedelta(days=30 * months)).isoformat()
    est = estimate_cost(len(handles), n)
    cap = max_charge_usd or config.get("collection.instagram.max_charge_usd", 4.0)
    plan = {"perfis": len(handles), "posts_por_perfil": n, "desde": newer_than, "custo_estimado_usd": est, "teto_usd": cap}
    if dry_run:
        return plan
    if est > cap:
        raise ValueError(f"custo estimado US$ {est} acima do teto US$ {cap}; reduza posts_por_perfil ou aumente o teto")

    collected_at = datetime.now(timezone.utc).isoformat()
    profiles = run_actor(PROFILE_ACTOR, {"usernames": handles}, max_charge_usd=round(len(handles) * PRICE_PROFILE * 2 + 0.05, 2),
                         max_items=len(handles))
    followers = {str(p.get("username", "")).lower(): p.get("followersCount") for p in profiles if p.get("username")}
    posts = run_actor(POST_ACTOR, {"username": handles, "resultsLimit": n, "onlyPostsNewerThan": newer_than,
                                   "skipPinnedPosts": True, "dataDetailLevel": "basicData"},
                      max_charge_usd=cap, max_items=len(handles) * n)
    for p in posts:
        p["followersCount"] = followers.get(str(p.get("ownerUsername", "")).lower())
        p["collected_at"] = collected_at
        if p.get("productType") == "clips":  # Reels: o 'type' vem como Video
            p["type"] = "clips"

    out_dir = config.raw_dir("instagram_export")
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    (out_dir / f"apify_profiles_{stamp}.json").write_text(json.dumps(profiles, ensure_ascii=False), encoding="utf-8")
    export = out_dir / f"apify_posts_{stamp}.json"
    export.write_text(json.dumps(posts, ensure_ascii=False), encoding="utf-8")

    n_ok, errs = instagram.import_file(export, route_name="apify/instagram-post-scraper", collected_at=collected_at,
                                       only_handles=handles)
    # as URLs de imagem do Instagram expiram em poucos dias: baixa as capas agora
    thumbs = sum(get_thumbnail(f"ig_{p['shortCode']}", p.get("displayUrl")) is not None for p in posts if p.get("shortCode"))
    print(f"[apify] {thumbs} capas salvas em data/media/thumbs", flush=True)
    sem_seg = sorted(h for h in handles if not followers.get(h))
    por_perfil = pd.Series([str(p.get("ownerUsername", "")).lower() for p in posts]).value_counts().to_dict()
    return {**plan, "perfis_retornados": len(followers), "posts_retornados": len(posts), "importados": n_ok, "capas": thumbs,
            "erros_import": errs[:10], "sem_seguidores": sem_seg,
            "sem_posts": sorted(h for h in handles if h not in por_perfil), "export": str(export)}


def import_existing(path: str | Path) -> tuple[int, list[str]]:
    """Reimporta um export salvo (sem gastar créditos), só com posts dos perfis do profiles.csv."""
    prof = pd.read_csv(config.path("config", "profiles.csv"), dtype=str)
    handles = prof.loc[prof.platform == "instagram", "handle"].str.lstrip("@").str.lower().tolist()
    return instagram.import_file(path, route_name="apify/instagram-post-scraper", only_handles=handles)
