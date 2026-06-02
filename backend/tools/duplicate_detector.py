"""
tools/duplicate_detector.py
----------------------------
Detects duplicate documents before ingestion.
Strategy: SHA-256 hash of the raw document text.
Stores hashes in SQLite to avoid re-querying Pinecone.
"""
from __future__ import annotations

import hashlib

from memory.database import get_db
from core.logger import get_logger

logger = get_logger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS document_hashes (
    hash       TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    filename   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _ensure_table() -> None:
    with get_db() as db:
        db.executescript(_DDL)


def is_duplicate(text: str) -> tuple[bool, str]:
    """
    Returns (is_duplicate: bool, existing_document_id: str).
    existing_document_id is empty string if not a duplicate.
    """
    _ensure_table()
    digest = _hash(text)
    with get_db() as db:
        row = db.execute(
            "SELECT document_id FROM document_hashes WHERE hash = ?",
            (digest,),
        ).fetchone()
    if row:
        logger.info("duplicate_detected", document_id=row["document_id"])
        return True, row["document_id"]
    return False, ""


def register_document(text: str, document_id: str, filename: str) -> None:
    """Record the hash so future duplicates can be caught."""
    _ensure_table()
    digest = _hash(text)
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO document_hashes (hash, document_id, filename) VALUES (?,?,?)",
            (digest, document_id, filename),
        )
    logger.info("document_hash_registered", document_id=document_id)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
