"""Módulo de conexão e gerenciamento de esquema SQLite para o Contratos_auto."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


# Diretório base de armazenamento (na raiz do projeto, fora de backend para não disparar uvicorn --reload)
BASE_STORAGE_DIR = Path(__file__).resolve().parents[3] / "storage"
BASE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = BASE_STORAGE_DIR / "database.db"


class Database:
    """Gerenciador de conexão SQLite thread-safe com suporte a WAL mode e busy timeout."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Obtém uma conexão isolada por thread."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=10.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            # Ativa WAL mode e foreign keys
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA busy_timeout=5000;")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager transacional atômico."""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def init_db(self) -> None:
        """Cria as tabelas caso não existam."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        with conn:
            # 1. Tabela de Jobs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    error_count INTEGER NOT NULL DEFAULT 0,
                    invalid_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    finished_at DATETIME,
                    duration_seconds REAL,
                    error_summary TEXT,
                    user_credentials_username TEXT
                );
            """)

            # Migração automática e segura para bancos SQLite existentes criados em versões anteriores
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN user_credentials_username TEXT;")
            except sqlite3.OperationalError:
                pass  # Coluna já existe

            # 2. Tabela de Itens
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_items (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    row_index INTEGER NOT NULL,
                    nro_cotacao TEXT NOT NULL,
                    categoria_veiculo TEXT,
                    cidade TEXT,
                    uf TEXT,
                    nome TEXT,
                    placa TEXT,
                    data_pagamento TEXT,
                    viagem_extra TEXT DEFAULT 'Não',
                    remetente TEXT,
                    validade TEXT,
                    frete_a_pagar TEXT,
                    frete_negociado TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDENTE',
                    error_message TEXT,
                    extracted_nro_pedido TEXT,
                    extracted_obs_interna TEXT,
                    extracted_nf TEXT,
                    cte_number TEXT,
                    duration_seconds REAL,
                    executed_at DATETIME
                );
            """)

            # Índices de consulta rápida
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_items_job_id ON job_items(job_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_items_status ON job_items(status);")

            # 3. Tabela de Logs Estruturados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL DEFAULT 'INFO',
                    phase TEXT DEFAULT 'GERAL',
                    nro_cotacao TEXT,
                    message TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_logs_job_id ON job_logs(job_id);")

            # 4. Tabela de Artefatos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_artifacts (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    nro_cotacao TEXT,
                    artifact_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_size_bytes INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_job_artifacts_job_id ON job_artifacts(job_id);")

        conn.close()

    def close(self) -> None:
        """Fecha conexão da thread atual."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None


# Instância global singleton
db = Database()
