"""
core/schemas.py
---------------
Shared Pydantic v2 models used across agents, routes, and services.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class IntentType(str, Enum):
    GREETING = "greeting"
    GENERAL_CHAT = "general_chat"
    QUESTION = "question"
    SUMMARY = "summary"
    PROJECT_KNOWLEDGE = "project_knowledge"
    ONBOARDING = "onboarding"
    RECOMMENDATION = "recommendation"
    CHECKLIST = "checklist"
    PLANNER = "planner"
    SECURITY_SENSITIVE = "security_sensitive"
    GENERAL_KNOWLEDGE = "general_knowledge"


class ExperienceLevel(str, Enum):
    NEW_JOINER = "New Joiner"
    TRANSFERRED = "Transferred Team Member"
    EXISTING = "Existing Team Member"


class ProgressStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"


# ── User Profile ──────────────────────────────────────────────────────────────

class UserProfileCreate(BaseModel):
    employee_id: str
    name: str
    email: str
    role: str
    project: str = ""          # no longer required — project lives in chat session
    experience_level: ExperienceLevel


class UserProfileUpdate(BaseModel):
    role: Optional[str] = None
    experience_level: Optional[ExperienceLevel] = None


class UserProfileOut(BaseModel):
    employee_id: str
    name: str
    email: str
    role: str
    project: str
    experience_level: str
    created_at: datetime
    updated_at: datetime


# ── Learning Progress ─────────────────────────────────────────────────────────

class LearningProgressCreate(BaseModel):
    employee_id: str
    topic: str
    status: ProgressStatus = ProgressStatus.PENDING


class LearningProgressOut(BaseModel):
    employee_id: str
    topic: str
    status: str
    completed_at: Optional[datetime]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str               # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    employee_id: str
    message: str
    session_id: Optional[str] = None
    selected_project: Optional[str] = None   # project chosen in chat, used as search filter


class ChatResponse(BaseModel):
    session_id: str
    intent: str
    answer: str
    groundedness_score: float
    sources: list[str] = []
    planning_used: bool = False


# ── Ingestion ─────────────────────────────────────────────────────────────────

class IngestionResult(BaseModel):
    document_id: str
    filename: str
    chunks_stored: int
    pii_detected: bool
    duplicate: bool
    status: str
    message: str


# ── Agent State (LangGraph) ───────────────────────────────────────────────────

class AgentState(BaseModel):
    """Shared state passed between LangGraph nodes."""
    employee_id: str
    session_id: str
    user_message: str
    intent: Optional[IntentType] = None
    selected_project: Optional[str] = None   # from chat session project picker
    retrieved_context: list[str] = []
    source_ids: list[str] = []
    draft_answer: Optional[str] = None
    final_answer: Optional[str] = None
    groundedness_score: float = 0.0
    planning_used: bool = False
    user_profile: Optional[dict[str, Any]] = None
    conversation_history: list[dict[str, str]] = []
    error: Optional[str] = None
