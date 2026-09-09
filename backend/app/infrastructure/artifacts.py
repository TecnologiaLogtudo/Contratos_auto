"""Gerenciador de armazenamento, registro e retenção de artefatos do Contratos_auto."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Optional

from .database import BASE_STORAGE_DIR
from .repository import JobRepository, job_repository


DEFAULT_ARTIFACTS_DIR = BASE_STORAGE_DIR / "artifacts"
DEFAULT_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class ArtifactManager:
    """Gerencia ciclo de vida, diretórios e limpeza de arquivos gerados por execuções."""

    def __init__(self, base_dir: Optional[Path | str] = None, repository: Optional[JobRepository] = None):
        self.base_dir = Path(base_dir) if base_dir else DEFAULT_ARTIFACTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repo = repository or job_repository

    def get_job_dir(self, job_id: str) -> Path:
        """Retorna o diretório base para um Job específico, criando se necessário."""
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def get_screenshots_dir(self, job_id: str) -> Path:
        """Retorna o diretório de screenshots de erro para o Job."""
        s_dir = self.get_job_dir(job_id) / "screenshots"
        s_dir.mkdir(parents=True, exist_ok=True)
        return s_dir

    def get_traces_dir(self, job_id: str) -> Path:
        """Retorna o diretório de traces e vídeos Playwright para o Job."""
        t_dir = self.get_job_dir(job_id) / "traces"
        t_dir.mkdir(parents=True, exist_ok=True)
        return t_dir

    def save_error_screenshot(
        self,
        job_id: str,
        nro_cotacao: str,
        image_bytes: bytes,
    ) -> str:
        """Salva screenshot capturado no momento da falha e registra no repositório."""
        s_dir = self.get_screenshots_dir(job_id)
        file_name = f"erro_cotacao_{nro_cotacao}_{int(time.time())}.png"
        target_path = s_dir / file_name
        target_path.write_bytes(image_bytes)

        return self.repo.add_artifact(
            job_id=job_id,
            artifact_type="SCREENSHOT_ERROR",
            file_path=str(target_path),
            file_name=file_name,
            nro_cotacao=nro_cotacao,
            file_size_bytes=len(image_bytes),
        )

    def register_excel_report(
        self,
        job_id: str,
        source_excel_path: Path | str,
    ) -> str:
        """Copia ou move o Excel processado para o diretório de artefatos do Job com nome ddmmaa-xxxxx.xlsx e registra no DB."""
        src = Path(source_excel_path)
        if not src.exists():
            raise FileNotFoundError(f"Arquivo de relatório não encontrado: {src}")

        dest_dir = self.get_job_dir(job_id)
        dest_name = f"{job_id}{src.suffix}"
        dest_path = dest_dir / dest_name

        if src.resolve() != dest_path.resolve():
            shutil.copy2(src, dest_path)

        size_bytes = dest_path.stat().st_size
        return self.repo.add_artifact(
            job_id=job_id,
            artifact_type="EXCEL_RESULT",
            file_path=str(dest_path),
            file_name=dest_name,
            file_size_bytes=size_bytes,
        )

    def cleanup_expired_artifacts(self, max_age_days: int = 7) -> int:
        """
        Executa limpeza de traces e vídeos temporários com idade superior a max_age_days.
        Mantém os relatórios Excel e screenshots essenciais.
        """
        cleaned_count = 0
        now = time.time()
        max_age_seconds = max_age_days * 86400

        if not self.base_dir.exists():
            return 0

        for job_folder in self.base_dir.iterdir():
            if not job_folder.is_dir():
                continue

            # Limpa traces e vídeos
            traces_dir = job_folder / "traces"
            if traces_dir.exists():
                for trace_file in traces_dir.glob("*"):
                    if trace_file.is_file() and (now - trace_file.stat().st_mtime) > max_age_seconds:
                        try:
                            trace_file.unlink()
                            cleaned_count += 1
                        except Exception:
                            pass

        return cleaned_count


# Instância global singleton
artifact_manager = ArtifactManager()
