"""Broadcaster e gerenciador de conexões WebSocket para logs e eventos em tempo real."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket

from .repository import JobRepository, job_repository


logger = logging.getLogger("contratos_auto.broadcaster")


class JobBroadcaster:
    """Gerencia conexões WebSocket e SSE ativas por Job e emite logs estruturados com persistência."""

    def __init__(self, repository: Optional[JobRepository] = None):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._sse_queues: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self.repo = repository or job_repository
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Registra o loop de eventos principal do FastAPI para chamadas thread-safe."""
        self.main_loop = loop

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        """Aceita e registra uma conexão WebSocket para o Job."""
        await websocket.accept()
        async with self._lock:
            if job_id not in self._connections:
                self._connections[job_id] = set()
            self._connections[job_id].add(websocket)

    async def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        """Remove a conexão WebSocket."""
        async with self._lock:
            if job_id in self._connections:
                self._connections[job_id].discard(websocket)
                if not self._connections[job_id]:
                    del self._connections[job_id]

    def register_sse(self, job_id: str, queue: asyncio.Queue) -> None:
        """Registra uma fila assíncrona de eventos SSE para o Job."""
        if job_id not in self._sse_queues:
            self._sse_queues[job_id] = set()
        self._sse_queues[job_id].add(queue)

    def unregister_sse(self, job_id: str, queue: asyncio.Queue) -> None:
        """Remove a fila SSE do Job."""
        if job_id in self._sse_queues:
            self._sse_queues[job_id].discard(queue)
            if not self._sse_queues[job_id]:
                del self._sse_queues[job_id]

    async def broadcast_event(self, job_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Envia um evento estruturado para todos os clientes conectados (WebSocket e SSE)."""
        message = {
            "type": event_type,
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "data": payload,
        }
        text_payload = json.dumps(message, ensure_ascii=False)

        # 1. Envio para WebSockets
        async with self._lock:
            sockets = list(self._connections.get(job_id, set()))

        for ws in sockets:
            try:
                await ws.send_text(text_payload)
            except Exception:
                async with self._lock:
                    if job_id in self._connections:
                        self._connections[job_id].discard(ws)

        # 2. Envio para SSE Queues
        queues = list(self._sse_queues.get(job_id, set()))
        for q in queues:
            try:
                q.put_nowait(message)
            except Exception:
                pass

    def _schedule_broadcast(self, job_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        """Agenda o broadcast de forma thread-safe seja do loop assíncrono ou de Worker Threads."""
        target_loop = self.main_loop
        if not target_loop or not target_loop.is_running():
            try:
                target_loop = asyncio.get_running_loop()
            except RuntimeError:
                target_loop = None

        if target_loop and target_loop.is_running():
            try:
                # Se estamos na mesma thread do loop:
                if asyncio.get_running_loop() is target_loop:
                    target_loop.create_task(self.broadcast_event(job_id, event_type, payload))
                    return
            except RuntimeError:
                pass
            # Se estamos em thread separada (Worker Thread):
            target_loop.call_soon_threadsafe(
                lambda: target_loop.create_task(self.broadcast_event(job_id, event_type, payload))
            )

    def log(
        self,
        job_id: str,
        message: str,
        level: str = "INFO",
        phase: str = "GERAL",
        nro_cotacao: Optional[str] = None,
    ) -> None:
        """
        Registra o log no banco SQLite e agenda o broadcast assíncrono para WebSockets e SSE.
        Totalmente thread-safe para chamadas da Worker Thread.
        """
        # 1. Persistência no SQLite
        try:
            self.repo.add_log(
                job_id=job_id,
                message=message,
                level=level,
                phase=phase,
                nro_cotacao=nro_cotacao,
            )
        except Exception as e:
            logger.error(f"Erro ao salvar log no SQLite: {e}")

        # 2. Broadcast via loop assíncrono
        payload = {
            "level": level.upper(),
            "phase": phase,
            "nro_cotacao": nro_cotacao,
            "message": message,
        }
        self._schedule_broadcast(job_id, "log", payload)

    def emit_progress(
        self,
        job_id: str,
        current_index: int,
        total_items: int,
        status: str,
        current_item: Optional[dict] = None,
    ) -> None:
        """Emite evento de atualização de progresso para a UI de forma thread-safe."""
        payload = {
            "current_index": current_index,
            "total_items": total_items,
            "percent": round((current_index / total_items * 100), 1) if total_items > 0 else 0,
            "status": status,
            "current_item": current_item,
        }
        self._schedule_broadcast(job_id, "progress", payload)


# Instância global singleton
broadcaster = JobBroadcaster()
