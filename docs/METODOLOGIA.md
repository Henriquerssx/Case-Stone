# Metodologia

Como os dados foram coletados, filtrados, ranqueados, descritos e analisados. As decisões que fogem do padrão estão
declaradas em [Decisões declaradas](#decisões-declaradas). A referência de escopo é o Termo de Abertura do Projeto (TAP).

## 1. Pergunta e recorte

- **Pergunta norteadora:** quais características de conteúdo, formato e perfil de criador aparecem nas publicações de
  maior engajamento voltadas a micro e pequenos empreendedores (MPEs), e como transformar isso em criativos para a Stone?
- **Canal-alvo dos criativos:** @impulsostone (Instituto Stone Impacto). Lead = interesse ou inscrição no programa.
- **Plataformas:** Instagram (principal) e YouTube Shorts (complementar).

## 2. Base de dados

| Item | Valor |
|---|---|
| Origem | **Instagram:** Apify (`instagram-profile-scraper` para seguidores + `instagram-post-scraper`, nível `basicData`), a rota definida no kickoff e citada na Aula 1. **YouTube:** Data API v3 (oficial) |
| Nota sobre a rota do Instagram | O Apify extrai dados públicos do Instagram por terceiros, o que está em tensão com o TAP §4.3 (scraping fora do escopo). Usamos porque foi a rota acordada no kickoff. O projeto nunca acessa o Instagram diretamente, coleta só métricas públicas agregadas (sem dados de seguidores ou comentaristas) e registra a rota em `source_route` em cada post. |
| Período publicado / coletado | publicados de 2018-03 a 2026-11 (78% em 2025–2026) · coletados em 2026-11-23 (`outputs/base_stats.json`) |
| Volume | **6.675 publicações** · 6.235 elegíveis · **625 no top 10%**. Instagram: 820 posts (613 elegíveis: 386 Reels, 165 carrosséis, 62 imagens), top = 62, limiar 2,00%, mediana 0,31%. YouTube: 5.855 Shorts (5.622 elegíveis), top = 563, limiar 1,29%, mediana 0,04% |
| Perfis | **55 com dados**: 38 canais de YouTube (11 micro · 12 médio · 15 grande) e 17 perfis de Instagram (2 micro · 8 médio · 7 grande), por faixa: micro ≤ 10 mil · médio 10–100 mil · grande > 100 mil. 42 perfis têm ao menos 1 post no top. Dos 21 perfis de Instagram candidatos, 2 não existem mais e 2 estavam privados/vazios na coleta. Exclusões: 272 com menos de 14 dias, 84 com curtidas ocultas, 76 com comentários desativados, 8 vídeos indisponíveis. 113 posts de colaboração cujo dono não está na lista foram descartados |
| Critérios de seleção | público MPE declarado na bio, ativo nos últimos 12 meses, diversidade de tamanho de conta; embaixadores Stone limitados a 2 |
| Perfis candidatos | 59 em `config/profiles.csv` (38 YouTube · 21 Instagram), com faixa estimada de 16 micro · 21 médio · 20 grande + 2 parceiros. Segmentos: alimentação 14, varejo 10, finanças 9, geral 9, beleza 8, marketing 5, serviços 4. Até 6 marcas (Sebrae, Stone, Ton, InfinitePay, PagBank, Cora). Handles do YouTube verificados (URL 200 + RSS com envios nos últimos 12 meses). No Instagram, só a existência do perfil foi conferida. |
| Descoberta | busca por palavra-chave (MEI, lojista, confeitaria, salão, oficina, delivery…), curadoria do setor (Semana do MEI, Rede Mulher Empreendedora), concorrentes e ecossistema Stone. Descartados: canais inativos há mais de 12 meses, perfis cujo público não é dono de negócio e perfis com público amplo demais (ex.: 11 milhões de seguidores). |
| Seguidores do Instagram | `followers_estimado` vem de buscas na web e **nunca** é usado na métrica. O denominador vem sempre da rota de coleta, na data da coleta. |
| Licença | Dados públicos usados só para análise. Mídia baixada (thumbnails) não é redistribuída; posts citados por link. |

**Critérios de elegibilidade:** posts com ≥ 14 dias na data de coleta, seguidores > 0, curtidas e comentários visíveis.
As exclusões ficam registradas por motivo (`exclusion_reason`) e contadas em `base_stats.json`.

**Limitações de representatividade:**
- Seguidores são os da data de coleta, não da data do post (posts antigos de contas que cresceram ficam subestimados).
- Impulsionamento pago não aparece nos dados públicos e pode inflar curtidas e comentários.
- Viés de descoberta: contas grandes são mais fáceis de encontrar (mitigado com cotas por faixa).
- YouTube não marca Shorts na API: usamos duração ≤ 180 s (opcionalmente confirmada via URL `/shorts/`).
- **Concentração:** 4 canais somam 66% do top (os Shorts são distribuídos para quem não segue o canal, então contas pequenas com um vídeo viral chegam a taxas muito altas). Por isso cada padrão é reportado também com `n_criadores` e `freq_por_criador` (cada criador pesa igual), e o agente usa no máximo 2 referências por criador.

## 3. Métrica e ranking

1. **Engajamento:** `(curtidas + comentários) ÷ seguidores`, com seguidores na data da coleta.
2. **Alto desempenho:** posts com engajamento ≥ percentil 90 **da própria plataforma** (Instagram ≥ 2,00%; YouTube ≥ 1,29%).
   O ranking combinado também é calculado como análise de sensibilidade: 602 dos 625 posts coincidem.
3. **Elegibilidade:** pelo menos 14 dias no ar na data da coleta, seguidores > 0, curtidas e comentários visíveis.
   Exclusões por motivo: 272 com menos de 14 dias, 84 com curtidas ocultas, 76 com comentários desativados, 8 vídeos indisponíveis.

### Métrica ponderada (IDP)

Leitura complementar que controla nicho, perfil, período e porte. Cada post recebe quatro percentis (0 a 1):

| Componente | Grupo de comparação | Peso |
|---|---|---|
| `c_nicho` | mesmo segmento e plataforma | 0,35 |
| `c_perfil` | engajamento ÷ mediana do próprio criador, comparado na plataforma | 0,30 |
| `c_periodo` | mesmo trimestre de publicação e plataforma | 0,20 |
| `c_porte` | mesma faixa de seguidores e plataforma | 0,15 |

`IDP = Σ peso × componente`. Grupos com menos de 20 posts usam o percentil da plataforma. Top do IDP = percentil 90 do
índice por plataforma. O componente de perfil é o mais importante contra o viés de concentração: um post só pontua alto
se foi melhor do que o normal do próprio criador. Implementação: `src/stone_mpe/analysis/weighted.py`.

## 4. Categorização multimodal

- **Rubrica fixa** (TAP §6.2) em Pydantic (`multimodal/rubric.py`): formato do vídeo, tipo e força do gancho, tema, rosto,
  criador é empreendedor real, prova social, texto na tela, tom, linguagem regional, clareza, CTA e oferta explícita.
- **Nível 1** (todo o top + 150 posts de fora do top): legenda + capa → modelo de visão → JSON validado. JSON inválido é
  pedido de novo; a modalidade usada (`caption`, `thumbnail`) e o modelo ficam registrados em cada post.
- **Campos calculados, não pedidos ao modelo:** `tipo_post`, `duracao_faixa` e `legenda_tamanho` saem dos metadados.
- **Nível 2** (opcional, `--level 2`): frames do vídeo + transcrição (yt-dlp, ffmpeg, faster-whisper); o ritmo de cortes é
  medido, não julgado. Substitui o Nível 1 do mesmo post quando existe.

## 5. Validação

- **Humana:** amostra cega de 50 posts do top, estratificada por plataforma × porte (`cli sample`, semente 42).
  A pessoa rotula sem ver a resposta do modelo (`demo/rotular.py`). Métricas: concordância e κ de Cohen para campos
  categóricos e booleanos; MAE e % dentro de ±2 pontos para notas (`cli agreement` → `outputs/concordancia.csv`).
- **Rotulagem cega assistida por IA (complementar):** um assistente de IA rotula a mesma amostra vendo só capa, título
  e legenda, sem acesso à categorização (`validation/rotulagem_ia.csv`; `cli agreement --file ... --out concordancia_ia`).
  Fica em arquivo separado e nunca é apresentada como validação humana.
- **Entre modelos (complementar):** outro modelo recategoriza a mesma amostra (`cli cross-check`). Mede a estabilidade da
  rubrica, não o acerto, e não substitui a validação humana.

## 6. Análise

- **Frequências no top** com `n`, exemplos reais e duas leituras: **% dos posts** e **% por criador** (cada criador pesa igual).
- **Concentração:** número de criadores e participação dos 4 maiores em cada recorte.
- **Lift top × resto:** frequência no top ÷ frequência numa amostra aleatória de 150 posts elegíveis de fora do top
  (estratificada por plataforma). Só entram linhas com pelo menos 5 posts no resto.
- **Tema × formato**, **perfis em destaque** (presença no top ponderada pela taxa) e **nichos** (engajamento, % no top, metas).
- **Comentários (YouTube):** até 50 por post do top, classificados por regras em contato, dúvida, objeção e elogio.
  Nenhum autor é guardado; só contagens.
- **Lead (indireto):** presença e tipo de CTA, razão comentários/curtidas e intenção de contato nos comentários.

## 7. Agente

Grafo LangGraph determinístico (`agent/graph.py`):
`validar_entrada → consulta_base → posts_referencia → (redigir | gerar_criativo) → validar_saida ↺ → registrar`.

- Números e links vêm só das ferramentas (SQL na base). O modelo de linguagem apenas redige.
- `validar_saida` descarta qualquer `post_id` que não veio de `posts_referencia` e pede nova geração (máximo 2).
- No máximo 2 referências por criador, para que um canal dominante não monopolize as referências.
- Recortes com menos de 10 posts no top ligam `confidence_flag`.
- Sem modelo disponível, um template determinístico responde com os mesmos dados (a demo nunca quebra).

## Decisões declaradas

| Parâmetro | Valor |
|---|---|
| Ranking | top 10%, percentil **por plataforma** (IG e YT têm distribuições diferentes); a versão combinada também é calculada (sensibilidade) |
| `confidence_flag` | ativado quando o recorte tem < 10 publicações de alto desempenho ou quando foi ampliado |
| Valores fora do TAP | `duracao_faixa` = `<15s \| 15-30s \| 30-60s \| 60-90s \| >90s`; `legenda_tamanho` = `curta <125 \| média ≤500 \| longa`; `tipo_cta` inclui `nenhum` |
| Campos calculados, não pedidos ao modelo | `tipo_post`, `duracao_faixa` e `legenda_tamanho` saem dos metadados. Nível 1: `ritmo_cortes_0a10 = null` |
| Nível 2: ritmo de cortes | `ritmo_cortes_0a10 = min(10, round(10 × trocas de cena/s))`, com limiar de cena 0,3. É medido, e não julgado pelo modelo. |
| Nível 2: precedência | a categorização N2 (`v1-n2`) substitui a N1 do mesmo post nas análises |
| Comentários | classificador por regras: contato, dúvida, objeção, elogio. Sem autores; só contagens e até 3 exemplos curtos por classe. |
| Lift | frequência no top ÷ frequência numa amostra aleatória (estratificada por plataforma) de 150 posts elegíveis fora do top |
| Concentração | `n_criadores` e `freq_por_criador` ao lado de cada frequência; no máximo 2 referências por criador (`agent.max_refs_per_creator`) |

## Modelos e configurações

Os parâmetros ficam em `config/settings.yaml`. Os provedores e a ordem de fallback ficam em `LLM_PROVIDERS` (`.env`).

| Uso | Padrão | Fallback | Por quê |
|---|---|---|---|
| Categorização (VLM) | `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite` (plano gratuito) | OpenRouter `nvidia/nemotron-3.5-super-vl:free` → `google/gemma-4-31b-it:free` | gratuito, aceita imagem, modo JSON nativo. O modelo usado em cada post fica na coluna `model` |
| Agente (texto) | `gemini-3.5-flash` → `gemini-3.5-flash-lite` | OpenRouter `gemma-4-31b-it:free` → template offline | qualidade de redação; a demo nunca quebra |
| Similaridade de referências | BM25 lexical + percentil de engajamento | — | sem dependências; RAG com embeddings fica para o Nível 3 |
| Armazenamento | SQLite (consultas do agente) + Parquet (análise) | — | simples e reprodutível |

Os nomes de modelo mudam com frequência (os `gemini-2.5-*` já não aceitam chaves novas em 23/11/2026). Antes de rodar, confira se ainda estão disponíveis.
O plano gratuito do Gemini devolve 503 em horários de pico. Por isso `categorize --until-done` espera e retoma sozinho, e o `pipeline` já usa esse modo.
Ollama: apenas local (`ollama serve`). O Ollama Cloud exige créditos e não é usado.
