# Política de segurança

## Como relatar uma vulnerabilidade

Não abra uma issue pública. Use o relato privado do GitHub em
**Security › Report a vulnerability** neste repositório, com:

- descrição do problema e do impacto;
- passos para reproduzir;
- arquivo e linha, se souber.

A resposta inicial sai em até 5 dias úteis.

## Segredos

- Chaves de API ficam só no `.env` local, que nunca é versionado (`.env.example` é o modelo, sem valores).
- Se uma chave vazar, revogue-a no provedor (Google Cloud, Google AI Studio, OpenRouter, Apify) antes de qualquer outra ação.
- O repositório não contém dados brutos, texto de terceiros nem logs de execução.
  Ver [docs/DADOS_PRIVACIDADE_E_SEGURANCA.md](docs/DADOS_PRIVACIDADE_E_SEGURANCA.md).
