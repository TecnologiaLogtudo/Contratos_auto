# Runbook de Deploy Coolify — Contratos_auto (UI v2)

> Avaliação da pendência do README/journal (2026-09-17). A stack Docker está
> pronta e validada localmente; o deploy no servidor Coolify exige acesso ao
> painel/SSH da VPS Logtudo e deve seguir o guia abaixo.

## Estado atual

- `docker-compose.yml`: backend (FastAPI + Playwright, expose 8000, healthcheck
  `/health/ready`) + frontend (nginx servindo build Vite em `/contratos/`,
  proxindo `/contratos/api|health|artifacts|ws` → backend, WS com Upgrade).
- `frontend/Dockerfile`: build multi-stage `node:20-alpine` → `nginx:1.27-alpine`,
  build args `VITE_APP_BASE_PATH=/contratos/`, `VITE_API_BASE_URL=/contratos`.
- `backend/app/main.py` já monta `BASE_PATH` (padrão `/contratos`) e injeta
  `window.LOGTUDO_BASE_PATH`.

## Validação local (2026-09-17, Docker 29.7.2 / Compose v5.4.0)

`docker compose build` OK (frontend + backend). `docker compose up -d`:

- ambos os containers `healthy` (healthchecks do compose passando);
- `GET /contratos/` → 200 (HTML servido no subpath);
- `GET /contratos/health/ready` → `{"status":"ready"}`;
- `GET /contratos/api/config` → 200 (proxy → backend:8000 sem prefixo);
- refresh de rota interna `/contratos/<rota>` → 200 (SPA fallback `try_files`).

## Checklist no Coolify (quando autorizado o deploy na VPS)

1. Criar recurso **Docker Compose** apontando para
   `TecnologiaLogtudo/Contratos_auto` (branch `main`).
2. Env vars do serviço: `BASE_PATH=/contratos` (backend), build args do
   frontend já têm default `/contratos/` no compose; definir
   `AUTOMACAO_LOGIN`/`AUTOMACAO_SENHA`/`ADMIN_RESET_PASSWORD` como secrets
   (nunca hardcoded).
3. Domínio no Coolify: `https://automacao.logtudo.com.br/contratos` (ou domínio
   dedicado), garantindo que o proxy de borda **não** redirecione `/contratos/*`
   para `/` e preserve `Upgrade/Connection` (WS) — ver
   `Docs/GUIA_DEPLOY_SUBPATH_VPS.md` (seção 9: com `StripPrefix` ou sem, o
   backend/nginx cobrem os dois cenários).
4. Nada de `ports:` no host — o compose já usa `expose` apenas (padrão Coolify).
5. Healthcheck do Coolify: apontar para `/contratos/health/ready` no frontend.
6. Playwright: o backend precisa de `ipc: host` + seccomp já presentes no
   compose; conferir se a VPS roda o container com os mesmos `security_opt`.
7. Pós-deploy, rodar os 8 checks da seção 5 do `GUIA_DEPLOY_SUBPATH_VPS.md`
   (HTML, assets, health, POST api, WS handshake, refresh, download, CORS).

## Observação sobre credenciais do portal

`config.ini` no repo contém login/senha do portal e-Login (`Atualizarbi`).
Em produção no Coolify, usar env vars `AUTOMACAO_LOGIN`/`AUTOMACAO_SENHA`
(já suportadas pelo compose) e tratar `config.ini` como fallback dev apenas.
