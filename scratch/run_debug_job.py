import time
from pathlib import Path

from backend.app.services.automation_manager import manager


source = Path(r"C:\Users\felipe\Downloads\relatorio (12).xls")
cfg = manager.load_config()
job = manager.create_job(source, cfg, "codex-debug")

print(f"JOB_ID={job.status.id}", flush=True)
seen = 0
deadline = time.time() + 1800
reached_f5 = False
final_states = {"completed", "error", "stopped"}

while time.time() < deadline:
    with job.lock:
        logs = list(job.logs)
        state = job.status.state
        message = job.status.message
        phase = job.status.current_phase

    for ev in logs[seen:]:
        print(
            f"[{ev.timestamp}] {ev.level} {ev.phase or ''} {ev.message}",
            flush=True,
        )
        if ev.phase == "F5" or "[F5]" in ev.message:
            reached_f5 = True

    seen = len(logs)
    if state in final_states:
        print(
            f"FINAL_STATE={state}; MESSAGE={message}; PHASE={phase}; REACHED_F5={reached_f5}",
            flush=True,
        )
        break

    time.sleep(1)
else:
    print("TIMEOUT_WAITING_JOB", flush=True)
