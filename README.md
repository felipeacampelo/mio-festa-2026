# Mio Festa 2026

Sistema simples de venda de ingressos para festa junina com:

- landing page publica
- checkout sem login
- PIX e cartao com o mesmo valor
- tickets nominados com QR code
- consulta publica do pedido
- login admin por token
- tela admin de pedidos, reenvio, edicao e transferencia
- check-in com camera e fallback manual

## Estrutura

- `backend/`: Django + DRF
- `frontend/`: React + Vite

## Backend

```bash
cd /Users/felipecampelo/Mio-Festa-2026
cp .env.example .env
python3 -m pip install -r backend/requirements.txt
python3 backend/manage.py migrate
python3 backend/manage.py createsuperuser
python3 backend/manage.py runserver
```

Para produção no Railway, o backend usa:

- `DATABASE_URL` para Postgres
- `gunicorn` para iniciar a aplicação
- `whitenoise` para servir arquivos estáticos
- `backend/Procfile`
- `backend/railway.json`

## Frontend

```bash
cd /Users/felipecampelo/Mio-Festa-2026/frontend
npm install
npm run dev
```

## Endpoints principais

- `GET /api/events/current/`
- `POST /api/orders/checkout/`
- `POST /api/orders/lookup/`
- `GET /api/orders/<public_id>/?access_token=...`
- `POST /api/auth/login/`
- `POST /api/checkin/scan/`
- `POST /api/checkin/manual/`
- `GET /api/admin/orders/`
- `GET /api/admin/tickets/`

## Validacoes executadas

- `python3 backend/manage.py check`
- `python3 backend/manage.py makemigrations`
- `python3 backend/manage.py migrate`
- `python3 backend/manage.py test apps.orders.tests`
- `npm run build`

## Variáveis de ambiente

Use `.env.example` como base para configurar:

- Django
- URLs do frontend/backend
- Asaas
- Resend
- Postgres (`DATABASE_URL`)
- CORS / CSRF para a URL pública
- Asaas usa `ASAAS_ENV=sandbox` ou `ASAAS_ENV=production`; `ASAAS_BASE_URL` é opcional para sobrescrever manualmente.
- Em produção, `ASAAS_API_KEY` é obrigatório. Sem chave, o checkout falha e nenhum pedido é criado.
- A confirmação manual de pagamento fica desabilitada por padrão; use `ALLOW_MANUAL_PAYMENT_CONFIRMATION=true` apenas em ambiente controlado.

## Regras operacionais

- Apenas pagamento confirmado consome vaga.
- Pedidos pendentes ficam registrados para auditoria, mas não reservam capacidade.
- Se duas pessoas iniciarem pagamento para a última vaga, a vaga fica com quem tiver o pagamento confirmado primeiro.
- Ingressos só são emitidos após confirmação de pagamento.
- Webhooks repetidos não reenviam ingressos se o pagamento já estiver confirmado.
- O admin lista pedidos e ingressos com paginação de 50 registros por página.

## Procedimento se webhook falhar

1. Abrir o pedido no admin pela busca usando nome, e-mail ou código do pedido.
2. Clicar em `Sincronizar` para consultar o status atual diretamente no Asaas.
3. Se o Asaas retornar pagamento confirmado, o sistema marca o pedido como pago e ativa os ingressos.
4. Após a ativação, usar `Reenviar` se o comprador ou participante não recebeu o e-mail.
5. Conferir os logs do Railway filtrando por `apps.payments` para investigar falhas de webhook ou requisições rejeitadas.

## Logs de pagamento

Os logs da integração com Asaas são emitidos no logger `apps.payments` e incluem:

- criação de cobrança
- confirmação de pagamento
- expiração de pagamento
- sincronização manual
- falhas de requisição ao Asaas
- webhooks inválidos ou desconhecidos

## Railway

Dois serviços no mesmo projeto: `backend` (Django) e `frontend` (build estático servido por `serve`).

### Backend

- Root Directory: `backend`
- Build/Start command: não precisa configurar nada no dashboard — `backend/railway.json` já define o start
  (`migrate` → `bootstrap_admin` → `collectstatic` → `gunicorn`)
- Criar um banco Postgres no projeto e ligar `DATABASE_URL` a ele
- Variáveis obrigatórias: `DJANGO_SECRET_KEY` (gerar uma nova), `DJANGO_ALLOWED_HOSTS`,
  `FRONTEND_URL`, `BACKEND_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
  `ASAAS_ENV=production`, `ASAAS_API_KEY`, `ASAAS_WEBHOOK_TOKEN`
- Variáveis que têm default de dev e precisam virar produção: `DJANGO_DEBUG=false`,
  `CORS_ALLOW_ALL_ORIGINS=false`, `DJANGO_SECURE_SSL_REDIRECT=true`,
  `DJANGO_SESSION_COOKIE_SECURE=true`, `DJANGO_CSRF_COOKIE_SECURE=true`
- Acesso ao admin: como o Railway não expõe shell/CLI para rodar `createsuperuser` manualmente,
  preencha `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD` —
  o `bootstrap_admin` cria o superuser automaticamente no primeiro start (é idempotente, não
  recria se já existir um superuser)
- Opcionais: `RESEND_API_KEY`/`DEFAULT_FROM_EMAIL` (sem `RESEND_API_KEY` os e-mails caem no
  backend de console), `ALLOW_MANUAL_PAYMENT_CONFIRMATION` (manter `false`)

### Frontend

- Root Directory: `frontend`
- Build command: `npm run build` (já em `frontend/railway.json`)
- Start command: `npm run start`, que roda `serve -s dist -l $PORT` (já em `frontend/Procfile` / `frontend/railway.json`)
- Variável obrigatória: `VITE_API_URL` apontando para a URL pública do backend (ex.: `https://seu-backend.up.railway.app/api`) —
  é lida em build time, então precisa estar setada antes do `npm run build` rodar
