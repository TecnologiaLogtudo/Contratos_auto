# Traces do piloto Contratos de frete

## Escopo

OTel SDK1.45.1 e exportador OTLP/HTTP1.45.1 (extra requests), versões verificadas no PyPI oficial. Nenhum Collector/Uptrace/banco novo. SDK opcional, OTEL_TRACING_ENABLED=false por padrão. Sem auto-instrumentação HTTP/SQL/FastAPI/Playwright, logs, métricas ou profiling. Recurso usa allowlist explícita de service.namespace/name/version/ambiente, sem detectores de processo ou argumentos de linha de comando.

Fluxo web ativo: ContractRunner.process_single_item cria raiz contratos.cotacao independentemente da thread da API. Quatro spans filhos: contratos.fase2.preparacao, contratos.fase3.conhecimento, contratos.fase4.frete e contratos.fase5.contrato. Login/fechamento separados quando fora do item; recuperação de sessão e relogin dentro da cotação tornam-se filhos. Um item normal gera5 spans; esperas entre fases3/4 entram nesses spans. Não instrumenta individualmente cliques/polling, HTTP de navegador, banco, planilha, arquivo/screenshot ou geração de relatório. Fluxo legado ContractRunner.run não recebeu as quatro fases nesta entrega; escopo é worker web do piloto.

Resultado sucesso=False marca raiz ERROR mesmo quando runner trata exceção. Spans de fase com erro recebem status ERROR e classe do erro. Não exportar mensagens, stack, eventos, credenciais, usuários, NF/cotação comercial ou planilha. job_id técnico é validado por formato/tamanho. Exceções de negócio e resultados mantêm comportamento original; tracing não cancela nem repete emissão.

Batch em background: fila512 spans, batch64, janela5s, timeout de exportação5s, gzip e amostragem por trace com ParentBased/TraceIdRatioBased. Fila cheia/falha de transporte pode perder telemetria; emissão não aguarda rede por item. Flush só em diagnóstico/finalização. Sem persistência de fila e sem recuperação de traces em execução após processo morrer. Desligamento normal tenta enviar pendentes; kill/restart brusco pode perder dados.

## Variáveis do backend

OTEL_TRACING_ENABLED=true
OTEL_SERVICE_NAME=contratos-frete-backend
OTEL_TRACES_SAMPLER_ARG=1.0
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-sa-east-1.grafana.net/otlp
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<VALOR_BASE64_FORNECIDO_PELO_PORTAL>

Última linha é placeholder: usar valor real fornecido pelo portal, apenas como segredo no Coolify. Não colar no chat/Git/log. Remover prefixo export/aspas da sintaxe shell quando cadastrar campo individual no Coolify. Basic%20 é aceito e decodificado; espaço literal Basic também é aceito. Usar apenas o par Authorization, sem headers extras. Endpoint base deve ser HTTPS de domínio .grafana.net e caminho /otlp; o código acrescenta /v1/traces uma única vez. Não definir endpoint sinal-específico adicional nesta implementação; o código usa as variáveis genéricas explicitamente.

Preservar SENTRY_DSN, SENTRY_ENVIRONMENT=production, JOB_ITEM_WARNING_SECONDS=180 e atualizar SENTRY_RELEASE para revisão implantada; esta release também identifica service.version dos traces. Manter tracing Sentry desligado.

Taxa1.0 acompanha todas as cotações do piloto. Para serviços futuros com maior volume, configurar taxa independente. Head sampling<1 pode perder traces de erros/lentidão; GlitchTip continua independente. IDs locais podem existir para trace não amostrado.

## Correlação com erros

report_exception adiciona tags trace_id e span_id válidas enquanto houver span ativo. GlitchTip preserva apenas hex de32/16 caracteres. Procurar esse trace_id no Grafana/Tempo; não foi criado link automático no Telegram nem integração nativa GlitchTip/Tempo. Erro tratado do item é capturado no span raiz porque a fase já terminou. Watchdog usa outra thread sem copiar contexto OTel: seus dois sinais continuam correlacionados por job_id, sem garantia de trace_id. Não propagar dados comerciais como baggage.

## Teste manual sem ERP

Depois do deploy/variáveis, terminal do backend no diretório /app:

python -m backend.app.infrastructure.trace_smoke --send --with-error

O comando inicia processo separado e envia um trace sintético com filho e um erro controlado GlitchTip/Telegram. Não chama ERP/DB/runner nem emite contrato. Só é executado com --send. Guard main evita envio ao importar/descobrir testes. Imprime referência sintética e IDs locais, nunca segredo. Flush bem-sucedido só indica fila processada, não aceitação HTTP remota. Conferir trace raiz/filho no Grafana, ambos ERROR no teste com erro; tags trace_id no GlitchTip e alerta no Telegram. Resolver somente incidente sintético depois da conferência. Executar sem --with-error se quiser apenas trace sintético.

Para procurar: Grafana Explore/Traces → fonte Tempo da stack → buscar trace_id impresso ou consultar { resource.service.name = "contratos-frete-backend" }. Escopo de tempo recente. Não confundir ausência de métricas/dashboards APM com falha de ingestão: esta entrega envia traces somente.

## Rollback

OTEL_TRACING_ENABLED=false e redeploy em janela sem lote ativo. Mantém SDK instalado, desativa nova coleta sem tocar em Sentry/watchdog/DB. Restart interrompe threads de jobs: nunca fazê-lo com lote ativo. Não restaurar estado anterior ao watchdog por engano.

## Aceite e expansão

Antes do deploy: instalar requirements e executar testes/test_tracing.py, test_observability.py, test_item_watchdog.py, test_contract_runner.py sem falhas ou skips de SDK real. Teste real usa InMemorySpanExporter e não envia HTTP/ERP; confere hierarquia, falha tratada, sanitização, taxa0 e threads independentes. Testes simulados cobrem falha do SDK/observador e configuração inválida. Regressão inteira segue checks habituais do projeto.

Medir ingestão em Cost Management and Billing → Usage → Traces em dias/lotes representativos. Plano Free,50GB mensais compartilhados,14dias; avaliação14dias ampliada não representa franquia definitiva. Instrumentação não cobra licença, mas trafega bytes: confirmar franquia da VPS. Sem upgrade pago/cartão. Adicionar sistemas um a um, com service.name/token próprios e amostragem por serviço; SDK/exportador pode ser reutilizado por tecnologia, não copiar lógica de cotação para outros domínios.

Backup adiado e monitor externo excluído por decisão explícita. Lote real pós-instrumentação aguardará próxima execução disponível.
