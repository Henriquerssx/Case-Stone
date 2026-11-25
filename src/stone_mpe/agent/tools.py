"""Ferramentas do agente. Todos os dados vêm da base (SQLite) — nunca do LLM."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter

import pandas as pd

from stone_mpe import config
from stone_mpe.analysis.patterns import frequencies, load_top
from stone_mpe.agent.schemas import Finding, ReferencePost

FINDING_FIELDS = ["tipo_post", "formato_video", "tipo_hook", "tema_principal", "tipo_cta", "tom", "duracao_faixa",
                  "legenda_tamanho", "tem_rosto", "texto_na_tela", "prova_social", "criador_e_empreendedor_real",
                  "oferta_ou_beneficio_explicito"]
BOOL_FINDINGS = {"tem_rosto", "texto_na_tela", "prova_social", "criador_e_empreendedor_real", "oferta_ou_beneficio_explicito"}

SEGMENT_KEYWORDS = {
    "alimentacao": ["restaurante", "lanchonete", "comida", "alimentacao", "confeitaria", "doceria", "padaria", "food", "marmita", "hamburgueria", "gastronomia", "bolo"],
    "beleza": ["salao", "beleza", "cabeleireir", "manicure", "estetica", "barbearia", "maquiagem", "unha", "sobrancelha"],
    "varejo": ["loja", "varejo", "brecho", "roupa", "moda", "boutique", "comercio", "mercadinho"],
    "servicos": ["servico", "prestador", "autonomo", "freelancer", "consultoria", "oficina", "eletricista", "diarista"],
    "financas": ["financas", "precificacao", "preco", "caixa", "lucro", "mei", "dinheiro"],
}
TIPO_POST_KEYWORDS = {"reels": ["reels", "reel"], "carrossel": ["carrossel", "carousel"], "short": ["shorts", "short"]}

STOP = set("a o os as de da do das dos e em para por com um uma que no na nos nas se mais como ao seu sua quais qual "
           "sobre ser ter pra pro me eu voce voces isso esse essa este esta entre ou mas muito pelo pela".split())


def fold(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


def tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", fold(s)) if len(t) > 2 and t not in STOP]


def infer_scope(query: str, segment: str | None, filters: dict) -> tuple[str | None, dict, list[str]]:
    """Infere segmento e tipo de post do texto quando não informados. Retorna notas para a explicação."""
    q = " " + fold(query) + " "
    notes = []
    if not segment:
        for seg, kws in SEGMENT_KEYWORDS.items():
            if seg == "financas":
                continue  # tema, não segmento de negócio: não restringe o recorte
            if any(k in q for k in kws):
                segment = seg
                notes.append(f"segmento inferido do pedido: {seg}")
                break
    if not filters.get("tipo_post"):
        hits = [tp for tp, kws in TIPO_POST_KEYWORDS.items() if any(re.search(rf"\b{k}\b", q) for k in kws)]
        if len(hits) == 1:  # "Reels/Shorts" cita mais de um tipo: não filtra
            filters = {**filters, "tipo_post": hits[0]}
            notes.append(f"tipo de post inferido do pedido: {hits[0]}")
    return segment, filters, notes


def consulta_base(segment: str | None, filters: dict, min_posts: int = 3) -> tuple[pd.DataFrame, list[Finding], dict]:
    """Recorte do top + frequências. Amplia o recorte (e sinaliza) se ficar vazio/pequeno demais."""
    meta = {"segment_used": segment, "filters_used": dict(filters), "widened": []}
    df = load_top(segment, filters)
    if len(df) < min_posts and segment:
        meta["widened"].append(f"segmento '{segment}' tem só {len(df)} posts no top; recorte ampliado para todos os segmentos")
        segment = None
        meta["segment_used"] = None
        df = load_top(None, filters)
    if len(df) < min_posts and filters.get("tipo_post"):
        meta["widened"].append(f"tipo_post '{filters['tipo_post']}' com poucos posts; filtro removido")
        filters = {k: v for k, v in filters.items() if k != "tipo_post"}
        meta["filters_used"] = filters
        df = load_top(segment, filters)
    freq = frequencies(df, FINDING_FIELDS)
    k = config.get("agent.findings_per_field", 3)
    out: list[Finding] = []
    for field, g in freq.groupby("field", sort=False):
        if field in BOOL_FINDINGS:
            g = g[g["value"] == "sim"]
        for r in g.head(k).itertuples():
            out.append(Finding(feature=f"{field}={r.value}", frequency=round(r.freq, 4), n_posts=r.n, total=r.total,
                               example_post_ids=list(r.example_post_ids)))
    meta["n_top_recorte"] = len(df)
    return df, out, meta


def _bm25(query_toks: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    if n == 0:
        return []
    avg = sum(len(d) for d in docs) / n or 1
    df_ = Counter(t for d in docs for t in set(d))
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for t in query_toks:
            if t not in tf:
                continue
            idf = math.log(1 + (n - df_[t] + 0.5) / (df_[t] + 0.5))
            s += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(d) / avg))
        scores.append(s)
    return scores


def _doc_text(r: pd.Series) -> str:
    el = r.get("elementos_top5") or "[]"
    try:
        el = " ".join(json.loads(el))
    except (TypeError, ValueError):
        el = str(el)
    return " ".join(str(r.get(c) or "") for c in ("caption", "hook_primeiros_3s", "tema_principal", "formato_video", "tipo_hook")) + " " + el


CATEGORY_COLS = ["tipo_post", "formato_video", "tipo_hook", "hook_primeiros_3s", "tema_principal", "tom", "tipo_cta",
                 "tem_rosto", "texto_na_tela", "prova_social", "criador_e_empreendedor_real", "elementos_top5"]


def posts_referencia(df: pd.DataFrame, query: str, k: int | None = None) -> list[ReferencePost]:
    """Top posts do recorte mais semelhantes ao pedido (BM25 lexical) com desempate por engajamento."""
    k = k or config.get("agent.reference_k", 5)
    if df.empty:
        return []
    df = df.copy()
    df["_score"] = _bm25(tokens(query), [tokens(_doc_text(r)) for _, r in df.iterrows()])
    # normaliza a similaridade e mistura com o percentil de engajamento (0.7 similaridade, 0.3 desempenho)
    mx = df["_score"].max()
    df["_rank"] = 0.7 * (df["_score"] / mx if mx > 0 else 0) + 0.3 * df["percentile"].fillna(0)
    # diversidade: no máximo N referências por criador (o top é concentrado em poucos canais)
    per = config.get("agent.max_refs_per_creator", 2)
    ranked = df.sort_values("_rank", ascending=False)
    ranked = ranked[ranked.groupby("handle").cumcount() < per] if "handle" in ranked else ranked
    out = []
    for _, r in ranked.head(k).iterrows():
        cats = {}
        for c in CATEGORY_COLS:
            v = r.get(c)
            if c == "elementos_top5" and isinstance(v, str):
                try:
                    v = json.loads(v)
                except ValueError:
                    pass
            if hasattr(v, "item"):  # numpy -> python (serializável)
                v = v.item()
            cats[c] = None if (isinstance(v, float) and math.isnan(v)) else v
        out.append(ReferencePost(post_id=r["post_id"], url=r["url"], platform=r["platform"], handle=r["handle"],
                                 engagement_rate=round(float(r["engagement_rate"]), 5), categories=cats))
    return out
