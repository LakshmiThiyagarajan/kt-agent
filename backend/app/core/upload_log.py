import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("upload_logs.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                hash TEXT PRIMARY KEY,
                file_name TEXT,
                uploaded_at TEXT,
                chunks INTEGER,
                uploaded_by TEXT
            )
        """)


def upload_exists(file_hash: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT 1 FROM uploads WHERE hash = ?",
            (file_hash,)
        )
        return cur.fetchone() is not None


def log_upload(file_hash: str, file_name: str, chunks: int, uploaded_by: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO uploads (hash, file_name, uploaded_at, chunks, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
        """, (
            file_hash,
            file_name,
            datetime.utcnow().isoformat(),
            chunks,
            uploaded_by
        ))