"""
memory/database.py
------------------
SQLite schema creation and connection management.
All tables are created here on first run.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Generator

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

DDL = """
-- User Profile
CREATE TABLE IF NOT EXISTS user_profiles (
    employee_id    TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL,
    role           TEXT NOT NULL,
    project        TEXT NOT NULL,
    experience_level TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Learning Progress
CREATE TABLE IF NOT EXISTS learning_progress (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id    TEXT NOT NULL,
    topic          TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Pending',
    completed_at   TEXT,
    UNIQUE(employee_id, topic),
    FOREIGN KEY (employee_id) REFERENCES user_profiles(employee_id)
);

-- Conversation Memory
CREATE TABLE IF NOT EXISTS conversations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    employee_id    TEXT NOT NULL,
    role           TEXT NOT NULL,   -- 'user' | 'assistant'
    content        TEXT NOT NULL,
    timestamp      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_employee ON conversations(employee_id);

-- Ingestion Audit Log
CREATE TABLE IF NOT EXISTS ingestion_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    TEXT NOT NULL,
    filename       TEXT NOT NULL,
    uploaded_by    TEXT,
    chunks_stored  INTEGER DEFAULT 0,
    pii_detected   INTEGER DEFAULT 0,
    duplicate      INTEGER DEFAULT 0,
    status         TEXT NOT NULL,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    db_path = str(settings.db_path)
    logger.info("initialising_sqlite", path=db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(DDL)
        # Seed demo users (INSERT OR IGNORE = safe to run every startup)
        seed_users = [
            ("EMP-001", "Demo User",  "demo@kt-agent.com",  "Software Engineer",       "Existing Team Member"),
            ("EMP-003", "Sarah Chen", "sarah@kt-agent.com", "Senior Backend Engineer",  "Existing Team Member"),
        ]
        for emp in seed_users:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_profiles
                    (employee_id, name, email, role, project, experience_level,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, '', ?, datetime('now'), datetime('now'))
                """,
                emp,
            )
        # EMP-002 (Alex) intentionally NOT seeded — new joiner fills profile on first login
        conn.commit()
    logger.info("sqlite_ready")


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row_factory set."""
    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
