# Relatório executivo

**Mapeamento de conteúdo de alto engajamento para MPEs · Impulso Stone**
Stone × Inteli Academy · novembro de 2026

---

## Em uma frase

Analisamos 6.675 publicações de 55 perfis que falam com micro e pequenos empreendedores, identificamos o que as
publicações de maior engajamento têm em comum e entregamos um agente que transforma esses padrões em roteiros prontos
para o @impulsostone, cada um ligado às publicações reais em que se apoia.

## O problema

A escolha de conteúdo para MPEs se apoia em intuição, referências pontuais e cópia de tendências. Não havia uma base
que mostrasse o que de fato engaja quem tem um pequeno negócio, nem um jeito de transformar isso em pauta.

## O que foi feito

| Etapa | Resultado |
|---|---|
| Base | 6.675 publicações de 55 perfis: 820 do Instagram (17 perfis) e 5.855 Shorts do YouTube (38 canais), em 7 nichos |
| Métrica | (curtidas + comentários) ÷ seguidores; top 10% por plataforma = **625 publicações** |
| Categorização | as 625 publicações do top e 150 de fora do top descritas por uma rubrica fixa de 20 campos, via IA |
| Análise | padrões do top, comparação top × resto, concentração por criador, nichos, 19.941 comentários |
| Métrica ponderada | índice que controla nicho, perfil, período e porte, para separar padrão de efeito de tamanho |
| Produto | agente (função Python e servidor MCP), painel interativo e playbook com 6 criativos prontos |

## O que os dados mostram

1. **O gancho de curiosidade é o sinal mais forte.** Aparece em 48% do top contra 24% do resto (2,0×), em 25 criadores
   diferentes. Continua em 48% quando nicho, perfil, época e porte são controlados.
2. **Gente real, de rosto, falando informal, com texto na tela.** Quem aparece é empreendedor real em 84% do top;
   rosto em 76%; tom informal em 73%; texto na tela em 65% no YouTube e 82% no Instagram. Valem para a maioria dos criadores.
3. **Humor e vídeos curtos se destacam.** Humor/esquete aparece 2,7× mais no top; vídeos de 15–30 s, 2,2×.
4. **Os comentários pedem resposta.** 17% são dúvidas e 4,5% mostram intenção de contato ("quero", "qual o link").
   Dúvida recorrente é pauta pronta.
5. **A maioria dos criadores do top usa CTA** (59%), sobretudo "link na bio", embora a maioria dos posts não use:
   poucos canais grandes sem CTA distorcem a leitura por post.
6. **Nichos engajam de forma muito diferente.** Alimentação e beleza levam mais posts ao top; finanças e varejo engajam
   menos e dependem de talking head. As metas de engajamento devem ser por nicho, e o painel as calcula.

Todos são padrões **observados**, não garantia de resultado. Detalhes e fontes em [RESULTADOS.md](RESULTADOS.md).

## Recomendações para o @impulsostone

| # | Recomendação | Evidência |
|---|---|---|
| 1 | Abrir os vídeos com um gancho de curiosidade nos 3 primeiros segundos | lift 2,0×, 25 criadores, estável no índice ponderado |
| 2 | Colocar empreendedores reais do programa na frente da câmera, em tom de conversa | 84% do top; 80% dos criadores |
| 3 | Usar texto na tela em todo vídeo | 65–82% do top; campo com 98% de concordância entre modelos |
| 4 | Transformar as dúvidas recorrentes dos comentários em pauta e fechar com convite ao programa | 17% dos comentários são dúvidas |
| 5 | Fechar com CTA de inscrição ("link na bio") | 59% dos criadores do top usam CTA |
| 6 | Testar formatos curtos (15–30 s) e humor/esquete em parte da grade | lift 2,2× e 2,7× |
| 7 | Medir com os Insights do perfil (alcance, salvamentos, cliques) para validar o efeito real | lead aqui é indicador indireto |

## Entregas

| Entrega | Onde |
|---|---|
| Playbook com padrões, perfis em destaque e **6 criativos prontos** (gancho, storyboard, legenda, CTA, posts de referência) | [`outputs/playbook.md`](../outputs/playbook.md) |
| Agente: função `run()` e servidor MCP, três modos (analisar, recomendar, gerar criativo) | [Guia de uso](GUIA_DE_USO.md) |
| Painel interativo: roteiro com storyboard ilustrado, nichos, padrões, métrica ponderada | `streamlit run demo/app.py` |
| Base pública sanitizada e reprodutível | [`data/release/`](../data/release/README.md) |
| Metodologia, desempenho dos modelos, privacidade e segurança | [`docs/`](.) |

Os 6 criativos do playbook: *Precificação simples para começar* · *Cliente de volta* (pós-venda) · *Organizar o caixa e
crescer* · *Bastidores e vendas no restaurante* · *Separar o dinheiro do salão* · *Convite para a mentoria Impulso Stone*.

## Confiabilidade

- Campos objetivos (CTA, rosto, texto na tela) têm 96–98% de concordância entre dois modelos diferentes.
  Tema, gancho e formato, 69–76%: são lidos como tendência.
- O agente nunca cita uma publicação que não esteja na base: 75 de 75 execuções rastreáveis.
- Validação humana: 50 publicações sorteadas às cegas, rotuladas na ferramenta do projeto.

## Limitações

- Correlação, não causalidade.
- Seguidores medidos na data da coleta; impulsionamento pago não é visível.
- Instagram com 17 perfis: poucos por nicho, leitura como sinal.
- A coleta do Instagram usou o Apify (rota do kickoff), em tensão com o TAP §4.3; só métricas públicas agregadas.

## Próximos passos

1. Gravar e publicar os 6 criativos no @impulsostone e medir com os Insights do perfil.
2. Migrar a coleta do Instagram para a API oficial com contas parceiras.
3. Analisar frames e fala dos vídeos do top (Nível 2) para medir ritmo de cortes e gancho falado.
4. Atualizar a base a cada trimestre: o índice ponderado já separa tendência de época.
