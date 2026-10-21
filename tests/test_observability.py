from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import MagicMock
import sys
from types import ModuleType
import pytest

from backend.app.infrastructure import observability as obs


def test_event_allowlist_removes_erp_data_and_keeps_stack():
    event = {
        'event_id': 'abc', 'request': {'data': 'senha', 'headers': {'Cookie': 'session'}},
        'user': {'email': 'private@example.invalid'}, 'extra': {'usuario': 'erp'},
        'breadcrumbs': {'values': [{'message': 'senha'}]}, 'message': 'senha',
        'tags': {'service': 'contratos-auto-backend', 'job_id': 'job1', 'usuario': 'erp'},
        'exception': {'values': [{
            'type': 'ValueError', 'value': 'senha=supersecret',
            'stacktrace': {'frames': [{
                'filename': 'runner.py', 'lineno': 42, 'function': 'run',
                'vars': {'senha': 'supersecret'}, 'context_line': 'secret', 'abs_path': '/private',
            }]},
        }]},
    }
    clean = obs.before_send(event, {})
    assert 'supersecret' not in str(clean)
    assert not {'request', 'user', 'extra', 'breadcrumbs', 'message'} & clean.keys()
    assert clean['tags'] == {'service': 'contratos-auto-backend', 'job_id': 'job1'}
    assert clean['exception']['values'][0]['stacktrace']['frames'][0] == {
        'filename': 'runner.py', 'lineno': 42, 'function': 'run',
    }
    assert event['exception']['values'][0]['value'] == 'senha=supersecret'


def test_log_only_events_are_dropped():
    assert obs.before_send({'message': 'sensitive raw log'}, {}) is None


def test_without_dsn_sdk_is_not_required(monkeypatch):
    monkeypatch.delenv('SENTRY_DSN', raising=False)
    monkeypatch.setattr(obs, '_sdk', None)
    assert obs.init_observability() is False
    assert obs.report_exception(ValueError('test'), component='worker') is None


def test_init_configures_error_only_collection(monkeypatch):
    sdk = ModuleType('sentry_sdk')
    sdk.init = MagicMock()
    sdk.set_tag = MagicMock()
    monkeypatch.setitem(sys.modules, 'sentry_sdk', sdk)
    for module_name, integration_name in (
        ('sentry_sdk.integrations.fastapi', 'FastApiIntegration'),
        ('sentry_sdk.integrations.starlette', 'StarletteIntegration'),
    ):
        module = ModuleType(module_name)
        setattr(module, integration_name, MagicMock())
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setenv('SENTRY_DSN', 'https://public@example.invalid/1')
    monkeypatch.setattr(obs, '_sdk', None)
    assert obs.init_observability() is True
    options = sdk.init.call_args.kwargs
    assert options['before_send'] is obs.before_send
    assert options['include_local_variables'] is False
    assert options['max_request_body_size'] == 'never'
    assert options['traces_sample_rate'] == 0
    assert options['default_integrations'] is False
    assert options['enable_logs'] is False


def test_sdk_init_failure_does_not_break_startup(monkeypatch):
    sdk = ModuleType('sentry_sdk')
    sdk.init = MagicMock(side_effect=ValueError('invalid dsn'))
    monkeypatch.setitem(sys.modules, 'sentry_sdk', sdk)
    for module_name, integration_name in (
        ('sentry_sdk.integrations.fastapi', 'FastApiIntegration'),
        ('sentry_sdk.integrations.starlette', 'StarletteIntegration'),
    ):
        module = ModuleType(module_name)
        setattr(module, integration_name, MagicMock())
        monkeypatch.setitem(sys.modules, module_name, module)
    monkeypatch.setenv('SENTRY_DSN', 'invalid')
    monkeypatch.setattr(obs, '_sdk', None)
    assert obs.init_observability() is False
    assert obs._sdk is None


def test_report_failure_does_not_interrupt_business_flow(monkeypatch):
    sdk = MagicMock()
    sdk.new_scope.side_effect = RuntimeError('transport unavailable')
    monkeypatch.setattr(obs, '_sdk', sdk)
    assert obs.report_exception(ValueError('test'), component='worker') is None


def test_job_context_isolated_and_restored_across_threads(monkeypatch):
    reports = []
    @contextmanager
    def new_scope():
        scope = MagicMock()
        yield scope
        reports.append(scope.set_tag.call_args_list)
    sdk = MagicMock()
    sdk.new_scope.side_effect = new_scope
    monkeypatch.setattr(obs, '_sdk', sdk)
    def report(job):
        with obs.job_context(job):
            obs.report_exception(ValueError('test'), component='worker')
        assert obs._job_id.get() is None
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(report, ['job1', 'job2']))
    ids = {call.args[1] for calls in reports for call in calls if call.args[0] == 'job_id'}
    assert ids == {'job1', 'job2'}


def test_handled_item_error_is_reported_before_session_reset(monkeypatch):
    from backend.app.engine import contract_runner as runner_module
    from backend.app.domain.models import ItemContrato
    runner = runner_module.ContractRunner(usuario='erp', senha='secret')
    runner.page = MagicMock()
    runner.page.url = '/rotinas/formulario.php?rotina=trans_conhecimento'
    runner.page.is_closed.return_value = False
    runner.conhecimento_page = MagicMock()
    runner.conhecimento_page.preencher_fase3.side_effect = ValueError('controlled')
    runner._take_screenshot = MagicMock()
    runner._reset_session = MagicMock()
    capture = MagicMock()
    monkeypatch.setattr(runner_module, 'report_exception', capture)
    item = ItemContrato(nro_cotacao='101', nome='TESTE', placa='ABC1234', cidade='Salvador',
                        uf='BA', remetente='Latam', data_pagamento='10/08/2026')
    assert runner.process_single_item(item).sucesso is False
    assert capture.call_args.kwargs == {'component': 'contract_item'}
    runner._reset_session.assert_called_once()


def test_unhandled_worker_error_has_job_context(monkeypatch):
    from backend.app.infrastructure.worker import JobWorker
    sdk = MagicMock()
    monkeypatch.setattr(obs, '_sdk', sdk)
    worker = JobWorker(job_id='job-test', usuario='erp', senha='secret', excel_path='test.xlsx')
    worker._run_job = MagicMock(side_effect=ValueError('controlled'))
    with pytest.raises(ValueError):
        worker._run()
    tags = sdk.new_scope.return_value.__enter__.return_value.set_tag.call_args_list
    assert any(call.args == ('job_id', 'job-test') for call in tags)
    assert obs._job_id.get() is None
