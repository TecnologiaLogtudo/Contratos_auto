from __future__ import annotations

import sys
import asyncio

# On Windows, Playwright needs an event loop policy with subprocess support.
# Keep Proactor explicit so browser subprocesses can start correctly.
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
import json
import os
import tempfile
import sqlite3
import uuid
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_PATH = os.getenv('BASE_PATH', '').strip()
if BASE_PATH and not BASE_PATH.startswith('/'):
    BASE_PATH = f'/{BASE_PATH}'
BASE_PATH = BASE_PATH.rstrip('/') if BASE_PATH and BASE_PATH != '/' else ''

from .schemas import AutomationConfig, JobInfo, PreviewResponse
from .services.automation_manager import manager


class DeleteResultsPayload(BaseModel):
    ids: list[str]
    password: str


app = FastAPI(title="LogTudo Automacao API", version="1.0.0", root_path=BASE_PATH or "")

if BASE_PATH:
    @app.middleware("http")
    async def strip_base_path_middleware(request: Request, call_next):
        scope_path = request.scope.get("path", "")
        forwarded_prefix = request.headers.get("x-forwarded-prefix", "").strip()
        if forwarded_prefix and forwarded_prefix.startswith("/"):
            request.scope["root_path"] = forwarded_prefix.rstrip("/")

        if scope_path.startswith(BASE_PATH):
            request.scope["root_path"] = BASE_PATH
            request.scope["path"] = scope_path[len(BASE_PATH):] or "/"
        return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

web_dir = Path(__file__).parent.parent.parent / "web"
# Prefer the production build index.html when available
index_dist_path = web_dir / "dist" / "index.html"
index_path = index_dist_path if index_dist_path.exists() else web_dir / "index.html"
asset_dir_candidates = [web_dir / "assets", web_dir / "dist" / "assets"]
assets_dir = next((p for p in asset_dir_candidates if p.exists()), None)

if assets_dir:
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="web-assets")
    if BASE_PATH:
        app.mount(f"{BASE_PATH}/assets", StaticFiles(directory=str(assets_dir)), name="web-assets-basepath")

from .services.automation_manager import ARTIFACTS_DIR, DB_PATH, _resolve_artifact_disk_path
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts-static")
if BASE_PATH:
    app.mount(f"{BASE_PATH}/artifacts", StaticFiles(directory=str(ARTIFACTS_DIR)), name="artifacts-static-basepath")


@app.get("/artifacts/{filename:path}")
def serve_artifact_file(filename: str):
    # Tenta resolver o caminho físico real do arquivo usando o resolvedor robusto
    resolved = _resolve_artifact_disk_path(filename, "")
    if not resolved:
        resolved = _resolve_artifact_disk_path(str(ARTIFACTS_DIR / filename), "")
        
    if not resolved or not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Arquivo de artefato nao encontrado")
    
    # Define o content-type correto
    media_type = "application/octet-stream"
    suffix = resolved.suffix.lower()
    if suffix == ".png":
        media_type = "image/png"
    elif suffix in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif suffix == ".webm":
        media_type = "video/webm"
    elif suffix == ".mp4":
        media_type = "video/mp4"
    elif suffix == ".zip":
        media_type = "application/zip"
        
    return FileResponse(str(resolved), media_type=media_type)


@app.post("/api/files")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """
    Endpoint para realizar o upload inicial de planilhas de faturamento.
    Retorna o ID do arquivo gerado e o caminho persistido.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="Arquivo inválido. Use .xlsx ou .xls")
        
    from .services.automation_manager import UPLOADS_DIR
    file_id = str(uuid.uuid4())
    stored_file = UPLOADS_DIR / f"{file_id}_{file.filename}"
    
    try:
        with open(stored_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo de upload: {e}")
        
    return {
        "file_id": file_id,
        "filename": file.filename,
        "stored_path": str(stored_file.resolve())
    }


@app.get("/api/results/files")
def list_results_files():
    """
    Retorna uma listagem consolidada de todas as planilhas (originais ou processadas)
    armazenadas no banco de dados e verifica se estão fisicamente disponíveis para download.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM job_artifacts 
            WHERE type IN ('result_file', 'input_file')
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            resolved = _resolve_artifact_disk_path(r["file_path"], r["job_id"])
            results.append({
                "id": r["id"],
                "job_id": r["job_id"],
                "type": r["type"],
                "file_path": r["file_path"],
                "filename": Path(r["file_path"]).name,
                "created_at": r["created_at"],
                "available": resolved is not None
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos do histórico: {e}")


@app.get("/api/results/files/{artifact_id}/download")
def download_result_file(artifact_id: str):
    """
    Realiza o download de planilhas baseado no resolvedor de caminhos físicos robusto.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_artifacts WHERE id = ?", (artifact_id,))
        r = cursor.fetchone()
        conn.close()
        
        # Caso não encontre na nova tabela, tenta buscar no histórico legado para manter compatibilidade
        if not r:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM results_history WHERE id = ?", (artifact_id,))
            rh = cursor.fetchone()
            conn.close()
            if rh and rh["result_file"]:
                r = {"file_path": rh["result_file"], "job_id": rh["job_id"]}
                
        if not r:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
            
        resolved = _resolve_artifact_disk_path(r["file_path"], r["job_id"])
        if not resolved or not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="Arquivo físico do artefato não encontrado no disco")
            
        return FileResponse(path=str(resolved), filename=resolved.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao baixar arquivo: {e}")


@app.get("/api/admin/jobs/{job_id}/artifacts")
def list_job_artifacts(job_id: str):
    """
    Endpoint administrativo para retornar a lista de todos os artefatos de um determinado Job.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_artifacts WHERE job_id = ?", (job_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            resolved = _resolve_artifact_disk_path(r["file_path"], r["job_id"])
            results.append({
                "id": r["id"],
                "job_id": r["job_id"],
                "type": r["type"],
                "file_path": r["file_path"],
                "filename": Path(r["file_path"]).name,
                "created_at": r["created_at"],
                "available": resolved is not None
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar artefatos do job: {e}")


@app.get("/api/admin/artifacts/{artifact_id}/file")
def get_admin_artifact_file(artifact_id: str):
    """
    Endpoint administrativo para baixar ou servir diretamente qualquer arquivo de artefato pelo seu ID.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM job_artifacts WHERE id = ?", (artifact_id,))
        r = cursor.fetchone()
        conn.close()
        
        if not r:
            raise HTTPException(status_code=404, detail="Artefato não encontrado")
            
        resolved = _resolve_artifact_disk_path(r["file_path"], r["job_id"])
        if not resolved or not resolved.exists() or not resolved.is_file():
            raise HTTPException(status_code=404, detail="Arquivo físico do artefato não encontrado no disco")
            
        media_type = "application/octet-stream"
        suffix = resolved.suffix.lower()
        if suffix == ".png":
            media_type = "image/png"
        elif suffix in (".jpg", ".jpeg"):
            media_type = "image/jpeg"
        elif suffix == ".webm":
            media_type = "video/webm"
        elif suffix == ".mp4":
            media_type = "video/mp4"
        elif suffix == ".zip":
            media_type = "application/zip"
            
        return FileResponse(path=str(resolved), media_type=media_type, filename=resolved.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao acessar arquivo do artefato: {e}")




def _render_index_html() -> HTMLResponse:
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    content = index_path.read_text(encoding="utf-8")
    base_script = f'<script>window.LOGTUDO_BASE_PATH = "{BASE_PATH or ""}";</script>'
    if "window.LOGTUDO_BASE_PATH" not in content:
        if "</head>" in content:
            content = content.replace("</head>", f"  {base_script}\n  </head>")
        else:
            content = f"{base_script}\n{content}"
    return HTMLResponse(content)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict:
    return {"status": "ready"}


@app.get("/api/debug/artifacts")
def debug_artifacts():
    try:
        files = []
        if ARTIFACTS_DIR.exists():
            for p in ARTIFACTS_DIR.glob("**/*"):
                if p.is_file():
                    files.append({
                        "name": p.name,
                        "rel_path": str(p.relative_to(ARTIFACTS_DIR)),
                        "size": p.stat().st_size,
                        "absolute": str(p.resolve())
                    })
        return {
            "artifacts_dir": str(ARTIFACTS_DIR.resolve()),
            "exists": ARTIFACTS_DIR.exists(),
            "files": files
        }
    except Exception as e:
        return {"error": str(e)}



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
        try:
            return manager.preview_file(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Não foi possível ler a planilha enviada: {e}")
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
    dados_km: str = Form("20"),
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


@app.get("/")
def serve_index():
    return _render_index_html()


@app.get("/manual")
def serve_manual():
    return _render_index_html()


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "health", "assets/", "artifacts/")):
        raise HTTPException(status_code=404, detail="Not found")
    return _render_index_html()


