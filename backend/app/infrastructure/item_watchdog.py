"""Advisory duration warning around one active item; never retries ERP work."""
from __future__ import annotations

from contextlib import contextmanager
import logging
import math
import os
import threading

from .observability import job_context, report_exception

logger = logging.getLogger(__name__)


class ItemExecutionDelayed(RuntimeError):
    """An active item exceeded the advisory duration limit, not proof of deadlock."""


class ItemExecutionFinishedAfterDelay(RuntimeError):
    """The prolonged call ended; this does not imply successful issuance."""


def warning_seconds() -> float:
    try:
        value = float(os.getenv('JOB_ITEM_WARNING_SECONDS', '180'))
        if math.isfinite(value) and 0 <= value <= threading.TIMEOUT_MAX:
            return value
    except (TypeError, ValueError):
        pass
    logger.warning('JOB_ITEM_WARNING_SECONDS invalido; usando 180 segundos.')
    return 180.0


def _report(signal, job_id):
    try:
        # ContextVars do not propagate automatically into the Timer thread.
        with job_context(job_id):
            report_exception(signal, component='item_watchdog')
        logger.warning('%s (job_id=%s)', type(signal).__name__, job_id)
    except Exception:
        logger.warning('Falha no aviso de duracao; processamento nao interrompido.')


@contextmanager
def watch_item(job_id):
    seconds = warning_seconds()
    if seconds == 0:
        yield
        return

    finished = threading.Event()

    def notify():
        if finished.is_set():
            return
        _report(ItemExecutionDelayed('Cotacao excedeu o limite de duracao.'), job_id)
        # Wait only in the observer thread; the worker never waits for telemetry.
        finished.wait()
        _report(ItemExecutionFinishedAfterDelay('Chamada prolongada terminou; verificar resultado do item.'), job_id)

    try:
        timer = threading.Timer(seconds, notify)
        timer.daemon = True
        timer.start()
    except Exception:
        finished.set()
        logger.warning('Supervisor de duracao indisponivel; processamento continua.')
        yield
        return

    try:
        yield
    finally:
        finished.set()
        timer.cancel()
