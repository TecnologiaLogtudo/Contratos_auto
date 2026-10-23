"""Optional error reporting; ERP payloads remain in local operational records."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
import re

logger = logging.getLogger(__name__)
_sdk = None
_job_id = ContextVar('observability_job_id', default=None)


def before_send(event, hint):
    """Allow only diagnostic metadata, exception types and code locations."""
    clean = {key: event[key] for key in (
        'event_id', 'timestamp', 'level', 'platform', 'release', 'environment', 'sdk',
    ) if key in event}
    clean['tags'] = {key: value for key, value in event.get('tags', {}).items()
                     if key in ('service', 'component', 'job_id')}
    for key, length in (('trace_id', 32), ('span_id', 16)):
        value = event.get('tags', {}).get(key)
        if isinstance(value, str) and re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value):
            clean['tags'][key] = value
    values = []
    for exception in event.get('exception', {}).get('values', []):
        value = {
            'type': exception.get('type', 'Exception'),
            'value': 'Mensagem omitida; consultar registros locais pelo job_id.',
        }
        frames = exception.get('stacktrace', {}).get('frames', [])
        if frames:
            value['stacktrace'] = {'frames': [
                {key: frame[key] for key in ('filename', 'function', 'module', 'lineno', 'in_app')
                 if key in frame} for frame in frames
            ]}
        mechanism = exception.get('mechanism')
        if mechanism:
            value['mechanism'] = {key: mechanism[key] for key in ('type', 'handled') if key in mechanism}
        values.append(value)
    if not values:
        return None  # No raw log/message events in the first phase.
    clean['exception'] = {'values': values}
    return clean


def init_observability():
    global _sdk
    if not os.getenv('SENTRY_DSN', '').strip():
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=os.environ['SENTRY_DSN'],
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
            release=os.getenv('SENTRY_RELEASE') or None,
            default_integrations=False,
            auto_enabling_integrations=False,
            integrations=[FastApiIntegration(), StarletteIntegration()],
            send_default_pii=False,
            include_local_variables=False,
            include_source_context=False,
            max_request_body_size='never',
            max_breadcrumbs=0,
            traces_sample_rate=0.0,
            profiles_sample_rate=0.0,
            enable_logs=False,
            enable_metrics=False,
            auto_session_tracking=False,
            send_client_reports=False,
            transport_queue_size=100,
            before_send=before_send,
        )
        sentry_sdk.set_tag('service', 'contratos-auto-backend')
        _sdk = sentry_sdk
        return True
    except Exception:
        logger.warning('Observabilidade indisponivel; aplicacao continua com registros locais.')
        return False


def current_job_id():
    return _job_id.get()


@contextmanager
def job_context(job_id):
    token = _job_id.set(job_id)
    try:
        yield
    finally:
        _job_id.reset(token)


def report_exception(error, *, component):
    if _sdk is None:
        return None
    try:
        # A new scope prevents one worker/item leaking its tags to another.
        with _sdk.new_scope() as scope:
            scope.set_tag('component', component)
            if _job_id.get():
                scope.set_tag('job_id', _job_id.get())
            from .tracing import current_trace_ids
            for key, value in current_trace_ids().items():
                scope.set_tag(key, value)
            return _sdk.capture_exception(error)
    except Exception:
        logger.warning('Falha ao reportar incidente; registros locais preservados.')
        return None
