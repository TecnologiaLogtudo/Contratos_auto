from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .schemas import AutomationConfig, JobInfo, PreviewResponse
from .services.automation_manager import manager


class DeleteResultsPayload(BaseModel):
    ids: list[str]
    password: str


app = FastAPI(title="LogTudo Automacao API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config", response_model=AutomationConfig)
def get_config() -> AutomationConfig:
    return manager.load_config()


@app.put("/api/config", response_model=AutomationConfig)
def put_config(config: AutomationConfig) -> AutomationConfig:
    return manager.save_config(config)


@app.post("/api/preview", response_model=PreviewResponse)
async def preview_file(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Arquivo inválido. Use .xlsx ou .xls")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        return manager.preview_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/jobs")
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    login: str = Form(""),
    senha: str = Form(""),
    atraso_fases: float = Form(1.0),
    atraso_etapas: float = Form(0.3),
    dados_km: str = Form("10"),
    aceitar_frete_minimo_antt: bool = Form(True),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Arquivo inválido. Use .xlsx ou .xls")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    config = AutomationConfig(
        login=login,
        senha=senha,
        atraso_fases=atraso_fases,
        atraso_etapas=atraso_etapas,
        dados_km=dados_km,
        aceitar_frete_minimo_antt=aceitar_frete_minimo_antt,
    )
    manager.save_config(config)
    client_ip = request.client.host if request and request.client else ""
    job = manager.create_job(tmp_path, config, requester_ip=client_ip)
    return {"job_id": job.status.id, "status": job.status}


@app.get("/api/jobs/{job_id}", response_model=JobInfo)
def get_job(job_id: str):
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return JobInfo(status=job.status, logs_count=len(job.logs))


@app.post("/api/jobs/{job_id}/pause")
def pause_job(job_id: str):
    try:
        return manager.pause(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job não encontrado")


@app.post("/api/jobs/{job_id}/resume")
def resume_job(job_id: str):
    try:
        return manager.resume(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job não encontrado")


@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: str):
    try:
        return manager.stop(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job não encontrado")


@app.get("/api/jobs/{job_id}/logs")
async def stream_logs(job_id: str):
    job = manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    async def event_stream():
        cursor = 0
        while True:
            payloads = []
            with job.lock:
                if cursor < len(job.logs):
                    for evt in job.logs[cursor:]:
                        payloads.append(json.dumps(evt.model_dump(), ensure_ascii=False))
                    cursor = len(job.logs)
                state = job.status.state

            for payload in payloads:
                yield f"data: {payload}\n\n"

            if state in {"completed", "error", "stopped"} and cursor >= len(job.logs):
                break

            await asyncio.sleep(0.4)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/results/{job_id}")
def download_result(job_id: str):
    job = manager.get_job(job_id)
    if not job or not job.status.result_file:
        raise HTTPException(status_code=404, detail="Resultado não disponível")
    result_path = Path(job.status.result_file)
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de resultado não encontrado")
    return FileResponse(path=result_path, filename=result_path.name)


@app.get("/api/results/history")
def list_results_history():
    return manager.list_results_history()


@app.get("/api/results/history/{result_id}/download")
def download_history_result(result_id: str):
    history = manager.list_results_history()
    item = next((h for h in history if h.get("id") == result_id), None)
    if not item or not item.get("result_file"):
        raise HTTPException(status_code=404, detail="Resultado não encontrado")
    path = Path(item["result_file"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path=path, filename=path.name)


@app.post("/api/results/delete")
def delete_results(payload: DeleteResultsPayload):
    try:
        return manager.delete_results(payload.ids, payload.password)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/api/logs/sessions")
def list_log_sessions():
    return manager.list_log_sessions()


@app.get("/api/logs/sessions/{session_id}")
def get_log_session(session_id: str):
    data = manager.get_log_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Sessão de log não encontrada")
    return data


class ClearLogsPayload(BaseModel):
    password: str


@app.post("/api/logs/clear")
def clear_logs(payload: ClearLogsPayload):
    try:
        return manager.clear_logs(payload.password)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
