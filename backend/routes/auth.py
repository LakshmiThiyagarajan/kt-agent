"""
routes/auth.py
--------------
Demo authentication with username + password.
In production, replace DEMO_USERS with your company's DB / IdP.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logger import get_logger
from memory.user_profile_memory import UserProfileMemory

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

# ── Demo user store ────────────────────────────────────────────────────────────
# In production: replace this with a real DB lookup + bcrypt password check
DEMO_USERS = {
    "demo": {
        "password": "kt2024",
        "employee_id": "EMP-001",
        "name": "Demo User",
        "email": "demo@kt-agent.com",
    },
    "alex": {
        "password": "kt2024",
        "employee_id": "EMP-002",
        "name": "Alex Johnson",
        "email": "alex@kt-agent.com",
    },
    "sarah": {
        "password": "kt2024",
        "employee_id": "EMP-003",
        "name": "Sarah Chen",
        "email": "sarah@kt-agent.com",
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    employee_id: str
    name: str
    email: str
    is_new_user: bool
    profile_complete: bool
    message: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    # Check credentials
    user = DEMO_USERS.get(payload.username.lower())
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    employee_id = user["employee_id"]
    logger.info("login_success", employee_id=employee_id)

    exists = UserProfileMemory.profile_exists(employee_id)

    return LoginResponse(
        employee_id=employee_id,
        name=user["name"],
        email=user["email"],
        is_new_user=not exists,
        profile_complete=exists,
        message="Welcome back!" if exists else "Welcome! Please complete your profile.",
    )
