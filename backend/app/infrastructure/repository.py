"""Repositório unificado SQLite para Jobs, Itens, Logs e Artefatos do Contratos_auto."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from ..domain.models import ItemContrato, ItemStatus
from .database import Database, db


class JobRepository:
    """Implementa o padrão Repository para operações no SQLite."""

    def __init__(self, database: Optional[Database] = None):
        self.db = database or db

    # =========================================================================
    # JOBS
    # =========================================================================

    def generate_next_job_id(self, date: Optional[datetime] = None) -> str:
        """
        Gera um ID e nome sequencial diário para o Job no formato 'ddmmaa-xxxxx'.
        Exemplo: 080926-00001
        """
        target_date = date or datetime.now()
        prefix = target_date.strftime("%d%m%y")
        pattern = f"{prefix}-%"

        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM jobs WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
            (pattern,),
        )
        row = cur.fetchone()
        if row and row["id"]:
            try:
                last_seq = int(row["id"].split("-")[1])
                next_seq = last_seq + 1
            except (IndexError, ValueError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}-{next_seq:05d}"

    def create_job(
        self,
        filename: str,
        total_items: int,
        items: List[ItemContrato],
        invalid_items: Optional[List[Tuple[ItemContrato, str]]] = None,
        job_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> str:
        """Cria um novo Job com ID no padrão ddmmaa-xxxxx e insere todos os seus itens atomicamente."""
        jid = job_id or self.generate_next_job_id()
        invalid_items = invalid_items or []
        invalid_count = len(invalid_items)

        with self.db.transaction() as cur:
            initial_success = sum(1 for i in items if i.status == ItemStatus.CONCLUIDO)
            # 1. Cria o Job
            cur.execute(
                """
                INSERT INTO jobs (id, filename, status, total_items, success_count, error_count, invalid_count, user_credentials_username)
                VALUES (?, ?, 'PENDING', ?, ?, 0, ?, ?)
                """,
                (jid, filename, total_items, initial_success, invalid_count, username),
            )

            # 2. Insere os itens válidos
            for item in items:
                item_id = f"{jid}_{item.row_index}_{item.nro_cotacao}"
                cur.execute(
                    """
                    INSERT INTO job_items (
                        id, job_id, row_index, nro_cotacao, categoria_veiculo, cidade, uf,
                        nome, placa, data_pagamento, viagem_extra, remetente, validade,
                        frete_a_pagar, frete_negociado, status, error_message,
                        extracted_nro_pedido, extracted_obs_interna, extracted_nf, cte_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_id, jid, item.row_index, item.nro_cotacao, item.categoria_veiculo,
                        item.cidade, item.uf, item.nome, item.placa, item.data_pagamento,
                        item.viagem_extra, item.remetente, item.validade, item.frete_a_pagar,
                        item.frete_negociado, item.status.value, item.observacao_erro,
                        item.extracted_nro_pedido, item.extracted_obs_interna,
                        item.extracted_nf, None
                    ),
                )

            # 3. Insere os itens que falharam na validação prévia
            for inv_item, motivo in invalid_items:
                inv_id = f"{jid}_{inv_item.row_index}_{inv_item.nro_cotacao}"
                cur.execute(
                    """
                    INSERT INTO job_items (
                        id, job_id, row_index, nro_cotacao, categoria_veiculo, cidade, uf,
                        nome, placa, data_pagamento, viagem_extra, remetente, validade,
                        frete_a_pagar, frete_negociado, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        inv_id, jid, inv_item.row_index, inv_item.nro_cotacao, inv_item.categoria_veiculo,
                        inv_item.cidade, inv_item.uf, inv_item.nome, inv_item.placa, inv_item.data_pagamento,
                        inv_item.viagem_extra, inv_item.remetente, inv_item.validade, inv_item.frete_a_pagar,
                        inv_item.frete_negociado, ItemStatus.FALHA_VALIDACAO.value, motivo
                    ),
                )

        return jid

    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_summary: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Atualiza o estado global de um Job."""
        with self.db.transaction() as cur:
            now = datetime.now().isoformat()
            if status == "RUNNING":
                cur.execute(
                    "UPDATE jobs SET status = ?, started_at = COALESCE(started_at, ?) WHERE id = ?",
                    (status, now, job_id),
                )
            elif status in ("COMPLETED", "FAILED", "CANCELLED"):
                cur.execute(
                    """
                    UPDATE jobs
                    SET status = ?, finished_at = ?, error_summary = COALESCE(?, error_summary),
                        duration_seconds = COALESCE(?, duration_seconds)
                    WHERE id = ?
                    """,
                    (status, now, error_summary, duration_seconds, job_id),
                )
            else:
                cur.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))

    def update_job_counts(self, job_id: str) -> dict:
        """Recalcula e persiste as contagens de sucesso/erro de um Job."""
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT
                    SUM(CASE WHEN status = 'Concluído' THEN 1 ELSE 0 END) as success_cnt,
                    SUM(CASE WHEN status = 'Erro' THEN 1 ELSE 0 END) as error_cnt,
                    SUM(CASE WHEN status = 'Falha Validação' THEN 1 ELSE 0 END) as invalid_cnt
                FROM job_items WHERE job_id = ?
                """,
                (job_id,),
            )
            row = cur.fetchone()
            s_cnt = row["success_cnt"] or 0
            e_cnt = row["error_cnt"] or 0
            i_cnt = row["invalid_cnt"] or 0

            cur.execute(
                "UPDATE jobs SET success_count = ?, error_count = ?, invalid_count = ? WHERE id = ?",
                (s_cnt, e_cnt, i_cnt, job_id),
            )
            return {"success_count": s_cnt, "error_count": e_cnt, "invalid_count": i_cnt}

    def get_job(self, job_id: str) -> Optional[dict]:
        """Recupera metadados completos de um Job."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_jobs(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Lista jobs ordenados por data decrescente."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # ITENS
    # =========================================================================

    def get_pending_items(self, job_id: str) -> List[ItemContrato]:
        """Recupera itens pendentes ou em processamento para execução/retomada."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM job_items
            WHERE job_id = ? AND status IN ('Pendente', 'Processando')
            ORDER BY row_index ASC
            """,
            (job_id,),
        )
        items = []
        for r in cur.fetchall():
            items.append(
                ItemContrato(
                    nro_cotacao=r["nro_cotacao"],
                    categoria_veiculo=r["categoria_veiculo"] or "",
                    cidade=r["cidade"] or "",
                    uf=r["uf"] or "",
                    nome=r["nome"] or "",
                    placa=r["placa"] or "",
                    data_pagamento=r["data_pagamento"] or "",
                    viagem_extra=r["viagem_extra"] or "Não",
                    remetente=r["remetente"] or "",
                    validade=r["validade"],
                    frete_a_pagar=r["frete_a_pagar"],
                    frete_negociado=r["frete_negociado"],
                    status=ItemStatus(r["status"]),
                    observacao_erro=r["error_message"],
                    extracted_nro_pedido=r["extracted_nro_pedido"],
                    extracted_obs_interna=r["extracted_obs_interna"],
                    extracted_nf=r["extracted_nf"],
                    row_index=r["row_index"],
                )
            )
        return items

    def update_item_result(
        self,
        job_id: str,
        nro_cotacao: str,
        status: ItemStatus,
        error_message: Optional[str] = None,
        cte_number: Optional[str] = None,
        extracted_nf: Optional[str] = None,
        extracted_nro_pedido: Optional[str] = None,
        extracted_obs_interna: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Atualiza o resultado de processamento de um item individual com atomicidade."""
        with self.db.transaction() as cur:
            now = datetime.now().isoformat()
            cur.execute(
                """
                UPDATE job_items
                SET status = ?,
                    error_message = ?,
                    cte_number = COALESCE(?, cte_number),
                    extracted_nf = COALESCE(?, extracted_nf),
                    extracted_nro_pedido = COALESCE(?, extracted_nro_pedido),
                    extracted_obs_interna = COALESCE(?, extracted_obs_interna),
                    duration_seconds = ?,
                    executed_at = ?
                WHERE job_id = ? AND nro_cotacao = ?
                """,
                (
                    status.value,
                    error_message,
                    cte_number,
                    extracted_nf,
                    extracted_nro_pedido,
                    extracted_obs_interna,
                    duration_seconds,
                    now,
                    job_id,
                    nro_cotacao,
                ),
            )
        self.update_job_counts(job_id)

    def list_job_items(self, job_id: str) -> List[dict]:
        """Lista todos os itens de um job específico."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_items WHERE job_id = ? ORDER BY row_index ASC", (job_id,))
        return [dict(r) for r in cur.fetchall()]

    def update_job_username(self, job_id: str, username: str) -> None:
        """Atualiza o nome do operador (usuário) do Job."""
        try:
            with self.db.transaction() as cur:
                cur.execute(
                    "UPDATE jobs SET user_credentials_username = ? WHERE id = ?",
                    (username, job_id),
                )
        except Exception as e:
            logger.warning(f"Aviso ao atualizar operador do Job {job_id}: {e}")

    # =========================================================================
    # LOGS
    # =========================================================================

    def add_log(
        self,
        job_id: str,
        message: str,
        level: str = "INFO",
        phase: str = "GERAL",
        nro_cotacao: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Grava uma entrada de log estruturado para o Job com horário local."""
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO job_logs (job_id, timestamp, level, phase, nro_cotacao, message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, ts, level.upper(), phase, nro_cotacao, message),
            )

    def list_job_logs(
        self,
        job_id: str,
        level: Optional[str] = None,
        limit: int = 500,
    ) -> List[dict]:
        """Consulta histórico de logs estruturados de um Job."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        if level:
            cur.execute(
                "SELECT * FROM job_logs WHERE job_id = ? AND level = ? ORDER BY id ASC LIMIT ?",
                (job_id, level.upper(), limit),
            )
        else:
            cur.execute(
                "SELECT * FROM job_logs WHERE job_id = ? ORDER BY id ASC LIMIT ?",
                (job_id, limit),
            )
        return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # ARTEFATOS
    # =========================================================================

    def add_artifact(
        self,
        job_id: str,
        artifact_type: str,
        file_path: str,
        file_name: str,
        nro_cotacao: Optional[str] = None,
        file_size_bytes: int = 0,
    ) -> str:
        """Registra um artefato gerado no banco."""
        art_id = f"art_{uuid.uuid4().hex[:8]}"
        with self.db.transaction() as cur:
            cur.execute(
                """
                INSERT INTO job_artifacts (id, job_id, nro_cotacao, artifact_type, file_path, file_name, file_size_bytes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (art_id, job_id, nro_cotacao, artifact_type, file_path, file_name, file_size_bytes),
            )
        return art_id

    def list_job_artifacts(self, job_id: str) -> List[dict]:
        """Lista os artefatos vinculados a um Job."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_artifacts WHERE job_id = ? ORDER BY created_at ASC", (job_id,))
        return [dict(r) for r in cur.fetchall()]

    def get_artifact(self, artifact_id: str) -> Optional[dict]:
        """Busca um artefato pelo ID."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_artifacts WHERE id = ?", (artifact_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# Instância global singleton
job_repository = JobRepository()
