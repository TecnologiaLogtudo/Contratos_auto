# Análise da referência Contratos_auto

Coleta baseada no código em 30/09/2026, commit `918e2a8`. O grafo existente foi consultado, mas estava defasado (`c49482d`), portanto a confirmação foi feita diretamente nos arquivos atuais.

## Frontend encontrado

Stack: React 18, Vite 5 e Tailwind 4, com CSS semântico próprio. O aplicativo é uma SPA organizada em:

- `App.jsx`: estado global leve, carregamento de configuração/jobs, conexão em tempo real, toast e modal de screenshot;
- `Sidebar.jsx`: navegação, mini-card do lote ativo, conectividade e tema;
- `TabEmissao.jsx`: upload, pré-validação, início/pausa/retomada/cancelamento, itens e evidências;
- `TabHistorico.jsx`: busca, tabela de lotes, drawer de rastreio e download;
- `TabAdmin.jsx`: KPIs, falhas por fase, auditoria, sessões e inspeção de seletores;
- `StepperFases.jsx`: cinco fases operacionais;
- `TerminalLogs.jsx`: logs filtráveis e atualização ao vivo;
- `api.js` e `websocket.js`: REST, derivação de base path e reconexão.

Padrões visuais reaproveitados: fundo/superfícies em camadas, tokens semânticos, tipografia mono para IDs/logs, pills de estado, tabelas compactas, barra de progresso, terminal e navegação persistente. O novo template reproduz os padrões, mas não copia marca, nomes de fases nem regras de CT-e.

## Jornada funcional encontrada

1. Carregar planilha `.xlsx`/`.xls`.
2. Sanitizar, validar colunas e linhas e criar o job no SQLite.
3. Mostrar resumo de válidos, inválidos, já concluídos e pendentes.
4. Iniciar worker em thread dedicada com credenciais e parâmetros.
5. Processar itens sequencialmente usando Playwright.
6. Emitir logs e progresso por WebSocket; SSE também existe como alternativa.
7. Permitir pausa, retomada e cancelamento.
8. Persistir job, itens, logs e artefatos.
9. Expor histórico detalhado, evidências e relatório final para download.

## Funcionalidades periféricas encontradas

- SQLite thread-safe em WAL, foreign keys, busy timeout e transações;
- IDs sequenciais diários para jobs;
- worker desacoplado do request HTTP;
- broadcaster thread-safe para WebSocket e SSE;
- screenshots de erro, traces e planilha consolidada por job;
- retenção/limpeza de artefatos;
- endpoints de configuração e inspeção de seletores;
- healthcheck e readiness;
- Docker multi-stage, Nginx, volume persistente e dependência por healthcheck;
- suporte a subcaminho (`BASE_PATH`, `VITE_APP_BASE_PATH`, `VITE_API_BASE_URL`);
- testes de API, repositório, artefatos, parsing Excel e regras da automação.

## O que foi generalizado no template

- “cotação/CT-e” virou `reference/item/job`;
- cinco fases agora são configuráveis;
- campos de login e parâmetros são declarativos;
- a API ganhou um adaptador isolado;
- foi adicionado modo mock para prototipar sem backend;
- URLs não contêm marca nem subcaminho fixo;
- histórico, administração e tempo real permanecem como capacidades centrais.

## Pontos de atenção observados na referência

1. Configuração atual pode persistir e retornar `senha` em JSON; isso não deve ser replicado em produção.
2. CORS está como `allow_origins=["*"]` com credenciais; restrinja por ambiente.
3. As mesmas rotas são montadas em múltiplos prefixos por compatibilidade; um projeto novo deve escolher um contrato canônico.
4. Há helpers de formatação/status repetidos entre componentes; no template novo a duplicação foi reduzida sem criar uma biblioteca prematura.
5. O frontend original não possui suíte própria de testes; um projeto novo deve ao menos cobrir estado de execução, erros de API e reconexão.
6. A documentação rápida antiga descreve a UI desktop anterior e não representa integralmente a SPA atual.

## Fontes principais

- `web/src/App.jsx`
- `web/src/components/*`
- `web/src/services/api.js`
- `web/src/services/websocket.js`
- `web/src/styles.css`
- `backend/app/api/routes.py`
- `backend/app/infrastructure/{database,repository,worker,broadcaster,artifacts}.py`
- `frontend/{Dockerfile,nginx.conf}`
- `docker-compose.yml`
- `tests/*`
- `Docs/ARTIFACTS_ARCHITECTURE.md`
