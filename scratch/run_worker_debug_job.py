import configparser
import os
import time
from pathlib import Path

from backend.app.engine.excel_processor import ExcelProcessor
from backend.app.infrastructure.database import db
from backend.app.infrastructure.repository import job_repository
from backend.app.infrastructure.worker import JobWorker


source = Path(r"C:\Users\felipe\Downloads\relatorio (12).xls")
config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")

usuario = config.get("CREDENCIAS", "login", fallback="")
senha = config.get("CREDENCIAS", "senha", fallback="")
throttle = config.getfloat("AUTOMACAO", "atrasofases", fallback=0.1)

db.init_db()

processor = ExcelProcessor(source, log_callback=lambda msg, level="INFO": print(f"{level} {msg}", flush=True))
report = processor.validate_upload()
skip_first = int(os.getenv("SKIP_FIRST", "0"))
if skip_first:
    processor.items = processor.items[skip_first:]
    report.total_rows = len(processor.items) + len(processor.validation_errors)
    report.pending_rows_count = sum(1 for item in processor.items if item.status.value == "Pendente")
print(
    f"VALID={report.is_valid}; SKIP_FIRST={skip_first}; TOTAL={report.total_rows}; "
    f"PENDING={report.pending_rows_count}; INVALID={report.invalid_rows_count}",
    flush=True,
)
if not report.is_valid:
    raise SystemExit("Planilha sem itens válidos para execução.")

job_id = job_repository.create_job(
    filename=source.name,
    total_items=report.total_rows,
    items=processor.items,
    invalid_items=processor.validation_errors,
    username=usuario,
)
print(f"JOB_ID={job_id}", flush=True)

worker = JobWorker(
    job_id=job_id,
    usuario=usuario,
    senha=senha,
    excel_path=source,
    headless=False,
    throttle_seconds=throttle,
)
worker.start()

seen = 0
deadline = time.time() + 1800
final_states = {"COMPLETED", "FAILED", "CANCELLED"}

while time.time() < deadline:
    logs = job_repository.list_job_logs(job_id, limit=2000)
    for row in logs[seen:]:
        print(
            f"[{row['timestamp']}] {row['level']} {row['phase']} {row['message']}",
            flush=True,
        )
    seen = len(logs)

    job = job_repository.get_job(job_id) or {}
    status = job.get("status")
    if status in final_states:
        print(f"FINAL_STATE={status}; ERROR={job.get('error_summary') or ''}", flush=True)
        break

    time.sleep(1)
else:
    print("TIMEOUT_WAITING_JOB", flush=True)
