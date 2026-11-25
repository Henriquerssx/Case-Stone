"""Categorização das publicações com a rubrica fixa.

Nível 1: legenda + thumbnail (obrigatório).  prompt_version = categorization.prompt_version
Nível 2: + frames (gancho e corpo), transcrição e ritmo de cortes medido.  prompt_version = level2.prompt_version

- Checkpoint por post no SQLite: re-execução pula o que já está válido na mesma prompt_version.
- JSON inválido -> nova tentativa com o erro de validação no prompt (máx. N).
- Mídia indisponível -> cai para o que houver (thumbnail/legenda) e registra as modalidades usadas.
- `rest_sample`: categoriza uma amostra aleatória de posts FORA do top (comparação top × resto, Nível 3).
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pandas as pd
from pydantic import ValidationError

from stone_mpe import config, storage
from stone_mpe.collect.media import get_thumbnail
from stone_mpe.llm import FallbackClient, LLMUnavailable, get_client, parse_json
from stone_mpe.multimodal import rubric as R

PROMPT = """Você é um analista de conteúdo para redes sociais especializado em micro e pequenos empreendedores (MPEs) no Brasil.
Analise a publicação abaixo usando as imagens fornecidas, quando houver, e os textos.
Responda EXCLUSIVAMENTE com um objeto JSON neste formato, sem texto extra:

{schema}

Regras:
- Use exatamente os valores permitidos (com acentos). Não invente categorias.
- formato_video = null se a publicação for imagem ou carrossel sem vídeo.
- hook_primeiros_3s: {hook_rule}
- ritmo_cortes_0a10: {cuts_rule}
- tem_rosto / texto_na_tela: julgue pelas imagens; sem imagem, infira pela legenda e seja conservador (false).
- criador_e_empreendedor_real: true se quem aparece/fala tem negócio próprio (não apenas influenciador/marca).
- prova_social: depoimentos, números de clientes, resultados de terceiros, antes/depois.
- tem_cta / tipo_cta: chamada explícita na legenda, na fala ou na tela (comentar, salvar, link na bio, DM, seguir).
- elementos_top5: os 5 elementos que mais explicam o engajamento desta publicação, frases curtas.

Publicação:
- plataforma: {platform}
- perfil: @{handle} ({faixa}, segmento: {segmento})
- tipo de mídia: {media_type}
- duração: {duracao}
- imagens: {images_desc}
- legenda:
\"\"\"
{caption}
\"\"\"
{extra}"""

HOOK_L1 = "a frase de abertura mais provável (texto na capa ou primeira frase da legenda), até 15 palavras."
HOOK_L2 = "o que é DITO ou ESCRITO nos 3 primeiros segundos (use a transcrição dos 0–3 s e os 3 primeiros frames), até 15 palavras."
CUTS_L1 = "null — com apenas a capa não é possível observar cortes."
CUTS_L2 = "use a medição fornecida (trocas de cena por segundo) e os frames; 0 = plano único, 10 = cortes a cada segundo ou mais."


def pv(level: int) -> str:
    return config.get("level2.prompt_version", "v1-n2") if level == 2 else config.get("categorization.prompt_version", "v1")


def build_prompt(post: dict, error: str | None = None, bundle: dict | None = None, has_thumb: bool = False) -> str:
    cap = str(post.get("caption") or "")[: config.get("categorization.caption_max_chars", 2200)]
    dur = post.get("duration_s")
    bundle = bundle or {}
    n_frames = len(bundle.get("frames", []))
    l2 = n_frames > 0 or bundle.get("transcript")
    img = []
    if has_thumb:
        img.append("1ª imagem = capa/thumbnail")
    if n_frames:
        img.append(f"em seguida {n_frames} frames em ordem temporal (os 3 primeiros = 0,5 s, 1,5 s e 2,5 s, o gancho)")
    extra = ""
    tr = bundle.get("transcript")
    if tr:
        extra += f'\nTranscrição dos primeiros 3 s: "{tr["first_3s"][:300]}"\nTranscrição completa: """{tr["text"][:2500]}"""\n'
    elif l2:
        extra += "\nTranscrição: sem fala detectada (provavelmente só música).\n"
    if bundle.get("cuts_per_s") is not None:
        extra += f"Ritmo de cortes medido: {bundle['cuts_per_s']:.2f} trocas de cena por segundo.\n"
    p = PROMPT.format(
        schema=R.json_schema_hint(), platform=post["platform"], handle=post["handle"], faixa=post.get("faixa") or "?",
        segmento=post.get("segmento") or "geral", media_type=post["media_type"],
        duracao=f"{dur:.0f}s" if isinstance(dur, (int, float)) and dur == dur else "n/a",
        images_desc="; ".join(img) or "nenhuma", caption=cap, extra=extra,
        hook_rule=HOOK_L2 if l2 else HOOK_L1, cuts_rule=CUTS_L2 if bundle.get("cuts_per_s") is not None else CUTS_L1,
    )
    if error:
        p += f"\n\nSua resposta anterior era inválida: {error[:800]}\nCorrija e responda apenas com o JSON válido."
    return p


def categorize_post(post: dict, client: FallbackClient, level: int = 1, max_retries: int | None = None) -> tuple[R.Rubric | None, dict]:
    max_retries = config.get("categorization.max_json_retries", 2) if max_retries is None else max_retries
    thumb = get_thumbnail(post["post_id"], post.get("thumbnail_url"))
    bundle: dict = {}
    if level == 2:
        from stone_mpe.multimodal.video import cut_score_0a10, media_bundle
        bundle = media_bundle(post)
    images = ([thumb] if thumb else []) + [p.read_bytes() for p in bundle.get("frames", [])]
    modalities = ["caption"] + (["thumbnail"] if thumb else []) + bundle.get("modalities", [])
    error, raw = None, ""
    for _ in range(max_retries + 1):
        raw = client.complete(build_prompt(post, error, bundle, bool(thumb)), images=images or None, json_mode=True)
        try:
            judged = R.RubricLLM.model_validate(parse_json(raw))
            d = judged.model_dump()
            if level == 2 and bundle.get("cuts_per_s") is not None:
                d["ritmo_cortes_0a10"] = cut_score_0a10(bundle["cuts_per_s"])  # medição vence o julgamento
            full = R.Rubric(**d, tipo_post=R.tipo_post(post["media_type"]), duracao_faixa=R.duracao_faixa(post.get("duration_s")),
                            legenda_tamanho=R.legenda_tamanho(post.get("caption")))
            return full, {"raw_json": raw, "input_modalities": modalities, "error": None, "cuts_per_s": bundle.get("cuts_per_s")}
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            error = str(e)
    return None, {"raw_json": raw, "input_modalities": modalities, "error": error}


def save(post_id: str, result: R.Rubric | None, meta: dict, model: str, prompt_version: str | None = None) -> None:
    row = {
        "post_id": post_id, "prompt_version": prompt_version or pv(1), "model": model,
        "input_modalities": json.dumps(meta["input_modalities"]), "valid": int(result is not None),
        "error": meta["error"], "raw_json": meta["raw_json"], "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if result is not None:
        d = result.model_dump()
        d["elementos_top5"] = json.dumps(d["elementos_top5"], ensure_ascii=False)
        for k in R.BOOL_FIELDS:
            d[k] = int(d[k])
        row.update(d)
    cols = ", ".join(row)
    with storage.connect() as conn:
        conn.execute(f"INSERT OR REPLACE INTO categorizations ({cols}) VALUES ({', '.join('?' * len(row))})", tuple(row.values()))


def pending_posts(level: int = 1, limit: int | None = None, rest_sample: int = 0, seed: int = 42) -> pd.DataFrame:
    """Top sem categorização válida na versão do nível; ou amostra aleatória do resto elegível."""
    where = "p.is_top = 1" if not rest_sample else "p.is_top = 0 AND p.eligible = 1"
    if level == 2:
        where += " AND p.media_type IN ('reels', 'short', 'video')"
    df = storage.read_sql(
        f"""SELECT p.* FROM posts p
            LEFT JOIN categorizations c ON c.post_id = p.post_id AND c.prompt_version = ? AND c.valid = 1
            WHERE {where} AND c.post_id IS NULL ORDER BY p.engagement_rate DESC""",
        (pv(level),),
    )
    if rest_sample:
        done = storage.read_sql("""SELECT COUNT(*) n FROM posts p JOIN categorizations c ON c.post_id = p.post_id
                                   AND c.prompt_version = ? AND c.valid = 1 WHERE p.is_top = 0""", (pv(level),))["n"].iloc[0]
        need = max(0, rest_sample - int(done))
        # estratificado por plataforma, proporcional ao tamanho do resto
        if need and len(df):
            parts = [g.sample(min(len(g), round(need * len(g) / len(df))), random_state=seed) for _, g in df.groupby("platform")]
            df = pd.concat(parts)
        else:
            df = df.head(0)
    return df.head(limit) if limit else df


def run_until_done(level: int = 1, rest_sample: int = 0, wait_s: float = 180, max_hours: float = 6) -> dict:
    """Repete run() enquanto houver pendências, esperando `wait_s` quando todos os provedores falham
    (503/429 do plano gratuito são transitórios). Para quando uma rodada não avança ou após `max_hours`."""
    deadline = time.time() + max_hours * 3600
    total = {"level": level, "processed": 0, "valid": 0, "invalid": 0, "rounds": 0}
    while time.time() < deadline:
        r = run(level=level, rest_sample=rest_sample)
        total["rounds"] += 1
        for k in ("processed", "valid", "invalid"):
            total[k] += r[k]
        pending = len(pending_posts(level, rest_sample=rest_sample))
        total["remaining"] = pending
        if pending == 0 or (not r["exhausted"] and r["valid"] == 0):
            break  # terminou, ou só sobraram posts que falham sempre (registrados como inválidos)
        if r["exhausted"]:
            print(f"[categorize] {pending} pendentes; aguardando {wait_s:.0f}s antes de retomar...", flush=True)
            time.sleep(wait_s)
    return total


def run(limit: int | None = None, level: int = 1, rest_sample: int = 0, post_ids: list[str] | None = None,
        workers: int | None = None) -> dict:
    """Categoriza os pendentes. Com workers > 1 (só Nível 1), cada thread tem seu próprio cliente
    (disjuntor e `model` independentes); a gravação no SQLite fica na thread principal."""
    if not get_client("categorize").clients:
        raise LLMUnavailable("Configure GEMINI_API_KEY, OPENROUTER_API_KEY ou OLLAMA_BASE_URL no .env")
    todo = pending_posts(level, limit, rest_sample)
    if post_ids:
        todo = storage.read_sql(f"SELECT * FROM posts WHERE post_id IN ({','.join('?' * len(post_ids))})", tuple(post_ids))
    posts = todo.to_dict(orient="records")
    workers = 1 if level == 2 else (workers or config.get("categorization.workers", 1))
    gap = config.get("categorization.min_interval_s", 4.5) * workers  # mantém a taxa total ~1 chamada a cada min_interval_s
    local = threading.local()
    stop = threading.Event()

    def work(post: dict):
        if stop.is_set():
            return post, None, None, None
        if not hasattr(local, "client"):
            local.client = get_client("categorize")
        t0 = time.time()
        try:
            result, meta = categorize_post(post, local.client, level)
        except LLMUnavailable as e:
            stop.set()
            return post, None, None, e
        elapsed = time.time() - t0
        if gap - elapsed > 0 and elapsed > 0.3:  # resposta do cache -> sem espera
            time.sleep(gap - elapsed)
        return post, result, (meta, local.client.model), None

    ok = fail = 0
    exhausted = False
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(work, p) for p in posts]
        for i, fut in enumerate(as_completed(futures), 1):
            post, result, info, err = fut.result()
            if err is not None:
                if not exhausted:
                    print(f"[categorize] provedores esgotados em {post['post_id']}: {err}. Checkpoint salvo; rode de novo depois.", flush=True)
                exhausted = True
                continue
            if info is None:  # cancelado após esgotar
                continue
            meta, model = info
            save(post["post_id"], result, meta, model, pv(level))
            ok += result is not None
            fail += result is None
            print(f"[categorize N{level}] {i}/{len(posts)} {post['post_id']} {meta['input_modalities']} "
                  f"{'OK' if result else 'FALHA: ' + str(meta['error'])[:120]} [{model}]", flush=True)
    remaining = len(pending_posts(level)) if not rest_sample else None
    return {"level": level, "processed": ok + fail, "valid": ok, "invalid": fail, "remaining_top": remaining, "exhausted": exhausted}
