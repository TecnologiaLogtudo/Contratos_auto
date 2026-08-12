import sys
import os
import time
from pathlib import Path

# Add root folder to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir))

from backend.app.services.automation_manager import manager
from backend.app.schemas import AutomationConfig

def run():
    print("Initializing test job...")
    source_file = Path("c:/Users/felipe/OneDrive/NOVO PC/Logtudo/Contratos_auto/teste_teste_teste.xls")
    
    config = AutomationConfig(
        login="Atualizarbi",
        senha="Atualizar123BI",
        atraso_fases=0.1,
        atraso_etapas=0.05,
        dados_km="20",
        aceitar_frete_minimo_antt=True
    )
    
    # Create the job
    job = manager.create_job(source_file, config, requester_ip="127.0.0.1")
    job_id = job.status.id
    print(f"Job created with ID: {job_id}")
    print(f"Log Session ID: {job.log_session_id}")
    
    # Monitor the job status and logs
    last_log_seq = 0
    while True:
        # Fetch status
        status = job.status
        state = status.state
        message = status.message
        percent = status.percent
        
        # Print new logs
        logs = list(job.logs)
        for log in logs:
            if log.seq > last_log_seq:
                print(f"[{log.timestamp}] [{log.level}] {log.message}")
                last_log_seq = log.seq
                
        if state in ["completed", "error", "stopped"]:
            print(f"\nJob finished. Final state: {state.upper()}. Message: {message}")
            break
            
        time.sleep(1)

if __name__ == "__main__":
    run()
