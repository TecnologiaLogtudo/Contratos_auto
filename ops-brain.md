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

## Próximos passos
- Usar este cérebro como referência para futuras tarefas.
- Atualizar com decisões e resultados de cada ciclo de trabalho.
- Se houver ajuste futuro para LATAM, confirmar qual fluxo está ativo no ambiente: page object novo (`engine/pages/frete_page.py`) ou fase legada (`phases/fase4_frete.py` + `companies/latam.py`).
- Revisar o POP com a operação para ajustar nomes internos e exceções reais observadas em produção, se necessário.
