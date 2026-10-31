# Graph Report - Contratos_auto  (2026-10-30)

## Corpus Check
- 116 files · ~135,292 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 6, .conf 2, .css 2)

## Summary
- 1290 nodes · 2546 edges · 79 communities (63 shown, 11 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 163 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `8143c006`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AutomationManager
- Any
- ExcelProcessor
- BaseCompany
- lactalis_strategy.py
- JobRepository
- AutomacaoUI
- BaseStrategy
- wait_for_valid_select_options
- JobBroadcaster
- get_company
- errors.py
- web/package.json
- ContractRunner
- Database
- contract_runner.py
- fase1_processamento.py
- LoginPage
- worker.py
- ItemContrato
- PlaywrightVPSClient
- LactalisSpecialBaseCompany
- report_exception
- ArtifactManager
- web-automation-interface/src/App.jsx
- fechar_popups_alerta
- TabEmissao.jsx
- TabHistorico.jsx
- test_tracing.py
- FretePage
- TabAdmin.jsx
- repository.py
- app/main.py
- web/src/App.jsx
- LactalisBaseCompany
- LactalisDiariaParadaCompany
- .detectar_erro_negocio
- test_item_watchdog.py
- JobSocket
- Guia de Deploy em Subpath na VPS
- Sidebar.jsx
- web/src/services/api.js
- .to_row_nao_realizado
- test_session_recovery.py
- .__init__
- .create_job
- app/__init__.py
- SessionRecoveryManager
- web-automation-interface/package.json
- test_api_endpoints.py
- observability.py
- routes.py
- Arquitetura de Artefatos — Logs, Screenshots, Traces e Exports
- Ops Brain
- fase4_frete.py
- LactalisBaseStrategy
- Contrato mínimo do backend
- selectors.py
- Traces do piloto Contratos de frete
- Análise da referência Contratos_auto
- Regras Globais do Codex - Ops Brain
- Checklist para uma nova interface
- Template de Interface para Automação Web
- ManualTimer
- Conectividade Playwright para VPS
- Incidentes — Contratos de frete
- Runbook de Deploy Coolify — Contratos_auto (UI v2)
- span_api
- .update_item_result
- preencher_formulario
- test_worker_watches_only_the_item_call
- websocket_job_stream
- .get_fim_viagem
- Aviso de duração por cotação

## God Nodes (most connected - your core abstractions)
1. `ItemContrato` - 96 edges
2. `ContractRunner` - 40 edges
3. `ExcelProcessor` - 39 edges
4. `BaseStrategy` - 39 edges
5. `JobRepository` - 39 edges
6. `AutomationManager` - 38 edges
7. `ItemStatus` - 31 edges
8. `FretePage` - 31 edges
9. `BaseCompany` - 29 edges
10. `FormFillError` - 27 edges

## Surprising Connections (you probably didn't know these)
- `trace_span()` --calls--> `use_span()`  [INFERRED]
  backend/app/infrastructure/tracing.py → tests/test_tracing.py
- `TestCidadeOrigem` --uses--> `DPACompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/dpa.py
- `TestCidadeOrigem` --uses--> `LactalisDiariaParadaCompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/lactalis.py
- `TestCidadeOrigem` --uses--> `LactalisSpecialBaseCompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/lactalis.py
- `test_fluxo_erro_negocio_motivo_na_planilha()` --uses--> `SubmissionError`  [INFERRED]
  tests/test_erro_negocio_portal.py → backend/app/domain/errors.py

## Import Cycles
- None detected.

## Communities (79 total, 11 thin omitted)

### Community 0 - "AutomationManager"
Cohesion: 0.06
Nodes (23): AutomationConfig, JobInfo, JobStatus, LogEvent, PreviewResponse, BaseModel, AutomationManager, init_db() (+15 more)

### Community 1 - "Any"
Cohesion: 0.10
Nodes (22): clear_logs_endpoint(), debug_artifacts(), download_artifact(), get_config(), get_job_artifacts(), get_log_session(), list_log_sessions(), Any (+14 more)

### Community 2 - "ExcelProcessor"
Cohesion: 0.06
Nodes (45): ExcelProcessor, padronizar_cidade(), PreValidationReport, processar_cidade_uf(), processar_nome_placa(), Any, Path, Manipulador de planilhas in-memory com sanitização BSoft integrada e… (+37 more)

### Community 3 - "BaseCompany"
Cohesion: 0.05
Nodes (23): BaseCompany, Page, Retorna True se o remetente bater com este cliente., Executa a sincronização de remetente e destinatário no Playwright., Retorna o valor da Regra de Frete (select dados_regraFrete_id)., Passo opcional 8.5 na Fase 4 para preencher frete terceiros., Retorna o valor para o campo dados_observacaoPV na Fase 4. Por padrão usa…, Permite preencher campos adicionais/específicos na Fase 4. (+15 more)

### Community 4 - "lactalis_strategy.py"
Cohesion: 0.13
Nodes (17): DPAStrategy, Estratégia dedicada para DPA (Dairy Partners)., extrair_numero_nf(), LactalisDiariaGarantidaStrategy, LactalisDiariaParadaStrategy, LactalisPernoiteStrategy, Extrai o número da Nota Fiscal a partir da observação com regex flexível., Estratégia Lactalis: Diária Parado. (+9 more)

### Community 5 - "JobRepository"
Cohesion: 0.08
Nodes (19): JobRepository, Atualiza o estado global de um Job., Implementa o padrão Repository para operações no SQLite., Recupera metadados completos de um Job., Lista jobs ordenados por data decrescente., Lista todos os itens de um job específico., Atualiza o nome do operador (usuário) do Job., Grava uma entrada de log estruturado para o Job com horário local. (+11 more)

### Community 6 - "AutomacaoUI"
Cohesion: 0.10
Nodes (19): AutomacaoUI, get_resource_path(), Lê o config.ini e preenche os campos da UI., Salva os campos da UI no config.ini., Retorna o caminho absoluto para um recurso, funcionando em dev e no PyInstaller., Envia uma mensagem de log para a fila., Inicia o loop que consome a fila de log e atualiza a UI., Loga a mudança de aba e salva as configurações ao sair da aba de config. (+11 more)

### Community 7 - "BaseStrategy"
Cohesion: 0.07
Nodes (20): NavigationError, Falha de navegação, timeout de URL ou bloqueio de rota., ConhecimentoPage, Page, Page Object para a Fase 3 - Preenchimento Básico do Conhecimento., BaseStrategy, Contrato base para estratégias polimórficas de clientes/remetentes., Retorna True se a estratégia for aplicável ao remetente da planilha. (+12 more)

### Community 8 - "wait_for_valid_select_options"
Cohesion: 0.17
Nodes (5): wait_for_valid_select_options(), FakeOption, FakeOptions, FakeSelect, test_wait_for_valid_select_options_waits_until_matching_option()

### Community 9 - "JobBroadcaster"
Cohesion: 0.09
Nodes (16): AbstractEventLoop, JobBroadcaster, Any, WebSocket, Broadcaster e gerenciador de conexões WebSocket para logs e eventos em tempo…, Registra o log no banco SQLite e agenda o broadcast assíncrono para WebSockets…, Emite evento de atualização de progresso para a UI de forma thread-safe., Gerencia conexões WebSocket e SSE ativas por Job e emite logs estruturados com… (+8 more)

### Community 10 - "get_company"
Cohesion: 0.18
Nodes (6): get_company(), _remover_acentos(), LatamCompany, Page, Regra atual da LATAM: Destinatário é cópia do Remetente quando houver CNPJ; sem…, TestCidadeOrigem

### Community 11 - "errors.py"
Cohesion: 0.18
Nodes (12): AuthenticationError, AutomationError, Exception, QuoteExtractionError, Erro de validação ou leitura na planilha de entrada (dados faltantes ou…, Falha de login, credenciais inválidas ou timeout no 2FA., Falha na extração de dados da cotação no portal (Pedido, NF ou Status não…, Falha ao salvar o contrato de frete ou na aprovação de contingência de CFOP. (+4 more)

### Community 12 - "web/package.json"
Cohesion: 0.08
Nodes (24): tailwindcss, @tailwindcss/vite, allowScripts, esbuild@0.21.5, dependencies, react, react-dom, devDependencies (+16 more)

### Community 13 - "ContractRunner"
Cohesion: 0.12
Nodes (16): ExecutionSummary, Resumo consolidado do processamento do arquivo., ContractRunner, Exception, Sincroniza todas as instâncias de Page Objects com a página ativa atual., Processa um único item/cotação pelas Fases 2 a 5 de forma isolada., Fecha o navegador e limpa instâncias., Recupera a integridade da sessão após erro. Utiliza o SessionRecoveryManager… (+8 more)

### Community 14 - "Database"
Cohesion: 0.16
Nodes (9): Database, Path, Fecha conexão da thread atual., Gerenciador de conexão SQLite thread-safe com suporte a WAL mode e busy timeout., Obtém uma conexão isolada por thread., Context manager transacional atômico., Cria as tabelas caso não existam., Connection (+1 more)

### Community 15 - "contract_runner.py"
Cohesion: 0.10
Nodes (21): ItemResult, ItemStatus, Enum, str, Resultado da execução de um único contrato., DialogGuard, Guardião e interceptor ativo de diálogos, popups modais (jQuery UI,…, CotacoesPage (+13 more)

### Community 16 - "fase1_processamento.py"
Cohesion: 0.17
Nodes (20): _get_merged_cell_value(), _ler_com_openpyxl(), _ler_com_xlrd(), _padronizar_cidade(), _processar_cidade_uf(), _processar_nome_placa(), processar_planilha(), _processar_remetente() (+12 more)

### Community 17 - "LoginPage"
Cohesion: 0.15
Nodes (17): BrowserConfig, BrowserFactory, Browser, BrowserContext, Page, Fábrica responsável por instanciar e configurar o navegador Playwright., LoginPage, Page (+9 more)

### Community 18 - "worker.py"
Cohesion: 0.10
Nodes (14): JobWorker, Path, Worker orquestrador de execução em background em Thread dedicada., Gerencia a execução assíncrona de um lote via Thread dedicada., Gerenciador central de instâncias de workers. Permite múltiplos jobs…, Retorna o worker ativo do usuário, se houver., Retorna todos os workers atualmente em execução., Cria e dispara um novo worker para o Job. Permite múltiplos jobs paralelos de… (+6 more)

### Community 19 - "ItemContrato"
Cohesion: 0.10
Nodes (13): ItemContrato, BaseModel, Representação tipada e validada de uma linha da planilha de contratos., ContratoPage, Page, Page Object para a Fase 5 - Emissão e Finalização do Contrato de Frete., Valor a ser preenchido no campo dados_complementoPedido., Monta o texto para a observação PV (Fase 4). Padrão: 'Nome - Placa'. (+5 more)

### Community 20 - "PlaywrightVPSClient"
Cohesion: 0.16
Nodes (11): launch_browser(), perform_login(), any, Browser, BrowserContext, Page, Inicia o Playwright e o navegador configurado., Abre uma nova página (ou usa uma existente), realiza o login e navega para a… (+3 more)

### Community 23 - "ArtifactManager"
Cohesion: 0.15
Nodes (12): ArtifactManager, Path, Executa limpeza de traces e vídeos temporários com idade superior a…, Gerencia ciclo de vida, diretórios e limpeza de arquivos gerados por execuções., Retorna o diretório base para um Job específico, criando se necessário., Retorna o diretório de screenshots de erro para o Job., Retorna o diretório de traces e vídeos Playwright para o Job., Salva screenshot capturado no momento da falha e registra no repositório. (+4 more)

### Community 24 - "web-automation-interface/src/App.jsx"
Cohesion: 0.08
Nodes (22): AdminPanel(), save(), App(), notify(), openJob(), refreshJobs(), ExecutionPanel(), action() (+14 more)

### Community 25 - "fechar_popups_alerta"
Cohesion: 0.13
Nodes (21): LactalisPernoiteCompany, esperar_e_fechar_popups(), fechar_popups_alerta(), Page, Verifica se há popups, caixas de diálogo ou modais visíveis na tela (jQuery UI…, Executa verificação periódica por um breve período para capturar popups que…, Encontra a linha correspondente na aba 'Dados Processados', atualiza o status…, Encontra a planilha de output e registra uma linha na aba 'Contrato não… (+13 more)

### Community 26 - "TabEmissao.jsx"
Cohesion: 0.16
Nodes (5): FASES, StepperFases(), statusLabel(), TabEmissao(), TerminalLogs()

### Community 27 - "TabHistorico.jsx"
Cohesion: 0.22
Nodes (8): fmtBytes(), fmtDate(), fmtDur(), JobDetailDrawer(), labelFor(), pillFor(), shortId(), TabHistorico()

### Community 28 - "test_tracing.py"
Cohesion: 0.12
Nodes (25): main(), Manual synthetic acceptance test; never imported to send data by pytest., _configuration(), current_trace_ids(), flush_traces(), init_tracing(), mark_error(), Optional, manually scoped traces. No ERP payloads or automatic instrumentation. (+17 more)

### Community 29 - "FretePage"
Cohesion: 0.16
Nodes (8): FormFillError, Falha ao preencher campos, selecionar dropdowns ou avançar etapas do formulário., Detecta e fecha de forma resiliente modais jQuery UI, SweetAlert e overlays de…, Acessa a listagem de cotações, filtra pela cotação/Ravex, abre detalhes e…, FretePage, Page, Page Object para a Fase 4 - Dados do Frete, Motorista e Veículo., Executa a autenticação e aguarda o redirecionamento.

### Community 30 - "TabAdmin.jsx"
Cohesion: 0.21
Nodes (6): fmtDur(), jobPill(), jobStatusLabel(), shortId(), TabAdmin(), VisaoGeral()

### Community 31 - "repository.py"
Cohesion: 0.21
Nodes (4): Gerenciador de armazenamento, registro e retenção de artefatos do…, Módulo de conexão e gerenciamento de esquema SQLite para o Contratos_auto., Repositório unificado SQLite para Jobs, Itens, Logs e Artefatos do…, Testes unitários para o gerenciador de artefatos e política de retenção.

### Community 32 - "app/main.py"
Cohesion: 0.24
Nodes (13): shutdown_tracing(), health(), health_ready(), on_shutdown(), on_startup(), get, Inicializa banco SQLite e loop de eventos para o broadcaster., _render_index_html() (+5 more)

### Community 33 - "web/src/App.jsx"
Cohesion: 0.43
Nodes (3): App(), ScreenshotModal(), Toast()

### Community 34 - "LactalisBaseCompany"
Cohesion: 0.12
Nodes (3): DPACompany, Page, LactalisBaseCompany

### Community 36 - ".detectar_erro_negocio"
Cohesion: 0.29
Nodes (5): Page, Detecta o alerta genérico de erro de negócio do portal e-Login (div.rotina-…, Verifica e fecha popups repetidamente durante um breve intervalo., test_detectar_erro_negocio_extrai_motivo(), test_detectar_erro_negocio_sem_alerta_retorna_none()

### Community 37 - "test_item_watchdog.py"
Cohesion: 0.13
Nodes (23): ItemExecutionDelayed, ItemExecutionFinishedAfterDelay, Advisory duration warning around one active item; never retries ERP work., An active item exceeded the advisory duration limit, not proof of deadlock., The prolonged call ended; this does not imply successful issuance., _report(), warning_seconds(), watch_item() (+15 more)

### Community 39 - "Guia de Deploy em Subpath na VPS"
Cohesion: 0.09
Nodes (21): 1) Visão Geral do Problema (subpath vs raiz do domínio), 2.1 Variáveis críticas e responsabilidades, 2.2 Lógica que garante funcionamento no subpath, 2) Diagnóstico do Projeto Atual (o que faz funcionar), 3.1 Regra de ouro, 3.2 URLs absolutas: quando evitar e quando usar, 3.3 Contrato mínimo de proxy interno (Nginx do app), 3.4 Dependência externa (proxy de borda: Coolify/Traefik/Nginx host) (+13 more)

### Community 40 - "Sidebar.jsx"
Cohesion: 0.36
Nodes (7): hasJobActivity(), shortId(), Sidebar(), statusLabel(), ThemeContext, ThemeProvider(), useTheme()

### Community 42 - ".to_row_nao_realizado"
Cohesion: 0.40
Nodes (3): Any, Gera a linha para a aba 'Dados Processados'., Gera a linha para a aba 'Contrato não realizado'.

### Community 43 - "test_session_recovery.py"
Cohesion: 0.20
Nodes (13): HealthCheckResult, Enum, str, RecoveryStage, RecoveryStatus, fixture, recovery_manager(), test_login_page_logout() (+5 more)

### Community 44 - ".__init__"
Cohesion: 0.50
Nodes (3): Any, Event, Path

### Community 51 - "SessionRecoveryManager"
Cohesion: 0.18
Nodes (12): BrowserContext, Exception, Page, Executa o pipeline graduado de recuperação. Se houver erro de…, Estágio 1: Descarta popups e recarrega a URL base., Estágio 2 (Última Instância): Logout formal -> Novo Login., Estágio 3: Cria nova aba limpa, limpa cookies e refaz autenticação., Gerenciador determinístico e tipado de recuperação de sessão (Padrão Matt… (+4 more)

### Community 52 - "web-automation-interface/package.json"
Cohesion: 0.11
Nodes (18): dependencies, react, react-dom, vite, @vitejs/plugin-react, devDependencies, react, react-dom (+10 more)

### Community 53 - "test_api_endpoints.py"
Cohesion: 0.18
Nodes (17): anyio, get_job_details(), get_job_logs(), get_selectors_config(), list_jobs(), Retorna histórico paginado de todos os jobs., Retorna dados detalhados do Job e lista de todos os seus itens., Retorna histórico de logs estruturados de um Job. (+9 more)

### Community 54 - "observability.py"
Cohesion: 0.15
Nodes (14): before_send(), init_observability(), Optional error reporting; ERP payloads remain in local operational records., Allow only diagnostic metadata, exception types and code locations., test_event_allowlist_removes_erp_data_and_keeps_stack(), test_handled_item_error_is_reported_before_session_reset(), test_init_configures_error_only_collection(), test_job_context_isolated_and_restored_across_threads() (+6 more)

### Community 55 - "routes.py"
Cohesion: 0.23
Nodes (14): ActionResponse, cancel_job(), pause_job(), PreValidationResponse, BaseModel, Roteador de endpoints REST e WebSockets da API FastAPI., Inicia a execução sequencial do Job via Worker em Thread dedicada., Pausa a execução do lote após a conclusão do item atual. (+6 more)

### Community 56 - "Arquitetura de Artefatos — Logs, Screenshots, Traces e Exports"
Cohesion: 0.13
Nodes (14): 10. Checklist de verificação (passos rápidos), 11. Comandos úteis, 12. Recomendações para correção rápida, 13. Observações finais, 1. Visão geral, 2. Ferramentas principais, 3. Geração de artefatos (fluxo), 4. Persistência (onde gravar e como) (+6 more)

### Community 57 - "Ops Brain"
Cohesion: 0.15
Nodes (12): 2026-10-21 — Observabilidade: patch preparado (implantacao pendente), 2026-10-23 — Aviso consultivo de duracao por cotacao (candidato), 2026-10-23 — Traces Grafana Cloud Free (patch candidato), 2026-10-30 — Resiliência a formatos nativos de data do Excel (.xls e .xlsx), Checklist de atuação, Decisões registradas, Estado atual, Ops Brain (+4 more)

### Community 58 - "fase4_frete.py"
Cohesion: 0.26
Nodes (10): _fechar_popups_alerta(), _normalizar_texto(), _opcao_destinatario_tam_para_cidade(), _preencher_campo_se_editavel(), preencher_frete(), _perform_city_search_and_selection(), Event, Page (+2 more)

### Community 59 - "LactalisBaseStrategy"
Cohesion: 0.18
Nodes (3): LactalisBaseStrategy, Regras base compartilhadas por todas as modalidades Lactalis., Calcula a data programada da Lactalis baseada na Validade: - Dia <= 15: dia 05…

### Community 60 - "Contrato mínimo do backend"
Cohesion: 0.20
Nodes (9): Arquivo e pré-validação, Artefatos, Configuração, Consulta durável, Contrato mínimo do backend, Eventos ao vivo, Execução, Requisitos periféricos de produção (+1 more)

### Community 61 - "selectors.py"
Cohesion: 0.25
Nodes (7): ConhecimentoSelectors, ContratoSelectors, CotacoesSelectors, FreteSelectors, LoginSelectors, Catálogo centralizado de seletores e cadeias de fallback do portal LogTudo…, SelectorsCatalog

### Community 62 - "Traces do piloto Contratos de frete"
Cohesion: 0.25
Nodes (7): Aceite e expansão, Correlação com erros, Escopo, Rollback, Teste manual sem ERP, Traces do piloto Contratos de frete, Variáveis do backend

### Community 63 - "Análise da referência Contratos_auto"
Cohesion: 0.25
Nodes (7): Análise da referência Contratos_auto, Fontes principais, Frontend encontrado, Funcionalidades periféricas encontradas, Jornada funcional encontrada, O que foi generalizado no template, Pontos de atenção observados na referência

### Community 64 - "Regras Globais do Codex - Ops Brain"
Cohesion: 0.29
Nodes (6): Estrutura mínima do cérebro, Objetivo, Obrigatoriedade, Regra de edição do cérebro, Regra final, Regras Globais do Codex - Ops Brain

### Community 65 - "Checklist para uma nova interface"
Cohesion: 0.29
Nodes (6): 1. Definir o contrato, 2. Personalizar a interface, 3. Integrar o backend, 4. Preparar produção, 5. Validar em rodadas, Checklist para uma nova interface

### Community 66 - "Template de Interface para Automação Web"
Cohesion: 0.29
Nodes (6): Decisões herdadas da análise, Limites intencionais, O que já vem pronto, Pontos de extensão, Template de Interface para Automação Web, Uso rápido

### Community 67 - "ManualTimer"
Cohesion: 0.29
Nodes (4): ManualTimer, fixture, timers(), factory()

### Community 68 - "Conectividade Playwright para VPS"
Cohesion: 0.33
Nodes (5): Arquivos, Conectividade Playwright para VPS, Import no Python, Notas de VPS, Uso rápido

### Community 69 - "Incidentes — Contratos de frete"
Cohesion: 0.33
Nodes (5): Automação, Dados nas Issues, Incidentes — Contratos de frete, Severidade e fluxo, Triagem

### Community 70 - "Runbook de Deploy Coolify — Contratos_auto (UI v2)"
Cohesion: 0.33
Nodes (5): Checklist no Coolify (quando autorizado o deploy na VPS), Estado atual, Observação sobre credenciais do portal, Runbook de Deploy Coolify — Contratos_auto (UI v2), Validação local (2026-09-17, Docker 29.7.2 / Compose v5.4.0)

### Community 71 - "span_api"
Cohesion: 0.33
Nodes (5): clean_state(), configured(), fixture, span_api(), use_span()

### Community 73 - "preencher_formulario"
Cohesion: 0.50
Nodes (4): preencher_formulario(), Event, Page, Executa os passos de preenchimento da Fase 3.

### Community 75 - "websocket_job_stream"
Cohesion: 0.67
Nodes (3): websocket, Streaming bidirecional de logs, progresso e comandos para o Job via WebSocket., websocket_job_stream()

## Knowledge Gaps
- **136 isolated node(s):** `LoginSelectors`, `CotacoesSelectors`, `ConhecimentoSelectors`, `FreteSelectors`, `ContratoSelectors` (+131 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 574 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ItemContrato` connect `ItemContrato` to `ExcelProcessor`, `lactalis_strategy.py`, `JobRepository`, `BaseStrategy`, `.to_row_nao_realizado`, `errors.py`, `.get_fim_viagem`, `ContractRunner`, `.create_job`, `contract_runner.py`, `worker.py`, `observability.py`, `LactalisBaseStrategy`, `test_tracing.py`, `FretePage`, `repository.py`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `JobRepository` connect `JobRepository` to `.update_item_result`, `JobBroadcaster`, `.create_job`, `Database`, `contract_runner.py`, `worker.py`, `ItemContrato`, `test_api_endpoints.py`, `ArtifactManager`, `repository.py`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `get_company()` connect `get_company` to `AutomationManager`, `BaseCompany`, `AutomacaoUI`, `preencher_formulario`, `fase1_processamento.py`, `fechar_popups_alerta`, `fase4_frete.py`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `ItemContrato` (e.g. with `ContractRunner` and `ExcelProcessor`) actually correct?**
  _`ItemContrato` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `ContractRunner` (e.g. with `ExecutionSummary` and `ItemContrato`) actually correct?**
  _`ContractRunner` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `ExcelProcessor` (e.g. with `upload_and_validate()` and `ContractRunner`) actually correct?**
  _`ExcelProcessor` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BaseStrategy` (e.g. with `ConhecimentoPage` and `ContratoPage`) actually correct?**
  _`BaseStrategy` has 5 INFERRED edges - model-reasoned connections that need verification._