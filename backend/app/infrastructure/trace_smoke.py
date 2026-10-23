"""Manual synthetic acceptance test; never imported to send data by pytest."""
def main():
    import argparse
    import os
    import time
    from uuid import uuid4
    from backend.app.infrastructure import tracing
    from backend.app.infrastructure.observability import init_observability, job_context, report_exception

    parser = argparse.ArgumentParser(description='Send a synthetic trace, without ERP/DB calls.')
    parser.add_argument('--send', action='store_true', help='Explicitly send synthetic telemetry')
    parser.add_argument('--with-error', action='store_true', help='Also send one controlled error to GlitchTip/Telegram')
    args = parser.parse_args()
    if not args.send:
        parser.error('Use --send to run this manual acceptance test.')
    if not tracing.init_tracing():
        raise SystemExit('Tracing nao iniciou. Conferir OTEL_TRACING_ENABLED, variaveis e dependencias.')
    if args.with_error and not init_observability():
        tracing.shutdown_tracing()
        raise SystemExit('Sentry nao iniciou; teste de correlacao pendente.')
    reference = 'aceite-traces-' + uuid4().hex[:12]
    print('Servico:', os.getenv('OTEL_SERVICE_NAME', 'contratos-frete-backend'))
    print('Referencia sintetica:', reference)
    try:
        with job_context(reference):
            with tracing.trace_span('contratos.teste', root=True, job_id=reference) as root:
                ids = tracing.current_trace_ids()
                print('Trace ID local:', ids.get('trace_id'))
                try:
                    with tracing.trace_span('contratos.teste.etapa'):
                        time.sleep(0.1)
                        if args.with_error:
                            raise RuntimeError('Teste sintetico de correlacao; sem emissao real.')
                except RuntimeError as error:
                    # Root error is marked explicitly because the exception is handled here.
                    tracing.mark_error(root, error)
                    event_id = report_exception(error, component='trace_acceptance')
                    print('Evento GlitchTip ID local:', event_id)
        print('Fila processada:', tracing.flush_traces())
        if args.with_error:
            import sentry_sdk
            sentry_sdk.flush(timeout=10)
        print('Conferir trace no Grafana e, se solicitado, evento/trace_id no GlitchTip e alerta Telegram.')
        print('ID local ou fila processada nao comprovam entrega remota.')
    finally:
        tracing.shutdown_tracing()


if __name__ == '__main__':
    main()
