# Resultados

> Base coletada em 23–24/11/2026: 6.675 publicações de 55 perfis, 625 no top 10% por plataforma.
> Todos os padrões são **observados**, não causais. Cada número vem de um arquivo em `outputs/`, citado em cada seção.

- [Padrões do top](#padrões-do-top)
- [Engajamento por nicho](#engajamento-por-nicho)
- [Métrica ponderada (IDP)](#métrica-ponderada-índice-de-desempenho-ponderado-idp)
- [Confiabilidade da categorização](#confiabilidade-da-categorização)

## Padrões do top
Fontes: `outputs/frequencias_top.csv`, `tema_x_formato.csv`, `perfis_destaque.csv`, `patterns.json`, `playbook.md`.
Base: **625 de 625 posts do top categorizados** (Nível 1: legenda + capa): 563 do YouTube (26 criadores; os 4 maiores somam 66%)
e 62 do Instagram (16 perfis; os 4 maiores somam 61%). As tabelas abaixo são do YouTube; o Instagram vem em seguida.
Por isso cada padrão aparece de duas formas: **% dos posts** e **% por criador** (cada criador pesa igual).

**Padrões robustos** (altos nas duas leituras):

| Característica | % dos posts | % por criador | Criadores |
|---|---|---|---|
| Quem aparece é empreendedor real | 84% | 80% | 24 de 26 |
| Texto na tela | 65% | 77% | 24 |
| Rosto | 76% | 71% | 22 |
| Tom informal | 73% | 69% | 22 |
| Formato talking head (mais comum) | 29% | 45% | 20 |
| Gancho de promessa | 20% | 29% | 18 |

**Padrões que dependem de poucos canais** (a leitura por post engana):

| Característica | % dos posts | % por criador | Leitura |
|---|---|---|---|
| Sem CTA | 57% | 41% | por criador, a **maioria usa CTA** (59%), sobretudo "link na bio" |
| Duração 60–90 s | 42% | 29% | por criador, a faixa mais comum é **30–60 s** (42%) |
| Gancho de curiosidade | 49% | 30% | forte em 14 criadores; promessa e pergunta são mais espalhadas |
| Formato bastidores / antes-depois | 18% / 11% | 12% / 2% | estilo de poucos canais: bastidores em 9 criadores, antes/depois em só 2 |
| Prova social | 20% | 9% | rara: só 8 criadores |

**Instagram (62 posts do top, 16 perfis):**

| Característica | % dos posts | % por criador | Leitura |
|---|---|---|---|
| Texto na tela | 82% | 80% | ainda mais presente que no YouTube |
| Gancho de curiosidade | 48% | 50% | padrão robusto nas duas plataformas |
| Quem aparece é empreendedor real | 84% | 83% | igual ao YouTube |
| Talking head | 26% | 60% | formato mais comum por criador |
| Tom inspiracional | 26% | 35% | mais comum que no YouTube (12%) |
| Legenda média (125–500 caracteres) | 39% | 45% | no YouTube domina a legenda curta |
| CTA "comentar" | 16% | 21% | a CTA mais usada no Instagram; 74% dos posts do top não têm CTA |
| Tema marketing | 39% | 16% | concentrado em 4 perfis |

**Tema × formato:** vendas aparece com talking head, tutorial e antes/depois; histórias de empreendedor com talking head e
bastidores; atendimento quase só em humor/esquete (33 de 40 posts).
**Top × resto (lift)**, sobre uma amostra aleatória de 150 posts elegíveis de fora do top (`outputs/lift_top_vs_resto.csv`):

| Característica | No top | No resto | Lift | Criadores no top | Leitura |
|---|---|---|---|---|---|
| Gancho de curiosidade | 48% | 24% | **2,0** | 25 | o sinal mais robusto: muitos criadores e 36 posts no resto |
| Formato humor/esquete | 16% | 6% | **2,7** | 13 | associado ao top, espalhado entre criadores |
| Duração 15–30 s | 13% | 6% | **2,2** | 9 | vídeos curtos aparecem mais no top |
| Tom humorístico | 10% | 2% | 5,0 | 8 | lift alto, mas só 3 posts no resto: frágil |
| Antes/depois | 10% | 3% | 3,7 | 2 | estilo de 2 criadores, não padrão |

**Comentários (YouTube, 442 posts do top, 19.941 comentários, sem autores):** 17,2% trazem dúvidas, 4,5% intenção de contato
("quero", "como faço", "qual o link"), 4,2% objeções e 4,2% elogios. As dúvidas são a principal porta para conteúdo de resposta.
**Lead (indireto), ambas as plataformas:** 41% dos posts do top têm CTA explícita: "link na bio" (161), "comentar" (57), "seguir" (34).

## Engajamento por nicho

Mediana de (curtidas + comentários) ÷ seguidores entre os posts elegíveis, e a parte de cada nicho que chega ao top 10% da plataforma.
Fonte: `stone_mpe.analysis.niches` (aba **Nichos** do painel).

**Instagram** (613 posts elegíveis, 17 perfis; poucos perfis por nicho: leia como sinal, não como regra)

| Nicho | Perfis | Posts | Chegam ao top | Engajamento mediano | Formato mais comum no top | Gancho mais comum no top |
|---|---|---|---|---|---|---|
| Alimentação | 4 | 113 | 19% | 0,79% | tutorial (74%) | curiosidade (57%) |
| Varejo | 2 | 88 | 14% | 0,23% | bastidores (56%) | curiosidade (83%) |
| Finanças | 2 | 69 | 10% | 0,11% | talking head (100%) | polêmica (29%) |
| Beleza | 4 | 169 | 7% | 0,23% | talking head (83%) | polêmica (33%) |
| Marketing | 2 | 74 | 7% | 0,33% | — | curiosidade (40%) |
| Geral | 2 | 80 | 5% | 0,33% | talking head (100%) | promessa (75%) |
| Serviços | 1 | 20 | 5% | 0,06% | humor/esquete | pergunta |

**YouTube Shorts** (5.622 posts elegíveis, 38 canais)

| Nicho | Canais | Posts | Chegam ao top | Engajamento mediano | Formato mais comum no top | Duração mais comum no top |
|---|---|---|---|---|---|---|
| Beleza | 4 | 886 | 16% | 0,16% | antes/depois (43%) | 60–90 s |
| Geral | 7 | 1.603 | 14% | 0,03% | humor/esquete (39%) | 60–90 s |
| Alimentação | 8 | 1.000 | 13% | 0,06% | bastidores (45%) | 30–60 s |
| Finanças | 7 | 960 | 4% | 0,03% | talking head (68%) | 30–60 s |
| Varejo | 7 | 740 | 4% | 0,05% | talking head (65%) | 30–60 s |
| Marketing | 3 | 412 | 0,5% | 0,02% | talking head | 15–30 s |
| Serviços | 2 | 21 | 5% | 0,34% | tutorial | 60–90 s |

**Leitura:** alimentação e beleza são os nichos em que mais posts chegam ao top nas duas plataformas. Finanças e varejo
engajam menos em termos relativos e dependem mais de talking head. A diferença entre nichos é grande, e é isso que motiva a métrica ponderada abaixo.

## Métrica ponderada (Índice de Desempenho Ponderado, IDP)

A métrica oficial compara todos os posts da plataforma entre si e favorece nichos que engajam mais, contas com um viral
isolado e épocas em que a plataforma distribuía mais. O IDP compara cada post com os seus pares e soma os percentis com pesos:

| Componente | Compara o post com | Peso |
|---|---|---|
| Nicho | posts do mesmo segmento, na mesma plataforma | 0,35 |
| Perfil | a mediana do próprio criador (o post foi acima do normal dele?) | 0,30 |
| Período | posts do mesmo trimestre, na mesma plataforma (tendência) | 0,20 |
| Porte | contas da mesma faixa de seguidores | 0,15 |

Grupos com menos de 20 posts usam o percentil da plataforma. O top do IDP é o percentil 90 do índice, por plataforma.
Os pesos ficam em `config/settings.yaml` e podem ser ajustados ao vivo no painel (aba **Métrica ponderada**).

| | Instagram | YouTube |
|---|---|---|
| Top em comum com o ranking oficial | 81% (50 de 62) | 73% (411 de 563) |
| Criadores no top (oficial → IDP) | 16 → 16 | 26 → **30** |
| 4 maiores criadores somam (oficial → IDP) | 61% → **45%** | 66% → **51%** |

**Os padrões resistem ao controle de nicho, perfil, período e porte** (466 posts categorizados do top do IDP):

| Característica | Top oficial | Top do IDP |
|---|---|---|
| Gancho de curiosidade | 48% | 48% |
| Talking head | 30% | 32% |
| Humor/esquete | 16% | 19% |
| Tom informal | 73% | 72% |
| CTA "link na bio" | 26% | 31% |
| Sem CTA | 59% | 54% |

O IDP reduz a concentração em poucos canais e mantém os mesmos padrões. Isso reforça que gancho de curiosidade, rosto,
tom informal e texto na tela são características do conteúdo de alto desempenho para MPEs, e não estilo de um criador
ou efeito de nicho. Arquivos: `outputs/indice_ponderado.csv`, `indice_ponderado.json`, `indice_ponderado_padroes.csv`.

## Confiabilidade da categorização

**Concordância entre modelos (complementar):** outro modelo (Gemma 4) recategorizou 45 posts da amostra de validação.
Mede a estabilidade da rubrica, não o acerto. Arquivo: `outputs/concordancia_modelos.csv`.

| Campo | Concordância | Kappa de Cohen |
|---|---|---|
| Tem CTA · tipo de CTA | 98% · 96% | 0,96 · 0,93 |
| Rosto · texto na tela | 98% · 98% | 0,95 · 0,95 |
| Oferta ou benefício explícito | 91% | 0,81 |
| Tema | 76% | 0,70 |
| Gancho | 73% | 0,62 |
| Formato de vídeo | 69% | 0,62 |
| Tom · prova social · linguagem regional | 80% · 84% · 93% | 0,50 · 0,54 · 0,38 |
| Notas 0–10 (força do gancho, clareza), ±2 pontos | 100% · 98% | — |

Campos objetivos são estáveis. Tema, gancho e formato concordam moderadamente: os achados sobre eles são tendências.
Tom e linguagem regional não sustentam recomendações isoladas.

**Rotulagem cega assistida por IA (terceiro avaliador, não substitui a humana):** os mesmos 50 posts da amostra foram
rotulados por um assistente de IA que viu só a capa, o título e a legenda, sem acesso à categorização do modelo
(`validation/rotulagem_ia.csv`, `outputs/concordancia_ia.csv`).

| Campo | Concordância com o modelo | Kappa |
|---|---|---|
| Tem CTA · rosto · texto na tela | 98% · 98% · 98% | 0,96 · 0,96 · 0,95 |
| Tipo de CTA · oferta explícita · linguagem regional | 94% · 94% · 94% | 0,90 · 0,87 · 0,38 |
| Prova social · empreendedor real · tom | 88% · 80% · 80% | 0,65 · 0,45 · 0,48 |
| Gancho · formato · tema | 70% · 66% · 60% | 0,58 · 0,60 · 0,52 |
| Notas 0–10 (força do gancho · clareza), ±2 pontos | 90% · 72% | — |

Três leituras independentes (o modelo da análise, um segundo modelo e a rotulagem cega por IA) convergem: campos
objetivos acima de 94%, campos interpretativos entre 60% e 76%.

**Validação humana:** 50 posts sorteados do top (estratificados por plataforma e porte) em `validation/manual_sample.csv`,
rotulados às cegas em `demo/rotular.py`. O resultado sai em `outputs/concordancia.csv` com `python -m stone_mpe.cli agreement`.
