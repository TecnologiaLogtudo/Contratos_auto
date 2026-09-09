"""Testes unitários e de integração para as rotas da API FastAPI."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path
import openpyxl
import pytest
from starlette.datastructures import UploadFile

from backend.app.api.routes import (
    get_job_artifacts,
    get_job_details,
    get_job_logs,
    get_selectors_config,
    list_jobs,
    upload_and_validate,
)
from backend.app.infrastructure.database import Database
from backend.app.infrastructure.repository import JobRepository


@pytest.mark.anyio
async def test_upload_and_validate_endpoint():
    wb = openpyxl.Workbook()
    ws = wb.active

    for r in range(1, 7):
        ws.append([f"Cabecalho_{r}"])

    header_row = [
        "Status", "Nro Cotação", "", "", "", "", "Validade", "", "", "",
        "Categoria Veículo", "Remetente", "Cidade / UF", "", "", "",
        "Frete a Pagar", "", "Frete Negociado", "", "", "",
        "Motorista / Placa"
    ]
    ws.append(header_row)

    row_data = [
        None, "1832067", None, None, None, None, "15/08/2026", None, None, None,
        "TOCO", "LACTALIS DO BRASIL", "SALVADOR / BA", None, None, None,
        "R$ 500,00", None, "R$ 600,00", None, None, None,
        "JOAO PEDRO BRA2E19 15/08/2026"
    ]
    ws.append(row_data)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    wb.close()

    upload_file_obj = UploadFile(
        file=buf,
        filename="planilha_api_teste.xlsx",
        headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )

    response = await upload_and_validate(file=upload_file_obj)

    import re
    assert response.is_valid is True
    assert re.match(r"^\d{6}-\d{5}$", response.job_id) is not None
    assert response.valid_rows_count >= 1
    assert response.total_rows >= 1

    # Testa listagem
    jobs_res = await list_jobs(limit=10, offset=0)
    assert "jobs" in jobs_res
    assert any(j["id"] == response.job_id for j in jobs_res["jobs"])

    # Testa detalhes
    details_res = await get_job_details(response.job_id)
    assert details_res["job"]["id"] == response.job_id
    assert len(details_res["items"]) >= 1

    # Testa logs
    logs_res = await get_job_logs(response.job_id)
    assert "logs" in logs_res


@pytest.mark.anyio
async def test_selectors_config():
    config = await get_selectors_config()
    assert "login" in config
    assert "cotacoes" in config
    assert "conhecimento" in config
    assert "frete" in config
    assert "contrato" in config
    assert "input_usuario" in config["login"]


@pytest.mark.anyio
async def test_upload_with_already_completed_ctes():
    """Valida que CTEs já concluídos são detectados, contabilizados e não reprocessados."""
    wb = openpyxl.Workbook()
    ws = wb.active

    for r in range(1, 5):
        ws.append([f"Cabecalho_{r}"])

    header_row = [
        "Status", "Nro Cotação", "", "", "", "", "Validade", "", "", "",
        "Categoria Veículo", "Remetente", "Cidade / UF", "", "", "",
        "Frete a Pagar", "", "Frete Negociado", "", "", "",
        "Motorista / Placa"
    ]
    ws.append(header_row)

    # Linha 1: Já Concluído
    row_completed = [
        "Concluído", "1832001", None, None, None, None, "15/08/2026", None, None, None,
        "TOCO", "LACTALIS", "SALVADOR / BA", None, None, None,
        "R$ 500,00", None, "R$ 600,00", None, None, None,
        "MARCOS SILVA ABC1D23 15/08/2026"
    ]
    # Linha 2: Pendente
    row_pending = [
        "Pendente", "1832002", None, None, None, None, "15/08/2026", None, None, None,
        "TRUCK", "LACTALIS", "FEIRA DE SANTANA / BA", None, None, None,
        "R$ 700,00", None, "R$ 800,00", None, None, None,
        "JOSE SANTOS BRA2E19 15/08/2026"
    ]
    ws.append(row_completed)
    ws.append(row_pending)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    wb.close()

    upload_file_obj = UploadFile(
        file=buf,
        filename="planilha_com_concluidos.xlsx",
        headers={"content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    )

    response = await upload_and_validate(file=upload_file_obj)

    assert response.total_rows == 2
    assert response.already_completed_count == 1
    assert response.pending_rows_count == 1
    assert response.valid_rows_count == 2

    # Verifica persistência no SQLite
    details = await get_job_details(response.job_id)
    assert details["job"]["success_count"] == 1
    assert details["job"]["total_items"] == 2

    from backend.app.infrastructure.repository import job_repository
    pending_items = job_repository.get_pending_items(response.job_id)
    assert len(pending_items) == 1
    assert pending_items[0].nro_cotacao == "1832002"

