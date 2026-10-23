"""Optional, manually scoped traces. No ERP payloads or automatic instrumentation."""
from __future__ import annotations

import base64
from contextlib import contextmanager
from functools import wraps
import logging
import math
import os
import re
from urllib.parse import unquote, urlsplit

logger = logging.getLogger(__name__)
_provider = None
_tracer = None


def _configuration():
    endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', '').strip().rstrip('/')
    url = urlsplit(endpoint)
    if (url.scheme != 'https' or not url.hostname or not url.hostname.endswith('.grafana.net')
            or url.username or url.password or url.query or url.fragment
            or url.path != '/otlp' or url.port not in (None, 443)):
        raise ValueError('Invalid OTLP endpoint')
    if os.getenv('OTEL_EXPORTER_OTLP_PROTOCOL', 'http/protobuf') != 'http/protobuf':
        raise ValueError('Only HTTP/protobuf is supported')
    raw = os.getenv('OTEL_EXPORTER_OTLP_HEADERS', '').strip()
    key, separator, encoded = raw.partition('=')
    authorization = unquote(encoded)
    if not separator or key.lower() != 'authorization' or not authorization.startswith('Basic '):
        raise ValueError('Basic authorization required')
    credentials = base64.b64decode(authorization[6:], validate=True).decode('utf-8')
    user, separator, token = credentials.partition(':')
    if not separator or not user.isdigit() or not token:
        raise ValueError('Invalid OTLP credentials')
    ratio = float(os.getenv('OTEL_TRACES_SAMPLER_ARG', '1.0'))
    if not math.isfinite(ratio) or not 0 <= ratio <= 1:
        raise ValueError('Invalid sample ratio')
    return endpoint + '/v1/traces', {'Authorization': authorization}, ratio


def init_tracing():
    """Disabled by default. Failure cannot prevent application startup."""
    global _provider, _tracer
    if _provider is not None:
        return True
    if os.getenv('OTEL_TRACING_ENABLED', 'false').lower() != 'true':
        return False
    provider = None
    try:
        endpoint, headers, ratio = _configuration()
        from opentelemetry.exporter.otlp.proto.http import Compression
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import SpanLimits, TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

        # Resource(...) intentionally avoids automatic environment/process detectors.
        resource = Resource({
            'service.namespace': 'logtudo',
            'service.name': os.getenv('OTEL_SERVICE_NAME', 'contratos-frete-backend')[:80],
            'service.version': os.getenv('SENTRY_RELEASE', 'unknown')[:128],
            'deployment.environment.name': os.getenv('SENTRY_ENVIRONMENT', 'production')[:32],
        })
        provider = TracerProvider(
            resource=resource, sampler=ParentBased(TraceIdRatioBased(ratio)),
            span_limits=SpanLimits(max_attributes=8, max_events=0, max_links=0,
                                   max_attribute_length=128),
        )
        exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=5,
                                    compression=Compression.Gzip)
        provider.add_span_processor(BatchSpanProcessor(
            exporter, max_queue_size=512, max_export_batch_size=64,
            schedule_delay_millis=5000, export_timeout_millis=5000,
        ))
        _tracer = provider.get_tracer('logtudo.contratos', '1')
        _provider = provider  # Private provider avoids changing other libraries' globals.
        return True
    except Exception:
        if provider is not None:
            try:
                provider.shutdown()
            except Exception:
                pass
        logger.warning('Tracing indisponivel; aplicacao continua sem traces. Conferir configuracao/dependencias.')
        return False


def mark_error(span, error=None):
    if span is None:
        return
    try:
        from opentelemetry.trace import Status, StatusCode
        span.set_status(Status(StatusCode.ERROR))
        span.set_attribute('operation.outcome', 'error')
        if error is not None:
            span.set_attribute('error.type', type(error).__name__[:80])
    except Exception:
        pass


@contextmanager
def trace_span(name, *, root=False, job_id=None):
    """Caller supplies static span names. Business exceptions always propagate."""
    span = manager = None
    if _tracer is not None:
        try:
            from opentelemetry.context import Context
            from opentelemetry.trace import use_span
            attributes = {}
            if isinstance(job_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', job_id):
                attributes['job_id'] = job_id
            span = _tracer.start_span(name, context=Context() if root else None,
                                      attributes=attributes)
            manager = use_span(span, end_on_exit=False, record_exception=False,
                               set_status_on_exception=False)
            manager.__enter__()
        except Exception:
            if span is not None:
                try:
                    span.end()
                except Exception:
                    pass
            span = manager = None
    try:
        yield span
    except BaseException as error:
        mark_error(span, error)
        raise
    finally:
        if manager is not None:
            try:
                manager.__exit__(None, None, None)
            except Exception:
                pass
        if span is not None:
            try:
                span.end()
            except Exception:
                pass


def traced(name, *, root=False, item_result=False):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            from .observability import current_job_id
            with trace_span(name, root=root, job_id=current_job_id()) as span:
                result = function(*args, **kwargs)
                if item_result and getattr(result, 'sucesso', None) is False:
                    mark_error(span)
                return result
        return wrapped
    return decorate


def current_trace_ids():
    if _tracer is None:
        return {}
    try:
        from opentelemetry.trace import get_current_span
        context = get_current_span().get_span_context()
        if context.is_valid:
            return {'trace_id': f'{context.trace_id:032x}', 'span_id': f'{context.span_id:016x}'}
    except Exception:
        pass
    return {}


def flush_traces(timeout_millis=10000):
    # Only diagnostics/shutdown; never called for each business item.
    try:
        return bool(_provider and _provider.force_flush(timeout_millis=timeout_millis))
    except Exception:
        return False


def shutdown_tracing():
    global _provider, _tracer
    provider, _provider, _tracer = _provider, None, None
    if provider is not None:
        try:
            provider.shutdown()
        except Exception:
            logger.warning('Falha ao finalizar tracing; aplicacao continua.')
