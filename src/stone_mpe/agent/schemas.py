"""Contrato da ferramenta (TAP §7), validado por Pydantic na entrada e na saída."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Mode = Literal["analisar", "recomendar", "gerar_criativo"]


class Filters(BaseModel):
    platform: Optional[Literal["instagram", "youtube"]] = None
    date_from: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="ISO date, ex.: 2026-01-01")
    date_to: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    profile_size: Optional[Literal["micro", "medio", "grande"]] = None
    tipo_post: Optional[Literal["reels", "carrossel", "imagem", "short"]] = None


class AgentInput(BaseModel):
    mode: Mode
    query: str = Field(..., min_length=3, max_length=500)
    segment: Optional[str] = Field(None, max_length=40, pattern=r"^[a-z_]+$",
                                   description="alimentacao | beleza | varejo | servicos | financas | geral ...")
    filters: Optional[Filters] = None
    n_creatives: int = Field(1, ge=1, le=5)


class Finding(BaseModel):
    feature: str = Field(..., description="campo=valor, ex.: formato_video=lista/dicas")
    frequency: float = Field(..., ge=0, le=1, description="proporção no top do recorte")
    n_posts: int = Field(..., description="posts que sustentam a característica")
    total: int = Field(..., description="tamanho do recorte")
    example_post_ids: list[str]


class ReferencePost(BaseModel):
    post_id: str
    url: str
    platform: str
    handle: str
    engagement_rate: float
    categories: dict


PLANOS = ("rosto", "produto", "maos", "tela", "ambiente", "cliente")
_PLANO_KW = {"rosto": ["rosto", "camera", "câmera", "fala", "selfie", "close"], "produto": ["produto", "prato", "bolo", "doce", "salgado", "peça", "roupa"],
             "maos": ["mão", "mãos", "maos", "montando", "preparo", "preparando", "embalando", "fazendo"],
             "tela": ["tela", "celular", "app", "planilha", "maquininha", "papel", "calculadora", "gráfico", "print"],
             "ambiente": ["loja", "balcão", "balcao", "cozinha", "bastidores", "salão", "salao", "oficina", "fachada", "vitrine"],
             "cliente": ["cliente", "atendimento", "atendendo", "entrega", "entregando"]}


def guess_plano(text: str) -> str:
    t = (text or "").lower()
    for k in PLANOS:
        if t.strip() == k:
            return k
    scores = {k: sum(w in t for w in kws) for k, kws in _PLANO_KW.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else "rosto"


class Cena(BaseModel):
    """Uma cena do storyboard (vira um quadro 9:16 ilustrado no painel)."""
    tempo: str = Field("", description="ex.: 0-3s")
    plano: str = Field("rosto", description="rosto | produto | maos | tela | ambiente | cliente")
    visual: str = Field("", description="o que aparece na cena")
    fala: str = ""
    texto_tela: str = ""

    @field_validator("plano", mode="before")
    @classmethod
    def _plano(cls, v):
        return guess_plano(str(v or ""))


class Creative(BaseModel):
    titulo: str = ""
    formato: str = Field("", description="ex.: Reels 30–45s, talking head, lista/dicas")
    gancho: str
    roteiro: str
    legenda: str
    cta: str
    inspired_by: list[str] = Field(..., min_length=1, description="post_ids reais da base")
    justificativa: str = ""
    cenas: list[Cena] = Field(default_factory=list, description="storyboard: 4–6 cenas")


class AgentOutput(BaseModel):
    mode: Mode
    query: str
    segment_used: Optional[str] = None
    findings: list[Finding]
    reference_posts: list[ReferencePost]
    creatives: list[Creative] = Field(default_factory=list)
    confidence_flag: bool = Field(..., description="true só quando a confiança é baixa (menos de 10 posts no recorte)")
    confidence_level: Optional[Literal["alta", "media", "baixa"]] = None
    confidence_reason: str = ""
    segment_asked: Optional[str] = Field(None, description="nicho pedido ou inferido, antes de qualquer ampliação")
    notes: list[str] = Field(default_factory=list, description="como o recorte foi montado e ampliado, passo a passo")
    explanation: str
    run_id: str
    llm: str = Field("none", description="provedor/modelo usado ou 'none' (modo template)")

    @model_validator(mode="after")
    def _nivel(self):  # respostas antigas (cache da demo) só têm o flag
        if self.confidence_level is None:
            self.confidence_level = "baixa" if self.confidence_flag else "alta"
        return self
