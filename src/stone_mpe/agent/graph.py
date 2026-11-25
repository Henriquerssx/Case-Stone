"""Agente LangGraph — grafo determinístico curto (testável) em vez de ReAct livre.

validar_entrada -> consulta_base -> posts_referencia -> [analisar | recomendar | gerar_criativo]
               -> validar_saida (retry de criativo com referência inválida) -> registrar

Regra-chave: números e links só saem das ferramentas. O LLM recebe os dados prontos
e só redige; `validar_saida` descarta qualquer post_id que não veio de `posts_referencia`.
Sem LLM disponível, cada nó de redação cai para um template determinístico.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from stone_mpe import config
from stone_mpe.agent import prompts as P
from stone_mpe.agent import tools as T
from stone_mpe.agent.schemas import AgentInput, AgentOutput, Cena, Creative
from stone_mpe.llm import FallbackClient, LLMUnavailable, get_client, parse_json


class State(TypedDict, total=False):
    input: AgentInput
    run_id: str
    t0: float
    segment: str | None
    filters: dict
    notes: list[str]
    df: Any
    findings: list
    refs: list
    meta: dict
    creatives: list
    explanation: str
    creative_error: str | None
    retries: int
    tools_called: list[str]
    llm_used: str
    output: AgentOutput


# ---------- helpers ----------

def _recorte(s: State) -> str:
    parts = [f"segmento={s.get('meta', {}).get('segment_used') or 'todos'}"]
    parts += [f"{k}={v}" for k, v in (s.get("meta", {}).get("filters_used") or {}).items() if v]
    parts.append(f"{s.get('meta', {}).get('n_top_recorte', 0)} posts de alto desempenho")
    return ", ".join(parts)


def _findings_json(s: State, limit: int = 18) -> str:
    # frequência já formatada ("29% (157/543)"): o modelo copia o número sem inventar casas decimais
    return json.dumps([{"feature": f.feature, "frequencia": f"{round(f.frequency * 100)}% ({f.n_posts}/{f.total})"}
                       for f in s["findings"][:limit]], ensure_ascii=False)


def _refs_json(s: State) -> str:
    keep = ("formato_video", "tipo_hook", "hook_primeiros_3s", "tema_principal", "tipo_cta", "elementos_top5")
    return json.dumps([{"post_id": r.post_id, "perfil": "@" + r.handle, "plataforma": r.platform, "taxa_engajamento": r.engagement_rate,
                        **{k: r.categories.get(k) for k in keep}} for r in s["refs"]], ensure_ascii=False)


def _top(s: State, field: str) -> tuple[str | None, Any]:
    for f in s["findings"]:
        name, _, val = f.feature.partition("=")
        if name == field:
            return val, f
    return None, None


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%".replace(".", ",")


def confidence(total: int, meta: dict) -> tuple[str, str]:
    """Nível de confiança do recorte: alta (≥ 30 posts no nicho pedido), média (10–29, ou padrões gerais porque o
    nicho tem poucos posts no top) e baixa (< 10 posts sustentam os padrões)."""
    lo = config.get("agent.confidence_min_posts", 10)
    hi = config.get("agent.confidence_high_posts", 30)
    if total < lo:
        return "baixa", f"só {total} publicações de alto desempenho sustentam estes padrões"
    if meta.get("segment_dropped"):
        return "media", (f"o nicho pedido tem poucos posts no top; os padrões vêm de {total} publicações de toda a base")
    if total < hi:
        return "media", f"{total} publicações de alto desempenho no recorte"
    extra = " (com filtros ampliados)" if meta.get("widened") else ""
    return "alta", f"{total} publicações de alto desempenho no recorte{extra}"


def _template_explanation(s: State) -> str:
    total = s["meta"].get("n_top_recorte", 0)
    if total == 0:
        return "Não há publicações de alto desempenho categorizadas neste recorte. Amplie os filtros ou conclua a categorização."
    bits = []
    for field, label in [("tipo_post", "tipo de post"), ("formato_video", "formato"), ("tipo_hook", "gancho"),
                         ("tema_principal", "tema"), ("tipo_cta", "CTA")]:
        v, f = _top(s, field)
        if f:
            bits.append(f"{label} '{v}' ({_pct(f.frequency)}, {f.n_posts}/{f.total})")
    refs = ", ".join(dict.fromkeys(f"@{r.handle}" for r in s["refs"]))
    head = "Recomendação" if s["input"].mode == "recomendar" else "Padrões observados"
    return (f"{head} entre {total} publicações de alto desempenho ({_recorte(s)}): " + "; ".join(bits) +
            f". Referências: {refs}. São padrões observados na base, não garantia de resultado.")


HOOK_TEMPLATES = {
    "dor": "Você está perdendo dinheiro com isso no seu negócio e nem percebe",
    "pergunta": "Você sabe quanto realmente sobra no fim do mês do seu negócio?",
    "número": "3 erros que travam as vendas de quem está começando",
    "promessa": "Com esse ajuste simples, você organiza o caixa em 10 minutos por dia",
    "curiosidade": "O que os negócios que vendem todo mês fazem diferente",
    "polêmica": "Vender mais não resolve o seu problema de dinheiro",
}


def _template_creative(s: State) -> Creative:
    hook_type, _ = _top(s, "tipo_hook")
    formato, _ = _top(s, "formato_video")
    tipo, _ = _top(s, "tipo_post")
    cta_type, _ = _top(s, "tipo_cta")
    tema, _ = _top(s, "tema_principal")
    cta = {"comentar": "Comenta QUERO que a gente te manda como participar do Impulso",
           "salvar": "Salva esse post para conferir depois", "link na bio": "Inscreva-se pelo link na bio",
           "DM": "Manda um direct pra gente com a palavra IMPULSO"}.get(cta_type or "", "Salva esse post para conferir depois")
    ids = [r.post_id for r in s["refs"][:3]]
    return Creative(
        titulo=f"Rascunho (template, sem LLM) — {tema or 'gestão'}",
        formato=f"{tipo or 'reels'}, 30–45s, {formato or 'lista/dicas'}",
        gancho=HOOK_TEMPLATES.get(hook_type or "", HOOK_TEMPLATES["número"]),
        roteiro="1) Gancho na tela nos 3 primeiros segundos. 2) Três pontos práticos, um por corte, com texto na tela. "
                "3) Exemplo de um empreendedor real. 4) CTA falado e escrito.",
        legenda=f"{HOOK_TEMPLATES.get(hook_type or '', '')}\n\nNo Impulso Stone a gente aprende junto, na prática. 💚\n\n{cta}",
        cta=cta,
        inspired_by=ids or ["sem_referencia"],
        justificativa="Gerado por template a partir dos padrões mais frequentes do recorte (LLM indisponível). Revisar antes de produzir.",
        cenas=[Cena(tempo="0-3s", plano="rosto", visual="Empreendedor olhando para a câmera, enquadramento fechado",
                    fala=HOOK_TEMPLATES.get(hook_type or "", HOOK_TEMPLATES["número"]), texto_tela=HOOK_TEMPLATES.get(hook_type or "", HOOK_TEMPLATES["número"])),
               Cena(tempo="3-15s", plano="ambiente", visual="Bastidores do negócio: balcão, cozinha ou loja", fala="Primeiro ponto prático.",
                    texto_tela="1. Primeiro ponto"),
               Cena(tempo="15-30s", plano="tela", visual="Anotação, planilha ou maquininha mostrando o número", fala="Segundo e terceiro pontos.",
                    texto_tela="2. Segundo · 3. Terceiro"),
               Cena(tempo="30-40s", plano="rosto", visual="Volta para o rosto, tom de convite", fala=cta, texto_tela=cta)],
    )


# ---------- nós ----------

def make_graph(llm: FallbackClient | None = None):
    llm = llm or get_client("agent")

    def validar_entrada(s: State) -> State:
        inp = s["input"]
        filters = inp.filters.model_dump(exclude_none=True) if inp.filters else {}
        seg, filters, notes = T.infer_scope(inp.query, inp.segment, filters)
        return {"segment": seg, "filters": filters, "notes": notes, "retries": 0, "tools_called": [], "llm_used": "none", "creatives": []}

    def consulta_base(s: State) -> State:
        df, findings, meta = T.consulta_base(s["segment"], s["filters"])
        return {"df": df, "findings": findings, "meta": meta, "tools_called": s["tools_called"] + ["consulta_base"]}

    def posts_referencia(s: State) -> State:
        refs = T.posts_referencia(s["df"], s["input"].query)
        return {"refs": refs, "tools_called": s["tools_called"] + ["posts_referencia"]}

    def redigir(s: State) -> State:
        mode = s["input"].mode
        if not s["findings"]:
            return {"explanation": _template_explanation(s)}
        prompt = P.EXPLAIN.format(regras=P.REGRAS_DADOS, mode=mode, query=s["input"].query, recorte=_recorte(s),
                                  findings=_findings_json(s), refs=_refs_json(s),
                                  instrucao=P.INSTR_ANALISAR if mode == "analisar" else P.INSTR_RECOMENDAR)
        try:
            text = llm.complete(prompt, json_mode=False).strip()
            return {"explanation": text, "llm_used": llm.model}
        except LLMUnavailable:
            return {"explanation": _template_explanation(s)}

    def gerar_criativo(s: State) -> State:
        tools = s["tools_called"] + ["gerar_criativo"]
        if not s["refs"]:
            return {"creatives": [], "creative_error": None, "tools_called": tools,
                    "explanation": "Sem publicações de referência no recorte: nenhum criativo gerado (rastreabilidade obrigatória)."}
        erro = f"\nATENÇÃO, sua resposta anterior foi rejeitada: {s['creative_error']}\n" if s.get("creative_error") else ""
        prompt = P.CREATIVE.format(tom=P.TOM_DE_VOZ, regras=P.REGRAS_DADOS, query=s["input"].query, recorte=_recorte(s),
                                   findings=_findings_json(s), refs=_refs_json(s), erro=erro, n=s["input"].n_creatives)
        try:
            raw = llm.complete(prompt, json_mode=True)
        except LLMUnavailable:
            return {"creatives": [_template_creative(s)], "creative_error": None, "tools_called": tools}
        try:
            items = parse_json(raw).get("creatives", [])
            creatives = [Creative.model_validate(c) for c in items]
            err = None if creatives else "lista 'creatives' vazia"
        except (ValueError, ValidationError) as e:
            creatives, err = [], str(e)[:500]
        return {"creatives": creatives, "creative_error": err, "tools_called": tools, "llm_used": llm.model}

    def validar_saida(s: State) -> State:
        valid_ids = {r.post_id for r in s["refs"]}
        kept, dropped = [], []
        for c in s.get("creatives", []):
            ids = [i for i in c.inspired_by if i in valid_ids]
            if ids:
                upd = {"inspired_by": ids}
                # todo criativo do Impulso precisa chamar para a inscrição, mesmo que o top use pouca CTA
                if c.cta.strip().lower() in ("", "nenhum", "nenhuma", "none", "sem cta"):
                    upd["cta"] = "Quer aprender isso na prática, de graça? Inscreva-se no Impulso Stone pelo link na bio"
                kept.append(c.model_copy(update=upd))
            else:
                dropped.append(c.titulo or c.gancho[:40])
        err = s.get("creative_error")
        if s["input"].mode == "gerar_criativo" and s["refs"] and not kept:
            err = err or f"inspired_by sem nenhum post_id válido. Use apenas: {sorted(valid_ids)}"
        else:
            err = None
        return {"creatives": kept, "creative_error": err, "retries": s["retries"] + (1 if err else 0)}

    def depois_validar(s: State) -> str:
        if s.get("creative_error") and s["retries"] <= config.get("agent.max_creative_retries", 2):
            return "gerar_criativo"
        return "registrar"

    def registrar(s: State) -> State:
        inp = s["input"]
        creatives = s.get("creatives", [])
        if inp.mode == "gerar_criativo" and not creatives and s["refs"]:
            creatives = [_template_creative(s)]  # último recurso, ainda rastreável
        total = s["meta"].get("n_top_recorte", 0)
        level, reason = confidence(total, s["meta"])
        low = level == "baixa"
        explanation = s.get("explanation") or ""
        if inp.mode == "gerar_criativo" and not explanation:
            explanation = _template_explanation(s)
        notes = s["notes"] + s["meta"].get("widened", [])
        notes.append(f"confiança {'média' if level == 'media' else level}: {reason}")
        if notes:
            explanation += "\n\nNotas: " + "; ".join(notes) + "."
        out = AgentOutput(mode=inp.mode, query=inp.query, segment_used=s["meta"].get("segment_used"), findings=s["findings"],
                          reference_posts=s["refs"], creatives=creatives, confidence_flag=low, confidence_level=level, confidence_reason=reason,
                          segment_asked=s["meta"].get("segment_asked"), notes=notes, explanation=explanation.strip(),
                          run_id=s["run_id"], llm=s.get("llm_used", "none"))
        rec = {"run_id": s["run_id"], "ts": datetime.now(timezone.utc).isoformat(), "mode": inp.mode, "query": inp.query,
               "segment": inp.segment, "segment_used": out.segment_used, "filters": s["meta"].get("filters_used"),
               "tools_called": s["tools_called"], "reference_post_ids": [r.post_id for r in s["refs"]],
               "creative_inspired_by": [c.inspired_by for c in creatives], "n_findings": len(s["findings"]),
               "confidence_flag": low, "llm": out.llm, "prompt_version": P.PROMPT_VERSION, "retries": s["retries"],
               "latency_ms": int((time.time() - s["t0"]) * 1000), "error": s.get("creative_error")}
        with open(config.outputs_dir() / "runs.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return {"output": out}

    g = StateGraph(State)
    for name, fn in [("validar_entrada", validar_entrada), ("consulta_base", consulta_base), ("posts_referencia", posts_referencia),
                     ("redigir", redigir), ("gerar_criativo", gerar_criativo), ("validar_saida", validar_saida), ("registrar", registrar)]:
        g.add_node(name, fn)
    g.add_edge(START, "validar_entrada")
    g.add_edge("validar_entrada", "consulta_base")
    g.add_edge("consulta_base", "posts_referencia")
    g.add_conditional_edges("posts_referencia", lambda s: "gerar_criativo" if s["input"].mode == "gerar_criativo" else "redigir",
                            {"gerar_criativo": "gerar_criativo", "redigir": "redigir"})
    g.add_edge("redigir", "validar_saida")
    g.add_edge("gerar_criativo", "validar_saida")
    g.add_conditional_edges("validar_saida", depois_validar, {"gerar_criativo": "gerar_criativo", "registrar": "registrar"})
    g.add_edge("registrar", END)
    return g.compile()


def invoke(inp: AgentInput, llm: FallbackClient | None = None) -> AgentOutput:
    graph = make_graph(llm)
    final = graph.invoke({"input": inp, "run_id": uuid.uuid4().hex[:12], "t0": time.time()})
    return final["output"]
