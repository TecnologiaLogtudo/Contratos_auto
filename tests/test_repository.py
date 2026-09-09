"""Testes unitários e de integração para o repositório SQLite unificado."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from backend.app.domain.models import ItemContrato, ItemStatus
from backend.app.infrastructure.database import Database
from backend.app.infrastructure.repository import JobRepository


@pytest.fixture
def temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_database.db"
        test_db = Database(db_path=db_path)
        repo = JobRepository(database=test_db)
        yield repo
        test_db.close()


def test_create_job_and_list_items(temp_repo: JobRepository):
    # Itens válidos
    item1 = ItemContrato(
        nro_cotacao="1001",
        categoria_veiculo="TOCO",
        cidade="São Paulo",
        uf="SP",
        nome="Motorista 1",
        placa="ABC1234",
        data_pagamento="10/08/2026",
        viagem_extra="Não",
        remetente="EMPRESA A",
        validade="10/08/2026",
        row_index=8,
    )
    item2 = ItemContrato(
        nro_cotacao="1002",
        categoria_veiculo="CARRETA",
        cidade="Curitiba",
        uf="PR",
        nome="Motorista 2",
        placa="XYZ9876",
        data_pagamento="12/08/2026",
        viagem_extra="Sim",
        remetente="EMPRESA B",
        row_index=9,
    )

    # Item inválido
    inv_item = ItemContrato(
        nro_cotacao="1003",
        categoria_veiculo="TOCO",
        cidade="Rio de Janeiro",
        uf="RJ",
        nome="Motorista 3",
        placa="PLACA NÃO ENCONTRADA",
        data_pagamento="15/08/2026",
        row_index=10,
    )

    job_id = temp_repo.create_job(
        filename="planilha_teste.xlsx",
        total_items=3,
        items=[item1, item2],
        invalid_items=[(inv_item, "Placa não encontrada")],
        username="operador_teste",
    )

    import re
    assert re.match(r"^\d{6}-\d{5}$", job_id) is not None

    # Verifica se o próximo job incrementa o sequencial (00002)
    next_job_id = temp_repo.create_job(
        filename="planilha_teste_2.xlsx",
        total_items=1,
        items=[item1],
    )
    assert next_job_id.endswith("-00002")

    # Verifica metadados do Job
    job = temp_repo.get_job(job_id)
    assert job is not None
    assert job["filename"] == "planilha_teste.xlsx"
    assert job["status"] == "PENDING"
    assert job["total_items"] == 3
    assert job["invalid_count"] == 1
    assert job["user_credentials_username"] == "operador_teste"

    # Verifica listagem de itens
    items = temp_repo.list_job_items(job_id)
    assert len(items) == 3

    val_item_row = next(i for i in items if i["nro_cotacao"] == "1001")
    assert val_item_row["status"] == ItemStatus.PENDENTE.value

    inv_item_row = next(i for i in items if i["nro_cotacao"] == "1003")
    assert inv_item_row["status"] == ItemStatus.FALHA_VALIDACAO.value
    assert "Placa" in inv_item_row["error_message"]


def test_update_item_result_and_counts(temp_repo: JobRepository):
    item1 = ItemContrato(
        nro_cotacao="2001",
        categoria_veiculo="TOCO",
        cidade="Belo Horizonte",
        uf="MG",
        nome="José",
        placa="BHZ1234",
        data_pagamento="20/08/2026",
        row_index=8,
    )
    item2 = ItemContrato(
        nro_cotacao="2002",
        categoria_veiculo="TOCO",
        cidade="Salvador",
        uf="BA",
        nome="Antonio",
        placa="BAH5678",
        data_pagamento="22/08/2026",
        row_index=9,
    )

    job_id = temp_repo.create_job(
        filename="teste2.xlsx",
        total_items=2,
        items=[item1, item2],
    )

    # 1. Item 1 concluído com sucesso
    temp_repo.update_item_result(
        job_id=job_id,
        nro_cotacao="2001",
        status=ItemStatus.CONCLUIDO,
        cte_number="CTE-998877",
        extracted_nf="12345",
        duration_seconds=12.5,
    )

    # 2. Item 2 falha com erro
    temp_repo.update_item_result(
        job_id=job_id,
        nro_cotacao="2002",
        status=ItemStatus.ERRO,
        error_message="Regra de carretos bloqueada",
        duration_seconds=8.0,
    )

    # Verifica Job e contagens
    job = temp_repo.get_job(job_id)
    assert job["success_count"] == 1
    assert job["error_count"] == 1


def test_resume_get_pending_items(temp_repo: JobRepository):
    item1 = ItemContrato(nro_cotacao="3001", row_index=8, placa="AAA1111", data_pagamento="01/01/2026")
    item2 = ItemContrato(nro_cotacao="3002", row_index=9, placa="BBB2222", data_pagamento="01/01/2026")
    item3 = ItemContrato(nro_cotacao="3003", row_index=10, placa="CCC3333", data_pagamento="01/01/2026")

    job_id = temp_repo.create_job(
        filename="teste_resume.xlsx",
        total_items=3,
        items=[item1, item2, item3],
    )

    # Marca item 1 como concluído
    temp_repo.update_item_result(
        job_id=job_id,
        nro_cotacao="3001",
        status=ItemStatus.CONCLUIDO,
        cte_number="CTE-001",
    )

    # Itens pendentes para resume devem ser apenas item 2 e 3
    pending = temp_repo.get_pending_items(job_id)
    assert len(pending) == 2
    assert [p.nro_cotacao for p in pending] == ["3002", "3003"]


def test_logs_and_artifacts_storage(temp_repo: JobRepository):
    job_id = temp_repo.create_job(filename="logs_test.xlsx", total_items=1, items=[])

    # Adiciona logs
    temp_repo.add_log(job_id, "Iniciando F1...", level="INFO", phase="F1")
    temp_repo.add_log(job_id, "Erro no login", level="ERRO", phase="F2")
    temp_repo.add_log(job_id, "CTE emitido!", level="SUCESSO", phase="F5", nro_cotacao="999")

    logs = temp_repo.list_job_logs(job_id)
    assert len(logs) == 3
    assert logs[1]["level"] == "ERRO"
    assert logs[2]["phase"] == "F5"

    # Filtro por nível
    error_logs = temp_repo.list_job_logs(job_id, level="ERRO")
    assert len(error_logs) == 1
    assert error_logs[0]["message"] == "Erro no login"

    # Artefatos
    art_id = temp_repo.add_artifact(
        job_id=job_id,
        artifact_type="EXCEL_RESULT",
        file_path="/path/to/result.xlsx",
        file_name="result.xlsx",
        file_size_bytes=1024,
    )
    assert art_id.startswith("art_")

    art = temp_repo.get_artifact(art_id)
    assert art is not None
    assert art["file_name"] == "result.xlsx"
    assert art["file_size_bytes"] == 1024
