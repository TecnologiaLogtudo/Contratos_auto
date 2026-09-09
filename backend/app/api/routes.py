"""Roteador de endpoints REST e WebSockets da API FastAPI."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..domain.models import ItemStatus
from ..engine.excel_processor import ExcelProcessor
from ..engine.selectors import SELECTORS
from ..infrastructure.artifacts import artifact_manager
from ..infrastructure.broadcaster import broadcaster
from ..infrastructure.database import BASE_STORAGE_DIR
from ..infrastructure.repository import job_repository
from ..infrastructure.worker import worker_manager


router = APIRouter()
UPLOADS_DIR = BASE_STORAGE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DTOs / Schemas Pydantic
# =============================================================================

class StartJobRequest(BaseModel):
    usuario: str = Field(..., description="Usuário do ERP LogTudo")
    senha: str = Field(..., description="Senha do ERP LogTudo")
    headless: bool = Field(default=False, description="Executar navegador em background")
    throttle_seconds: float = Field(default=2.5, description="Intervalo entre cotações em segundos")


class PreValidationResponse(BaseModel):
    job_id: str
    is_valid: bool
    filename: str
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    already_completed_count: int = 0
    pending_rows_count: int = 0
    missing_mandatory_columns: List[str]
    row_errors: List[Dict[str, Any]]
    preview: List[Dict[str, Any]]


class ActionResponse(BaseModel):
    success: bool
    message: str
    job_id: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/jobs/upload-and-validate", response_model=PreValidationResponse)
async def upload_and_validate(file: UploadFile = File(...)) -> PreValidationResponse:
    """
    Recebe a planilha Excel (.xlsx ou .xls), aplica pré-tratamento BSoft, validação de campos
    obrigatórios e formatos, e inicializa o registro do Job no SQLite.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Apenas arquivos .xlsx e .xls são aceitos.")

    job_id = job_repository.generate_next_job_id()
    dest_path = UPLOADS_DIR / f"{job_id}_{file.filename}"
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        processor = ExcelProcessor(dest_path)
        report = processor.validate_upload()

        # Cria o Job no SQLite persistindo o estado inicial e itens
        job_repository.create_job(
            job_id=job_id,
            filename=file.filename,
            total_items=report.total_rows,
            items=processor.items,
            invalid_items=processor.validation_errors,
        )

        return PreValidationResponse(
            job_id=job_id,
            is_valid=report.is_valid,
            filename=file.filename,
            total_rows=report.total_rows,
            valid_rows_count=report.valid_rows_count,
            invalid_rows_count=report.invalid_rows_count,
            already_completed_count=report.already_completed_count,
            pending_rows_count=report.pending_rows_count,
            missing_mandatory_columns=report.missing_mandatory_columns,
            row_errors=report.row_errors,
            preview=report.preview,
        )
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Erro ao processar planilha: {str(e)}")


@router.post("/jobs/{job_id}/start", response_model=ActionResponse)
async def start_job(job_id: str, req: StartJobRequest) -> ActionResponse:
    """Inicia a execução sequencial do Job via Worker em Thread dedicada."""
    job = job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")

    if job["status"] == "RUNNING":
        raise HTTPException(status_code=400, detail="Este Job já está em execução.")

    # Localiza arquivo original do upload de forma determinística
    excel_file = UPLOADS_DIR / f"{job_id}_{job['filename']}"
    if not excel_file.exists():
        matching = [f for f in UPLOADS_DIR.iterdir() if f.is_file() and (f.name.startswith(f"{job_id}_") or job["filename"] in f.name)]
        if not matching:
            raise HTTPException(status_code=404, detail="Arquivo original da planilha não encontrado.")
        excel_file = matching[0]

    try:
        worker_manager.create_and_start_worker(
            job_id=job_id,
            usuario=req.usuario,
            senha=req.senha,
            excel_path=excel_file,
            headless=req.headless,
            throttle_seconds=req.throttle_seconds,
        )
        return ActionResponse(success=True, message="Execução iniciada com sucesso.", job_id=job_id)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/jobs/{job_id}/pause", response_model=ActionResponse)
async def pause_job(job_id: str) -> ActionResponse:
    """Pausa a execução do lote após a conclusão do item atual."""
    worker = worker_manager.get_worker(job_id)
    if not worker or not worker.is_running():
        raise HTTPException(status_code=400, detail="O Job não está em execução ativa.")
    worker.pause()
    return ActionResponse(success=True, message="Pausa solicitada.", job_id=job_id)


@router.post("/jobs/{job_id}/resume", response_model=ActionResponse)
async def resume_job(job_id: str) -> ActionResponse:
    """Retoma a execução de um Job pausado."""
    worker = worker_manager.get_worker(job_id)
    if not worker:
        raise HTTPException(status_code=400, detail="Instância de Worker não encontrada.")
    worker.resume()
    return ActionResponse(success=True, message="Execução retomada.", job_id=job_id)


@router.post("/jobs/{job_id}/cancel", response_model=ActionResponse)
async def cancel_job(job_id: str) -> ActionResponse:
    """Cancela a execução do lote imediatamente."""
    worker = worker_manager.get_worker(job_id)
    if worker and worker.is_running():
        worker.cancel()
    else:
        job_repository.update_job_status(job_id, "CANCELLED")
    return ActionResponse(success=True, message="Cancelamento solicitado.", job_id=job_id)


@router.get("/jobs")
async def list_jobs(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    """Retorna histórico paginado de todos os jobs."""
    jobs = job_repository.list_jobs(limit=limit, offset=offset)
    return {"jobs": jobs, "limit": limit, "offset": offset}


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str) -> Dict[str, Any]:
    """Retorna dados detalhados do Job e lista de todos os seus itens."""
    job = job_repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    items = job_repository.list_job_items(job_id)
    artifacts = job_repository.list_job_artifacts(job_id)
    return {"job": job, "items": items, "artifacts": artifacts}


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, level: Optional[str] = None, limit: int = 500) -> Dict[str, Any]:
    """Retorna histórico de logs estruturados de um Job."""
    logs = job_repository.list_job_logs(job_id=job_id, level=level, limit=limit)
    return {"job_id": job_id, "logs": logs}


@router.get("/jobs/{job_id}/artifacts")
async def get_job_artifacts(job_id: str) -> Dict[str, Any]:
    """Lista todos os artefatos vinculados a um Job."""
    artifacts = job_repository.list_job_artifacts(job_id)
    return {"job_id": job_id, "artifacts": artifacts}


@router.get("/jobs/{job_id}/download/{artifact_id}")
async def download_artifact(job_id: str, artifact_id: str):
    """Download seguro de arquivo gerado (Excel, Screenshot, etc.)."""
    art = job_repository.get_artifact(artifact_id)
    file_path = None
    file_name = f"{job_id}.xlsx"

    if art and art["job_id"] == job_id:
        file_path = Path(art["file_path"])
        file_name = art["file_name"]
    else:
        # Fallback para download direto do Excel consolidado pelo job_id
        job_dir = artifact_manager.get_job_dir(job_id)
        candidate_excel = job_dir / f"{job_id}.xlsx"
        if candidate_excel.exists():
            file_path = candidate_excel
            file_name = f"{job_id}.xlsx"

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo ou relatório do lote não encontrado no storage.")

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if file_path.suffix == ".xlsx" else "application/octet-stream"
    if file_path.suffix == ".png":
        media_type = "image/png"

    return FileResponse(path=str(file_path), filename=file_name, media_type=media_type)


CONFIG_FILE = BASE_STORAGE_DIR / "config.json"


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Retorna as configurações operacionais salvas."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "login": "",
        "senha": "",
        "atraso_fases": 2.5,
        "atraso_etapas": 0.05,
        "dados_km": "20",
        "aceitar_frete_minimo_antt": True,
    }


@router.put("/config")
async def save_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Salva configurações operacionais no storage."""
    CONFIG_FILE.write_text(json.dumps(config_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_data


@router.get("/logs/sessions")
async def list_log_sessions() -> List[Dict[str, Any]]:
    """Lista as sessões de logs baseadas no histórico de Jobs."""
    jobs = job_repository.list_jobs(limit=50)
    sessions = []
    for j in jobs:
        sessions.append({
            "id": j["id"],
            "job_id": j["id"],
            "created_at": j["created_at"],
            "total_logs": (j["success_count"] + j["error_count"]),
        })
    return sessions


@router.get("/logs/sessions/{session_id}")
async def get_log_session(session_id: str) -> Dict[str, Any]:
    """Retorna logs detalhados de uma sessão específica."""
    logs = job_repository.list_job_logs(job_id=session_id)
    return {"id": session_id, "logs": logs}


@router.post("/logs/clear")
async def clear_logs_endpoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Limpa artefatos temporários expirados."""
    cleaned = artifact_manager.cleanup_expired_artifacts(max_age_days=0)
    return {"success": True, "message": f"Limpeza concluída. {cleaned} arquivos temporários removidos."}


@router.get("/debug/artifacts")
async def debug_artifacts() -> Dict[str, Any]:
    """Diagnóstico do diretório de armazenamento."""
    return {"storage_dir": str(BASE_STORAGE_DIR), "exists": True}


@router.get("/config/selectors")
async def get_selectors_config() -> Dict[str, Any]:
    """Inspeciona os seletores ativos de automação."""
    return {
        "login": SELECTORS.login.__dict__,
        "cotacoes": SELECTORS.cotacoes.__dict__,
        "conhecimento": SELECTORS.conhecimento.__dict__,
        "frete": SELECTORS.frete.__dict__,
        "contrato": SELECTORS.contrato.__dict__,
    }


# =============================================================================
# STREAMING (WEBSOCKET & SSE)
# =============================================================================

@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_stream(websocket: WebSocket, job_id: str):
    """Streaming bidirecional de logs, progresso e comandos para o Job via WebSocket."""
    await broadcaster.connect(job_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            worker = worker_manager.get_worker(job_id)

            if action == "pause" and worker:
                worker.pause()
            elif action == "resume" and worker:
                worker.resume()
            elif action == "cancel" and worker:
                worker.cancel()
    except WebSocketDisconnect:
        await broadcaster.disconnect(job_id, websocket)
    except Exception:
        await broadcaster.disconnect(job_id, websocket)


@router.get("/jobs/{job_id}/stream")
async def sse_job_stream(job_id: str, request: Request):
    """Streaming unidirecional de logs e progresso via Server-Sent Events (SSE)."""
    async def event_generator():
        q: asyncio.Queue = asyncio.Queue()
        broadcaster.register_sse(job_id, q)
        try:
            # Handshake de conexão
            handshake = json.dumps({"type": "connection", "job_id": job_id, "status": "connected"})
            yield f"data: {handshake}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f": keep-alive\n\n"
        finally:
            broadcaster.unregister_sse(job_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
