"""Fixtures com base SINTÉTICA — usada apenas para testar o código, nunca como resultado."""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from stone_mpe import storage
from stone_mpe.multimodal import rubric as R
from stone_mpe.multimodal.categorize import save
from stone_mpe.process import normalize

TEMAS = list(R.Tema.__args__)
FORMATOS = list(R.FormatoVideo.__args__)
HOOKS = list(R.TipoHook.__args__)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("STONE_MPE_DB", str(tmp_path / "test.sqlite"))
    monkeypatch.setenv("STONE_MPE_OUTPUTS", str(tmp_path / "outputs"))
    monkeypatch.setenv("STONE_MPE_DATA", str(tmp_path / "data"))
    monkeypatch.setenv("STONE_MPE_VALIDATION", str(tmp_path / "validation"))  # nunca tocar na amostra real
    monkeypatch.setenv("LLM_PROVIDERS", "none")
    return tmp_path


def synthetic_raw(n_per_profile: int = 40, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rnd = random.Random(seed)
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    profiles = [("instagram", "loja_micro", 5_000, "varejo"), ("instagram", "chef_medio", 50_000, "alimentacao"),
                ("instagram", "salao_grande", 400_000, "beleza"), ("youtube", "canal_mei", 80_000, "financas")]
    rows = []
    for plat, handle, fol, _seg in profiles:
        for i in range(n_per_profile):
            age = rnd.randint(1, 300)
            rows.append({
                "post_id": f"{'yt' if plat == 'youtube' else 'ig'}_{handle}_{i}", "platform": plat, "handle": handle,
                "url": f"https://example.com/{handle}/{i}", "media_type": "short" if plat == "youtube" else rnd.choice(["reels", "carrossel"]),
                "posted_at": (now - timedelta(days=age)).isoformat(), "collected_at": now.isoformat(),
                "caption": f"dica {i} de {handle} sobre caixa e precificação para restaurante e salão",
                "tags": [], "likes": int(fol * rnd.uniform(0.002, 0.08)), "comments": int(fol * rnd.uniform(0, 0.01)),
                "views": None, "duration_s": rnd.choice([12.0, 25.0, 45.0, 70.0]), "thumbnail_url": None,
                "followers": fol, "source_route": "sintetico",
            })
    meta = pd.DataFrame([{"platform": p, "handle": h, "origem": "teste", "segmento": s, "justificativa": "sintético"} for p, h, _, s in profiles])
    return pd.DataFrame(rows), meta


@pytest.fixture
def synthetic_db(env):
    return build_synthetic_db()


def build_synthetic_db():
    raw, meta = synthetic_raw()
    posts = normalize.build(raw, meta)
    profiles = normalize.profiles_table(posts)
    db = posts.copy()
    for c in ("posted_at", "collected_at"):
        db[c] = db[c].astype(str)
    storage.write_table(db, "posts")
    storage.write_table(profiles, "profiles")
    rnd = random.Random(3)
    for p in posts[posts["is_top"]].to_dict(orient="records"):
        rub = R.Rubric(
            formato_video=rnd.choice(FORMATOS[:3]), hook_primeiros_3s="Você sabe quanto sobra no caixa?",
            tipo_hook=rnd.choice(HOOKS[:3]), forca_hook_0a10=rnd.randint(4, 9), tema_principal=rnd.choice(TEMAS[:4]),
            tem_rosto=rnd.random() > 0.3, criador_e_empreendedor_real=rnd.random() > 0.5, prova_social=rnd.random() > 0.7,
            texto_na_tela=True, ritmo_cortes_0a10=None, tom="informal", usa_linguagem_regional=False,
            clareza_mensagem_0a10=8, tem_cta=True, tipo_cta=rnd.choice(["comentar", "salvar"]), oferta_ou_beneficio_explicito=False,
            elementos_top5=["gancho de dor", "lista", "texto na tela", "rosto", "cta de comentário"],
            tipo_post=R.tipo_post(p["media_type"]), duracao_faixa=R.duracao_faixa(p["duration_s"]), legenda_tamanho=R.legenda_tamanho(p["caption"]),
        )
        save(p["post_id"], rub, {"raw_json": json.dumps({}), "input_modalities": ["caption"], "error": None}, "sintetico")
    return posts


class FakeLLM:
    """Cliente LLM falso: devolve respostas pré-programadas em sequência."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.prompts: list[str] = []
        self.clients = [self]
        self.name = "fake"

    @property
    def model(self) -> str:
        return "fake/test"

    def complete(self, prompt, images=None, json_mode=True):
        self.prompts.append(prompt)
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
