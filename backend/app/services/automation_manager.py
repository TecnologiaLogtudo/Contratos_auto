from __future__ import annotations

import configparser
import json
import os
import re
import shutil
import threading
import time
import traceback
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import openpyxl
import xlrd

from ..phases import (
    fase1_processamento,
    fase2_login,
    fase3_preenchimento,
    fase4_frete,
    fase5_contrato_frete,
)

from ..schemas import AutomationConfig, JobStatus, LogEvent

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
ARTIFACTS_DIR = DATA_DIR / "artifacts"
LOGS_HISTORY_PATH = DATA_DIR / "logs_history.json"
CONFIG_PATH = BASE_DIR / "config.ini"
RESULTS_HISTORY_PATH = DATA_DIR / "results_history.json"
DB_PATH = DATA_DIR / "automation.db"
URL_DESTINO = "https://logtudo.e-login.net/versoes/versao5.0/rotinas/formulario.php?rotina=trans_conhecimento&OP=O1&_qsf=1"

PHASE_RE = re.compile(r"\[(F\d)\]")
COTACAO_RE = re.compile(r"Cotação:\s*([^\]\s]+)")


def init_db() -> None:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results_history (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                log_session_id TEXT,
                arquivo_original TEXT,
                result_file TEXT,
                status TEXT,
                total INTEGER,
                processados INTEGER,
                sucessos INTEGER,
                erros INTEGER,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_history (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                created_at TEXT,
                status TEXT,
                user TEXT,
                ip TEXT,
                acoes_criticas TEXT,
                passos_acoes TEXT,
                artefatos TEXT,
                browser_logs TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[DB] Erro ao inicializar banco de dados SQLite: {e}")



@dataclass
class JobRuntime:
    status: JobStatus
    config: AutomationConfig
    source_file: Path
    stored_file: Path
    logs: list[LogEvent] = field(default_factory=list)
    seq: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)
    condition: threading.Condition = field(default_factory=lambda: threading.Condition(threading.Lock()))
    pause_event: threading.Event = field(default_factory=threading.Event)
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None

    playwright_instance: object = None
    browser: object = None
    browser_context: object = None
    page: object = None
    planilha_processada_path: Optional[str] = None
    log_session_id: str = ""
    requester_ip: str = ""
    configured_user: str = ""
    critical_actions: list[dict] = field(default_factory=list)
    browser_logs: list[dict] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)

    def emit(self, message: str, level: str = "INFO") -> None:
        with self.lock:
            self.seq += 1
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            phase = None
            cotacao = None
            phase_m = PHASE_RE.search(message)
            cotacao_m = COTACAO_RE.search(message)
            if phase_m:
                phase = phase_m.group(1)
                self.status.current_phase = phase
            if cotacao_m:
                cotacao = cotacao_m.group(1)
                self.status.current_cotacao = cotacao

            event = LogEvent(
                seq=self.seq,
                timestamp=ts,
                level=level.upper(),
                message=message,
                phase=phase,
                cotacao=cotacao,
            )
            self.logs.append(event)
            step = event.model_dump()
            if level.upper() in {"ERRO", "AVISO"}:
                self.critical_actions.append(step)
        with self.condition:
            self.condition.notify_all()

    def take_screenshot(self, name: str) -> None:
        try:
            if not self.page:
                return
            clean_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()
            clean_name = clean_name.replace(" ", "_")
            filename = f"{self.log_session_id}_{clean_name}_{int(time.time())}.png"
            filepath = ARTIFACTS_DIR / filename
            
            # Take screenshot using Playwright
            self.page.screenshot(path=str(filepath))
            
            with self.lock:
                self.artifacts.append({
                    "type": "printscreen",
                    "name": filename,
                    "path": str(filepath.resolve())
                })
            self.emit(f"Printscreen salvo: {filename}", "DEBUG")
        except Exception as e:
            self.emit(f"Falha ao tirar printscreen ({name}): {e}", "DEBUG")



class AutomationManager:
    def __init__(self) -> None:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, JobRuntime] = {}
        self._jobs_lock = threading.Lock()
        self._history_lock = threading.RLock()
        
        # Inicializa banco SQLite
        init_db()

        if not RESULTS_HISTORY_PATH.exists():
            RESULTS_HISTORY_PATH.write_text("[]", encoding="utf-8")
        if not LOGS_HISTORY_PATH.exists():
            LOGS_HISTORY_PATH.write_text("[]", encoding="utf-8")


    def load_config(self) -> AutomationConfig:
        parser = configparser.ConfigParser()
        if CONFIG_PATH.exists():
            parser.read(CONFIG_PATH, encoding="utf-8")

        return AutomationConfig(
            login=parser.get("CREDENCIAS", "login", fallback=""),
            senha=parser.get("CREDENCIAS", "senha", fallback=""),
            atraso_fases=parser.getfloat("AUTOMACAO", "atrasofases", fallback=1.0),
            atraso_etapas=parser.getfloat("AUTOMACAO", "atrasoetapas", fallback=0.3),
            dados_km=parser.get("AUTOMACAO", "dados_km", fallback="10"),
            aceitar_frete_minimo_antt=parser.getboolean("AUTOMACAO", "aceitarfreteminimoantt", fallback=True),
        )

    def save_config(self, config: AutomationConfig) -> AutomationConfig:
        parser = configparser.ConfigParser()
        parser["CREDENCIAS"] = {
            "login": config.login,
            "senha": config.senha,
        }
        parser["AUTOMACAO"] = {
            "atrasofases": str(config.atraso_fases),
            "atrasoetapas": str(config.atraso_etapas),
            "dados_km": config.dados_km,
            "aceitarfreteminimoantt": str(config.aceitar_frete_minimo_antt),
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            parser.write(f)
        return config

    def preview_file(self, file_path: Path) -> dict:
        suffix = file_path.suffix.lower()
        if suffix == ".xls":
            return self._preview_xls(file_path)
        return self._preview_xlsx(file_path)

    def _preview_xlsx(self, file_path: Path) -> dict:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb.active
            headers_raw = [c.value for c in ws[1]] if ws.max_row > 0 else []
            headers = [str(h) if h is not None else "" for h in headers_raw]
            preview = []
            for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
                if i > 10:
                    break
                row_dict = {}
                for idx, value in enumerate(row):
                    key = headers[idx] if idx < len(headers) and headers[idx] else f"col_{idx+1}"
                    row_dict[key] = value
                preview.append(row_dict)
            rows = max(0, ws.max_row - 1)
            cols = ws.max_column
            return {"filename": file_path.name, "rows": rows, "cols": cols, "headers": headers, "preview": preview}
        finally:
            wb.close()

    def _preview_xls(self, file_path: Path) -> dict:
        wb = xlrd.open_workbook(str(file_path), formatting_info=False)
        sheet = wb.sheet_by_index(0)
        headers_raw = sheet.row_values(0) if sheet.nrows > 0 else []
        headers = [str(h) if h is not None else "" for h in headers_raw]
        preview = []
        max_preview = min(sheet.nrows, 11)
        for row_idx in range(1, max_preview):
            row = sheet.row_values(row_idx)
            row_dict = {}
            for idx, value in enumerate(row):
                key = headers[idx] if idx < len(headers) and headers[idx] else f"col_{idx+1}"
                row_dict[key] = value
            preview.append(row_dict)
        rows = max(0, sheet.nrows - 1)
        cols = sheet.ncols
        return {"filename": file_path.name, "rows": rows, "cols": cols, "headers": headers, "preview": preview}

    def create_job(self, source_file: Path, config: AutomationConfig, requester_ip: str = "") -> JobRuntime:
        job_id = str(uuid.uuid4())
        log_session_id = datetime.now().strftime("%d%m%Y-%H%M")
        stored_file = UPLOADS_DIR / f"{job_id}_{source_file.name}"
        shutil.copyfile(source_file, stored_file)

        runtime = JobRuntime(
            status=JobStatus(id=job_id, log_session_id=log_session_id, state="running", message="Inicializando"),
            config=config,
            source_file=source_file,
            stored_file=stored_file,
            log_session_id=log_session_id,
            requester_ip=requester_ip,
            configured_user=(config.login or "").strip(),
        )
        runtime.pause_event.set()
        runtime.thread = threading.Thread(target=self._run_job, args=(runtime,), daemon=True)
        with self._jobs_lock:
            self._jobs[job_id] = runtime
        runtime.thread.start()
        return runtime

    def get_job(self, job_id: str) -> Optional[JobRuntime]:
        with self._jobs_lock:
            return self._jobs.get(job_id)

    def pause(self, job_id: str) -> JobStatus:
        job = self._must_get(job_id)
        job.pause_event.clear()
        with job.lock:
            if job.status.state == "running":
                job.status.state = "paused"
                job.status.message = "Pausado"
        job.emit("Execução pausada pelo usuário.", "AVISO")
        return job.status

    def resume(self, job_id: str) -> JobStatus:
        job = self._must_get(job_id)
        job.pause_event.set()
        with job.lock:
            if job.status.state == "paused":
                job.status.state = "running"
                job.status.message = "Executando"
        job.emit("Execução retomada pelo usuário.", "INFO")
        return job.status

    def stop(self, job_id: str) -> JobStatus:
        job = self._must_get(job_id)
        job.stop_event.set()
        job.pause_event.set()
        with job.lock:
            if job.status.state in {"running", "paused"}:
                job.status.state = "stopped"
                job.status.message = "Parado pelo usuário"
        job.emit("Parada solicitada pelo usuário.", "AVISO")
        
        # Save logs and result history immediately when stopping to guarantee persistence
        try:
            self._append_result_history(job)
            self._append_logs_history(job)
        except Exception as e:
            job.emit(f"Erro ao persistir logs imediatos da parada: {e}", "ERRO")
            
        return job.status


    def list_results_history(self) -> list[dict]:
        # Tenta ler do SQLite primeiro
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM results_history ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[DB] Erro ao ler histórico de resultados do SQLite: {e}")

        # Fallback para JSON
        return self._load_results_history_json()

    def _load_results_history_json(self) -> list[dict]:
        with self._history_lock:
            try:
                data = json.loads(RESULTS_HISTORY_PATH.read_text(encoding="utf-8"))
                return sorted(data, key=lambda x: x.get("created_at", ""), reverse=True)
            except Exception:
                return []

    def delete_results(self, ids: list[str], password: str) -> dict:
        self._validate_admin_reset_password(password)

        # Exclui do SQLite primeiro
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(ids))
            cursor.execute(f"SELECT result_file FROM results_history WHERE id IN ({placeholders})", ids)
            rows = cursor.fetchall()
            for r in rows:
                if r[0]:
                    Path(r[0]).unlink(missing_ok=True)
            
            cursor.execute(f"DELETE FROM results_history WHERE id IN ({placeholders})", ids)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao excluir resultados do SQLite: {e}")

        # Fallback para JSON
        with self._history_lock:
            history = self._load_results_history_json()
            keep = []
            removed = 0
            for item in history:
                if item.get("id") in ids:
                    path = item.get("result_file")
                    if path:
                        Path(path).unlink(missing_ok=True)
                    removed += 1
                else:
                    keep.append(item)
            try:
                RESULTS_HISTORY_PATH.write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[JSON] Erro ao salvar fallback JSON de exclusão: {e}")

        return {"removed": len(ids)}

    def _append_result_history(self, job: JobRuntime) -> None:
        item = {
            "id": str(uuid.uuid4()),
            "job_id": job.status.id,
            "log_session_id": job.log_session_id,
            "arquivo_original": job.stored_file.name,
            "result_file": job.status.result_file,
            "status": job.status.state,
            "total": job.status.total_items,
            "processados": job.status.current_item,
            "sucessos": len([e for e in job.logs if e.level == "SUCESSO" and "Automação concluída" not in e.message]),
            "erros": len([e for e in job.logs if e.level == "ERRO"]),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Salva no SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO results_history (
                    id, job_id, log_session_id, arquivo_original, result_file, status, total, processados, sucessos, erros, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["id"], item["job_id"], item["log_session_id"], item["arquivo_original"], item["result_file"],
                item["status"], item["total"], item["processados"], item["sucessos"], item["erros"], item["created_at"]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            job.emit(f"[DB] Erro ao salvar histórico de resultados no SQLite: {e}", "ERRO")

        # Fallback JSON
        with self._history_lock:
            try:
                history = self._load_results_history_json()
                history.append(item)
                RESULTS_HISTORY_PATH.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                job.emit(f"[JSON] Erro ao salvar histórico de resultados no fallback: {e}", "ERRO")

    def _append_logs_history(self, job: JobRuntime) -> None:
        item = {
            "id": job.log_session_id,
            "job_id": job.status.id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": job.status.state,
            "user": job.configured_user,
            "ip": job.requester_ip,
            "acoes_criticas": job.critical_actions,
            "passos_acoes": [e.model_dump() for e in job.logs],
            "artefatos": job.artifacts,
            "browser_logs": job.browser_logs,
        }

        # Salva no SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO logs_history (
                    id, job_id, created_at, status, user, ip, acoes_criticas, passos_acoes, artefatos, browser_logs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["id"], item["job_id"], item["created_at"], item["status"], item["user"], item["ip"],
                json.dumps(item["acoes_criticas"], ensure_ascii=False),
                json.dumps(item["passos_acoes"], ensure_ascii=False),
                json.dumps(item["artefatos"], ensure_ascii=False),
                json.dumps(item["browser_logs"], ensure_ascii=False)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            job.emit(f"[DB] Erro ao salvar log de sessão no SQLite: {e}", "ERRO")

        # Fallback JSON
        with self._history_lock:
            try:
                sessions = self._load_logs_history_json()
                sessions = [s for s in sessions if s.get("id") != item["id"]]
                sessions.append(item)
                LOGS_HISTORY_PATH.write_text(json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                job.emit(f"[JSON] Erro ao salvar log de sessão no fallback: {e}", "ERRO")

    def list_log_sessions(self) -> list[dict]:
        # Tenta ler do SQLite primeiro
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs_history ORDER BY created_at DESC")
            rows = cursor.fetchall()
            conn.close()
            sessions = []
            for r in rows:
                sessions.append({
                    "id": r["id"],
                    "job_id": r["job_id"],
                    "created_at": r["created_at"],
                    "status": r["status"],
                    "user": r["user"],
                    "ip": r["ip"],
                    "acoes_criticas": json.loads(r["acoes_criticas"] or "[]"),
                    "passos_acoes": json.loads(r["passos_acoes"] or "[]"),
                    "artefatos": json.loads(r["artefatos"] or "[]"),
                    "browser_logs": json.loads(r["browser_logs"] or "[]")
                })
            return sessions
        except Exception as e:
            print(f"[DB] Erro ao ler logs de sessões do SQLite: {e}")

        # Fallback para JSON
        return self._load_logs_history_json()

    def _load_logs_history_json(self) -> list[dict]:
        with self._history_lock:
            try:
                data = json.loads(LOGS_HISTORY_PATH.read_text(encoding="utf-8"))
                return sorted(data, key=lambda x: x.get("created_at", ""), reverse=True)
            except Exception:
                return []

    def get_log_session(self, session_id: str) -> Optional[dict]:
        # Tenta SQLite primeiro
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs_history WHERE id = ?", (session_id,))
            r = cursor.fetchone()
            conn.close()
            if r:
                return {
                    "id": r["id"],
                    "job_id": r["job_id"],
                    "created_at": r["created_at"],
                    "status": r["status"],
                    "user": r["user"],
                    "ip": r["ip"],
                    "acoes_criticas": json.loads(r["acoes_criticas"] or "[]"),
                    "passos_acoes": json.loads(r["passos_acoes"] or "[]"),
                    "artefatos": json.loads(r["artefatos"] or "[]"),
                    "browser_logs": json.loads(r["browser_logs"] or "[]")
                }
        except Exception as e:
            print(f"[DB] Erro ao ler log de sessão individual do SQLite: {e}")

        # Fallback para JSON
        sessions = self._load_logs_history_json()
        return next((s for s in sessions if s.get("id") == session_id), None)

    def clear_logs(self, password: str) -> dict:
        self._validate_admin_reset_password(password)

        # Limpa do SQLite
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs_history")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DB] Erro ao limpar logs do SQLite: {e}")

        # Fallback JSON
        with self._history_lock:
            try:
                LOGS_HISTORY_PATH.write_text("[]", encoding="utf-8")
            except Exception as e:
                print(f"[JSON] Erro ao limpar logs no fallback JSON: {e}")

        return {"cleared": True}


    def _validate_admin_reset_password(self, password: str) -> None:
        admin_password = os.getenv("ADMIN_RESET_PASSWORD", "").strip()
        if not admin_password:
            raise PermissionError("ADMIN_RESET_PASSWORD não configurada no ambiente.")
        if password != admin_password:
            raise PermissionError("Senha inválida")

    def _must_get(self, job_id: str) -> JobRuntime:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        return job

    def _update_progress(self, job: JobRuntime, current: int, total: int, message: str = "") -> None:
        with job.lock:
            job.status.current_item = current
            job.status.total_items = total
            job.status.percent = round((current / total) * 100, 2) if total else 0
            if message:
                job.status.message = message

    def _run_job(self, job: JobRuntime) -> None:
        cfg = job.config
        try:
            if not cfg.login or not cfg.senha:
                raise ValueError("Login e senha são obrigatórios para iniciar a automação.")

            job.emit("[F0] Job iniciado.", "INFO")
            with job.lock:
                job.status.state = "running"
                job.status.message = "Processando planilha"

            filepath = str(job.stored_file)
            if self._is_planilha_tratada(filepath):
                job.planilha_processada_path = filepath
                job.emit("[F1] Planilha já tratada detectada. Pulando Fase 1.", "INFO")
            else:
                job.emit("[F1] Iniciando processamento da planilha...", "INFO")
                job.planilha_processada_path = fase1_processamento.processar_planilha(filepath, job.emit)
                if not job.planilha_processada_path:
                    raise RuntimeError("Falha ao processar planilha na Fase 1.")

            with job.lock:
                job.status.message = "Login e setup"

            job.playwright_instance, job.browser, job.browser_context = fase2_login.launch_browser(job.emit)
            if not job.browser or not job.browser_context:
                raise RuntimeError("Falha ao iniciar navegador.")

            job.page = fase2_login.perform_login(
                job.browser_context,
                cfg.login,
                cfg.senha,
                URL_DESTINO,
                job.emit,
                browser_log_callback=lambda m, l="ERROR": job.browser_logs.append(
                    {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "level": l, "message": m}
                ),
            )
            if not job.page:
                raise RuntimeError("Falha no login.")
            
            job.take_screenshot("login_sucesso")


            dados_planilha = self._ler_dados_planilha(job)
            dados_para_processar = [item for item in dados_planilha if item.get("Status") == "Pendente"]
            if not dados_para_processar:
                job.emit("Nenhum item pendente encontrado.", "AVISO")
                with job.lock:
                    job.status.state = "completed"
                    job.status.message = "Finalizado sem pendências"
                return

            total = len(dados_para_processar)
            self._update_progress(job, 0, total, "Executando fases 3-5")

            for idx, item in enumerate(dados_para_processar, start=1):
                if job.stop_event.is_set():
                    break
                while not job.pause_event.is_set():
                    if job.stop_event.is_set():
                        break
                    time.sleep(0.2)
                if job.stop_event.is_set():
                    break

                nro = item.get("Nro cotação", "N/A")
                self._update_progress(job, idx - 1, total, f"Processando cotação {nro}")
                job.emit(f"--- Processando Item {idx}/{total} (Cotação: {nro}) ---", "INFO")

                ok3 = fase3_preenchimento.preencher_formulario(job.page, item, job.emit, job.pause_event, job.planilha_processada_path, cfg.atraso_etapas, cfg.atraso_fases)
                if not ok3:
                    job.take_screenshot(f"falha_formulario_cotacao_{nro}")
                    self._sleep_or_stop(job, cfg.atraso_fases)
                    self._reset_session(job, nro, cfg.atraso_fases)
                    continue

                self._sleep_or_stop(job, cfg.atraso_fases)
                ok4 = fase4_frete.preencher_frete(job.page, item, job.emit, job.pause_event, job.planilha_processada_path, cfg.atraso_etapas)
                if not ok4:
                    job.take_screenshot(f"falha_frete_cotacao_{nro}")
                    self._sleep_or_stop(job, cfg.atraso_fases)
                    self._reset_session(job, nro, cfg.atraso_fases)
                    continue

                self._sleep_or_stop(job, cfg.atraso_fases)
                ok5 = fase5_contrato_frete.preencher_contrato_frete(job.page, item, job.emit, job.pause_event, cfg.atraso_etapas, job.planilha_processada_path, cfg.atraso_fases, cfg.dados_km)
                if not ok5:
                    job.take_screenshot(f"falha_contrato_cotacao_{nro}")
                    self._sleep_or_stop(job, cfg.atraso_fases)
                    self._reset_session(job, nro, cfg.atraso_fases)
                    continue

                job.take_screenshot(f"sucesso_contrato_cotacao_{nro}")
                self._sleep_or_stop(job, cfg.atraso_fases)
                job.page.goto(URL_DESTINO, wait_until="networkidle", timeout=60000)
                self._update_progress(job, idx, total, f"Cotação {nro} concluída")

            with job.lock:
                if job.status.state != "stopped":
                    job.status.state = "completed"
                    job.status.message = "Finalizado"
                job.status.percent = 100.0 if job.status.total_items else 0
                if job.planilha_processada_path:
                    source_res = Path(job.planilha_processada_path)
                    final_res = RESULTS_DIR / f"{job.status.id}_{source_res.name}"
                    if source_res.exists() and source_res.resolve() != final_res.resolve():
                        shutil.copyfile(source_res, final_res)
                    job.status.result_file = str(final_res.resolve())

            if job.status.state == "stopped":
                job.emit("Execução interrompida.", "AVISO")
            else:
                job.emit("Automação concluída.", "SUCESSO")

        except Exception as e:
            try:
                job.take_screenshot("erro_critico_execucao")
            except Exception:
                pass
            job.emit(f"Erro crítico: {e}", "ERRO")
            job.emit(traceback.format_exc(), "DEBUG")
            with job.lock:
                job.status.state = "error"
                job.status.message = str(e)
        finally:
            video_path = None
            try:
                if job.page and job.page.video:
                    video_path = job.page.video.path()
            except Exception:
                pass

            self._close_resources(job)
            self._collect_video_artifact(job, video_path)
            self._append_result_history(job)
            self._append_logs_history(job)
            with job.condition:
                job.condition.notify_all()


    def _sleep_or_stop(self, job: JobRuntime, seconds: float) -> None:
        end = time.time() + max(seconds, 0)
        while time.time() < end:
            if job.stop_event.is_set():
                return
            while not job.pause_event.is_set():
                if job.stop_event.is_set():
                    return
                time.sleep(0.2)
            time.sleep(0.1)

    def _reset_session(self, job: JobRuntime, nro_cotacao: str, atraso_fases: float) -> None:
        if job.stop_event.is_set():
            return
        job.emit(f"[F0] [Item {nro_cotacao}] Reset de sessão via relogin.", "DEBUG")
        login = job.config.login
        senha = job.config.senha
        job.page = fase2_login.perform_login(job.browser_context, login, senha, URL_DESTINO, job.emit, existing_page=job.page)
        if not job.page:
            raise RuntimeError("Falha no relogin durante reset de sessão")
        self._sleep_or_stop(job, atraso_fases)

    def _is_planilha_tratada(self, filepath: str) -> bool:
        headers_esperados = ["Nro cotação", "Categoria veículo", "Cidade", "UF", "Nome", "Placa", "Data pagamento", "Viagem extra", "Remetente", "Status"]
        path = Path(filepath)
        if path.suffix.lower() == ".xls":
            wb = xlrd.open_workbook(filepath, formatting_info=False)
            sheet = wb.sheet_by_index(0)
            headers_encontrados = sheet.row_values(0) if sheet.nrows > 0 else []
            headers_limpos = [h for h in headers_encontrados if h is not None and str(h).strip() != ""]
            return headers_limpos == headers_esperados

        workbook = openpyxl.load_workbook(filepath, read_only=True)
        try:
            sheet = workbook.active
            headers_encontrados = [cell.value for cell in sheet[1]]
            headers_limpos = [h for h in headers_encontrados if h is not None]
            return headers_limpos == headers_esperados
        finally:
            workbook.close()

    def _ler_dados_planilha(self, job: JobRuntime) -> list[dict]:
        if not job.planilha_processada_path:
            return []
        wb = openpyxl.load_workbook(job.planilha_processada_path, data_only=True)
        ws = wb.active
        headers = [cell.value for cell in ws[1] if cell.value is not None]
        dados = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if all(cell is None for cell in row):
                continue
            row_data = dict(zip(headers, row))
            if row_data.get("Nro cotação"):
                dados.append(row_data)
        wb.close()
        return dados

    def _close_resources(self, job: JobRuntime) -> None:
        try:
            if job.browser_context:
                job.browser_context.close()
        except Exception:
            pass
        try:
            if job.browser:
                job.browser.close()
        except Exception:
            pass

    def _collect_video_artifact(self, job: JobRuntime, video_path: Optional[str] = None) -> None:
        try:
            source_path = video_path
            if not source_path and job.page and job.page.video:
                try:
                    source_path = job.page.video.path()
                except Exception:
                    pass
            if not source_path:
                return
            source = Path(source_path)
            if not source.exists():
                return
            target = ARTIFACTS_DIR / f"{job.log_session_id}_{source.name}"
            shutil.copyfile(source, target)
            with job.lock:
                # Evita duplicidade se já houver
                if not any(a.get("name") == target.name for a in job.artifacts):
                    job.artifacts.append({"type": "video", "name": target.name, "path": str(target.resolve())})
        except Exception:
            pass
        try:
            if job.playwright_instance:
                job.playwright_instance.stop()
        except Exception:
            pass



manager = AutomationManager()
