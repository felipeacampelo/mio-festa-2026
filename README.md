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

## Logs de pagamento

Os logs da integração com Asaas são emitidos no logger `apps.payments` e incluem:

- criação de cobrança
- confirmação de pagamento
- expiração de pagamento
- sincronização manual
- falhas de requisição ao Asaas
- webhooks inválidos ou desconhecidos

## Railway

Checklist mínima para o deploy no Railway:

- criar banco Postgres no projeto
- preencher `DATABASE_URL`
- preencher `DJANGO_ALLOWED_HOSTS`
- preencher `FRONTEND_URL` e `BACKEND_URL`
- preencher `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS`
- preencher `ASAAS_API_KEY` e `ASAAS_WEBHOOK_TOKEN`
- rodar migrations no deploy ou manualmente após o primeiro deploy
