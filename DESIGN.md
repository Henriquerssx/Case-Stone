---
name: Impulso Stone · Engajamento MPE
description: Painel noturno no mundo do Clube dos Sonhos, em que o top 10% dos posts brilha em verde-limão.
colors:
  ink: "#03211D"
  ink-soft: "#06352E"
  deep: "#055046"
  teal: "#32ADA1"
  mist: "#E6EAE9"
  mist-muted: "#A9BDB7"
  lime: "#C7F93C"
  sherwood: "#004132"
  border: "#0E4A40"
  chart-teal: "#2EA99C"
  chart-purple: "#9A78F0"
typography:
  display:
    fontFamily: "Outfit, sans-serif"
    fontSize: "clamp(2.4rem, 4.6vw, 4.4rem)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Outfit, sans-serif"
    fontWeight: 800
    lineHeight: 0.98
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Outfit, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 700
  body:
    fontFamily: "Manrope, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Outfit, sans-serif"
    fontSize: "0.76rem"
    fontWeight: 700
    letterSpacing: "0.08em"
rounded:
  md: "0.9rem"
  card: "1.1rem"
  pill: "999px"
components:
  button-primary:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0.6rem 1.4rem"
  tab-selected:
    backgroundColor: "{colors.teal}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
  tab:
    textColor: "{colors.mist}"
    rounded: "{rounded.pill}"
  niche-card:
    backgroundColor: "{colors.ink-soft}"
    textColor: "{colors.mist}"
    rounded: "{rounded.card}"
---

# Design System: Impulso Stone · Engajamento MPE

## Overview

**Creative North Star: "A constelação do Impulso"**

O painel vive no mundo do Clube dos Sonhos: noite verde-tinta, títulos grandes em caixa alta e uma estrela de quatro
pontas como motivo. Cada publicação é uma estrela, e as que chegam ao top 10% brilham em verde-limão do Impulso Stone.
A primeira tela pergunta "O que faz um pequeno negócio brilhar?" e responde com números reais. Dali em diante o painel
é uma ferramenta de leitura: densa, clara e sem ornamento que não carregue dado.

**Key Characteristics:**
- Tema único escuro: o mundo do Clube dos Sonhos é noturno.
- Verde-limão reservado ao que "brilha": top 10%, números de destaque, a estrela.
- Ações e navegação em pílulas verde-água com texto tinta, em caixa alta.
- 3D só com função: a estrela do topo (proporção real do top) e a galáxia de posts.

## Colors

Noite verde com um único brilho quente-ácido.

- **Ink `#03211D`**: fundo de tudo, com dois halos radiais suaves (verde-água no canto superior esquerdo, limão no direito).
- **Ink-soft `#06352E`**: painéis, campos e cabeçalho de tabelas.
- **Teal `#32ADA1`**: ações primárias, aba ativa, foco e seleção de texto.
- **Mist `#E6EAE9`**: texto; a 12% de opacidade vira a linha fina das bordas.
- **Lime `#C7F93C`**: só o que brilha (top 10%, o 625 da frase de prova, a palavra do título, a estrela, a etapa pendente).
- **Links**: verde-água; nas tabelas, a coluna de link mostra "abrir" em vez da URL.
- **Gráficos**: verde-água `#2EA99C` (série única) e o roxo do Impulso `#9A78F0` como segunda série, validados sobre a tinta
  (contraste ≥ 3:1, separação para daltonismo; verde-água + névoa foi testado e reprovado: a névoa lê como cinza).
  Sequencial de `#06352E` a `#C7F93C`.

## Typography

Outfit (display, títulos, rótulos) e Manrope (texto), servidas pelo projeto (`demo/static/fonts`, OFL).
O display usa caixa alta, peso 800 e entrelinha 0,95. Os rótulos de métricas e das abas usam caixa alta com espaçamento
de 0,08–0,16em. O texto corrido fica em Manrope, com 1,55 de entrelinha e medida de até 34rem no topo.

## Layout

- Container de até 1320px.
- Topo em duas colunas (1,25 : 1): pergunta e números à esquerda, estrela 3D à direita. No celular, as colunas empilham.
- Abas em pílulas que quebram linha no celular.
- Cartões de nicho em 7 colunas, proporção 9:16 (a de um vídeo curto), com o botão "Ver nicho" embaixo de cada um.
- Etapas do pipeline numa trilha única (ícone, etapa, numeral Outfit, detalhe), e não em cartões iguais.

## Elevation & Depth

Profundidade por luz, não por sombra:
- brilho em verde-limão na palavra "brilhar" e nos pontos do top;
- halo névoa na estrela;
- uma única sombra difusa sob o botão primário.

Os painéis são planos e se separam por tom (ink-soft) e linha fina.

## Shapes

- Pílula (999px) para ações, abas e selos.
- 0,9rem para campos.
- 1,1rem para cartões.
- A estrela de quatro pontas (SVG em `brand.star_svg`) é o único ícone autoral. Os demais ícones vêm do Material Symbols do Streamlit.

## Components

- **Botão primário**: verde-água, texto tinta em caixa alta (Outfit 700); clareia 10% no hover.
- **Abas**: pílula com borda fina; a borda vira verde-água no hover; a aba ativa é preenchida de verde-água.
- **Cartão de nicho** ("Escolha o seu nicho"):
  - fundo: a capa real do post de maior engajamento do nicho, sob um gradiente de tinta de baixo para cima;
  - texto: nome em Outfit 800 caixa alta e a taxa no top em verde-limão;
  - hover: borda verde-água e sobe 3px;
  - escolha: o botão "Ver nicho" seleciona o nicho no detalhe abaixo;
  - capas configuráveis: `demo.cover_skip` em `config/settings.yaml` tira capas impróprias para o pitch.
- **Gancho do roteiro**: estrela e a frase em Outfit 700, sem rótulo acima (o "0–3 s" vai na linha de formato).
- **Quadros do storyboard**: fundo ink-soft→deep, figuras em verde-água e névoa, um acento limão, texto na tela em caixa alta.
- **Estrela 3D** (`brand.star3d_html`):
  - estrela facetada em canvas 2D, sem bibliotecas, com 420 partículas, das quais a proporção real do top 10% em verde-limão;
  - inclina com o ponteiro e gira ao arrastar;
  - com movimento reduzido, mostra um quadro estático.
- **Galáxia 3D** (`brand.galaxy_figure`): Plotly scatter3d dos 6.235 posts elegíveis por nicho, ano e engajamento (log), com o top em verde-limão.

## Do's and Don'ts

- **Do:** reservar o verde-limão ao que está no top 10% ou é o número-chave.
- **Do:** escapar todo texto vindo de dados (`html.escape`) antes de entrar em HTML.
- **Do:** manter o painel funcional sem capas: o cartão cai para o gradiente verde.
- **Don't:** usar logotipos da Stone ou do Impulso (marcas registradas).
- **Don't:** emoji como ícone, nem rótulo pequeno acima de título.
- **Don't:** 3D decorativo sem dado por trás.
