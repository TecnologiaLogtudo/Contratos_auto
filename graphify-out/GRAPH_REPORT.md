# Graph Report - Contratos_auto  (2026-09-22)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 956 nodes · 1995 edges · 51 communities (41 shown, 6 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c49482da`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46

## God Nodes (most connected - your core abstractions)
1. `ItemContrato` - 89 edges
2. `JobRepository` - 39 edges
3. `BaseStrategy` - 39 edges
4. `AutomationManager` - 38 edges
5. `ExcelProcessor` - 38 edges
6. `ContractRunner` - 34 edges
7. `ItemStatus` - 31 edges
8. `FretePage` - 29 edges
9. `BaseCompany` - 29 edges
10. `FormFillError` - 25 edges

## Surprising Connections (you probably didn't know these)
- `TestCidadeOrigem` --uses--> `DPACompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/dpa.py
- `TestCidadeOrigem` --uses--> `LactalisDiariaParadaCompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/lactalis.py
- `TestCidadeOrigem` --uses--> `LactalisSpecialBaseCompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/lactalis.py
- `TestCidadeOrigem` --uses--> `LatamCompany`  [INFERRED]
  scratch/test_cidade_origem.py → backend/app/companies/latam.py
- `test_fluxo_erro_negocio_motivo_na_planilha()` --uses--> `SubmissionError`  [INFERRED]
  tests/test_erro_negocio_portal.py → backend/app/domain/errors.py

## Import Cycles
- None detected.

## Communities (51 total, 6 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (23): AutomationConfig, JobInfo, JobStatus, LogEvent, PreviewResponse, BaseModel, AutomationManager, init_db() (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (63): anyio, ActionResponse, cancel_job(), clear_logs_endpoint(), debug_artifacts(), download_artifact(), get_config(), get_job_artifacts() (+55 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (35): padronizar_cidade(), PreValidationReport, processar_cidade_uf(), processar_nome_placa(), Any, Path, Executa validação prévia detalhada da planilha antes de liberar o botão de…, Carrega, sanitiza e trata a planilha de origem. (+27 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (23): BaseCompany, Page, Retorna True se o remetente bater com este cliente., Executa a sincronização de remetente e destinatário no Playwright., Retorna o valor da Regra de Frete (select dados_regraFrete_id)., Passo opcional 8.5 na Fase 4 para preencher frete terceiros., Retorna o valor para o campo dados_observacaoPV na Fase 4. Por padrão usa…, Permite preencher campos adicionais/específicos na Fase 4. (+15 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (20): DPAStrategy, Estratégia dedicada para DPA (Dairy Partners)., extrair_numero_nf(), LactalisBaseStrategy, LactalisDiariaGarantidaStrategy, LactalisDiariaParadaStrategy, LactalisPernoiteStrategy, Extrai o número da Nota Fiscal a partir da observação com regex flexível. (+12 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (27): ItemStatus, JobRepository, Atualiza o estado global de um Job., Recalcula e persiste as contagens de sucesso/erro de um Job., Implementa o padrão Repository para operações no SQLite., Recupera metadados completos de um Job., Lista jobs ordenados por data decrescente., Recupera itens pendentes ou em processamento para execução/retomada. (+19 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (20): Exception, AutomacaoUI, get_resource_path(), Lê o config.ini e preenche os campos da UI., Salva os campos da UI no config.ini., Retorna o caminho absoluto para um recurso, funcionando em dev e no PyInstaller., Envia uma mensagem de log para a fila., Inicia o loop que consome a fila de log e atualiza a UI. (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (15): BaseStrategy, Page, Contrato base para estratégias polimórficas de clientes/remetentes., Retorna True se a estratégia for aplicável ao remetente da planilha., Indica se a data de pagamento é obrigatória na planilha., Indica se a data de validade é obrigatória na planilha., Retorna se o checkbox 'Emitir Recibo de Frete' deve ser marcado na Fase 3., Retorna o nome da cidade para busca no campo Origem (Fase 4). (+7 more)

### Community 8 - "Community 8"
Cohesion: 0.11
Nodes (15): wait_for_valid_select_options(), _fechar_popups_alerta(), _normalizar_texto(), _opcao_destinatario_tam_para_cidade(), _preencher_campo_se_editavel(), preencher_frete(), _perform_city_search_and_selection(), Event (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (15): AbstractEventLoop, JobBroadcaster, Any, WebSocket, Registra o log no banco SQLite e agenda o broadcast assíncrono para WebSockets…, Emite evento de atualização de progresso para a UI de forma thread-safe., Gerencia conexões WebSocket e SSE ativas por Job e emite logs estruturados com…, Registra o loop de eventos principal do FastAPI para chamadas thread-safe. (+7 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (15): get_company(), _remover_acentos(), preencher_formulario(), Event, Page, Executa os passos de preenchimento da Fase 3., Encontra a linha correspondente na aba 'Dados Processados', atualiza o status…, registrar_sucesso_em_planilha() (+7 more)

### Community 11 - "Community 11"
Cohesion: 0.15
Nodes (13): AuthenticationError, AutomationError, QuoteExtractionError, Erro de validação ou leitura na planilha de entrada (dados faltantes ou…, Falha de login, credenciais inválidas ou timeout no 2FA., Falha na extração de dados da cotação no portal (Pedido, NF ou Status não…, Falha ao salvar o contrato de frete ou na aprovação de contingência de CFOP., Exceção base para todas as falhas na automação de contratos. (+5 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (23): react-dom, tailwindcss, @tailwindcss/vite, vite, @vitejs/plugin-react, allowScripts, esbuild@0.21.5, dependencies (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (13): ExecutionSummary, Resumo consolidado do processamento do arquivo., ContractRunner, Processa um único item/cotação pelas Fases 2 a 5 de forma isolada., Fecha o navegador e limpa instâncias., Orquestrador unificado de execução de contratos com Playwright. Garante…, Inicializa o navegador e realiza o login único compartilhado para o lote., CotacoesPage (+5 more)

### Community 14 - "Community 14"
Cohesion: 0.10
Nodes (12): Database, Path, Fecha conexão da thread atual., Gerenciador de conexão SQLite thread-safe com suporte a WAL mode e busy timeout., Obtém uma conexão isolada por thread., Context manager transacional atômico., Cria as tabelas caso não existam., Connection (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (10): NavigationError, Falha de navegação, timeout de URL ou bloqueio de rota., ItemResult, Resultado da execução de um único contrato., DialogGuard, Detecta o alerta genérico de erro de negócio do portal e-Login (div.rotina-…, Guardião e interceptor ativo de diálogos, popups modais (jQuery UI,…, Teste real (navegador headless) do tratamento de erros de negócio do portal.… (+2 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (20): _get_merged_cell_value(), _ler_com_openpyxl(), _ler_com_xlrd(), _padronizar_cidade(), _processar_cidade_uf(), _processar_nome_placa(), processar_planilha(), _processar_remetente() (+12 more)

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (14): BrowserConfig, BrowserFactory, Browser, BrowserContext, Page, Fábrica responsável por instanciar e configurar o navegador Playwright., LoginPage, Page (+6 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (11): JobWorker, Path, Gerencia a execução assíncrona de um lote via Thread dedicada., Gerenciador central de instâncias de workers., Retorna o worker atualmente em execução, se houver., Cria e dispara um novo worker para o Job., Verifica se a thread do worker está ativa., Inicia a thread do worker. (+3 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (10): ItemContrato, BaseModel, Representação tipada e validada de uma linha da planilha de contratos., Valor a ser preenchido no campo dados_complementoPedido., Monta o texto para a observação PV (Fase 4). Padrão: 'Nome - Placa'., Retorna a data programada para o pagamento do saldo (Fase 5)., LactalisSpecialBaseStrategy, Page (+2 more)

### Community 20 - "Community 20"
Cohesion: 0.16
Nodes (11): launch_browser(), perform_login(), any, Browser, BrowserContext, Page, Inicia o Playwright e o navegador configurado., Abre uma nova página (ou usa uma existente), realiza o login e navega para a… (+3 more)

### Community 21 - "Community 21"
Cohesion: 0.14
Nodes (4): LactalisSpecialBaseCompany, Page, Encontra a planilha de output e registra uma linha na aba 'Contrato não…, registrar_erro_em_planilha()

### Community 22 - "Community 22"
Cohesion: 0.15
Nodes (9): ExcelProcessor, Manipulador de planilhas in-memory com sanitização BSoft integrada e…, Marca o item como concluído com sucesso., Marca o item como erro e registra a causa detalhada., NormalizedSpreadsheet, Loop de trabalho principal da Thread., test_contract_runner_lifecycle_with_mocked_browser(), test_parse_raw_workbook_mixed_rows() (+1 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (10): ArtifactManager, Path, Executa limpeza de traces e vídeos temporários com idade superior a…, Gerencia ciclo de vida, diretórios e limpeza de arquivos gerados por execuções., Retorna o diretório base para um Job específico, criando se necessário., Retorna o diretório de screenshots de erro para o Job., Retorna o diretório de traces e vídeos Playwright para o Job., Salva screenshot capturado no momento da falha e registra no repositório. (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (4): DPACompany, Page, LactalisDiariaGarantidaCompany, LactalisPernoiteCompany

### Community 25 - "Community 25"
Cohesion: 0.24
Nodes (9): esperar_e_fechar_popups(), fechar_popups_alerta(), Page, Verifica se há popups, caixas de diálogo ou modais visíveis na tela (jQuery UI…, Executa verificação periódica por um breve período para capturar popups que…, test_fechar_popup_lactalis_nf_duplicada(), log_cb(), test_lactalis_especial_remetente_destinatario_inalterados() (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.16
Nodes (5): FASES, StepperFases(), statusLabel(), TabEmissao(), TerminalLogs()

### Community 27 - "Community 27"
Cohesion: 0.22
Nodes (8): fmtBytes(), fmtDate(), fmtDur(), JobDetailDrawer(), labelFor(), pillFor(), shortId(), TabHistorico()

### Community 28 - "Community 28"
Cohesion: 0.28
Nodes (5): FormFillError, Falha ao preencher campos, selecionar dropdowns ou avançar etapas do formulário., ContratoPage, Page, Page Object para a Fase 5 - Emissão e Finalização do Contrato de Frete.

### Community 29 - "Community 29"
Cohesion: 0.24
Nodes (3): FretePage, Page, Page Object para a Fase 4 - Dados do Frete, Motorista e Veículo.

### Community 30 - "Community 30"
Cohesion: 0.21
Nodes (6): fmtDur(), jobPill(), jobStatusLabel(), shortId(), TabAdmin(), VisaoGeral()

### Community 31 - "Community 31"
Cohesion: 0.26
Nodes (6): Gerenciador de armazenamento, registro e retenção de artefatos do…, Broadcaster e gerenciador de conexões WebSocket para logs e eventos em tempo…, Módulo de conexão e gerenciamento de esquema SQLite para o Contratos_auto., Repositório unificado SQLite para Jobs, Itens, Logs e Artefatos do…, Worker orquestrador de execução em background em Thread dedicada., datetime

### Community 32 - "Community 32"
Cohesion: 0.27
Nodes (11): health(), health_ready(), on_startup(), get, Inicializa banco SQLite e loop de eventos para o broadcaster., _render_index_html(), serve_index(), serve_manual() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.33
Nodes (6): react, App(), ScreenshotModal(), Toast(), ThemeContext, ThemeProvider()

### Community 36 - "Community 36"
Cohesion: 0.31
Nodes (3): Page, Verifica e fecha popups repetidamente durante um breve intervalo., Detecta e fecha de forma resiliente modais jQuery UI, SweetAlert e overlays de…

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (6): ConhecimentoPage, Page, Page Object para a Fase 3 - Preenchimento Básico do Conhecimento., Teste unitário da vinculação e sincronização do campo de Nota Fiscal (NF) na…, Testa se ConhecimentoPage preenche, busca e seleciona a Nota Fiscal quando…, test_vincular_cotacao_com_nf()

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (3): LatamCompany, Page, Regra atual da LATAM: Destinatário é cópia do Remetente (Busca pelo CNPJ e…

### Community 40 - "Community 40"
Cohesion: 0.60
Nodes (5): hasJobActivity(), shortId(), Sidebar(), statusLabel(), useTheme()

### Community 42 - "Community 42"
Cohesion: 0.40
Nodes (3): Any, Gera a linha para a aba 'Dados Processados'., Gera a linha para a aba 'Contrato não realizado'.

### Community 43 - "Community 43"
Cohesion: 0.40
Nodes (3): browser_page(), portal_url(), fixture

### Community 44 - "Community 44"
Cohesion: 0.50
Nodes (3): Any, Event, Path

## Knowledge Gaps
- **24 isolated node(s):** `ConhecimentoSelectors`, `ContratoSelectors`, `CotacoesSelectors`, `FreteSelectors`, `LoginSelectors` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 390 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ItemContrato` connect `Community 19` to `Community 2`, `Community 36`, `Community 37`, `Community 4`, `Community 7`, `Community 5`, `Community 42`, `Community 11`, `Community 13`, `Community 45`, `Community 15`, `Community 18`, `Community 22`, `Community 28`, `Community 29`, `Community 31`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `JobRepository` connect `Community 5` to `Community 1`, `Community 9`, `Community 45`, `Community 14`, `Community 18`, `Community 19`, `Community 23`, `Community 31`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `BaseCompany` connect `Community 3` to `Community 34`, `Community 39`, `Community 10`, `Community 24`, `Community 25`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `ItemContrato` (e.g. with `ContractRunner` and `ExcelProcessor`) actually correct?**
  _`ItemContrato` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `JobRepository` (e.g. with `ArtifactManager` and `JobBroadcaster`) actually correct?**
  _`JobRepository` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `BaseStrategy` (e.g. with `ConhecimentoPage` and `ContratoPage`) actually correct?**
  _`BaseStrategy` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `AutomationManager` (e.g. with `AutomationConfig` and `JobStatus`) actually correct?**
  _`AutomationManager` has 2 INFERRED edges - model-reasoned connections that need verification._