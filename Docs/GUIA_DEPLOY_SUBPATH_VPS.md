# Guia de Deploy em Subpath na VPS

## Objetivo
Este guia explica por que a URL `https://automacao.logtudo.com.br/NotasCompensadas-FBL1/` funciona neste projeto e como replicar o mesmo padrão em futuros sistemas, evitando:
- redirecionamento para o domínio principal
- tela branca no frontend
- 404/502 em API e WebSocket

## 1) Visão Geral do Problema (subpath vs raiz do domínio)
Quando uma aplicação é publicada em subpath (ex.: `/NotasCompensadas-FBL1/`) e não na raiz (`/`), frontend, servidor web, proxy e backend precisam concordar no mesmo prefixo.

Se qualquer camada usar caminho de raiz por engano (`/api`, `/assets`, `/ws`) sem considerar o subpath, surgem sintomas como:
- HTML abre, mas JS/CSS quebram (tela branca)
- refresh em rota interna retorna 404
- API responde em URL errada
- WS não conecta
- proxy externo redireciona para home do domínio

Regra principal: o mesmo subpath deve ser respeitado em build, assets, SPA fallback e proxy de API/WS.

## 2) Diagnóstico do Projeto Atual (o que faz funcionar)

### 2.1 Variáveis críticas e responsabilidades

| Variável | Onde aparece | Responsabilidade |
|---|---|---|
| `VITE_APP_BASE_PATH` | `docker-compose.yml`, `frontend/Dockerfile`, `frontend/vite.config.ts`, frontend runtime | Define base do app/frontend (assets + paths do app) |
| `VITE_API_BASE_URL` | `docker-compose.yml`, `frontend/Dockerfile`, `frontend/src/api/client.ts` | Define base HTTP para chamadas de API |
| `VITE_WS_BASE_URL` | `docker-compose.yml`, `frontend/Dockerfile`, `frontend/src/App.tsx` | Override opcional de WS; vazio usa host atual + subpath |
| `ALLOWED_ORIGINS` | `docker-compose.yml`, `backend/app/config.py`, `backend/app/main.py` | CORS permitido pelo backend |

### 2.2 Lógica que garante funcionamento no subpath

1. `frontend/vite.config.ts`
- `base: process.env.VITE_APP_BASE_PATH ?? "/"`
- Resultado: build do Vite publica assets com prefixo correto (`/NotasCompensadas-FBL1/...`) em vez de raiz.

2. `frontend/Dockerfile`
- Recebe `ARG`/`ENV` de `VITE_APP_BASE_PATH`, `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`.
- Copia build para `/usr/share/nginx/html/NotasCompensadas-FBL1/`.
- Resultado: arquivos estáticos servidos no mesmo subpath esperado pelo build.

3. `frontend/nginx.conf`
- `location /NotasCompensadas-FBL1/ { try_files $uri $uri/ /NotasCompensadas-FBL1/index.html; }`
- Resultado: SPA fallback correto (inclusive em refresh direto).
- Blocos com `rewrite` para:
  - `/NotasCompensadas-FBL1/api/`
  - `/NotasCompensadas-FBL1/ws/`
  - `/NotasCompensadas-FBL1/health/`
- Resultado: remove prefixo antes de enviar ao backend, que expõe rotas em `/api`, `/ws`, `/health`.
- Blocos fallback sem prefixo (`/api`, `/ws`, `/health`).
- Resultado: funciona também se proxy externo fizer strip de prefixo.

4. `frontend/src/api/client.ts`
- `API_BASE_URL = VITE_API_BASE_URL ?? VITE_APP_BASE_PATH`
- `axios.create({ baseURL: API_BASE_URL })`
- Resultado: requisições para `/api/...` são montadas dentro do subpath quando configurado.

5. `frontend/src/App.tsx`
- Se `VITE_WS_BASE_URL` estiver vazio, monta WS como:
  - `wss://<host><normalizedBasePath>/ws/jobs/<jobId>`
- Resultado: WebSocket segue automaticamente o mesmo subpath da aplicação.

6. `docker-compose.yml`
- Defaults:
  - `VITE_APP_BASE_PATH=/NotasCompensadas-FBL1/`
  - `VITE_API_BASE_URL=/NotasCompensadas-FBL1/`
  - `VITE_WS_BASE_URL=` (vazio)
- Healthcheck do frontend em `/NotasCompensadas-FBL1/health/ready`.
- Resultado: validação operacional alinhada ao subpath real.

## 3) Padrão Reutilizável para Futuros Projetos

### 3.1 Regra de ouro
Use o mesmo subpath em todas as camadas:
- build frontend
- caminhos de assets
- fallback da SPA
- proxy de API
- proxy de WebSocket

Se uma camada usar `/` enquanto outra usa `/MeuApp/`, haverá quebra intermitente ou total.

### 3.2 URLs absolutas: quando evitar e quando usar
Evitar no frontend (salvo decisão explícita):
- `/api`
- `/ws`
- `/assets`

Preferir base configurável por variável (`VITE_*`) e composição por ambiente.

Use domínio dedicado para API/WS apenas quando for arquitetura intencional (ex.: `api.seudominio.com`), e nesse caso configure:
- `VITE_API_BASE_URL=https://api.seudominio.com`
- `VITE_WS_BASE_URL=wss://api.seudominio.com`

### 3.3 Contrato mínimo de proxy interno (Nginx do app)
Para app em `/MeuApp/`:
- `try_files` com fallback para `/MeuApp/index.html`
- rotas `/MeuApp/api`, `/MeuApp/ws`, `/MeuApp/health`
- `rewrite` removendo prefixo antes de enviar ao backend
- headers de WS (`Upgrade` e `Connection`) preservados

### 3.4 Dependência externa (proxy de borda: Coolify/Traefik/Nginx host)
Garanta que o proxy de borda:
- não redirecione `/MeuApp/*` para `/`
- preserve ou faça strip de prefixo de forma consistente com o proxy interno
- encaminhe corretamente Upgrade/Connection para WS

## 4) Matriz de Sintomas x Causa Raiz x Correção

| Sintoma | Causa raiz provável | Correção |
|---|---|---|
| Tela branca após abrir URL | `base` do Vite incorreto (assets apontando para `/`) | Ajustar `VITE_APP_BASE_PATH` e rebuildar frontend |
| 404 em refresh de rota SPA | `try_files` sem fallback para `index.html` no subpath | Corrigir fallback para `/MeuApp/index.html` |
| API 404/502 em subpath | Falta de `rewrite` do prefixo no Nginx | Adicionar rewrite para `/MeuApp/api/* -> /api/*` |
| WS não conecta | URL WS sem subpath ou sem headers de upgrade | Ajustar montagem WS e headers `Upgrade`/`Connection` |
| URL cai na home do domínio | Proxy de borda redirecionando path não mapeado | Criar regra explícita para `/MeuApp/*` no proxy externo |
| CORS bloqueando chamadas | `ALLOWED_ORIGINS` sem domínio correto | Incluir origem real do frontend no backend |

## 5) Checklist de Deploy (8 checks)

1. HTML
- `GET https://automacao.logtudo.com.br/NotasCompensadas-FBL1/` retorna 200.

2. Assets JS/CSS
- Arquivos carregam com prefixo `/NotasCompensadas-FBL1/` e sem 404.

3. Health
- `GET /NotasCompensadas-FBL1/health/ready` retorna `{"status":"ready"}`.

4. POST API
- `POST /NotasCompensadas-FBL1/api/process` responde sem erro de rota/proxy.

5. WS Handshake
- `wss://.../NotasCompensadas-FBL1/ws/...` conecta e recebe mensagens.

6. Refresh de rota interna
- Recarregar página interna da SPA não retorna 404.

7. Download de arquivo
- Download (`/api/process/{job_id}/download/...`) funciona via subpath.

8. CORS
- Origem do frontend permitida (`ALLOWED_ORIGINS`) no backend.

## 6) Checklist de Troubleshooting Rápido

1. Confirmar variáveis de build do frontend (`VITE_APP_BASE_PATH`, `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`).
2. Confirmar pasta de publicação do build no Nginx (`/usr/share/nginx/html/<subpath>/`).
3. Confirmar `try_files` para `<subpath>/index.html`.
4. Confirmar `rewrite` de `<subpath>/api|ws|health` para backend.
5. Confirmar headers de WS (`Upgrade`/`Connection`).
6. Confirmar regras do proxy externo para `<subpath>/*`.
7. Confirmar `ALLOWED_ORIGINS` no backend.
8. Revalidar em navegador (Network tab) procurando 301/302 indevidos e 404 de assets.

## 7) Cenários de Validação

### Cenário feliz
- Abrir `https://automacao.logtudo.com.br/NotasCompensadas-FBL1/`.
- Carregar estáticos sem 404.
- API responder em `/NotasCompensadas-FBL1/api/...`.
- WS conectar em `/NotasCompensadas-FBL1/ws/...`.

### Falhas comuns esperadas
- Tela branca por `base` incorreto no Vite.
- 404 em refresh da SPA por `try_files` incorreto.
- API 404/502 por ausência de `rewrite` do prefixo.
- WS falhando por URL sem subpath ou sem `Upgrade/Connection`.
- Redirecionamento para domínio principal por regra externa sem exceção do path.

## 8) Referências diretas deste projeto
- `docker-compose.yml`
- `frontend/vite.config.ts`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx`
- `backend/app/config.py`
- `backend/app/main.py`

## 9) Aplicação prática neste projeto (`/contratos`)

### 9.1 Regras aplicadas no `docker-compose.yml`
- `BASE_PATH=/contratos`
- Build args frontend:
  - `VITE_APP_BASE_PATH=/contratos/`
  - `VITE_API_BASE_URL=/contratos`
- Traefik com rota explícita:
  - `Host(...) && PathPrefix(/contratos)`
- Middleware de borda:
  - `StripPrefix(/contratos)` habilitado

### 9.2 Contrato esperado com Traefik/Coolify
- Com `StripPrefix` ativo, backend recebe caminhos sem `/contratos` (ex.: `/api/config`), mas mantém `root_path` compatível.
- Sem `StripPrefix`, backend também funciona via middleware interno que remove `/contratos` quando presente.
- Em ambos os casos, frontend buildado em subpath deve publicar assets com prefixo `/contratos/assets/...`.

---
Este documento é operacional e pode ser reutilizado como template em qualquer app SPA + API publicado em subpath na VPS.
