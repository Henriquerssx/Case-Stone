# Desempenho dos modelos

Como os modelos de IA se comportaram na categorização e no agente, medido nos registros de execução de 23 e 24/11/2026.
Todo o projeto roda nos **planos gratuitos** do Google Gemini e do OpenRouter, sem custo de inferência.

## Resumo

| Indicador | Valor | Leitura |
|---|---|---|
| Posts categorizados | **775** (625 do top + 150 de fora) | 100% com JSON válido na rubrica |
| Modelos usados na categorização | 7, em cadeia de fallback | o modelo de cada post fica na coluna `model` |
| Latência mediana da categorização | 4–5 s (Gemini Flash-Lite) | 20 s no OpenRouter, 40 s no Gemma |
| Falhas de chamada absorvidas | 1.136 (772 de cota, 364 de sobrecarga) | nenhuma virou dado perdido: retry, fallback e retomada |
| Estabilidade da rubrica entre modelos | 96–98% nos campos objetivos | 69–76% em tema, gancho e formato |
| Execuções do agente | 75 | 100% rastreáveis a posts reais |
| Latência mediana do agente | 30 s com modelo; < 1 s no modo offline | a demonstração usa respostas pré-calculadas |

## Categorização (Nível 1: legenda + capa)

| Modelo | Posts | Participação | Latência mediana |
|---|---|---|---|
| Gemini 3.5 Flash-Lite | 309 | 40% | 5,0 s |
| Gemini 3.1 Flash-Lite | 254 | 33% | 4,2 s |
| Nemotron 3.5 Super VL (OpenRouter, gratuito) | 83 | 11% | 20,0 s |
| Gemini Flash-Lite (latest) | 54 | 7% | 4,6 s |
| Gemini 3 Flash (preview) | 38 | 5% | 9,2 s |
| Gemini 3.6 Flash | 24 | 3% | 30,0 s |
| Gemma 4 26B | 13 | 2% | 42,7 s |

**Por que uma cadeia de modelos:** no plano gratuito, cada modelo Flash do Gemini aceita só 20 pedidos por dia e os
servidores devolvem sobrecarga (503) em horários de pico. O cliente (`llm.FallbackClient`) passa para o próximo modelo
quando um falha, pausa o modelo com problema (90 s para sobrecarga, 1 h para cota diária esgotada) e a categorização
retoma de onde parou (`categorize --until-done`). Das 2.168 chamadas registradas, 51% das de categorização tiveram sucesso
na primeira tentativa. As demais foram absorvidas sem perda de dado.

**Garantia de formato:** a resposta precisa passar na validação Pydantic da rubrica. JSON inválido é pedido de novo.
Valores com acento ou caixa diferentes são normalizados (`multimodal/rubric.py`).

## Estabilidade da rubrica (concordância entre modelos)

Outro modelo (Gemma 4) recategorizou 45 posts da amostra de validação, e as respostas foram comparadas com as usadas na
análise (`python -m stone_mpe.cli cross-check`).

| Grupo de campos | Concordância | Kappa de Cohen | Uso recomendado |
|---|---|---|---|
| CTA, rosto, texto na tela | 96–98% | 0,93–0,96 | base sólida para recomendações |
| Oferta ou benefício explícito | 91% | 0,81 | base sólida |
| Tema, gancho, formato | 69–76% | 0,62–0,70 | tendência; conferir exemplos |
| Tom, prova social, linguagem regional | 80–93% | 0,38–0,54 | não usar isoladamente |
| Notas 0–10 (±2 pontos) | 98–100% | — | estáveis |

Isso mede a estabilidade, não o acerto. A medida de acerto é a **validação humana** em 50 posts (`demo/rotular.py`),
que calcula concordância e kappa entre a pessoa e o modelo.

## Agente

| Indicador | Valor |
|---|---|
| Execuções registradas | 75 (62 de geração de criativo) |
| Criativos com referências válidas | 75 de 75: todo `inspired_by` aponta para um post real recuperado da base |
| Respostas com confiança adequada | 72 de 75 (as 3 restantes tinham recorte com menos de 10 posts no top) |
| Respostas por modelo | Gemini 3.5 Flash-Lite 31 · Gemini 3.5 Flash 20 · Gemma 4 9 · template sem modelo 15 |
| Latência | mediana 30 s, p75 51 s com modelo |

**Por que o agente é confiável:** números e links saem só de consultas à base (SQL). O modelo apenas redige.
A etapa `validar_saida` descarta qualquer post que não veio das ferramentas e pede nova geração (até 2 vezes).
Sem modelo disponível, um template determinístico monta o roteiro com os mesmos dados.

## Limites conhecidos

- As cotas gratuitas mudam sem aviso e reiniciam por volta das 05:00 (horário de Brasília).
- Nomes de modelo mudam com frequência; a configuração fica em `config/settings.yaml`.
- O Nível 1 não vê o vídeo: gancho falado, ritmo de cortes e áudio só entram no Nível 2 (frames + transcrição).
