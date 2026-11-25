"""Gera outputs/playbook.md: características, perfis em destaque, formatos recomendados,
exemplos reais e ≥ 5 criativos vinculados às publicações de referência (TAP §10)."""
from __future__ import annotations

import json

from stone_mpe import config
from stone_mpe.agent.prompts import PILARES, TEMA_PARA_PILAR
from stone_mpe.analysis import comments, creators, lead_signals, patterns
from stone_mpe.api import run

BRIEFS = [
    {"pilar": "Educação financeira", "query": "Vídeo curto (Reels/Shorts) ensinando a precificar um produto para quem está começando a empreender", "segment": None},
    {"pilar": "Gestão e vendas", "query": "conteúdo sobre pós-venda e como fazer o cliente voltar a comprar", "segment": None},
    {"pilar": "Histórias reais", "query": "história real de empreendedora que organizou o caixa e cresceu", "segment": None},
    {"pilar": "Gestão e vendas", "query": "Vídeo curto (Reels/Shorts) para atrair donos de pequenos restaurantes", "segment": "alimentacao"},
    {"pilar": "Educação financeira", "query": "conteúdo para donas de salão de beleza sobre separar o dinheiro do negócio", "segment": "beleza"},
    {"pilar": "Comunidade", "query": "convite para microempreendedores se inscreverem numa mentoria gratuita", "segment": None},
]

LABELS = {"tipo_post": "Tipo de post", "formato_video": "Formato de vídeo", "tipo_hook": "Tipo de gancho",
          "tema_principal": "Tema", "tom": "Tom", "tipo_cta": "CTA", "duracao_faixa": "Duração",
          "legenda_tamanho": "Tamanho da legenda", "tem_rosto": "Rosto na capa", "texto_na_tela": "Texto na tela",
          "prova_social": "Prova social", "criador_e_empreendedor_real": "Criador é empreendedor real",
          "oferta_ou_beneficio_explicito": "Oferta/benefício explícito", "usa_linguagem_regional": "Linguagem regional"}


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _links(df, ids: list[str]) -> str:
    m = df.set_index("post_id")
    return ", ".join(f"[@{m.at[i, 'handle']}]({m.at[i, 'url']})" for i in ids if i in m.index)


def _fmt(d: dict) -> str:
    return ", ".join(f"{k}: {v:,}".replace(",", ".") if isinstance(v, int) else f"{k}: {v}" for k, v in d.items())


def build(n_creatives_min: int = 5) -> str:
    stats_p = config.outputs_dir() / "base_stats.json"
    stats = json.loads(stats_p.read_text(encoding="utf-8")) if stats_p.exists() else {}
    top = patterns.load_top()
    freq = patterns.frequencies(top)
    feat = creators.featured(top)
    leads = lead_signals.cta_summary(top)
    L: list[str] = []
    w = L.append

    w("# Playbook de conteúdo para MPEs — Impulso Stone\n")
    w("> Padrões **observados** nas publicações de maior engajamento voltadas a micro e pequenos empreendedores. "
      "Não são garantia de resultado: cada recomendação aponta as publicações reais em que se apoia.\n")

    w("## 1. Como este playbook foi feito\n")
    w(f"- Base: **{stats.get('n_posts_raw', '?')} publicações** de **{stats.get('n_profiles', '?')} perfis** "
      f"({_fmt(stats.get('by_platform', {}))}), publicadas entre {stats.get('posted_from', '?')} e {stats.get('posted_to', '?')}, "
      f"coletadas entre {stats.get('collected_from', '?')} e {stats.get('collected_to', '?')}.")
    w(f"- Elegíveis (≥ 14 dias, métricas visíveis): **{stats.get('n_posts_eligible', '?')}**. Perfis por faixa: {_fmt(stats.get('profiles_by_faixa', {}))}.")
    w("- Métrica: **(curtidas + comentários) ÷ seguidores**. Alto desempenho = **top 10%** "
      f"(percentil calculado por {'plataforma' if stats.get('ranking_scope') == 'platform' else 'base combinada'}).")
    n2 = int(top["prompt_version"].eq(config.get("level2.prompt_version", "v1-n2")).sum()) if "prompt_version" in top else 0
    w(f"- Publicações de alto desempenho categorizadas com a rubrica: **{len(top)}** "
      f"({n2} com Nível 2: frames + transcrição; demais com legenda + capa).\n")

    w("## 2. O que mais aparece no top\n")
    w("| Característica | Mais frequente | Frequência | Exemplos |\n|---|---|---|---|")
    for field in ["tipo_post", "formato_video", "tipo_hook", "tema_principal", "tom", "tipo_cta", "duracao_faixa",
                  "legenda_tamanho", "tem_rosto", "texto_na_tela", "prova_social", "criador_e_empreendedor_real"]:
        g = freq[freq["field"] == field]
        if g.empty:
            continue
        r = g.iloc[0]
        w(f"| {LABELS.get(field, field)} | {r['value']} | {_pct(r['freq'])} ({r['n']}/{r['total']}) | {_links(top, r['example_post_ids'][:2])} |")
    w("")
    ct = patterns.crosstab(top)
    if not ct.empty:
        w("### Tema × formato (contagem no top)\n")
        cols = list(ct.columns)
        w("| tema \\ formato | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols))
        for tema_v, row in ct.iterrows():
            w(f"| {tema_v} | " + " | ".join(str(int(row[c])) for c in cols) + " |")
        w("")

    w("### Mapeamento para os pilares editoriais do Impulso\n")
    tema = freq[freq["field"] == "tema_principal"]
    w("| Tema na base | Pilar do Impulso | Frequência no top |\n|---|---|---|")
    for r in tema.itertuples():
        w(f"| {r.value} | {TEMA_PARA_PILAR.get(r.value, '—')} | {_pct(r.freq)} ({r.n}) |")
    w("")

    w("## 3. Perfis em destaque\n")
    if not feat.empty:
        w("| Perfil | Plataforma | Faixa | Posts no top | Taxa no top | Tema predominante | Formato predominante |\n|---|---|---|---|---|---|---|")
        for r in feat.head(10).itertuples():
            taxa = _pct(r.taxa_no_top) if r.taxa_no_top == r.taxa_no_top else "—"
            w(f"| @{r.handle} | {r.platform} | {r.faixa} | {r.n_top} | {taxa} | {r.tema_predominante} | {r.formato_predominante or '—'} |")
        w("")

    w("## 4. Sinais de lead (indicador indireto)\n")
    if leads:
        w(f"- {_pct(leads['share_com_cta'])} das publicações do top têm CTA explícita; tipos: " + ", ".join(f"{k} ({v})" for k, v in leads["tipos_cta"].items()) + ".")
        w(f"- {_pct(leads['share_oferta_explicita'])} trazem oferta ou benefício explícito.")
        w(f"- Mediana de comentários por curtida no top: {leads['mediana_comentarios_por_curtida']:.2f} "
          "(valores altos sugerem CTA de comentário — ex.: \"comenta QUERO\").")
    cm = comments.summary()
    if cm:
        w(f"- Em {cm['comentarios_analisados']} comentários de {cm['posts']} publicações do top: intenção de contato "
          f"{_pct(cm['taxa_contato'])}, dúvidas {_pct(cm['taxa_duvida'])}, objeções {_pct(cm['taxa_objecao'])}.")
        # citações literais de comentários ficam fora por padrão (repositório público; LGPD)
        for k, label in [("duvida", "Dúvidas recorrentes"), ("objecao", "Objeções")]:
            if config.get("playbook.include_comment_examples", False) and cm["exemplos"].get(k):
                w(f"- {label} (exemplos): " + " · ".join(f"“{x}”" for x in cm["exemplos"][k][:3]))
    w("")
    lf = patterns.lift(["formato_video", "tipo_hook", "tema_principal", "tipo_cta", "tem_rosto", "texto_na_tela"])
    if not lf.empty:
        w("### O que diferencia o top do resto da base\n")
        w("Lift = frequência no top ÷ frequência numa amostra categorizada do restante. Acima de 1: mais associado ao alto desempenho do que ao nicho em geral.\n")
        w("Só entram linhas com pelo menos 5 posts no resto. O número de criadores mostra se é padrão ou estilo de poucos canais.\n")
        w("| Característica | No top | No resto | Lift |\n|---|---|---|---|")
        for r in lf[lf["n_rest"].fillna(0) >= 5].head(8).itertuples():
            w(f"| {LABELS.get(r.field, r.field)} = {r.value} | {_pct(r.freq_top)} ({r.n_top}) | {_pct(r.freq_rest)} ({int(r.n_rest)}) | "
              f"{r.lift:.2f} ({r.n_criadores} criadores) |")
        w("")

    w("## 5. Formatos recomendados\n")
    rec = run("recomendar", "Qual formato, gancho, tema e CTA usar no Instagram do Impulso Stone para atrair microempreendedores para o programa?")
    w(rec.explanation + "\n")
    w("Referências: " + ", ".join(f"[@{r.handle}]({r.url})" for r in rec.reference_posts) + "\n")

    w("## 6. Criativos prontos para produção\n")
    n = 0
    for b in BRIEFS:
        out = run("gerar_criativo", b["query"], segment=b["segment"])
        refs = {r.post_id: r for r in out.reference_posts}
        for c in out.creatives:
            n += 1
            w(f"### Criativo {n} — {c.titulo or b['query']}\n")
            w(f"- **Pilar:** {b['pilar']} ({PILARES.get(b['pilar'], '')})  ")
            w(f"- **Pedido:** {b['query']}  ")
            w(f"- **Formato:** {c.formato}  ")
            w(f"- **Gancho (0–3s):** {c.gancho}  ")
            w(f"- **CTA:** {c.cta}  ")
            _lv = out.confidence_level or ("baixa" if out.confidence_flag else "alta")
            w(f"- **Confiança:** {'média' if _lv == 'media' else _lv}" + (f" ({out.confidence_reason})" if out.confidence_reason else "") + "\n")
            if c.cenas:
                w("**Roteiro (storyboard)**\n")
                w("| Tempo | Plano | O que aparece | Fala | Texto na tela |\n|---|---|---|---|---|")
                for cena in c.cenas:
                    cell = [str(x or "").replace("|", "/").replace("\n", " ")
                            for x in (cena.tempo, cena.plano, cena.visual, cena.fala, cena.texto_tela)]
                    w("| " + " | ".join(cell) + " |")
                w("")
            if c.roteiro and (not c.cenas or len(c.roteiro) > 120):
                w(f"**Roteiro**\n\n{c.roteiro}\n")
            w("**Legenda**\n\n> " + c.legenda.replace("\n", "\n> ") + "\n")
            w("**Publicações de referência**\n")
            for pid in c.inspired_by:
                r = refs[pid]
                w(f"- [@{r.handle} — {r.platform}]({r.url}) · engajamento {r.engagement_rate:.2%} · "
                  f"{r.categories.get('formato_video') or r.categories.get('tipo_post')}, gancho {r.categories.get('tipo_hook')}")
            w(f"\n**Por quê:** {c.justificativa}\n")
    if n < n_creatives_min:
        w(f"> ⚠️ Apenas {n} criativos gerados (meta: {n_creatives_min}). Verifique a base/LLM e rode de novo.\n")

    w("## 7. Limitações\n")
    w("- Correlação, não causalidade: características frequentes no top podem ser apenas comuns no nicho (ver comparação top × resto, quando disponível).")
    w("- Seguidores são os da data de coleta, não da data do post; contas que cresceram têm posts antigos subestimados.")
    w("- Impulsionamento pago não é visível nos dados públicos e pode inflar curtidas/comentários de alguns posts.")
    w("- Categorização Nível 1 usa só legenda e capa: ritmo de cortes e gancho falado não são observados.")
    w("- Lead é indicador indireto (CTA e intenção nos comentários); conversão real exige Insights do @impulsostone.\n")

    text = "\n".join(L)
    (config.outputs_dir() / "playbook.md").write_text(text, encoding="utf-8")
    return text
