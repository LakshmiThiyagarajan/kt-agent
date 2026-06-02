"""
memory/user_profile_memory.py
------------------------------
CRUD operations for user profiles and learning progress.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.logger import get_logger
from core.schemas import (
    ExperienceLevel,
    LearningProgressCreate,
    LearningProgressOut,
    ProgressStatus,
    UserProfileCreate,
    UserProfileOut,
    UserProfileUpdate,
)
from memory.database import get_db

logger = get_logger(__name__)


class UserProfileMemory:
    # ── Profile ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_profile(employee_id: str) -> Optional[UserProfileOut]:
        with get_db() as db:
            row = db.execute(
                "SELECT * FROM user_profiles WHERE employee_id = ?",
                (employee_id,),
            ).fetchone()
        if row is None:
            return None
        return UserProfileOut(
            employee_id=row["employee_id"],
            name=row["name"],
            email=row["email"],
            role=row["role"],
            project=row["project"],
            experience_level=row["experience_level"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def create_profile(data: UserProfileCreate) -> UserProfileOut:
        now = datetime.utcnow().isoformat()
        with get_db() as db:
            db.execute(
                """
                INSERT INTO user_profiles
                    (employee_id, name, email, role, project, experience_level, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.employee_id,
                    data.name,
                    data.email,
                    data.role,
                    data.project,
                    data.experience_level.value,
                    now,
                    now,
                ),
            )
        logger.info("profile_created", employee_id=data.employee_id)
        return UserProfileMemory.get_profile(data.employee_id)  # type: ignore[return-value]

    @staticmethod
    def update_profile(employee_id: str, data: UserProfileUpdate) -> Optional[UserProfileOut]:
        now = datetime.utcnow().isoformat()
        fields: dict = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        if not fields:
            return UserProfileMemory.get_profile(employee_id)

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [now, employee_id]

        with get_db() as db:
            db.execute(
                f"UPDATE user_profiles SET {set_clause}, updated_at = ? WHERE employee_id = ?",
                values,
            )
        logger.info("profile_updated", employee_id=employee_id, fields=list(fields.keys()))
        return UserProfileMemory.get_profile(employee_id)

    @staticmethod
    def profile_exists(employee_id: str) -> bool:
        with get_db() as db:
            row = db.execute(
                "SELECT 1 FROM user_profiles WHERE employee_id = ?",
                (employee_id,),
            ).fetchone()
        return row is not None

    # ── Learning Progress ─────────────────────────────────────────────────────

    @staticmethod
    def get_progress(employee_id: str) -> list[LearningProgressOut]:
        with get_db() as db:
            rows = db.execute(
                "SELECT * FROM learning_progress WHERE employee_id = ? ORDER BY id",
                (employee_id,),
            ).fetchall()
        return [
            LearningProgressOut(
                employee_id=r["employee_id"],
                topic=r["topic"],
                status=r["status"],
                completed_at=datetime.fromisoformat(r["completed_at"]) if r["completed_at"] else None,
            )
            for r in rows
        ]

    @staticmethod
    def upsert_progress(data: LearningProgressCreate) -> None:
        completed_at = (
            datetime.utcnow().isoformat()
            if data.status == ProgressStatus.COMPLETED
            else None
        )
        with get_db() as db:
            db.execute(
                """
                INSERT INTO learning_progress (employee_id, topic, status, completed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(employee_id, topic)
                DO UPDATE SET status = excluded.status, completed_at = excluded.completed_at
                """,
                (data.employee_id, data.topic, data.status.value, completed_at),
            )
        logger.info("progress_upserted", employee_id=data.employee_id, topic=data.topic)

    @staticmethod
    def get_completed_topics(employee_id: str) -> list[str]:
        with get_db() as db:
            rows = db.execute(
                "SELECT topic FROM learning_progress WHERE employee_id = ? AND status = 'Completed'",
                (employee_id,),
            ).fetchall()
        return [r["topic"] for r in rows]

    @staticmethod
    def get_pending_topics(employee_id: str) -> list[str]:
        with get_db() as db:
            rows = db.execute(
                "SELECT topic FROM learning_progress WHERE employee_id = ? AND status != 'Completed'",
                (employee_id,),
            ).fetchall()
        return [r["topic"] for r in rows]
