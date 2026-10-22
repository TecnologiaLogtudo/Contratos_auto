# Incidentes — Contratos de frete

Erros e ocorrências ficam no GlitchTip; trabalho de investigação/correção fica nas Issues do repositório e no Project Logtudo — Incidentes e Melhorias.

## Triagem

1. Confirmar impacto atual e verificar se o evento veio de teste controlado.
2. Procurar Issue existente com o mesmo link de incidente e ambiente.
3. Se existir, adicionar recorrência e novas evidências; não abrir outra Issue por evento.
4. Se não existir e houver ação necessária, abrir o formulário Incidente de produção.
5. Definir responsável (Assignee), severidade e Status no Project.

O identificador GlitchTip agrupa ocorrências, mas não prova causa comum. Avaliar pilha, impacto e regras de negócio antes de classificar como defeito. FormFillError pode representar dado inválido ou mudança de tela; a mensagem sanitizada sozinha não permite decidir.

## Severidade e fluxo

- P0: operação crítica indisponível ou risco à integridade dos dados.
- P1: fluxo principal bloqueado e sem alternativa.
- P2: falha parcial com alternativa operacional.
- P3: impacto baixo ou ação preventiva.
- A classificar: impacto ainda não confirmado; precisa de triagem.

Fluxo do Project: Backlog → Triagem → Em andamento → Validação → Concluído.
Uma Issue concluída precisa de evidência de correção/contorno e validação operacional, não apenas ausência de um novo alerta. GlitchTip pode manter eventos históricos após a correção. Reabrir ou atualizar a Issue se a mesma causa persistir; abrir nova apenas quando a causa/ação for distinta e vincular o histórico.

## Dados nas Issues

Incluir link do GlitchTip, ambiente, release, impacto, horário/fuso, reprodução segura, job_id quando disponível e critério de resolução. O webhook atual não inclui job_id: abrir o evento/registro local para obtê-lo, sem inventar.

Não registrar credenciais do ERP, tokens, DSN, cookies, dados de clientes, planilhas ou URLs autenticadas de webhook. Atribuir responsável e prazo no Project durante triagem. Incidente descartado como teste deve registrar esse motivo.

## Automação

Fase inicial: Telegram avisa; operador faz triagem e cria/atualiza a Issue. Não há sincronização automática GlitchTip/GitHub nem criação por ocorrência. Automatizar somente após definir deduplicação, permissões e política de reabertura.
