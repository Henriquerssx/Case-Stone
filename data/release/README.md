# Base pública sanitizada

Versão publicável da base do projeto. Gerada por `python -m stone_mpe.cli export-release` e carregada por
`python -m stone_mpe.cli bootstrap`, que confere o SHA-256 de cada arquivo contra o `MANIFEST.json`.

Coleta: 23–24/11/2026. Legendas, títulos, tags, URLs de miniatura, texto de comentários e respostas brutas dos modelos
foram removidos (ver [Dados, privacidade e segurança](../../docs/DADOS_PRIVACIDADE_E_SEGURANCA.md)).

## Arquivos

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `posts.csv.gz` | 6.675 | um post por linha: métricas, elegibilidade, engajamento e ranking |
| `profiles.csv` | 55 | perfis com dados: plataforma, faixa de seguidores, segmento, contagens |
| `categorizations.csv.gz` | 775 | categorização pela rubrica (625 posts do top + 150 de fora do top) |
| `comment_signals.csv` | 442 | sinais agregados de comentários por post do top (YouTube) |
| `MANIFEST.json` | — | data de geração, colunas removidas, linhas e SHA-256 de cada arquivo |

## Dicionário: `posts.csv.gz`

| Coluna | Descrição |
|---|---|
| `post_id` | `ig_<código>` ou `yt_<id do vídeo>` |
| `platform` | `instagram` ou `youtube` |
| `handle`, `profile_id` | perfil público do criador |
| `url` | link do post |
| `media_type` | `reels`, `carrossel`, `imagem` ou `short` |
| `posted_at`, `collected_at` | data de publicação e data da coleta (UTC) |
| `likes`, `comments`, `views`, `duration_s` | métricas públicas (views e duração só no YouTube) |
| `followers` | seguidores do perfil na data da coleta |
| `source_route` | rota de coleta (`youtube_data_api_v3` ou `apify/instagram-post-scraper`) |
| `age_days`, `eligible`, `exclusion_reason` | elegibilidade (≥ 14 dias, métricas visíveis) e motivo de exclusão |
| `engagement_rate` | (curtidas + comentários) ÷ seguidores |
| `faixa` | `micro` (≤ 10 mil), `medio` (10–100 mil), `grande` (> 100 mil) |
| `segmento`, `origem`, `justificativa` | nicho, como o perfil foi encontrado e por que entrou na base |
| `percentile_platform`, `is_top_platform` | percentil e top 10% dentro da plataforma (ranking oficial) |
| `percentile_combined`, `is_top_combined` | idem na base combinada (sensibilidade) |
| `is_top`, `percentile` | ranking usado nas análises (por plataforma) |

## Dicionário: `categorizations.csv.gz`

Campos da rubrica (`src/stone_mpe/multimodal/rubric.py`): `formato_video`, `tipo_hook`, `hook_primeiros_3s`
(resumo do gancho escrito pelo modelo), `forca_hook_0a10`, `tema_principal`, `tem_rosto`, `criador_e_empreendedor_real`,
`prova_social`, `texto_na_tela`, `legenda_tamanho`, `ritmo_cortes_0a10`, `tom`, `usa_linguagem_regional`,
`clareza_mensagem_0a10`, `tem_cta`, `tipo_cta`, `oferta_ou_beneficio_explicito`, `elementos_top5`, `tipo_post`,
`duracao_faixa`. Metadados: `prompt_version`, `model` (modelo que categorizou), `input_modalities`, `valid`, `created_at`.

## Dicionário: `comment_signals.csv`

`n_sampled` (comentários lidos no post), `n_contato`, `n_duvida`, `n_objecao`, `n_elogio` e as taxas correspondentes.
Nenhum autor e nenhum texto de comentário.

## Uso

Dados públicos agregados, para análise. Respeite os termos de uso das plataformas de origem e cite os posts por link.
