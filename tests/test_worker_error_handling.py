"""Testes unitários para o isolamento de erro e persistência imediata no Worker (R4)."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from backend.app.domain.models import ItemContrato, ItemResult, ItemStatus
from backend.app.infrastructure import worker as module


@contextmanager
def dummy_watch_item(job_id: str):
    yield


def test_worker_persists_item_error_immediately_on_exception(monkeypatch):
    """Garante que exceções não tratadas no processamento de um item são capturadas,
    registram ItemStatus.ERRO imediatamente no SQLite e Excel, salvam o relatório
    e permitem que os itens seguintes continuem sendo processados.
    """
    repo = MagicMock()
    excel_proc = MagicMock()
    runner = MagicMock()
    artifacts = MagicMock()
    artifacts.get_job_dir.return_value = Path("dummy-dir")

    item1 = ItemContrato(nro_cotacao="101", remetente="Latam", status=ItemStatus.PENDENTE)
    item2 = ItemContrato(nro_cotacao="102", remetente="Latam", status=ItemStatus.PENDENTE)
    repo.get_pending_items.return_value = [item1, item2]
    repo.get_job.return_value = {"total_items": 2}

    # Item 1 lança exceção grave; Item 2 é processado com sucesso
    runner.process_single_item.side_effect = [
        RuntimeError("Queda súbita do navegador"),
        ItemResult(nro_cotacao="102", status=ItemStatus.CONCLUIDO, sucesso=True, cte_number="CTE-1234"),
    ]
    runner.page = None

    monkeypatch.setattr(module, "watch_item", dummy_watch_item)
    monkeypatch.setattr(module, "ContractRunner", MagicMock(return_value=runner))
    monkeypatch.setattr(module, "ExcelProcessor", MagicMock(return_value=excel_proc))

    worker = module.JobWorker("test-job-01", "u", "p", "test.xlsx", repository=repo, artifacts=artifacts, broadcaster_inst=MagicMock())
    worker._save_and_register_report = MagicMock()

    worker._run_job()

    # Verifica se Item 1 registrou ERRO imediatamente no SQLite
    repo.update_item_result.assert_any_call(
        job_id="test-job-01",
        nro_cotacao="101",
        status=ItemStatus.ERRO,
        error_message="Exceção durante processamento do item: Queda súbita do navegador",
        duration_seconds=pytest.approx(0.0, abs=5.0),
    )

    # Verifica se Item 1 foi marcado no ExcelProcessor
    excel_proc.mark_error.assert_called_with("101", "Exceção durante processamento do item: Queda súbita do navegador")

    # Verifica se o relatório foi salvo imediatamente na ocorrência do erro do item 1
    assert worker._save_and_register_report.call_count >= 1

    # Verifica se Item 2 continuou a ser processado (loop não foi quebrado)
    assert runner.process_single_item.call_count == 2
    repo.update_item_result.assert_any_call(
        job_id="test-job-01",
        nro_cotacao="102",
        status=ItemStatus.CONCLUIDO,
        cte_number="CTE-1234",
        extracted_nf=None,
        extracted_nro_pedido=None,
        extracted_obs_interna=None,
        duration_seconds=pytest.approx(0.0, abs=5.0),
    )


def test_worker_persists_item_error_when_result_not_sucesso(monkeypatch):
    """Garante que retorno de ItemResult com sucesso=False salva imediatamente o relatório e registra ERRO."""
    repo = MagicMock()
    excel_proc = MagicMock()
    runner = MagicMock()
    artifacts = MagicMock()
    artifacts.get_job_dir.return_value = Path("dummy-dir")

    item1 = ItemContrato(nro_cotacao="201", remetente="Latam", status=ItemStatus.PENDENTE)
    repo.get_pending_items.return_value = [item1]
    repo.get_job.return_value = {"total_items": 1}

    runner.process_single_item.return_value = ItemResult(
        nro_cotacao="201",
        status=ItemStatus.ERRO,
        sucesso=False,
        motivo_erro="Validação de negócio reprovada",
    )
    runner.page = None

    monkeypatch.setattr(module, "watch_item", dummy_watch_item)
    monkeypatch.setattr(module, "ContractRunner", MagicMock(return_value=runner))
    monkeypatch.setattr(module, "ExcelProcessor", MagicMock(return_value=excel_proc))

    worker = module.JobWorker("test-job-02", "u", "p", "test.xlsx", repository=repo, artifacts=artifacts, broadcaster_inst=MagicMock())
    worker._save_and_register_report = MagicMock()

    worker._run_job()

    repo.update_item_result.assert_any_call(
        job_id="test-job-02",
        nro_cotacao="201",
        status=ItemStatus.ERRO,
        error_message="Validação de negócio reprovada",
        duration_seconds=pytest.approx(0.0, abs=5.0),
    )
    excel_proc.mark_error.assert_called_with("201", "Validação de negócio reprovada")
    # Salvo imediatamente no erro e ao término
    assert worker._save_and_register_report.call_count >= 1
