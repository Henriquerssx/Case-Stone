"""Validação da categorização (TAP §6.1): amostra manual ≥ 50 e concordância por campo.

Fluxo:
1. `make_sample()` gera validation/manual_sample.csv — estratificado por plataforma × faixa,
   SEM a saída do modelo (rotulagem cega).
2. Você preenche as colunas da rubrica na planilha.
3. `compute()` compara com a categorização automática:
   - categóricos e booleanos: % de concordância + kappa de Cohen
   - notas 0–10: MAE e % dentro de ±2
"""
from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from stone_mpe import config, storage
from stone_mpe.multimodal import rubric as R

LABEL_FIELDS = R.CATEGORICAL_FIELDS + R.BOOL_FIELDS + ["forca_hook_0a10", "clareza_mensagem_0a10"]


def sample_path():
    import os
    from pathlib import Path
    p = Path(os.environ["STONE_MPE_VALIDATION"]) if os.environ.get("STONE_MPE_VALIDATION") else config.path("validation")
    p.mkdir(parents=True, exist_ok=True)
    return p / "manual_sample.csv"


def make_sample(n: int = 50, seed: int = 42, overwrite: bool = False) -> pd.DataFrame:
    """Sorteia do top inteiro (não só do que já foi categorizado): a rotulagem é cega, então
    pode começar antes do modelo terminar. Não sobrescreve rótulos existentes sem overwrite=True."""
    if sample_path().exists() and not overwrite:
        cur = pd.read_csv(sample_path(), dtype=str, encoding="utf-8-sig").fillna("")
        if (cur[[f for f in LABEL_FIELDS if f in cur]] != "").any(axis=1).any():
            raise FileExistsError(f"{sample_path()} já tem rótulos; use --overwrite para sortear de novo")
    df = storage.read_sql(
        "SELECT p.post_id, p.platform, p.faixa, p.handle, p.url, p.media_type FROM posts p WHERE p.is_top = 1")
    if len(df) < n:
        print(f"[agreement] só {len(df)} posts no top; amostra terá {len(df)} (meta: {n})")
        n = len(df)
    strata = df.groupby(["platform", "faixa"], dropna=False)
    frac = n / len(df) if len(df) else 0
    parts = [g.sample(max(1, round(len(g) * frac)), random_state=seed) for _, g in strata]
    s = pd.concat(parts) if parts else df
    if len(s) > n:
        s = s.sample(n, random_state=seed)
    elif len(s) < n:
        s = pd.concat([s, df.drop(s.index).sample(n - len(s), random_state=seed)])
    s = s.copy()
    for f in LABEL_FIELDS:
        s[f] = ""
    s["annotator"] = ""
    s.to_csv(sample_path(), index=False, encoding="utf-8-sig")
    return s


def cohen_kappa(a: list, b: list) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return None if pe == 1 else (po - pe) / (1 - pe)


def _norm_bool(v):
    if pd.isna(v) or v == "":
        return None
    s = str(v).strip().lower()
    return {"1": 1, "true": 1, "sim": 1, "s": 1, "0": 0, "false": 0, "não": 0, "nao": 0, "n": 0}.get(s)


def compute(path: str | Path | None = None, out_name: str = "concordancia") -> pd.DataFrame:
    """Concordância entre uma rotulagem (padrão: a manual) e a categorização usada nas análises.

    path/out_name permitem avaliar outra rotulagem (ex.: validation/rotulagem_ia.csv → outputs/concordancia_ia.csv)
    sem tocar no arquivo da validação humana."""
    manual = pd.read_csv(path or sample_path(), dtype=str, encoding="utf-8-sig").fillna("")
    join, params = storage.categ_join()
    auto = storage.read_sql(f"SELECT c.* FROM posts p {join}", params)
    m = manual.merge(auto, on="post_id", suffixes=("_man", "_auto"))
    rows = []
    for f in LABEL_FIELDS:
        if f + "_man" not in m:  # rotulagem parcial: campo não rotulado fica de fora
            continue
        man, aut = m[f + "_man"], m[f + "_auto"]
        if f in R.BOOL_FIELDS:
            pairs = [(_norm_bool(x), int(y)) for x, y in zip(man, aut) if _norm_bool(x) is not None and pd.notna(y)]
        elif f.endswith("0a10"):
            pairs = [(float(x), float(y)) for x, y in zip(man, aut) if str(x).strip() != "" and pd.notna(y)]
            if pairs:
                diffs = [abs(x - y) for x, y in pairs]
                rows.append({"campo": f, "n": len(pairs), "concordancia": sum(d <= 2 for d in diffs) / len(pairs),
                             "kappa": None, "mae": sum(diffs) / len(diffs), "metrica": "±2 pontos"})
            continue
        else:
            pairs = [(R._coerce_enum(x, _lit(f)), y if pd.notna(y) else "null") for x, y in zip(man, aut) if str(x).strip() != ""]
        if not pairs:
            continue
        a, b = zip(*pairs)
        rows.append({"campo": f, "n": len(pairs), "concordancia": sum(x == y for x, y in pairs) / len(pairs),
                     "kappa": cohen_kappa(list(a), list(b)), "mae": None, "metrica": "exata"})
    res = pd.DataFrame(rows)
    res.to_csv(config.outputs_dir() / f"{out_name}.csv", index=False)
    (config.outputs_dir() / f"{out_name}.json").write_text(res.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    return res


def _lit(field: str):
    return {"formato_video": R.FormatoVideo, "tipo_hook": R.TipoHook, "tema_principal": R.Tema, "tom": R.Tom, "tipo_cta": R.TipoCta}[field]


def cross_model(model: str = "gemma-4-26b-a4b-it,gemma-4-31b-it", gap_s: float = 4.0, client=None) -> pd.DataFrame:
    """Checagem COMPLEMENTAR (não substitui a validação humana): outro modelo recategoriza os posts
    da amostra e medimos a concordância com a categorização usada nas análises.

    Mede consistência entre modelos (o quanto a rubrica é estável), não acerto. Posts que já foram
    categorizados pelo mesmo modelo ficam de fora. Saída: outputs/concordancia_modelos.csv/.json.
    """
    import time

    from stone_mpe.llm import FallbackClient, GeminiClient
    from stone_mpe.multimodal.categorize import categorize_post

    sample = pd.read_csv(sample_path(), dtype=str, encoding="utf-8-sig")
    join, params = storage.categ_join()
    auto = storage.read_sql(f"SELECT p.*, c.model AS cat_model, {', '.join('c.' + f for f in LABEL_FIELDS)} "
                            f"FROM posts p {join} WHERE p.post_id IN ({','.join('?' * len(sample))})",
                            tuple(params) + tuple(sample["post_id"]))
    auto = auto.loc[:, ~auto.columns.duplicated()]
    from stone_mpe.llm import LLMUnavailable
    models = [m.strip() for m in model.split(",") if m.strip()]
    client = client or FallbackClient([GeminiClient(m, "categorize") for m in models], "categorize")
    rows = []
    for post in auto.to_dict(orient="records"):
        if any(m in str(post.get("cat_model", "")) for m in models):
            continue
        t0 = time.time()
        res = None
        for attempt in range(4):  # 503 do plano gratuito é transitório
            try:
                res, meta = categorize_post(post, client)
                break
            except LLMUnavailable:
                time.sleep(20 * (attempt + 1))
                client._down_until.clear() if hasattr(client, "_down_until") else None
        if res is None:
            continue
        rows.append({"post_id": post["post_id"], **{f + "_b": getattr(res, f) for f in LABEL_FIELDS},
                     **{f + "_a": post.get(f) for f in LABEL_FIELDS}})
        if time.time() - t0 > 0.3:
            time.sleep(max(0.0, gap_s - (time.time() - t0)))
    df = pd.DataFrame(rows)
    out = []
    for f in LABEL_FIELDS:
        if df.empty:
            break
        a, b = df[f + "_a"], df[f + "_b"]
        ok = a.notna() & b.notna()
        if f.endswith("0a10"):
            d = (a[ok].astype(float) - b[ok].astype(float)).abs()
            out.append({"campo": f, "n": int(ok.sum()), "concordancia": float((d <= 2).mean()), "kappa": None,
                        "mae": float(d.mean()), "metrica": "±2 pontos"})
        else:
            if f in R.BOOL_FIELDS:
                aa, bb = a[ok].astype(float).astype(int).tolist(), b[ok].astype(int).tolist()
            else:
                aa, bb = a[ok].astype(str).tolist(), b[ok].astype(str).tolist()
            out.append({"campo": f, "n": len(aa), "concordancia": sum(x == y for x, y in zip(aa, bb)) / len(aa) if aa else None,
                        "kappa": cohen_kappa(aa, bb), "mae": None, "metrica": "exata"})
    res = pd.DataFrame(out)
    res.insert(0, "verificador", model)
    res.to_csv(config.outputs_dir() / "concordancia_modelos.csv", index=False)
    (config.outputs_dir() / "concordancia_modelos.json").write_text(res.to_json(orient="records", force_ascii=False, indent=2), encoding="utf-8")
    return res
