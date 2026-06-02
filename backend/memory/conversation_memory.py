"""
memory/conversation_memory.py
------------------------------
Store and retrieve conversation turns per session.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core.logger import get_logger
from core.schemas import ChatMessage
from memory.database import get_db

logger = get_logger(__name__)

MAX_HISTORY = 20   # max messages returned per session


class ConversationMemory:

    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def add_message(
        session_id: str,
        employee_id: str,
        role: str,
        content: str,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with get_db() as db:
            db.execute(
                "INSERT INTO conversations (session_id, employee_id, role, content, timestamp) VALUES (?,?,?,?,?)",
                (session_id, employee_id, role, content, now),
            )

    @staticmethod
    def get_history(
        session_id: str,
        limit: int = MAX_HISTORY,
    ) -> list[ChatMessage]:
        with get_db() as db:
            rows = db.execute(
                """
                SELECT role, content, timestamp FROM conversations
                WHERE session_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [
            ChatMessage(
                role=r["role"],
                content=r["content"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
            for r in reversed(rows)
        ]

    @staticmethod
    def get_history_as_dicts(session_id: str, limit: int = MAX_HISTORY) -> list[dict]:
        msgs = ConversationMemory.get_history(session_id, limit)
        return [{"role": m.role, "content": m.content} for m in msgs]

    @staticmethod
    def clear_session(session_id: str) -> None:
        with get_db() as db:
            db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        logger.info("session_cleared", session_id=session_id)
