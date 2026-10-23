# Aviso de duração por cotação

Máximo normal estimado pelo operador: 90 segundos. Limite inicial proposto: JOB_ITEM_WARNING_SECONDS=180, configurável em runtime e propagado pelo Compose. Valor0 desativa. Valores inválidos/negativos/não finitos usam180 e deixam aviso local.

Um Timer daemon acompanha apenas a chamada process_single_item de cada cotação do worker web. Sem item em processamento, nenhuma supervisão é criada. Pausas e espera entre itens não contam. Pedido de pausa/cancelamento durante uma chamada não a interrompe no código atual; a chamada ainda em curso continua observada até terminar.

Acima do limite, evento Sentry ItemExecutionDelayed indica possível travamento/lentidão, com componente item_watchdog e job_id. É um aviso consultivo, não muda resultado, estado de job, sessão ERP nem tenta novamente. Quando a chamada sai, mesmo por erro, ItemExecutionFinishedAfterDelay informa fim da chamada prolongada; não significa que o contrato foi emitido com sucesso e não resolve automaticamente uma Issue anterior.

A sanitização existente omite a mensagem bruta e mantém tipo/pilha/tags permitidas. O operador identifica os sinais pelos tipos acima e consulta job_id no GlitchTip; o webhook atual não inclui job_id no texto Telegram. Regras de frequência do GlitchTip podem agrupar/suprimir avisos; captura local não é garantia de uma mensagem por item.

O worker não espera o envio da telemetria. Um Timer permanece esperando conclusão apenas para itens que excederam o limite e morre quando a chamada sai ou quando o processo termina. Se o processo inteiro cair, esse supervisor também cai: ele não detecta jobs órfãos após restart nem substitui monitor externo. Login inicial, geração/salvamento de relatórios, screenshots fora da chamada e fechamento do browser não são cobertos nesta primeira implementação. Não confundir duração da chamada inteira com medição de cada fase/progresso.

## Aplicação

Revisar e aplicar contratos-watchdog.patch a partir do repositório, executar testes, commitar/publicar pelo fluxo habitual. No Coolify backend: JOB_ITEM_WARNING_SECONDS=180. Atualizar SENTRY_RELEASE para o SHA implantado. Não reduzir limiar em produção para simular atraso nem emitir contrato real para testar; testes automatizados simulam Timer/worker.

Rollback da funcionalidade: configurar JOB_ITEM_WARNING_SECONDS=0 e recriar container para novas chamadas. Timers já iniciados leem limite no início e não mudam dinamicamente. Uma reimplantação do backend interrompe threads/lotes ativos; escolher janela sem lote em andamento. Nenhum deploy foi feito por esta sessão.
