# AI-GOV.NETWORK

Landing page em Flask, servida com gunicorn e publicada no Railway a partir de `main` (https://www.ai-gov.network/).

## Webhooks da Meta

Callback URL:

https://www.ai-gov.network/webhooks/meta

Variáveis de ambiente (definir no Railway; não commitar os valores):

- `META_VERIFY_TOKEN` — token escolhido por nós e copiado para o painel da app Meta. No GET de verificação, a resposta é o `hub.challenge` (`text/plain`, 200) apenas quando `hub.mode` é `subscribe` e `hub.verify_token` coincide com este valor (comparação em tempo constante). Caso contrário, ou se a variável não estiver definida, a resposta é 403.
- `META_APP_SECRET` — App Secret da app Meta. No POST, o cabeçalho `X-Hub-Signature-256` tem de ser `sha256=` seguido do HMAC-SHA256 do corpo bruto do pedido. Assinatura em falta ou inválida, ou variável ausente, responde 403.

O endpoint recebe mensagens WhatsApp Business (`whatsapp_business_account`), mensagens Instagram (`instagram`), Lead Ads (`page` com o campo `leadgen`) e alterações ao catálogo de produtos. Não há login nem CSRF: a autenticação é o token de verificação e a assinatura. A rota não entra no sitemap nem na navegação.

# Exemplo de commit de ficheiros alterados

git add app.py
git commit -m "Set new flask behaviour"
git push
