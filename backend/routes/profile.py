"""
routes/profile.py
-----------------
User profile and learning progress management routes.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.logger import get_logger
from core.schemas import (
    LearningProgressCreate,
    LearningProgressOut,
    UserProfileCreate,
    UserProfileOut,
    UserProfileUpdate,
)
from memory.user_profile_memory import UserProfileMemory

router = APIRouter(prefix="/profile", tags=["profile"])
logger = get_logger(__name__)


@router.post("", response_model=UserProfileOut, status_code=201)
async def create_profile(payload: UserProfileCreate):
    if UserProfileMemory.profile_exists(payload.employee_id):
        raise HTTPException(400, "Profile already exists. Use PATCH to update.")
    profile = UserProfileMemory.create_profile(payload)
    return profile


@router.get("/{employee_id}")
async def get_profile(employee_id: str):
    profile = UserProfileMemory.get_profile(employee_id)
    if not profile:
        logger.warning("profile_not_found_fallback", employee_id=employee_id)
        from datetime import datetime
        return {
            "employee_id": employee_id,
            "name": "New User",
            "email": "",
            "role": "Not configured",
            "project": "Not configured",
            "experience_level": "New Joiner",
            "profile_complete": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
    return profile


@router.patch("/{employee_id}", response_model=UserProfileOut)
async def update_profile(employee_id: str, payload: UserProfileUpdate):
    profile = UserProfileMemory.update_profile(employee_id, payload)
    if not profile:
        raise HTTPException(404, f"No profile found for employee_id={employee_id}")
    return profile


# ── Learning Progress ─────────────────────────────────────────────────────────

@router.get("/{employee_id}/progress", response_model=list[LearningProgressOut])
async def get_progress(employee_id: str):
    return UserProfileMemory.get_progress(employee_id)


@router.post("/{employee_id}/progress", status_code=201)
async def upsert_progress(employee_id: str, payload: LearningProgressCreate):
    payload.employee_id = employee_id
    UserProfileMemory.upsert_progress(payload)
    return {"message": "Progress updated."}
