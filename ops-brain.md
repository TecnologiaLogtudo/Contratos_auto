# Ops Brain

## Visão geral
Memória compartilhada para coordenação de trabalho entre agentes e projetos. Este arquivo deve ser lido antes de qualquer ação e atualizado ao final de cada tarefa relevante.

## Estado atual
- Projeto: Contratos_auto
- Contexto: workspace de automação de contratos com backend, frontend e dados em storage.
- Modo operacional: leitura e atualização do cérebro antes de executar alterações e ao concluir cada etapa.

## Regras de operação
- Sempre ler o cérebro antes de atuar no projeto.
- Sempre registrar mudanças, conclusões e pendências.
- Usar o cérebro como fonte de contexto compartilhado, não como anotações isoladas.
- Priorizar evidência do código, ambiente e validações.

## Decisões registradas
- O `AGENTS.md` é a regra global do Codex para este workspace.
- O `ops-brain.md` é o ponto de memória compartilhada para o projeto.
- Qualquer tarefa deve manter o histórico consistente e atualizar as pendências.

## Checklist de atuação
- [ ] Ler o cérebro antes de iniciar.
- [ ] Identificar objetivo e escopo.
- [ ] Executar trabalho com foco em evidência.
- [ ] Registrar o que mudou.
- [ ] Validar impacto relevante.
- [ ] Atualizar pendências e próximos passos.

## Última atualização
- Data inicial de sincronização: 2026-09-22
- Status: pronto para uso como cérebro compartilhado do projeto.
- 2026-09-22: investigada a configuração do preenchimento de Destinatário para LATAM. Sem alterações de código. Evidência principal: `backend/app/engine/pages/frete_page.py` usa o CNPJ do Remetente para pesquisar o Destinatário e tenta fallback pelo mesmo value do Remetente; `backend/app/companies/latam.py` mantém regra equivalente no fluxo legado.
- 2026-09-22: criado `Docs/procedimento_operacional_fluxos.txt` com POP dos processos executados: fluxo operacional do lote, decisão por remetente/modalidade, LATAM/Padrão, DPA, Lactalis Diária Parada, Lactalis Pernoite/Diária em Rota/Diária no Cliente, Lactalis Diária Garantida, fases comuns, erros/evidências e fluxo legado. Validação: leitura do arquivo criado e conferência por `rg` dos títulos principais.
- 2026-09-22: ajustada regra LATAM/Padrão para quando o Remetente não tiver CNPJ identificável: o Destinatário passa a ser pesquisado como LogTudo pelo CNPJ `20511709000169`. Alterados fluxo novo (`backend/app/engine/pages/frete_page.py`), fluxo legado (`backend/app/companies/latam.py`) e POP (`Docs/procedimento_operacional_fluxos.txt`). Validação: `PYTHONPATH=.` com `pytest tests\test_frete_page.py tests\test_strategies.py` resultou em 5 testes aprovados.
- 2026-09-22: corrigida extração de CNPJ LATAM/Padrão para não juntar números soltos do texto do Remetente. Agora só aceita CNPJ no formato `00.000.000/0000-00` ou 14 dígitos consecutivos; caso contrário usa LogTudo `20511709000169`. Alterados `backend/app/engine/pages/frete_page.py`, `backend/app/companies/latam.py`, `tests/test_frete_page.py` e POP. Validação: `PYTHONPATH=.` com `pytest tests\test_frete_page.py tests\test_strategies.py` resultou em 6 testes aprovados.
- 2026-09-30: analisados frontend e recursos periféricos; criado `templates/web-automation-interface`, template React/Vite reutilizável com modo mock, contrato REST/WebSocket, checklist, Docker/Nginx e inventário da referência. Validação: `npm run build` com Vite 6.4.3 (30 módulos) e `npm audit` sem vulnerabilidades.
- 2026-10-08: corrigida identificação de Motorista, Placa e Cidade/UF para relatórios BSoft com layout sem coluna A inicial e dados em "Observação Interna" / "Fim prestação". Atualizado `sanitizer.py` (sinônimos de cidade_uf), `excel_processor.py` e `fase1_processamento.py` (fallback semântico para observação interna e limpeza de pipes). Validação: 45 testes aprovados no pytest (incluindo 2 novos testes) e 10/10 itens válidos na planilha reportada.
- 2026-10-13: implementado o módulo resiliente `backend/app/engine/session_recovery.py` (`SessionRecoveryManager`) para recuperação e reparo determinístico de sessão pós-erro no padrão Matt Pocock. Adicionado `logout()` formal no `LoginPage` (`backend/app/engine/pages/login_page.py`), fechando popups, acionando menu 'Sair' e limpando cookies de forma defensiva. `ContractRunner._reset_session()` agora opera em estratégia graduada: tenta primeiro a recuperação leve (Soft Reload com health check de formulário); se insuficiente, aciona a última instância com Reset completo (logout formal -> novo login); em caso de colapso de página, executa contingência criando nova aba limpa. Validação: 55 testes aprovados no pytest (incluindo 9 novos testes em `test_session_recovery.py` e 1 novo em `test_contract_runner.py`).
- 2026-10-13: atualizado `backend/requirements.txt` com `uvicorn[standard]==0.32.0` e `websockets>=12.0` para solucionar erro de `Unsupported upgrade request` / handshake de WebSocket rejeitado que deixava a interface em status "aguardando" no Coolify/servidor. Validação: 55 testes mantidos 100% verdes no pytest.
- 2026-10-13: regra de domínio crítica do ERP LogTudo (BSoft): dados parciais inseridos no formulário (Fases 3, 4 e 5) persistem na sessão do servidor PHP (`$_SESSION`), logo um refresh/soft reload não expurga os dados e contamina a cotação seguinte (gerando timeout de 45s em campos dependentes como Talão). Ajustado `SessionRecoveryManager` e `ContractRunner` para que erros de processamento/dados na cotação repassam o erro e forçam diretamente o Reset Completo (Logout -> Login), limpando os dados anteriores no servidor. Validação: 57 testes aprovados no pytest (incluindo teste com `FormFillError` em `test_session_recovery.py` e teste de repasse de erro em `test_contract_runner.py`).
- 2026-10-13: suporte multiusuário — `WorkerManager` alterado para travar por usuário (case-insensitive) em vez de trava global. Cada usuário pode ter no máximo 1 job ativo, mas usuários diferentes rodam em paralelo com instâncias Playwright independentes. Arquivo alterado: `backend/app/infrastructure/worker.py`. Métodos renomeados: `get_active_worker()` → `get_active_worker_for_user(usuario)`; adicionado `get_active_workers()`. Validação: AST ok, 5 testes inline passaram (paralelo, bloqueio mesmo user, case-insensitive).
- 2026-11-13: isolamento completo de sessão multi-usuário por Browser UUID (Token). Corrigido bug onde qualquer cliente acessando a aplicação herdava o primeiro job RUNNING/PAUSED no frontend e visualizava jobs de terceiros. Backend atualizado para persistir e indexar `session_token` no SQLite (`jobs.session_token`), e validar `_assert_job_owner` em rotas de controle (`/pause`, `/resume`, `/cancel`). Rota `/jobs` e `upload-and-validate` passam a filtrar/associar via header `X-Session-Token`. Frontend unificado com `crypto.randomUUID()` permanente por máquina em `localStorage`, e `sessionStorage` para `job_id` local. Validação: 103 testes aprovados no pytest (100% verde), `npm run build` do frontend sem erros (Vite 5.4.21).

## Próximos passos
- Usar este cérebro como referência para futuras tarefas.
- Atualizar com decisões e resultados de cada ciclo de trabalho.
- Realizar deploy no Coolify e verificar se a rota WebSocket `/ws/jobs/{job_id}` conecta imediatamente sem advertências.
- Monitorar execuções reais com cotações com erro (como Perfil de Apropriação) para verificar a transição suave com logout e novo login entre os itens.
- Se houver ajuste futuro para LATAM, confirmar qual fluxo está ativo no ambiente: page object novo (`engine/pages/frete_page.py`) ou fase legada (`phases/fase4_frete.py` + `companies/latam.py`).
- Revisar o POP com a operação para ajustar nomes internos e exceções reais observadas em produção, se necessário.
- Ao iniciar uma nova automação web, copiar `templates/web-automation-interface`, editar `src/template.config.js` e implementar `BACKEND_CONTRACT.md`.





## 2026-10-21 — Observabilidade: patch preparado (implantacao pendente)
- Objetivo: integrar Contratos de frete ao GlitchTip em erros.logtudo.com.br.
- Mudancas propostas: inicializacao opcional Sentry no FastAPI, captura de erros tratados no runner/worker, contexto job_id, sanitizacao por allowlist e variaveis no Compose. Sem SENTRY_DSN a coleta fica desativada; tracing Sentry desligado para fase futura OTel/Uptrace.
- Validacoes na copia isolada: 9 testes novos passaram com SDK simulado. Suite completa encontrou bloqueios de permissoes em temporarios e Playwright; SDK real/envio ao GlitchTip ainda precisam ser validados.
- Riscos/pendencias: aplicacao deste patch, instalacao da dependencia, teste real de HTTP/worker, DSN e release no Coolify, DNS/GlitchTip, Telegram e backlog. Mensagens brutas omitidas por privacidade; diagnostico utiliza tipo/pilha/job_id e registros locais.
- Proximos passos: validar patch na revisao de destino, testar com SDK real, atualizar grafo Graphify apos aplicar, fazer commit/push e deploy somente apos revisao operacional.


## 2026-10-23 — Aviso consultivo de duracao por cotacao (candidato)
- Objetivo: detectar cotacao ativa longa sem heartbeat por horario; usuario informou maximo normal estimado90s e lotes exclusivamente manuais.
- Mudancas: item_watchdog envolve apenas process_single_item do worker com Timer daemon; JOB_ITEM_WARNING_SECONDS padrao180, zero desativa. Emite ItemExecutionDelayed uma vez e ItemExecutionFinishedAfterDelay ao sair da chamada, sem cancelar/reemitir ou alterar resultado.
- Validacoes na copia isolada: 25 testes direcionados passaram, incluindo SDK Sentry2.72 real com transporte em memoria, corrida de conclusao, cancelamento antes do item e falhas do observador/transporte. Nenhuma emissao real ou deploy executado pela sessao.
- Riscos/pendencias: prazo e aviso de possivel atraso, nao prova de travamento. Final da chamada pode ser erro. Login, relatorio, fechamento e queda total do processo nao cobertos; monitor externo/reconciliacao de orfaos ficam futuros. Regras de alerta GlitchTip podem agrupar/suprimir sinais.
- Proximos passos: aplicar/revisar patch, testar e publicar quando nao houver lote ativo; configurar180 e release, validar captura em operacao e ajustar conforme duracoes. Atualizar grafo Graphify apos aplicar ao projeto real. Backup continua adiado.

## 2026-10-23 — Traces Grafana Cloud Free (patch candidato)
- Objetivo: instrumentar piloto Contratos de frete e preparar padrao reutilizavel para outros sistemas, sem custo de licenca ou banco novo na VPS.
- Decisoes vigentes: usuario adiou backup mesmo com OneDrive pessoal5GB; recusou monitor externo; aceitou retencao14dias e Grafana Free. Erros/Telegram/backlog/uptime/watchdog validados pelo usuario; lote normal aguardara oportunidade real.
- Mudancas: tracing opcional/desativado por padrao, OTel SDK e OTLP/HTTP1.45.1, cinco spans por cotacao normal (raiz+4fases) do worker web; login/fechamento/recuperacao separados conforme contexto; correlacao via tags trace_id/span_id no Sentry. Batch limitado e nenhuma mensagem/stack/evento bruto. Teste sintetico executavel por modulo sem ERP/DB, documentacao e variaveis Compose. Fluxo legado run/API/SQL/browser nao auto-instrumentados.
- Validacoes na copia isolada:54 testes passaram,1 teste SDK OTel real pulado porque dependencias indisponiveis e acesso PyPI bloqueado nesta sessao; instalar requirements e passar esse teste antes do deploy. Inclui regressao runner, Sentry real em memoria e watchdog. Teste XLSX passou com harness de temporarios do workspace devido ACL Python3.14 no sandbox. Compose config --quiet passou. Nenhum contrato real, envio remoto ou deploy por esta sessao.
- Riscos/pendencias: SDK/exportador real e ingestao Grafana ainda precisam validacao; plano atual tem avaliacao14dias e deve permanecer Free;50GB/mensais compartilhados, medir antes de expandir. Banda incluida VPS ainda nao confirmada. Contexto do Timer watchdog nao inclui trace_id; usar job_id. Head sampling<1 pode perder traces de erros; Sentry segue independente. Fila em memoria pode descartar spans e nao sobrevive a restart.
- Proximos passos: aplicar/revisar patch na revisao correta, instalar requirements e passar testes sem skips de SDK, configurar segredo OTLP no Coolify sem compartilhar token, commit/push/deploy sem lote ativo, executar trace_smoke --send --with-error e conferir Grafana/GlitchTip/Telegram. Atualizar grafo do projeto real apos aplicar. Medir consumo e expandir por service.name/token/taxa proprios.


## 2026-10-30 — Resiliência a formatos nativos de data do Excel (.xls e .xlsx)
- Objetivo: solucionar falha na extração e cálculo da Data Programada (Fase 5 / Lactalis) quando o usuário altera ou formata datas como Data nativa no Excel (gerando números seriais como `46296.0` para `01/10/2026`).
- Causa-raiz: `sanitizer.py` extraía valor bruto `46296.0` sem converter tipos `xlrd.XL_CELL_DATE`, e as estratégias Lactalis esperavam regex textual (`DD/MM/AAAA` ou `AAAA-MM-DD`), retornando `None` e travando a Fase 5 com `FormFillError: Data Programada não pode ser calculada`.
- Mudanças realizadas:
  1. `backend/app/engine/sanitizer.py`: em `sanitize_bsoft_xls`, identifica `xlrd.XL_CELL_DATE` e converte para `DD/MM/YYYY` via `xlrd.xldate_as_tuple()`. Em `sanitize_bsoft_xlsx`, converte instâncias nativas `date`/`datetime` para `DD/MM/YYYY`.
  2. `backend/app/engine/strategies/lactalis_strategy.py` e `backend/app/companies/lactalis.py`: adicionado fallback defensivo em `get_data_programada()` para interpretar números seriais na faixa `30000 <= val <= 60000` via época Excel (`1899-12-30`).
  3. `tests/test_strategies.py` e `tests/test_excel_processor.py`: novos testes para conversão de datas nativas do Excel e datas seriais.
- Validação: 100 testes passaram 100% verdes no pytest (`.venv\Scripts\python -m pytest tests/`). Teste com o arquivo real `C:\Users\felipe\Downloads\relatorio NOVO.xls` confirmou leitura e cálculo perfeitos para todos os 10 itens (`validade=01/10/2026` e `dt_prog=05/11/2026`).
- Riscos e pendências: nenhum risco colateral; alteração puramente aditiva e compatível com formatos texto e nativo. Pronto para execução no ambiente operacional.

## 2026-10-30 — Correção da planilha resultado retornada vazia após automação
- Objetivo: solucionar defeito em que a planilha consolidada para download após a execução do lote era gerada e entregue vazia (apenas linhas de cabeçalho).
- Causa-raiz:
  1. `JobWorker` inicializava `ExcelProcessor` sem carregar os dados originais (`load_and_parse()` não era chamado), deixando `self.items` vazio.
  2. Chamadas subsequentes a `mark_success` e `mark_error` não encontravam itens, e `save_output` escrevia 0 linhas de dados nas abas "Dados Processados" e "Contrato não realizado".
  3. Lotes cancelados ou interrompidos por falhas não geravam artefato consolidado.
- Mudanças realizadas:
  1. `backend/app/engine/excel_processor.py`: adicionados métodos `populate_from_db` e `sync_with_db` com normalização resiliente de status (`Concluído`, `Erro`, `Falha na Validação`), permitindo reconstruir e sincronizar 100% dos dados a partir do SQLite (`job_items`).
  2. `backend/app/infrastructure/worker.py`: adicionado método `_save_and_register_report`, integrando sincronização direta do banco e persistência/registro de artefatos em todos os fluxos: conclusão normal, cancelamento parcial, inexistência de itens pendentes ou interrupção.
  3. `backend/app/api/routes.py`: adicionada função de detecção `_is_empty_or_header_only_excel` e regeneração sob demanda no endpoint `download_artifact`. Caso o arquivo não exista no disco ou contenha apenas cabeçalhos (inclusive jobs executados no passado), o backend regenera a planilha consolidada automaticamente a partir do banco e entrega o arquivo completo.
  4. `tests/test_excel_processor.py` e `tests/test_api_endpoints.py`: testes adicionados cobrindo `populate_from_db`, `sync_with_db`, e regeneração dinâmica no download.
- Validação: 103 testes passaram 100% verdes no pytest (`.venv\Scripts\python -m pytest tests/`).
- Riscos e pendências: nenhum risco colateral; compatibilidade total com execuções ativas e histórico anterior.

## 2026-11-24 — Resiliência no Checkbox de Frete Mínimo ANTT (Fase 5)
- Objetivo: solucionar `TimeoutError` de 30 segundos no Playwright ao tentar marcar a confirmação de Frete Mínimo ANTT (`#confirmacaoFreteMinimo_concorda`) na Fase 5 (Emissão de Contrato), reportado no GlitchTip (Issue 20 / Job 241126-00002).
- Causa-raiz: O elemento `#confirmacaoFreteMinimo_concorda` é condicional e pode estar oculto, inacessível a ponteiros ou bloqueado por labels/overlays no portal e-Login. A chamada direta `chk_antt.check()` sem `force=True`, sem timeout reduzido e sem tratamento com fallback em JavaScript congelava a execução por 30 segundos até estourar `TimeoutError`.
- Mudanças realizadas:
  1. `backend/app/engine/pages/contrato_page.py`: criado método auxiliar `_confirmar_frete_minimo_antt(self, nro: str, delay_step: float) -> None`, executando `chk_antt.check(timeout=2500, force=True)` com captura defensiva de exceções e fallback instantâneo via injeção JavaScript (`page.evaluate()`). Aplicado na Etapa 12 do fluxo principal e na Etapa 14 da contingência de CFOP.
  2. `tests/test_contrato_page_antt.py`: testes unitários adicionados cobrindo sucesso no `check`, contingência JS sob erro e comportamento quando invisível.
- Validação: 102 testes passaram 100% verdes no pytest (`.venv\Scripts\python -m pytest tests/ --ignore=tests/test_erro_negocio_portal.py`). Diagnóstico validado e reproduzido em produção via GlitchTip e e-Login.
- Riscos e pendências: risco nulo; o fallback garante que contratos com ou sem exigência de anuência ANTT prossigam sem travar a automação.

## 2026-11-24 — Desacoplamento do Histórico Global e Restauração dos Dados do Admin
- Objetivo: solucionar defeito onde o usuário/administrador não conseguia visualizar o histórico de execuções dos demais operadores nem os dados analíticos na sessão Admin (KPIs zerados e "Nenhum dado de operador ainda").
- Causa-raiz: O endpoint `GET /jobs` estava filtrando compulsoriamente por `session_token = X-Session-Token` vindo de cada browser (UUID gerado localmente). Como o header era enviado em toda requisição pelo frontend, a listagem de jobs trazia apenas os lotes criados pelo próprio navegador do cliente. O Admin e o Histórico recebiam essa lista filtrada e ficavam desprovidos dos dados globais.
- Mudanças realizadas:
  1. `backend/app/api/routes.py`: adicionado parâmetro `my_session_only: bool = Query(False)` ao endpoint `GET /jobs`. Por padrão (`my_session_only=False`), a listagem retorna todos os jobs ordenados por data para visualização completa, auditoria e métricas do Admin.
  2. `web/src/services/api.js`: atualizado `listJobs(limit, offset, mySessionOnly)` permitindo filtrar a própria sessão apenas se explicitamente solicitado.
  3. `web/src/App.jsx`: blindada a lógica de startup que detecta job em execução (`running`), vinculando o console de emissão (`currentJob`) apenas ao lote desta sessão específica (`session.getJobId()` ou `session_token === browserId`).
  4. `web/src/components/TabHistorico.jsx`: adicionado filtro de escopo ("Todos os Operadores" vs "Apenas Meus Lotes"), permitindo alternar livremente.
  5. `web/src/components/TabAdmin.jsx`: corrigida a exibição de logs na aba "Sessões de Log", formatando linhas de log structured array (`[created_at] [level] message`).
  6. `web/dist/`: bundle de produção recompilado com sucesso via Vite (`npm run build`).
  7. `tests/test_api_endpoints.py`: adicionado teste de regressão para `list_jobs` com e sem `my_session_only`.
- Validação: 102 testes aprovados no pytest (100% verde), build do Vite concluído com sucesso em 1.16s.
- Riscos e pendências: nenhum risco colateral; isolamento do console ativo preservado e visibilidade total de auditoria restaurada.

## 2026-11-24 — Fechamento Ativo de Pop-up de KM e Resiliência no Destinatário do Contrato
- Objetivo: eliminar atraso/congelamento de 45 segundos e falha na seleção do Destinatário Contrato (`Logtudo`) causada pelo popup jQuery UI assíncrono `dialogo_distancia_km` e respectivo `ui-widget-overlay`.
- Causa-raiz: O cálculo de distância e KM dispara um modal jQuery UI `dialogo_distancia_km` com overlay escuro no portal e-Login. A busca do destinatário tentava clicar em `botaoPesquisa_dados_enderecoDestinatarioContrato_id` sem `dismiss_all_popups` prévio e com timeout padrão longo de 45s, sendo fisicamente interceptado pelo overlay.
- Mudanças realizadas:
  1. `backend/app/engine/dialog_guard.py`: expandidos seletores de fechamento do `DialogGuard` para detectar e fechar especificamente diálogos com `aria-describedby="dialogo_distancia_km"`, botões "Sim", "Confirmar", "Continuar" e expurgo determinístico via jQuery `$('#dialogo_distancia_km').dialog('close')`.
  2. `backend/app/engine/pages/contrato_page.py`: em `_configurar_destinatario_contrato`, adicionado `DialogGuard.dismiss_all_popups()` preventivo, timeout reduzido para 2.5s com auto-dismiss imediato, retry com `force=True` e `dispatch_event('click')`. Adicionada seleção resiliente no `<select>` (value `1` ou primeira opção válida).
  3. `tests/test_contrato_page_antt.py`: adicionado teste unitário `test_configurar_destinatario_contrato_com_popup_interceptor`.
- Validação: 103 testes aprovados no pytest (100% verde).
- Riscos e pendências: nenhum risco; o destinatário é vinculado com sucesso sem esperar 45s.

## 2026-11-24 — Milestone M1: Correções Críticas do Fluxo, Isolamento de Erros e Mitigação de Timeout Fase 4->5
- Objetivo: implementar as correções do Milestone M1 resolvendo os problemas R1 (seletor de logout Playwright), R2 (navegação determinística entre itens), R3 (reset defensivo de sessão no runner), R4 (persistência imediata de status ERRO no worker) e R5 (mitigação de timeout e modais bloqueantes na transição da Fase 4 para Fase 5).
- Mudanças realizadas:
  1. `backend/app/engine/pages/login_page.py` (R1): corrigido o seletor de logout de `a:has-text('Sair'), button:has-text('Sair'), text='Sair'` para `:is(a, button):has-text('Sair')`, eliminando a exceção de sintaxe CSS do Playwright (`Unexpected token "="`).
  2. `backend/app/engine/contract_runner.py` (R2 e R3):
     - R2: remoção da guarda condicional frágil de correspondência parcial de URL em `process_single_item` e `run()`, forçando a navegação incondicional para `URL_CONHECIMENTO_FORM` e chamada a `DialogGuard.dismiss_all_popups` entre cotações consecutivas.
     - R3: encapsulamento da chamada `self._reset_session(error=err)` em bloco defensivo `try/except Exception as reset_err:` com log de aviso e telemetria, assegurando o retorno incondicional do objeto `ItemResult(status=ItemStatus.ERRO)`.
  3. `backend/app/infrastructure/worker.py` (R4): no loop de itens de `_run_job`, isolado o processamento de cada item em `try/except Exception as item_exc:`. Qualquer falha ou `result.sucesso == False` agora persiste imediatamente o status `ItemStatus.ERRO` no SQLite (`self.repo.update_item_result`), marca o erro no `ExcelProcessor` (`excel_proc.mark_error`), salva o estado da planilha em disco (`_save_and_register_report`) com proteção contra duplicidade de artefatos, e permite que o lote continue para os itens seguintes.
  4. `backend/app/engine/dialog_guard.py` e `backend/app/engine/pages/frete_page.py` (R5):
     - `DialogGuard`: expandido para reconhecer botões afirmativos em diálogos jQuery UI e modais SweetAlert 1 & 2 ("Sim", "Confirmar", "Continuar", "Prosseguir", "Ciente", "Aceitar", etc.) e expurgar completamente overlays impeditivos (`.ui-widget-overlay, .swal2-container, .sweet-overlay, .modal-backdrop, .blockUI`). Enriquecida a detecção de erro de negócio do portal para cobrir SweetAlert, Bootstrap e caixas de mensagem.
     - `FretePage`: em `_aguardar_transicao_fase5`, adicionados seletores expandidos da Fase 5, detecção precoce de validações client-side com erro na Fase 4 (como `.swstatus-input-error`), auto-dismiss de modais afirmativos e registro de telemetria estruturada diagnóstica antes do timeout.
  5. `pytest.ini`: criado na raiz configurando `testpaths = tests` e `addopts = --ignore=tests/test_erro_negocio_portal.py`.
  6. Testes unitários novos e enriquecidos:
     - `tests/test_session_recovery.py`: testes para seletor de logout e conformidade sintática (R1).
     - `tests/test_contract_runner.py`: testes para navegação incondicional de formulário (R2) e retorno garantido de erro no reset de sessão (R3).
     - `tests/test_worker_error_handling.py`: testes para persistência imediata de ERRO no SQLite/Excel e continuidade do lote no worker (R4).
     - `tests/test_transicao_fase4_5.py`: testes para sucesso imediato, modais SweetAlert, avisos de peso/cubagem, aborto antecipado com erro de negócio/validação e telemetria de diagnóstico no timeout (R5).
- Validação: 116 testes executados e 116 aprovados (100% verde) em 8.92s via `.venv\Scripts\python.exe -m pytest`.
- Riscos e pendências: risco nulo; todas as alterações mantêm isolamento rigoroso, retrocompatibilidade com fluxos existentes e suíte completa de testes unitários herméticos.
