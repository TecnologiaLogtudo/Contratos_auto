"""Testes unitários para o gerenciador de artefatos e política de retenção."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
import pytest

from backend.app.infrastructure.artifacts import ArtifactManager
from backend.app.infrastructure.database import Database
from backend.app.infrastructure.repository import JobRepository


@pytest.fixture
def temp_artifacts_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir) / "artifacts"
        db_path = Path(tmpdir) / "test_db.db"
        test_db = Database(db_path=db_path)
        repo = JobRepository(database=test_db)
        manager = ArtifactManager(base_dir=base_dir, repository=repo)
        yield manager, repo
        test_db.close()


def test_artifact_directories_creation(temp_artifacts_env):
    manager, repo = temp_artifacts_env
    job_id = "job_test_dirs_01"

    job_dir = manager.get_job_dir(job_id)
    sc_dir = manager.get_screenshots_dir(job_id)
    tr_dir = manager.get_traces_dir(job_id)

    assert job_dir.exists() and job_dir.is_dir()
    assert sc_dir.exists() and sc_dir.is_dir()
    assert tr_dir.exists() and tr_dir.is_dir()


def test_save_error_screenshot(temp_artifacts_env):
    manager, repo = temp_artifacts_env
    job_id = repo.create_job(filename="teste.xlsx", total_items=1, items=[])

    fake_png = b"\x89PNG\r\n\x1a\nfake_image_bytes"
    art_id = manager.save_error_screenshot(job_id=job_id, nro_cotacao="1832067", image_bytes=fake_png)

    assert art_id.startswith("art_")
    art = repo.get_artifact(art_id)
    assert art is not None
    assert art["artifact_type"] == "SCREENSHOT_ERROR"
    assert Path(art["file_path"]).exists()
    assert Path(art["file_path"]).read_bytes() == fake_png


def test_register_excel_report(temp_artifacts_env):
    manager, repo = temp_artifacts_env
    job_id = repo.create_job(filename="teste.xlsx", total_items=1, items=[])

    # Cria arquivo excel falso na pasta temp
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(b"excel_content_bytes")
        tmp_path = Path(tmp.name)

    art_id = manager.register_excel_report(job_id=job_id, source_excel_path=tmp_path)
    tmp_path.unlink(missing_ok=True)

    art = repo.get_artifact(art_id)
    assert art is not None
    assert art["artifact_type"] == "EXCEL_RESULT"
    assert art["file_name"] == f"{job_id}.xlsx"
    assert Path(art["file_path"]).exists()
    assert Path(art["file_path"]).name == f"{job_id}.xlsx"


def test_cleanup_expired_artifacts(temp_artifacts_env):
    manager, repo = temp_artifacts_env
    job_id = "job_cleanup_test"

    # Cria arquivo antigo em traces
    traces_dir = manager.get_traces_dir(job_id)
    old_file = traces_dir / "old_trace.zip"
    old_file.write_bytes(b"trace_data")

    # Altera modification time para 10 dias atrás
    old_mtime = time.time() - (10 * 86400)
    import os
    os.utime(old_file, (old_mtime, old_mtime))

    # Cria arquivo novo
    new_file = traces_dir / "recent_trace.zip"
    new_file.write_bytes(b"recent_trace_data")

    cleaned = manager.cleanup_expired_artifacts(max_age_days=7)
    assert cleaned == 1
    assert not old_file.exists()
    assert new_file.exists()
