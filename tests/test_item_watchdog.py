from contextlib import contextmanager
from pathlib import Path
import threading
from unittest.mock import MagicMock

import pytest

from backend.app.infrastructure import item_watchdog as watcher
from backend.app.infrastructure import observability


class ManualTimer:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.daemon = False
        self.cancelled = False

    def start(self):
        pass

    def cancel(self):
        self.cancelled = True


@pytest.fixture
def timers(monkeypatch):
    created = []
    def factory(interval, callback):
        timer = ManualTimer(interval, callback)
        created.append(timer)
        return timer
    monkeypatch.setattr(watcher.threading, 'Timer', factory)
    monkeypatch.setenv('JOB_ITEM_WARNING_SECONDS', '180')
    return created


def test_normal_item_cancels_late_callback_without_alert(timers, monkeypatch):
    report = MagicMock()
    monkeypatch.setattr(watcher, 'report_exception', report)
    with watcher.watch_item('job1'):
        assert timers[0].interval == 180
        assert timers[0].daemon is True
    timers[0].callback()  # Late callback race after completion.
    assert timers[0].cancelled
    report.assert_not_called()


def test_disabled_does_not_create_observer(timers, monkeypatch):
    monkeypatch.setenv('JOB_ITEM_WARNING_SECONDS', '0')
    with watcher.watch_item('job1'):
        pass
    assert timers == []


@pytest.mark.parametrize('configured', ['nan', 'inf', '-1', 'invalid', '1e100'])
def test_invalid_limit_uses_safe_default(configured, monkeypatch):
    monkeypatch.setenv('JOB_ITEM_WARNING_SECONDS', configured)
    assert watcher.warning_seconds() == 180


def test_slow_item_warns_once_then_reports_end_in_order(timers, monkeypatch):
    reported = []
    warned = threading.Event()
    def capture(signal, *, component):
        reported.append((type(signal).__name__, observability._job_id.get(), component))
        if isinstance(signal, watcher.ItemExecutionDelayed):
            warned.set()
    monkeypatch.setattr(watcher, 'report_exception', capture)
    with observability.job_context('parent'):
        with watcher.watch_item('job1'):
            observer = threading.Thread(target=timers[0].callback, daemon=True)
            observer.start()
            assert warned.wait(2)
            assert len(reported) == 1
            assert observability._job_id.get() == 'parent'
        observer.join(2)
        assert not observer.is_alive()
    assert reported == [
        ('ItemExecutionDelayed', 'job1', 'item_watchdog'),
        ('ItemExecutionFinishedAfterDelay', 'job1', 'item_watchdog'),
    ]


def test_blocked_telemetry_does_not_block_worker_exit(timers, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    def capture(signal, **kwargs):
        if isinstance(signal, watcher.ItemExecutionDelayed):
            entered.set()
            release.wait(2)
    monkeypatch.setattr(watcher, 'report_exception', capture)
    try:
        with watcher.watch_item('job1'):
            observer = threading.Thread(target=timers[0].callback, daemon=True)
            observer.start()
            assert entered.wait(2)
        # Worker exits the context while its observer is blocked reporting.
        assert not release.is_set()
    finally:
        release.set()
        observer.join(2)
    assert not observer.is_alive()


def test_observer_start_failure_does_not_prevent_business_work(timers, monkeypatch):
    monkeypatch.setattr(ManualTimer, 'start', MagicMock(side_effect=RuntimeError('unavailable')))
    executed = False
    with watcher.watch_item('job1'):
        executed = True
    assert executed


def test_observer_constructor_failure_does_not_prevent_business_work(monkeypatch):
    monkeypatch.setenv('JOB_ITEM_WARNING_SECONDS', '180')
    monkeypatch.setattr(watcher.threading, 'Timer', MagicMock(side_effect=RuntimeError('unavailable')))
    with watcher.watch_item('job1'):
        assert True


def test_business_exception_is_not_suppressed(timers):
    with pytest.raises(ValueError, match='business failure'):
        with watcher.watch_item('job1'):
            raise ValueError('business failure')
    assert timers[0].cancelled


def test_failed_report_does_not_leak_job_context(monkeypatch):
    monkeypatch.setattr(watcher, 'report_exception', MagicMock(side_effect=RuntimeError('sdk unavailable')))
    with observability.job_context('parent'):
        watcher._report(watcher.ItemExecutionDelayed('test'), 'child')
        assert observability._job_id.get() == 'parent'


@pytest.mark.parametrize('cancelled', [False, True])
def test_worker_watches_only_the_item_call(monkeypatch, cancelled):
    from backend.app.infrastructure import worker as module
    active = []
    @contextmanager
    def guard(job_id):
        active.append(job_id)
        try:
            yield
        finally:
            active.pop()
    repository = MagicMock()
    item = MagicMock()
    repository.get_pending_items.return_value = [item]
    repository.get_job.return_value = {'total_items': 1}
    artifacts = MagicMock()
    artifacts.get_job_dir.return_value = Path('unused-output')
    runner = MagicMock()
    def process(current):
        assert current is item
        assert active == ['job-test']
        result = MagicMock()
        result.sucesso = True
        return result
    runner.process_single_item.side_effect = process
    runner.login.side_effect = lambda: pytest.fail('login must not be watched') if active else None
    monkeypatch.setattr(module, 'watch_item', guard)
    monkeypatch.setattr(module, 'ContractRunner', MagicMock(return_value=runner))
    monkeypatch.setattr(module, 'ExcelProcessor', MagicMock())
    job = module.JobWorker('job-test', '', '', 'input.xlsx', repository=repository,
                           artifacts=artifacts, broadcaster_inst=MagicMock())
    if cancelled:
        job._cancel_requested.set()
    job._run_job()
    if cancelled:
        runner.process_single_item.assert_not_called()
    else:
        runner.process_single_item.assert_called_once_with(item)
    assert active == []


def test_signals_pass_real_sdk_sanitizer_without_network(monkeypatch):
    import sentry_sdk
    from sentry_sdk.transport import Transport
    events = []
    guards = []
    class MemoryTransport(Transport):
        def capture_envelope(self, envelope):
            for item in envelope.items:
                event = item.get_event()
                if event is not None:
                    events.append(event)
    real_init = sentry_sdk.init
    def memory_init(**options):
        options['transport'] = MemoryTransport
        guard = real_init(**options)
        guards.append(guard)
        return guard
    monkeypatch.setattr(sentry_sdk, 'init', memory_init)
    monkeypatch.setattr(observability, '_sdk', None)
    monkeypatch.setenv('SENTRY_DSN', 'https://public@example.invalid/1')
    try:
        assert observability.init_observability()
        watcher._report(watcher.ItemExecutionDelayed('sensitive-example'), 'job-test')
        watcher._report(watcher.ItemExecutionFinishedAfterDelay('sensitive-example'), 'job-test')
        sentry_sdk.flush(timeout=1)
        assert len(events) == 2
        assert events[0]['exception']['values'][0]['type'] == 'ItemExecutionDelayed'
        assert events[1]['exception']['values'][0]['type'] == 'ItemExecutionFinishedAfterDelay'
        assert all(event['tags']['job_id'] == 'job-test' for event in events)
        assert all(event['tags']['component'] == 'item_watchdog' for event in events)
        assert 'sensitive-example' not in str(events)
    finally:
        for guard in guards:
            guard.__exit__(None, None, None)
