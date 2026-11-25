"""Prompts do agente. Tom de voz e pilares vêm do relatório do @impulsostone (S3 §6–7)."""
from __future__ import annotations

PROMPT_VERSION = "agent-v1"

TOM_DE_VOZ = (
    "Tom do Impulso Stone: próximo, acolhedor, educativo, encorajador e interativo. Linguagem simples e direta, "
    "sem jargão e sem promessas exageradas. Público real: 70% mulheres, quase metade entre 35 e 54 anos — "
    "comunicação objetiva, acessível e prática. Conectar conhecimento técnico à rotina do empreendedor."
)

PILARES = {
    "Educação financeira": "precificação, custos, caixa e lucro",
    "Gestão e vendas": "atendimento, pós-venda e estratégias comerciais",
    "Histórias reais": "trajetórias, desafios e conquistas",
    "Especialistas": "oficinas, mentorias e orientações",
    "Comunidade": "convites, interações e oportunidades",
}

TEMA_PARA_PILAR = {
    "finanças": "Educação financeira",
    "ferramentas/maquininha": "Educação financeira",
    "vendas": "Gestão e vendas",
    "atendimento": "Gestão e vendas",
    "gestão": "Gestão e vendas",
    "marketing": "Gestão e vendas",
    "história de empreendedor": "Histórias reais",
    "motivação": "Comunidade",
}

REGRAS_DADOS = (
    "REGRAS DE RASTREABILIDADE (obrigatórias):\n"
    "- Use SOMENTE os números e posts fornecidos abaixo. Não invente métricas, percentuais, perfis ou links.\n"
    "- Ao citar uma frequência, use exatamente o valor fornecido.\n"
    "- Descreva padrões como OBSERVADOS na base, nunca como garantia de resultado.\n"
)

EXPLAIN = """Você é o analista de conteúdo do Impulso Stone (braço social da Stone para micro e pequenos empreendedores).
{regras}
Pedido ({mode}): "{query}"
Recorte: {recorte}

Características mais frequentes nas publicações de alto desempenho do recorte (JSON):
{findings}

Publicações de referência (JSON):
{refs}

{instrucao}
Escreva em português do Brasil, em até 180 palavras, texto corrido (sem markdown pesado)."""

INSTR_ANALISAR = "Explique os padrões observados, citando 2–3 publicações de referência pelo @perfil."
INSTR_RECOMENDAR = (
    "Recomende ao time do Impulso Stone formato, tipo de gancho, tema e CTA para o objetivo pedido, "
    "justificando cada recomendação com as frequências e citando publicações de referência pelo @perfil. "
    "Lembre que um 'lead' para o Impulso é interesse/inscrição no programa."
)

CREATIVE = """Você cria roteiros de conteúdo para o Instagram do Impulso Stone (programa do Instituto Stone Impacto que leva
educação e mentoria a micro e pequenos empreendedores). {tom}

{regras}
Pedido: "{query}"
Recorte: {recorte}

Padrões observados no top do recorte (JSON):
{findings}

Publicações de referência que você DEVE usar como inspiração (JSON, com post_id):
{refs}
{erro}
Crie {n} criativo(s) ORIGINAL(is) — inspire-se nos padrões, não copie frases dos posts.
Responda EXCLUSIVAMENTE com JSON:
{{"creatives": [{{
  "titulo": "nome curto",
  "formato": "ex.: Reels 30-45s, talking head, lista/dicas",
  "gancho": "frase dos primeiros 3 segundos",
  "roteiro": "cenas/falas numeradas, prontas para gravar",
  "cenas": [{{"tempo": "0-3s", "plano": "rosto|produto|maos|tela|ambiente|cliente",
              "visual": "o que a câmera mostra", "fala": "o que é dito", "texto_tela": "texto sobreposto, curto"}}],
  "legenda": "legenda completa com quebras de linha",
  "cta": "chamada para ação alinhada a um lead do Impulso (comentar, salvar, link na bio para inscrição, DM)",
  "inspired_by": ["post_id", "..."],
  "justificativa": "quais padrões e quais posts sustentam as escolhas"
}}]}}
`inspired_by` deve conter apenas post_ids da lista de referências acima (mínimo 1).
`cenas`: 4 a 6 cenas que somam a duração do formato; a primeira é o gancho (0-3s). `plano` usa exatamente um dos valores listados."""
