"""Worker orquestrador de execução em background em Thread dedicada."""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from ..domain.models import ItemContrato, ItemResult, ItemStatus
from ..engine.contract_runner import ContractRunner
from ..engine.excel_processor import ExcelProcessor
from .artifacts import ArtifactManager, artifact_manager
from .broadcaster import JobBroadcaster, broadcaster
from .repository import JobRepository, job_repository

logger = logging.getLogger("contratos_auto.worker")


class JobWorker:
    """Gerencia a execução assíncrona de um lote via Thread dedicada."""

    def __init__(
        self,
        job_id: str,
        usuario: str,
        senha: str,
        excel_path: Path | str,
        headless: Optional[bool] = None,
        throttle_seconds: float = 2.5,
        repository: Optional[JobRepository] = None,
        artifacts: Optional[ArtifactManager] = None,
        broadcaster_inst: Optional[JobBroadcaster] = None,
    ):
        self.job_id = job_id
        self.usuario = usuario
        self.senha = senha
        self.excel_path = Path(excel_path)
        headless_env = os.getenv("PLAYWRIGHT_HEADLESS", "true").strip().lower() == "true"
        self.headless = headless if headless is not None else headless_env
        self.throttle_seconds = throttle_seconds

        self.repo = repository or job_repository
        self.artifacts = artifacts or artifact_manager
        self.broadcaster = broadcaster_inst or broadcaster

        self._thread: Optional[threading.Thread] = None
        self._cancel_requested = threading.Event()
        self._pause_requested = threading.Event()
        self._is_paused = False

    def is_running(self) -> bool:
        """Verifica se a thread do worker está ativa."""
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Inicia a thread do worker."""
        if self.is_running():
            raise RuntimeError(f"O Job {self.job_id} já está em execução.")

        self._cancel_requested.clear()
        self._pause_requested.clear()
        self._is_paused = False

        self._thread = threading.Thread(target=self._run, name=f"Worker-{self.job_id}", daemon=True)
        self._thread.start()

    def pause(self) -> None:
        """Solicita pausa na execução entre cotações."""
        self._pause_requested.set()
        self.repo.update_job_status(self.job_id, "PAUSED")
        self.broadcaster.log(self.job_id, "Pausa solicitada pelo usuário. Aguardando conclusão do item atual...", "AVISO")

    def resume(self) -> None:
        """Retoma a execução de um job pausado."""
        self._pause_requested.clear()
        self._is_paused = False
        self.repo.update_job_status(self.job_id, "RUNNING")
        self.broadcaster.log(self.job_id, "Execução retomada pelo usuário.", "INFO")

    def cancel(self) -> None:
        """Solicita cancelamento imediato da execução."""
        self._cancel_requested.set()
        self.broadcaster.log(self.job_id, "Cancelamento solicitado pelo usuário.", "AVISO")

    def _run(self) -> None:
        """Loop de trabalho principal da Thread."""
        start_time = time.time()
        if self.usuario:
            self.repo.update_job_username(self.job_id, self.usuario)
        self.repo.update_job_status(self.job_id, "RUNNING")
        self.broadcaster.log(self.job_id, f"Iniciando processamento do Job {self.job_id}...", "INFO")

        # 1. Carrega itens pendentes para processar (suporte nativo a Resume)
        pending_items = self.repo.get_pending_items(self.job_id)
        job_meta = self.repo.get_job(self.job_id) or {}
        total_items = job_meta.get("total_items", len(pending_items))

        if not pending_items:
            self.broadcaster.log(self.job_id, "Nenhum item pendente encontrado para este Job.", "AVISO")
            self.repo.update_job_status(self.job_id, "COMPLETED", duration_seconds=time.time() - start_time)
            return

        # 2. Configura callbacks de log e progresso
        def log_cb(msg: str, level: str = "INFO") -> None:
            phase = "GERAL"
            for p in ("F1", "F2", "F3", "F4", "F5"):
                if f"[{p}]" in msg:
                    phase = p
                    break
            self.broadcaster.log(self.job_id, msg, level=level, phase=phase)

        def progress_cb(current: int, total: int, item: ItemContrato) -> None:
            self.broadcaster.emit_progress(
                self.job_id,
                current_index=current,
                total_items=total,
                status="RUNNING",
                current_item=item.model_dump(),
            )

        # 3. Inicializa o processador de Excel e o runner de automação
        excel_proc = ExcelProcessor(self.excel_path, log_callback=log_cb)
        runner = ContractRunner(
            usuario=self.usuario,
            senha=self.senha,
            headless=self.headless,
            throttle_seconds=self.throttle_seconds,
            log_callback=log_cb,
            progress_callback=progress_cb,
        )

        try:
            # Login único compartilhado para o lote
            runner.login()

            for idx, item in enumerate(pending_items, start=1):
                # Verifica cancelamento
                if self._cancel_requested.is_set():
                    self.broadcaster.log(self.job_id, "Execução cancelada pelo usuário.", "AVISO")
                    self.repo.update_job_status(self.job_id, "CANCELLED", duration_seconds=time.time() - start_time)
                    break

                # Verifica pausa
                while self._pause_requested.is_set():
                    self._is_paused = True
                    time.sleep(1.0)
                    if self._cancel_requested.is_set():
                        break

                if self._cancel_requested.is_set():
                    self.repo.update_job_status(self.job_id, "CANCELLED", duration_seconds=time.time() - start_time)
                    break

                # Atualiza item como PROCESSANDO
                item_start = time.time()
                self.repo.update_item_result(
                    job_id=self.job_id,
                    nro_cotacao=item.nro_cotacao,
                    status=ItemStatus.PENDENTE,
                )

                # Executa a linha individualmente
                result = runner.process_single_item(item)
                item_duration = time.time() - item_start

                # Persiste o resultado unitário imediatamente no SQLite
                if result.sucesso:
                    excel_proc.mark_success(item.nro_cotacao)
                    self.repo.update_item_result(
                        job_id=self.job_id,
                        nro_cotacao=item.nro_cotacao,
                        status=ItemStatus.CONCLUIDO,
                        cte_number=result.cte_number,
                        extracted_nf=item.extracted_nf,
                        extracted_nro_pedido=item.extracted_nro_pedido,
                        extracted_obs_interna=item.extracted_obs_interna,
                        duration_seconds=item_duration,
                    )
                else:
                    motivo = result.motivo_erro or "Erro não identificado"
                    excel_proc.mark_error(item.nro_cotacao, motivo)
                    self.repo.update_item_result(
                        job_id=self.job_id,
                        nro_cotacao=item.nro_cotacao,
                        status=ItemStatus.ERRO,
                        error_message=motivo,
                        duration_seconds=item_duration,
                    )

                    # Se houver captura de tela em caso de erro
                    if runner.page:
                        try:
                            sc_bytes = runner.page.screenshot(full_page=True)
                            self.artifacts.save_error_screenshot(self.job_id, item.nro_cotacao, sc_bytes)
                        except Exception as e:
                            logger.error(f"Falha ao salvar screenshot de erro: {e}")

                # Rate limiting suave entre cotações
                if idx < len(pending_items) and not self._cancel_requested.is_set():
                    time.sleep(self.throttle_seconds)

            # 4. Finalização e geração do relatório consolidado
            if not self._cancel_requested.is_set():
                out_excel = self.artifacts.get_job_dir(self.job_id) / f"{self.job_id}.xlsx"
                excel_proc.save_output(out_excel)
                self.artifacts.register_excel_report(self.job_id, out_excel)

                total_duration = time.time() - start_time
                self.repo.update_job_status(self.job_id, "COMPLETED", duration_seconds=total_duration)
                self.broadcaster.log(self.job_id, f"Lote concluído com sucesso em {total_duration:.1f}s.", "SUCESSO")

        except Exception as e:
            logger.exception(f"Erro fatal durante execução do worker: {e}")
            total_duration = time.time() - start_time
            self.repo.update_job_status(self.job_id, "FAILED", error_summary=str(e), duration_seconds=total_duration)
            self.broadcaster.log(self.job_id, f"Falha fatal no lote: {e}", "ERRO")
        finally:
            runner.close()


class WorkerManager:
    """Gerenciador central de instâncias de workers."""

    def __init__(self):
        self._workers: Dict[str, JobWorker] = {}
        # RLock (reentrante): get_active_worker é chamado dentro de create_and_start_worker,
        # que já segura o lock — Lock comum causava deadlock no endpoint /start.
        self._lock = threading.RLock()

    def get_active_worker(self) -> Optional[JobWorker]:
        """Retorna o worker atualmente em execução, se houver."""
        with self._lock:
            for w in self._workers.values():
                if w.is_running():
                    return w
            return None

    def create_and_start_worker(
        self,
        job_id: str,
        usuario: str,
        senha: str,
        excel_path: Path | str,
        headless: Optional[bool] = None,
        throttle_seconds: float = 2.5,
    ) -> JobWorker:
        """Cria e dispara um novo worker para o Job."""
        with self._lock:
            active = self.get_active_worker()
            if active:
                raise RuntimeError(f"Já existe um lote em execução ({active.job_id}). Aguarde a conclusão ou cancele-o.")

            worker = JobWorker(
                job_id=job_id,
                usuario=usuario,
                senha=senha,
                excel_path=excel_path,
                headless=headless,
                throttle_seconds=throttle_seconds,
            )
            self._workers[job_id] = worker
            worker.start()
            return worker

    def get_worker(self, job_id: str) -> Optional[JobWorker]:
        with self._lock:
            return self._workers.get(job_id)


# Instância global singleton
worker_manager = WorkerManager()
