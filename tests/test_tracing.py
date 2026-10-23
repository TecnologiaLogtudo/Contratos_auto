import base64
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock
import sys

import pytest

from backend.app.infrastructure import observability as obs
from backend.app.infrastructure import tracing


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setattr(tracing, '_provider', None)
    monkeypatch.setattr(tracing, '_tracer', None)
    monkeypatch.setenv('OTEL_TRACING_ENABLED', 'false')
    monkeypatch.delenv('OTEL_TRACES_SAMPLER_ARG', raising=False)
    monkeypatch.delenv('OTEL_EXPORTER_OTLP_PROTOCOL', raising=False)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('OTEL_TRACING_ENABLED', 'true')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'https://otlp-gateway-prod-sa-east-1.grafana.net/otlp')
    encoded = base64.b64encode(b'1889753:test-token-only').decode()
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_HEADERS', 'Authorization=Basic%20' + encoded)


def test_disabled_requires_no_sdk_and_business_executes_once():
    assert tracing.init_tracing() is False
    calls = []
    @tracing.traced('contratos.cotacao', root=True, item_result=True)
    def business():
        calls.append(1)
        return SimpleNamespace(sucesso=True)
    assert business().sucesso
    assert calls == [1]
    assert tracing.current_trace_ids() == {}


def test_config_decodes_python_header_and_appends_signal_once(configured):
    endpoint, headers, ratio = tracing._configuration()
    assert endpoint == 'https://otlp-gateway-prod-sa-east-1.grafana.net/otlp/v1/traces'
    assert headers['Authorization'].startswith('Basic ')
    assert 'test-token-only' not in str(headers)
    assert ratio == 1


@pytest.mark.parametrize('endpoint', [
    'http://example.grafana.net/otlp',
    'https://example.invalid/otlp',
    'https://token@example.grafana.net/otlp',
    'https://example.grafana.net/otlp?token=private',
    'https://example.grafana.net/otlp/v1/traces',
    'https://example.grafana.net:bad/otlp',
])
def test_bad_endpoint_does_not_break_startup_or_log_secrets(configured, monkeypatch, caplog, endpoint):
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_ENDPOINT', endpoint)
    assert tracing.init_tracing() is False
    assert endpoint not in caplog.text
    assert 'test-token-only' not in caplog.text


@pytest.mark.parametrize('ratio', ['nan', 'inf', '-0.1', '1.1', 'invalid'])
def test_invalid_sampling_fails_closed(configured, monkeypatch, ratio):
    monkeypatch.setenv('OTEL_TRACES_SAMPLER_ARG', ratio)
    assert tracing.init_tracing() is False


@pytest.mark.parametrize('header', ['', 'Authorization=Bearer private', 'Cookie=secret',
                                    'Authorization=Basic%20invalid',
                                    'Authorization=Basic%20' + base64.b64encode(b'no-colon').decode()])
def test_invalid_headers_fail_closed(configured, monkeypatch, caplog, header):
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_HEADERS', header)
    assert tracing.init_tracing() is False
    assert 'private' not in caplog.text and 'secret' not in caplog.text


def test_protocol_must_match_http_exporter(configured, monkeypatch):
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_PROTOCOL', 'grpc')
    assert tracing.init_tracing() is False


def test_missing_sdk_does_not_prevent_business(configured, monkeypatch):
    import builtins
    original_import = builtins.__import__
    def absent(name, *args, **kwargs):
        if name.startswith('opentelemetry.exporter'):
            raise ImportError('sdk unavailable')
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', absent)
    assert tracing.init_tracing() is False
    with tracing.trace_span('contratos.cotacao') as span:
        assert span is None


@pytest.fixture
def span_api(monkeypatch):
    package = ModuleType('opentelemetry')
    package.__path__ = []
    api = ModuleType('opentelemetry.trace')
    context = ModuleType('opentelemetry.context')
    context.Context = type('Context', (), {})
    api.Status = lambda status: status
    api.StatusCode = SimpleNamespace(ERROR='ERROR')
    active = []
    @contextmanager
    def use_span(span, **options):
        assert options == {'end_on_exit': False, 'record_exception': False,
                           'set_status_on_exception': False}
        active.append(span)
        try:
            yield span
        finally:
            active.pop()
    api.use_span = use_span
    api.get_current_span = lambda: active[-1]
    package.trace = api
    monkeypatch.setitem(sys.modules, 'opentelemetry', package)
    monkeypatch.setitem(sys.modules, 'opentelemetry.trace', api)
    monkeypatch.setitem(sys.modules, 'opentelemetry.context', context)
    tracer = MagicMock()
    tracer.created_spans = []
    def start(*args, **kwargs):
        span = MagicMock()
        tracer.created_spans.append(span)
        return span
    tracer.start_span.side_effect = start
    monkeypatch.setattr(tracing, '_tracer', tracer)
    return tracer, active


def test_active_root_has_safe_job_tag_and_exits_on_business_exception(span_api):
    tracer, active = span_api
    error = ValueError('PRIVATE-ERP-CONTENT')
    with pytest.raises(ValueError) as caught:
        with tracing.trace_span('contratos.cotacao', root=True, job_id='job-123') as span:
            assert active == [span]
            raise error
    assert caught.value is error
    assert tracer.start_span.call_args.kwargs['attributes'] == {'job_id': 'job-123'}
    assert active == []
    span.end.assert_called_once()
    assert span.set_attribute.call_args_list[-1].args == ('error.type', 'ValueError')
    assert 'PRIVATE-ERP-CONTENT' not in str(span.mock_calls)


def test_unsafe_job_tag_dropped(span_api):
    tracer, _ = span_api
    with tracing.trace_span('contratos.login', job_id='user@example.invalid'):
        pass
    assert tracer.start_span.call_args.kwargs['attributes'] == {}


def test_start_or_end_failure_does_not_repeat_or_break_business(span_api):
    tracer, _ = span_api
    tracer.start_span.side_effect = RuntimeError('observer unavailable')
    calls = []
    @tracing.traced('contratos.cotacao', root=True)
    def business():
        calls.append(1)
        return 42
    assert business() == 42
    assert calls == [1]
    tracer.start_span.side_effect = None
    tracer.start_span.return_value.end.side_effect = RuntimeError('end unavailable')
    assert business() == 42
    assert calls == [1, 1]


def test_handled_false_result_is_error_and_job_context_restored(span_api):
    tracer, active = span_api
    @tracing.traced('contratos.cotacao', root=True, item_result=True)
    def business():
        return SimpleNamespace(sucesso=False, motivo_erro='PRIVATE')
    with obs.job_context('job-test'):
        assert business().sucesso is False
    assert obs.current_job_id() is None
    assert tracer.start_span.call_args.kwargs['attributes']['job_id'] == 'job-test'
    tracer.created_spans[-1].set_status.assert_called_once_with('ERROR')
    tracer.created_spans[-1].set_attribute.assert_called_once_with('operation.outcome', 'error')
    assert active == []


def test_sentry_correlation_keeps_only_valid_ids(monkeypatch):
    monkeypatch.setattr(tracing, 'current_trace_ids', lambda: {'trace_id': 'a' * 32, 'span_id': 'b' * 16})
    sdk = MagicMock()
    monkeypatch.setattr(obs, '_sdk', sdk)
    obs.report_exception(ValueError('PRIVATE'), component='contract_item')
    tags = sdk.new_scope.return_value.__enter__.return_value.set_tag.call_args_list
    assert any(call.args == ('trace_id', 'a' * 32) for call in tags)
    event = {'tags': {'trace_id': 'a' * 32, 'span_id': 'b' * 16, 'url': 'private'},
             'exception': {'values': [{'type': 'ValueError', 'value': 'PRIVATE'}]}}
    assert obs.before_send(event, {})['tags'] == {'trace_id': 'a' * 32, 'span_id': 'b' * 16}
    event['tags']['trace_id'] = 'PRIVATE'
    assert 'trace_id' not in obs.before_send(event, {})['tags']


def test_failed_flush_and_shutdown_do_not_raise(monkeypatch):
    provider = MagicMock()
    provider.force_flush.side_effect = RuntimeError('failed')
    provider.shutdown.side_effect = RuntimeError('failed')
    monkeypatch.setattr(tracing, '_provider', provider)
    monkeypatch.setattr(tracing, '_tracer', MagicMock())
    assert tracing.flush_traces() is False
    tracing.shutdown_tracing()
    assert tracing._provider is None and tracing._tracer is None


def test_real_sdk_runner_hierarchy_and_sampling_without_network(configured, monkeypatch):
    pytest.importorskip('opentelemetry.sdk.trace', reason='Install pinned OTel dependencies to validate real SDK')
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.exporter.otlp.proto.http import trace_exporter
    from opentelemetry.trace import StatusCode
    from backend.app.engine.contract_runner import ContractRunner
    from backend.app.domain.models import ItemContrato

    memory = InMemorySpanExporter()
    exporter_factory = MagicMock(return_value=memory)
    monkeypatch.setattr(trace_exporter, 'OTLPSpanExporter', exporter_factory)
    assert tracing.init_tracing()
    assert exporter_factory.call_args.kwargs['timeout'] == 5
    assert tracing.init_tracing()  # idempotent; no second exporter
    exporter_factory.assert_called_once()
    assert tracing._provider.resource.attributes['service.namespace'] == 'logtudo'
    assert 'process.command_args' not in tracing._provider.resource.attributes
    runner = ContractRunner('PRIVATE-USER', 'PRIVATE-PASSWORD', delay_fases=0)
    runner.page = MagicMock()
    runner.page.url = '/rotinas/formulario.php?rotina=trans_conhecimento'
    runner.page.is_closed.return_value = False
    runner.conhecimento_page = MagicMock()
    runner.frete_page = MagicMock()
    runner.contrato_page = MagicMock()
    runner._take_screenshot = MagicMock()
    runner._reset_session = MagicMock()
    item = ItemContrato(nro_cotacao='123', nome='PRIVATE-NAME', placa='ABC1234', cidade='PRIVATE-CITY',
                        uf='BA', remetente='Latam', data_pagamento='10/08/2026')
    captured_ids = []
    runner.frete_page.preencher_fase4.side_effect = ValueError('PRIVATE-ERROR')
    monkeypatch.setattr('backend.app.engine.contract_runner.report_exception',
                        lambda *a, **kw: captured_ids.append(tracing.current_trace_ids()))
    try:
        with obs.job_context('job-sdk-test'):
            result = runner.process_single_item(item)
        assert result.sucesso is False
        assert tracing.flush_traces()
        spans = memory.get_finished_spans()
        root = next(span for span in spans if span.name == 'contratos.cotacao')
        assert root.parent is None and root.status.status_code == StatusCode.ERROR
        assert root.attributes['job_id'] == 'job-sdk-test'
        assert len(spans) == 4  # root plus phases2/3/4, phase5 did not execute.
        assert all(span.parent.span_id == root.context.span_id for span in spans if span is not root)
        assert captured_ids[0]['trace_id'] == f'{root.context.trace_id:032x}'
        assert all(not span.events for span in spans)
        assert 'PRIVATE' not in str([dict(span.attributes) for span in spans])
        assert tracing.current_trace_ids() == {}
        memory.clear()
        runner.frete_page.preencher_fase4.side_effect = None
        assert runner.process_single_item(item).sucesso
        assert tracing.flush_traces()
        assert len(memory.get_finished_spans()) == 5
        memory.clear()
        from concurrent.futures import ThreadPoolExecutor
        def worker(job):
            with obs.job_context(job):
                with tracing.trace_span('contratos.cotacao', root=True, job_id=obs.current_job_id()):
                    with tracing.trace_span('contratos.fase3.conhecimento'):
                        assert tracing.current_trace_ids()
            assert obs.current_job_id() is None
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(worker, ['parallel-one', 'parallel-two']))
        assert tracing.flush_traces()
        roots = [span for span in memory.get_finished_spans() if span.parent is None]
        assert len(roots) == 2 and roots[0].context.trace_id != roots[1].context.trace_id
        assert {span.attributes['job_id'] for span in roots} == {'parallel-one', 'parallel-two'}
    finally:
        tracing.shutdown_tracing()
    monkeypatch.setenv('OTEL_TRACES_SAMPLER_ARG', '0')
    memory.clear()
    assert tracing.init_tracing()
    try:
        assert runner.process_single_item(item).sucesso
        assert tracing.flush_traces()
        assert memory.get_finished_spans() == ()
    finally:
        tracing.shutdown_tracing()
