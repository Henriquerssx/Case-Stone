"""Estado de cada etapa do pipeline (usado pelo painel e por `cli status`)."""
from __future__ import annotations

import json

import pandas as pd

from stone_mpe import config, storage


def _count(sql: str, params: tuple = ()) -> int:
    try:
        return int(storage.read_sql(sql, params).iloc[0, 0] or 0)
    except Exception:
        return 0


def _lines(path) -> int:
    return sum(1 for _ in open(path, encoding="utf-8")) if path.exists() else 0


def pipeline() -> list[dict]:
    """Uma linha por etapa: nome, número principal, detalhe, status (ok | parcial | pendente) e comando."""
    out = config.outputs_dir()
    prof = pd.read_csv(config.path("config", "profiles.csv"), dtype=str)
    n_prof = prof.groupby("platform").size().to_dict()
    has_posts = storage.table_exists("posts")
    raw = _count("SELECT COUNT(*) FROM posts") if has_posts else 0
    by_plat = storage.read_sql("SELECT platform, COUNT(*) n, SUM(eligible) e, SUM(is_top) t FROM posts GROUP BY platform") if has_posts else pd.DataFrame()
    elig = int(by_plat["e"].sum()) if not by_plat.empty else 0
    top = int(by_plat["t"].sum()) if not by_plat.empty else 0
    has_cat = storage.table_exists("categorizations")
    cat_top = _count("""SELECT COUNT(DISTINCT c.post_id) FROM categorizations c JOIN posts p USING(post_id)
                        WHERE c.valid = 1 AND p.is_top = 1""") if has_cat else 0
    cat_rest = _count("""SELECT COUNT(DISTINCT c.post_id) FROM categorizations c JOIN posts p USING(post_id)
                         WHERE c.valid = 1 AND p.is_top = 0""") if has_cat else 0
    cat_n2 = _count("SELECT COUNT(*) FROM categorizations WHERE valid = 1 AND prompt_version = ?",
                    (config.get("level2.prompt_version", "v1-n2"),)) if has_cat else 0
    from stone_mpe.analysis.agreement import sample_path
    sample = sample_path()
    labeled = 0
    if sample.exists():
        s = pd.read_csv(sample, dtype=str, encoding="utf-8-sig").fillna("")
        labeled = int((s.get("annotator", pd.Series(dtype=str)) != "").sum())
    conc = out / "concordancia.csv"
    n_comments = _count("SELECT SUM(n_sampled) FROM comment_signals") if storage.table_exists("comment_signals") else 0
    demo = json.loads((out / "demo_cache.json").read_text(encoding="utf-8")) if (out / "demo_cache.json").exists() else {}
    demo_llm = sum(1 for v in demo.values() if v.get("llm") not in (None, "none"))
    plats = ", ".join(f"{r.platform}: {int(r.n):,}".replace(",", ".") for r in by_plat.itertuples()) if not by_plat.empty else ""

    def st(done: bool, partial: bool = False) -> str:
        return "ok" if done else ("parcial" if partial else "pendente")

    return [
        {"etapa": "1. Perfis", "numero": len(prof), "detalhe": " · ".join(f"{k}: {v}" for k, v in n_prof.items()),
         "status": "ok", "comando": "config/profiles.csv"},
        {"etapa": "2. Coleta", "numero": raw, "detalhe": plats or "nenhum post coletado",
         "status": st("instagram" in set(by_plat.get("platform", [])) and raw > 0, raw > 0),
         "comando": "cli collect-youtube · cli collect-instagram"},
        {"etapa": "3. Base e métrica", "numero": elig, "detalhe": "elegíveis (≥ 14 dias, métricas visíveis) de " + f"{raw:,}".replace(",", "."),
         "status": st(elig > 0), "comando": "cli build-base"},
        {"etapa": "4. Top 10%", "numero": top, "detalhe": "percentil 90 de (curtidas + comentários) ÷ seguidores, por plataforma",
         "status": st(top > 0), "comando": "cli build-base"},
        {"etapa": "5. Categorização", "numero": cat_top, "detalhe": f"de {top} do top · {cat_rest} fora do top (lift) · {cat_n2} no Nível 2",
         "status": st(top > 0 and cat_top >= top, cat_top > 0), "comando": "cli categorize --until-done"},
        {"etapa": "6. Validação manual", "numero": labeled, "detalhe": "de 50 rotulados" + (" · concordância calculada" if conc.exists() else "")
                   + (" · checagem entre modelos feita" if (out / "concordancia_modelos.csv").exists() else "")
                   + (" · rotulagem cega por IA feita (não substitui a humana)" if (out / "concordancia_ia.csv").exists() else ""),
         "status": st(conc.exists() and labeled >= 50, labeled > 0), "comando": "streamlit run demo/rotular.py → cli agreement"},
        {"etapa": "7. Padrões", "numero": cat_top, "detalhe": f"comentários analisados: {n_comments}",
         "status": st((out / "patterns.json").exists() and cat_top >= top, (out / "patterns.json").exists()), "comando": "cli collect-comments · cli analyze"},
        {"etapa": "8. Agente", "numero": _lines(out / "runs.jsonl"), "detalhe": f"execuções registradas · cache da demo: {demo_llm}/{len(demo)} com LLM",
         "status": st(demo_llm > 0, len(demo) > 0), "comando": "cli ask · python -m stone_mpe.mcp_server"},
        {"etapa": "9. Playbook", "numero": int((out / "playbook.md").exists()), "detalhe": "outputs/playbook.md",
         "status": st((out / "playbook.md").exists()), "comando": "cli playbook"},
    ]


def reference_metrics(post_ids: list[str]) -> pd.DataFrame:
    """Métricas reais dos posts de referência (o que o criativo usa como base)."""
    if not post_ids:
        return pd.DataFrame()
    q = ",".join("?" * len(post_ids))
    return storage.read_sql(
        f"""SELECT post_id, handle, platform, url, faixa, followers, likes, comments, views, duration_s,
                   engagement_rate, percentile, posted_at FROM posts WHERE post_id IN ({q})""", tuple(post_ids))


def benchmarks(platform: str | None = None, segment: str | None = None) -> dict:
    """Limiar do top, mediana do top e mediana geral do recorte (para traduzir em metas)."""
    where, params = ["eligible = 1"], []
    if platform:
        where.append("platform = ?"); params.append(platform)
    if segment:
        where.append("segmento = ?"); params.append(segment)
    df = storage.read_sql(f"SELECT engagement_rate, is_top, views, followers, platform FROM posts WHERE {' AND '.join(where)}", tuple(params))
    if df.empty:
        return {}
    top = df[df.is_top == 1]
    stats = json.loads((config.outputs_dir() / "base_stats.json").read_text(encoding="utf-8")) \
        if (config.outputs_dir() / "base_stats.json").exists() else {}
    thr = stats.get("er_threshold_by_platform", {})
    # limiar do top é por plataforma; num recorte misto, usa o menor (mais conservador para meta)
    plats = [platform] if platform else sorted(df.platform.unique())
    limiar = min(thr[p] for p in plats if p in thr) if any(p in thr for p in plats) else float(df.engagement_rate.quantile(0.9))
    return {"n": len(df), "n_top": len(top), "mediana_geral": float(df.engagement_rate.median()),
            "limiar_top": float(limiar), "mediana_top": float(top.engagement_rate.median()) if len(top) else None,
            "views_por_seguidor_top": float((top.views / top.followers).median()) if len(top) and top.views.notna().any() else None}


def goals(followers: int, bm: dict) -> dict:
    """Interações (curtidas + comentários) necessárias para um perfil com `followers` seguidores."""
    if not bm or not followers:
        return {}
    return {"mediana_da_base": round(followers * bm["mediana_geral"]),
            "entrar_no_top": round(followers * bm["limiar_top"]),
            "mediana_do_top": round(followers * bm["mediana_top"]) if bm.get("mediana_top") else None}
