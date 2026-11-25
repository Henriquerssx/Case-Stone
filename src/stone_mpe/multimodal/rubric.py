"""Rubrica fixa de categorização (TAP §6.2), validada por Pydantic.

Separação deliberada:
- RubricLLM: só os campos de JULGAMENTO, respondidos pelo VLM/LLM.
- Campos DETERMINÍSTICOS (tipo_post, duracao_faixa, legenda_tamanho) vêm dos
  metadados do post — o modelo não precisa adivinhar o que já sabemos.

Valores não enumerados no TAP (duracao_faixa, legenda_tamanho, tipo_cta="nenhum")
são decisões deste projeto, declaradas no README (Aula 2 não disponível).
"""
from __future__ import annotations

import unicodedata
from typing import Literal, Optional, get_args

from pydantic import BaseModel, Field, field_validator, model_validator

FormatoVideo = Literal["talking head", "tutorial", "bastidores", "antes/depois", "humor/esquete", "depoimento", "lista/dicas", "trend"]
TipoHook = Literal["pergunta", "promessa", "dor", "número", "polêmica", "curiosidade"]
Tema = Literal["vendas", "finanças", "marketing", "atendimento", "gestão", "motivação", "ferramentas/maquininha", "história de empreendedor"]
Tom = Literal["informal", "técnico", "inspiracional", "humorístico"]
TipoCta = Literal["comentar", "salvar", "link na bio", "DM", "seguir", "nenhum"]
TipoPost = Literal["reels", "carrossel", "imagem", "short"]
DuracaoFaixa = Literal["<15s", "15-30s", "30-60s", "60-90s", ">90s"]
LegendaTamanho = Literal["curta", "média", "longa"]

CATEGORICAL_FIELDS = ["formato_video", "tipo_hook", "tema_principal", "tom", "tipo_cta"]
BOOL_FIELDS = ["tem_rosto", "criador_e_empreendedor_real", "prova_social", "texto_na_tela",
               "usa_linguagem_regional", "tem_cta", "oferta_ou_beneficio_explicito"]
SCORE_FIELDS = ["forca_hook_0a10", "ritmo_cortes_0a10", "clareza_mensagem_0a10"]
DETERMINISTIC_FIELDS = ["tipo_post", "duracao_faixa", "legenda_tamanho"]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace(" / ", "/").replace("_", " ").split())


def _coerce_enum(value, literal_type):
    """Aceita variações de caixa/acento/espaço ('Lista / Dicas', 'numero') e devolve o valor canônico."""
    if value is None or not isinstance(value, str):
        return value
    allowed = get_args(literal_type)
    folded = {_fold(a): a for a in allowed}
    return folded.get(_fold(value), value)


class RubricLLM(BaseModel):
    formato_video: Optional[FormatoVideo] = Field(None, description="null para imagem/carrossel sem vídeo")
    hook_primeiros_3s: str = Field(..., max_length=200)
    tipo_hook: TipoHook
    forca_hook_0a10: int = Field(..., ge=0, le=10)
    tema_principal: Tema
    tem_rosto: bool
    criador_e_empreendedor_real: bool
    prova_social: bool
    texto_na_tela: bool
    ritmo_cortes_0a10: Optional[int] = Field(None, ge=0, le=10, description="null se não observável (Nível 1)")
    tom: Tom
    usa_linguagem_regional: bool
    clareza_mensagem_0a10: int = Field(..., ge=0, le=10)
    tem_cta: bool
    tipo_cta: TipoCta
    oferta_ou_beneficio_explicito: bool
    elementos_top5: list[str] = Field(..., min_length=5, max_length=5)

    @field_validator("formato_video", mode="before")
    @classmethod
    def _fv(cls, v):
        return _coerce_enum(v, FormatoVideo) if v not in ("", "null", "n/a") else None

    @field_validator("tipo_hook", mode="before")
    @classmethod
    def _th(cls, v):
        return _coerce_enum(v, TipoHook)

    @field_validator("tema_principal", mode="before")
    @classmethod
    def _tema(cls, v):
        return _coerce_enum(v, Tema)

    @field_validator("tom", mode="before")
    @classmethod
    def _tom(cls, v):
        return _coerce_enum(v, Tom)

    @field_validator("tipo_cta", mode="before")
    @classmethod
    def _cta(cls, v):
        if v is None or v == "":
            return "nenhum"
        return "DM" if _fold(str(v)) in ("dm", "direct", "mensagem") else _coerce_enum(v, TipoCta)

    @model_validator(mode="after")
    def _consistencia_cta(self):
        if not self.tem_cta:
            self.tipo_cta = "nenhum"
        elif self.tipo_cta == "nenhum":
            self.tem_cta = False
        return self


class Rubric(RubricLLM):
    tipo_post: TipoPost
    duracao_faixa: Optional[DuracaoFaixa] = None
    legenda_tamanho: LegendaTamanho


def duracao_faixa(duration_s: float | None) -> str | None:
    if duration_s is None or duration_s != duration_s:  # NaN
        return None
    if duration_s < 15:
        return "<15s"
    if duration_s < 30:
        return "15-30s"
    if duration_s < 60:
        return "30-60s"
    if duration_s < 90:
        return "60-90s"
    return ">90s"


def legenda_tamanho(caption: str | None) -> str:
    n = len(caption or "")
    return "curta" if n < 125 else ("média" if n <= 500 else "longa")


def tipo_post(media_type: str) -> str:
    return {"video": "short"}.get(media_type, media_type)


def json_schema_hint() -> str:
    """Descrição compacta do JSON esperado, usada no prompt."""
    lines = []
    for name, f in RubricLLM.model_fields.items():
        ann = f.annotation
        args = [a for a in get_args(ann) if a is not type(None)]
        lit = get_args(args[0]) if args and get_args(args[0]) else get_args(ann)
        if lit and all(isinstance(x, str) for x in lit):
            t = " | ".join(f'"{x}"' for x in lit)
        elif name.endswith("0a10"):
            t = "inteiro 0-10"
        elif ann is bool:
            t = "true | false"
        elif name == "elementos_top5":
            t = "lista com exatamente 5 strings curtas"
        else:
            t = "string"
        nullable = " | null" if type(None) in get_args(ann) else ""
        lines.append(f'  "{name}": {t}{nullable}')
    return "{\n" + ",\n".join(lines) + "\n}"
