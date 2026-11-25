# Guia de uso

## 1. Instalação

Requisitos: Python 3.11 ou superior e Git.

```bash
git clone https://github.com/Henriquerssx/Case-Stone.git
cd Case-Stone
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.lock.txt      # versões exatas testadas
pip install -e . --no-deps
```

Sem o arquivo de lock: `pip install -e ".[dev,demo]"`.

## 2. Ver o projeto funcionando (sem chave de API)

```bash
python -m stone_mpe.cli bootstrap   # monta db/base.sqlite a partir de data/release/ (confere checksums)
streamlit run demo/app.py           # abre http://localhost:8501
```

O painel também faz o `bootstrap` sozinho na primeira abertura. A base pública não traz legendas nem capas
(ver [Dados, privacidade e segurança](DADOS_PRIVACIDADE_E_SEGURANCA.md)); todo o resto funciona.

### O painel

| Aba | Para quê |
|---|---|
| Como funciona | as 9 etapas com os números reais e o status de cada uma |
| Gerar roteiro | pedido em texto → roteiro com storyboard 9:16, legenda, CTA, vídeos de referência e metas de engajamento. Deixe **Modo offline** ligado para usar as respostas pré-calculadas (instantâneo, sem chave) |
| Nichos | engajamento, % de posts no top e o que o top de cada nicho usa; botão para gerar roteiro do nicho |
| Padrões do top | frequência de cada característica (% dos posts e % por criador), tema × formato, lift top × resto |
| Métrica ponderada | o Índice de Desempenho Ponderado, com os pesos ajustáveis ao vivo |
| Perfis em destaque · Base | perfis que mais aparecem no top, sinais de lead, distribuição e exclusões |

## 3. Usar o agente

### Linha de comando

```bash
python -m stone_mpe.cli ask gerar_criativo "vídeo curto para donos de pequenos restaurantes" --segment alimentacao
python -m stone_mpe.cli ask recomendar "como atrair microempreendedoras de beleza?" --platform instagram
python -m stone_mpe.cli ask analisar "o que funciona em finanças para MEI?"
```

### Função Python

```python
from stone_mpe.api import run

out = run("gerar_criativo", "vídeo curto para salão de beleza", segment="beleza",
          filters={"platform": "instagram"}, n_creatives=2)
for c in out.creatives:
    print(c.titulo, c.gancho, c.inspired_by)   # inspired_by = post_ids reais da base
```

Modos: `analisar`, `recomendar`, `gerar_criativo`. A entrada é validada (pergunta de 3 a 500 caracteres; segmento em minúsculas).

### Servidor MCP

```bash
python -m stone_mpe.mcp_server        # transporte stdio
```

Ferramentas expostas: `analisar_engajamento` (os três modos do agente) e `resumo_base`.
Exemplo de configuração em um cliente compatível com MCP:

```json
{
  "mcpServers": {
    "stone-mpe": {
      "command": "C:/caminho/para/Case-Stone/.venv/Scripts/python.exe",
      "args": ["-m", "stone_mpe.mcp_server"],
      "cwd": "C:/caminho/para/Case-Stone"
    }
  }
}
```

## 4. Chaves de API (só para coletar ou gerar ao vivo)

Copie `.env.example` para `.env` e preencha só o que for usar. O `.env` nunca é versionado.

| Variável | Para quê | Custo |
|---|---|---|
| `GEMINI_API_KEY` | categorização e agente ao vivo | plano gratuito |
| `OPENROUTER_API_KEY` | fallback de modelos | modelos `:free` |
| `YOUTUBE_API_KEY` | coleta do YouTube | cota gratuita da API |
| `APIFY_TOKEN` | coleta do Instagram | ~US$ 2,20 por coleta completa (crédito gratuito de US$ 5/mês) |

## 5. Reproduzir o pipeline completo

```bash
python -m stone_mpe.cli status                          # o que está pronto e qual o próximo comando
python -m stone_mpe.cli collect-youtube
python -m stone_mpe.cli collect-instagram --dry-run     # mostra o custo antes de gastar
python -m stone_mpe.cli collect-instagram
python -m stone_mpe.cli build-base
python -m stone_mpe.cli categorize --until-done
python -m stone_mpe.cli categorize --rest-sample 150 --until-done
python -m stone_mpe.cli collect-comments
python -m stone_mpe.cli analyze                         # padrões, lift, perfis, IDP
python -m stone_mpe.cli playbook                        # outputs/playbook.md
python -m stone_mpe.cli precompute-demo                 # respostas do modo offline
python -m stone_mpe.cli export-release                  # base pública sanitizada em data/release/
```

Ou tudo de uma vez: `python -m stone_mpe.cli pipeline`. No Google Colab: `notebooks/pipeline_colab.ipynb`.

## 6. Validação manual

```bash
python -m stone_mpe.cli sample -n 50      # sorteio cego (já feito: validation/manual_sample.csv)
streamlit run demo/rotular.py             # rotular post a post, sem ver a resposta do modelo
python -m stone_mpe.cli agreement         # concordância e kappa → outputs/concordancia.csv
python -m stone_mpe.cli cross-check       # complementar: outro modelo recategoriza a amostra
```

A tela de rotulagem mostra a legenda a partir da base local completa; num clone com a base pública, use o link do post.

## 7. Testes

```bash
pytest          # 65 testes com base sintética; não chamam APIs externas
```

## Problemas comuns

| Sintoma | Solução |
|---|---|
| "execução de scripts desabilitada" ao ativar o venv no PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Geração ao vivo demora ou cai no template | cota gratuita esgotada; use o Modo offline ou espere o reset (~05:00, horário de Brasília) |
| Painel sem dados | `python -m stone_mpe.cli bootstrap` |
| `bootstrap` diz que a base já existe | `python -m stone_mpe.cli bootstrap --force` para recriar a partir de `data/release/` |
