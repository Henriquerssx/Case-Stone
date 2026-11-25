# Dados, privacidade e segurança

## O que é coletado

| Dado | Coletado | Observação |
|---|---|---|
| Métricas públicas dos posts (curtidas, comentários, views, duração, data) | sim | agregados públicos |
| Seguidores do perfil, na data da coleta | sim | denominador da métrica |
| Link, legenda e capa do post | sim, só na base local | usados para categorizar; **não** são publicados |
| Comentários de posts do top (YouTube) | sim, só na base local | classificados por regras; apenas contagens são publicadas |
| Nome, foto ou perfil de quem comenta ou segue | **não** | em nenhuma etapa |
| Dados de mensagens privadas, stories ou contas privadas | **não** | |

**Fontes:** YouTube Data API v3 (oficial) e, para o Instagram, os atores públicos do Apify, rota definida no kickoff do
case. O Apify coleta dados públicos por terceiros, o que está em tensão com o TAP §4.3 (scraping fora do escopo).
O projeto declara isso, nunca acessa o Instagram diretamente, limita a coleta a métricas públicas agregadas e registra a
rota em `source_route` em cada post. Para uso contínuo pela Stone, o caminho recomendado é a API oficial (Instagram Graph
API) com as contas parceiras.

## O que este repositório publica

O repositório é público. Ele **não** contém:

- legendas, títulos, tags ou URLs de miniatura (URLs de CDN assinadas) dos posts;
- capas ou vídeos baixados;
- texto de comentários (nem citações curtas);
- a resposta bruta dos modelos (`raw_json`);
- logs de execução, consultas feitas ao agente e registros de chamadas de modelo;
- chaves de API ou qualquer arquivo `.env`.

Ele contém, em `data/release/`, uma **base pública sanitizada** com métricas agregadas, link de cada post,
a categorização pela rubrica e os sinais agregados de comentários (ver [dicionário](../data/release/README.md)).
O `MANIFEST.json` lista as colunas removidas e o SHA-256 de cada arquivo; o `bootstrap` recusa arquivos adulterados.

## LGPD

- **Finalidade:** análise agregada de padrões de conteúdo para fins educacionais e de pesquisa no case Stone × Inteli.
- **Minimização:** só métricas públicas e o necessário para categorizar; nenhum dado de pessoa física além do perfil
  público do criador, que publica conteúdo com finalidade comercial e profissional.
- **Transparência:** os posts são citados por link, e cada recomendação aponta a publicação em que se apoia.
- **Retenção:** dados brutos e mídia ficam só na máquina de quem roda o pipeline (`data/raw`, `data/media`, `db/`),
  fora do controle de versão.

## Segurança

| Risco | Proteção | Onde |
|---|---|---|
| Vazamento de chaves | `.env` ignorado; chaves enviadas em cabeçalho (nunca na URL); mensagens de erro mascaram `key=`/`token=`; cache HTTP não guarda parâmetros secretos | `.gitignore`, `collect/http.py`, `collect/youtube.py` |
| Injeção de HTML no painel ou no storyboard exportado | todo texto vindo de modelo ou de terceiros passa por `html.escape`; links só aceitam `https://` de Instagram e YouTube | `demo/app.py`, `storyboard.py` |
| Injeção de SQL | todas as consultas com valores externos usam parâmetros (`?`) | `storage.py`, `agent/tools.py` |
| Entradas abusivas no agente ou no servidor MCP | pergunta limitada a 500 caracteres, segmento e datas com formato fixo, até 5 criativos, filtros com valores fechados | `agent/schemas.py` |
| Caminhos de arquivo maliciosos em dados importados | código do post validado (`[A-Za-z0-9_-]`) antes de virar nome de arquivo | `collect/instagram.py` |
| Prompt injection via legendas de terceiros | o modelo não chama ferramentas nem escreve arquivos; a saída é validada por schema e os posts citados são filtrados contra a base | `agent/graph.py` |
| Gasto inesperado | coleta paga (Apify) só por comando explícito, com estimativa (`--dry-run`) e teto `maxTotalChargeUsd`; o servidor MCP não aciona coleta | `collect/apify.py`, `mcp_server.py` |
| Dependências | versões com limite superior em `pyproject.toml` e lock exato em `requirements.lock.txt` | |
| Execução de código | sem `eval`/`exec`/`pickle`; YAML com `safe_load`; subprocessos sem shell | |

Antes da publicação, o código passou por uma auditoria de segurança dedicada; os achados foram corrigidos e
estão cobertos por `tests/test_security.py`.

Para relatar uma vulnerabilidade, veja [SECURITY.md](../SECURITY.md).
