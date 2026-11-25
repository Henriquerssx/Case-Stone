import pytest
from pydantic import ValidationError

from stone_mpe.analysis.agreement import cohen_kappa
from stone_mpe.analysis.lead_signals import has_contact_intent
from stone_mpe.llm import parse_json
from stone_mpe.multimodal import rubric as R

BASE = dict(formato_video="lista/dicas", hook_primeiros_3s="3 erros no caixa", tipo_hook="número", forca_hook_0a10=8,
            tema_principal="finanças", tem_rosto=True, criador_e_empreendedor_real=True, prova_social=False,
            texto_na_tela=True, ritmo_cortes_0a10=None, tom="informal", usa_linguagem_regional=False,
            clareza_mensagem_0a10=9, tem_cta=True, tipo_cta="salvar", oferta_ou_beneficio_explicito=False,
            elementos_top5=["a", "b", "c", "d", "e"])


def test_valido():
    assert R.RubricLLM(**BASE).tema_principal == "finanças"


def test_enum_invalido_rejeitado():
    with pytest.raises(ValidationError):
        R.RubricLLM(**{**BASE, "tema_principal": "astrologia"})


def test_variacoes_de_acento_e_caixa_sao_normalizadas():
    r = R.RubricLLM(**{**BASE, "formato_video": "Lista / Dicas", "tipo_hook": "numero", "tema_principal": "Financas", "tipo_cta": "dm"})
    assert (r.formato_video, r.tipo_hook, r.tema_principal, r.tipo_cta) == ("lista/dicas", "número", "finanças", "DM")


def test_nota_fora_do_intervalo():
    with pytest.raises(ValidationError):
        R.RubricLLM(**{**BASE, "forca_hook_0a10": 11})


def test_elementos_top5_exige_cinco():
    with pytest.raises(ValidationError):
        R.RubricLLM(**{**BASE, "elementos_top5": ["a"]})


def test_cta_consistente():
    assert R.RubricLLM(**{**BASE, "tem_cta": False, "tipo_cta": "salvar"}).tipo_cta == "nenhum"


def test_campos_deterministicos():
    assert R.duracao_faixa(29.9) == "15-30s" and R.duracao_faixa(None) is None
    assert R.legenda_tamanho("x" * 124) == "curta" and R.legenda_tamanho("x" * 501) == "longa"
    assert R.tipo_post("video") == "short"


def test_schema_hint_lista_todos_os_campos():
    hint = R.json_schema_hint()
    for f in R.RubricLLM.model_fields:
        assert f'"{f}"' in hint


def test_parse_json_tolera_cercas():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_kappa():
    assert cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


def test_intencao_de_contato():
    assert has_contact_intent("Quero! Como faço pra participar?")
    assert has_contact_intent("qual é o link?")
    assert not has_contact_intent("que vídeo lindo")
