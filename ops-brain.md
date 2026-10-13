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

## Próximos passos
- Usar este cérebro como referência para futuras tarefas.
- Atualizar com decisões e resultados de cada ciclo de trabalho.
- Realizar deploy no Coolify e verificar se a rota WebSocket `/ws/jobs/{job_id}` conecta imediatamente sem advertências.
- Monitorar execuções reais com cotações com erro (como Perfil de Apropriação) para verificar a transição suave com logout e novo login entre os itens.
- Se houver ajuste futuro para LATAM, confirmar qual fluxo está ativo no ambiente: page object novo (`engine/pages/frete_page.py`) ou fase legada (`phases/fase4_frete.py` + `companies/latam.py`).
- Revisar o POP com a operação para ajustar nomes internos e exceções reais observadas em produção, se necessário.
- Ao iniciar uma nova automação web, copiar `templates/web-automation-interface`, editar `src/template.config.js` e implementar `BACKEND_CONTRACT.md`.



