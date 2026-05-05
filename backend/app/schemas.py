from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional


class AutomationConfig(BaseModel):
    login: str = ""
    senha: str = ""
    atraso_fases: float = Field(default=1.0, ge=0)
    atraso_etapas: float = Field(default=0.3, ge=0)
    dados_km: str = "10"
    aceitar_frete_minimo_antt: bool = True


class JobStatus(BaseModel):
    id: str
    log_session_id: Optional[str] = None
    state: Literal["idle", "running", "paused", "completed", "error", "stopped"] = "idle"
    current_phase: str = "F0"
    current_item: int = 0
    total_items: int = 0
    percent: float = 0.0
    current_cotacao: Optional[str] = None
    message: str = ""
    result_file: Optional[str] = None


class LogEvent(BaseModel):
    seq: int
    timestamp: str
    level: str
    message: str
    phase: Optional[str] = None
    cotacao: Optional[str] = None


class JobInfo(BaseModel):
    status: JobStatus
    logs_count: int


class PreviewResponse(BaseModel):
    filename: str
    rows: int
    cols: int
    headers: list[str]
    preview: list[dict]
