import json

import pytest
from pydantic import ValidationError

from stone_mpe import storage
from stone_mpe.api import run
from tests.conftest import FakeLLM


def _all_ids():
    return set(storage.read_sql("SELECT post_id FROM posts")["post_id"])


@pytest.mark.parametrize("mode", ["analisar", "recomendar", "gerar_criativo"])
def test_tres_modos_sem_llm_retornam_contrato(synthetic_db, mode):
    out = run(mode, "Reels para atrair donos de pequenos restaurantes")
    assert out.findings and out.reference_posts
    assert all(0 <= f.frequency <= 1 for f in out.findings)
    if mode == "gerar_criativo":
        assert out.creatives and all(set(c.inspired_by) <= _all_ids() for c in out.creatives)


def test_segmento_inferido_e_amplia_quando_pequeno(synthetic_db):
    out = run("analisar", "o que engaja donos de restaurante?")
    assert "segmento inferido do pedido: alimentacao" in out.explanation
    # o segmento sintético tem poucos posts no top -> recorre aos padrões gerais e diz por quê
    assert out.confidence_level in ("media", "baixa") and out.confidence_reason
    assert "padrões gerais" in out.explanation or out.confidence_level == "baixa"


def test_criativo_com_referencia_inventada_e_descartado_e_refeito(synthetic_db):
    bad = json.dumps({"creatives": [{"gancho": "g", "roteiro": "r", "legenda": "l", "cta": "c", "inspired_by": ["post_inventado"]}]})
    fake = FakeLLM([bad, "placeholder"])
    out_ids = {}

    def good_response():
        # 2ª tentativa: usa um id que o agente passou no prompt
        prompt = fake.prompts[-1]
        start = prompt.index('"post_id": "') + len('"post_id": "')
        pid = prompt[start:prompt.index('"', start)]
        out_ids["pid"] = pid
        return json.dumps({"creatives": [{"gancho": "g", "roteiro": "r", "legenda": "l", "cta": "c", "inspired_by": [pid, "fake_2"]}]})

    def complete(prompt, images=None, json_mode=True):
        fake.prompts.append(prompt)
        return bad if len(fake.prompts) == 1 else good_response()

    fake.complete = complete
    out = run("gerar_criativo", "Reels sobre precificação", llm=fake)
    assert len(fake.prompts) == 2 and "rejeitada" in fake.prompts[1]
    assert out.creatives[0].inspired_by == [out_ids["pid"]]  # id inexistente filtrado
    assert out.llm == "fake/test"


def test_numeros_vem_da_base_nao_do_llm(synthetic_db):
    fake = FakeLLM(["Texto livre do LLM."])
    out = run("analisar", "quais formatos aparecem?", llm=fake)
    f = out.findings[0]
    assert f.n_posts <= f.total and f.example_post_ids and set(f.example_post_ids) <= _all_ids()
    assert out.explanation.startswith("Texto livre do LLM.")


def test_entrada_invalida(synthetic_db):
    with pytest.raises(ValidationError):
        run("prever", "abc")
    with pytest.raises(ValidationError):
        run("analisar", "x")


def test_execucao_registrada(synthetic_db, env):
    run("analisar", "padrões gerais")
    lines = (env / "outputs" / "runs.jsonl").read_text(encoding="utf-8").strip().splitlines()
    rec = json.loads(lines[-1])
    assert rec["tools_called"] == ["consulta_base", "posts_referencia"] and rec["reference_post_ids"]


def test_filtro_sem_resultado_amplia_soltando_porte_antes_do_nicho(synthetic_db):
    out = run("gerar_criativo", "qualquer coisa", filters={"platform": "youtube", "profile_size": "micro"})
    assert "filtro de porte de perfil removido" in out.explanation
    assert out.findings and out.creatives


def test_niveis_de_confianca():
    from stone_mpe.agent.graph import confidence
    assert confidence(5, {})[0] == "baixa"
    assert confidence(15, {})[0] == "media"
    assert confidence(625, {"segment_dropped": True})[0] == "media"
    assert confidence(154, {})[0] == "alta"


def test_tipo_post_ambiguo_nao_filtra():
    from stone_mpe.agent.tools import infer_scope
    _, f, _ = infer_scope("Vídeo curto (Reels/Shorts) sobre precificação", None, {})
    assert "tipo_post" not in f
    _, f, _ = infer_scope("Reels sobre precificação", None, {})
    assert f["tipo_post"] == "reels"


def test_lift_exige_amostra_minima_do_resto(synthetic_db):
    from stone_mpe.analysis import patterns
    assert patterns.lift(min_rest=10_000).empty
