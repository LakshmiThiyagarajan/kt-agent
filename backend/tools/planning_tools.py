"""
tools/planning_tools.py
------------------------
PLANNING AGENT tools.

Three tools:
1. roadmap_generator    — role-specific learning roadmap
2. checklist_generator  — onboarding checklist
3. recommendation_tool  — next recommended topics

All tools require user profile + retrieved context.
They NEVER produce generic output when profile data is available.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from core.logger import get_logger
from memory.user_profile_memory import UserProfileMemory
from services.openai_service import chat_completion

logger = get_logger(__name__)


# ── Shared prompt helpers ─────────────────────────────────────────────────────

def _profile_block(employee_id: str) -> str:
    profile = UserProfileMemory.get_profile(employee_id)
    if not profile:
        return "User profile: Not available"

    completed = UserProfileMemory.get_completed_topics(employee_id)
    pending = UserProfileMemory.get_pending_topics(employee_id)

    lines = [
        f"Name: {profile.name}",
        f"Role: {profile.role}",
        f"Project: {profile.project}",
        f"Experience Level: {profile.experience_level}",
        f"Completed Topics: {', '.join(completed) if completed else 'None yet'}",
        f"Pending Topics: {', '.join(pending) if pending else 'None'}",
    ]
    return "\n".join(lines)


def _context_block(context_chunks: list[str]) -> str:
    if not context_chunks:
        return "No project documentation retrieved."
    return "\n\n---\n\n".join(context_chunks[:6])


# ── Tool 1: Roadmap Generator ─────────────────────────────────────────────────

@dataclass
class RoadmapOutput:
    phases: list[dict]       # [{"phase": str, "topics": [str], "duration": str}]
    summary: str
    raw: str


async def generate_roadmap(
    employee_id: str,
    context_chunks: list[str],
) -> RoadmapOutput:
    profile_text = _profile_block(employee_id)
    context_text = _context_block(context_chunks)

    system = (
        "You are an expert onboarding planner. "
        "Generate a personalised, phase-based learning roadmap. "
        "IMPORTANT: Speak directly to the user using 'you' and 'your' — never use their name or third person (no 'she', 'he', 'they', or the user's name in the body text). "
        "Use ONLY the user profile and project documentation provided. "
        "Output valid JSON with schema: "
        '{"phases": [{"phase": str, "topics": [str], "duration": str}], "summary": str}'
    )
    user = (
        f"USER PROFILE:\n{profile_text}\n\n"
        f"PROJECT DOCUMENTATION:\n{context_text}\n\n"
        f"Generate a role-specific onboarding roadmap for me. "
        f"Skip topics I have already completed."
    )

    raw = await chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        return RoadmapOutput(
            phases=data.get("phases", []),
            summary=data.get("summary", ""),
            raw=raw,
        )
    except Exception:
        return RoadmapOutput(phases=[], summary=raw, raw=raw)


# ── Tool 2: Checklist Generator ───────────────────────────────────────────────

@dataclass
class ChecklistOutput:
    items: list[dict]    # [{"task": str, "category": str, "priority": str}]
    raw: str


async def generate_checklist(
    employee_id: str,
    context_chunks: list[str],
    checklist_type: str = "onboarding",
) -> ChecklistOutput:
    profile_text = _profile_block(employee_id)
    context_text = _context_block(context_chunks)

    system = (
        "You are an expert technical onboarding specialist. "
        "Generate a practical checklist based on the user's role and project. "
        "IMPORTANT: Speak directly to the user using 'you' and 'your' — never use third person. "
        "Output valid JSON: "
        '{"items": [{"task": str, "category": str, "priority": "high|medium|low"}]}'
    )
    user = (
        f"USER PROFILE:\n{profile_text}\n\n"
        f"PROJECT DOCUMENTATION:\n{context_text}\n\n"
        f"Generate a {checklist_type} checklist for me. "
        f"Be specific to my role and project — avoid generic items."
    )

    raw = await chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        return ChecklistOutput(items=data.get("items", []), raw=raw)
    except Exception:
        return ChecklistOutput(items=[], raw=raw)


# ── Tool 3: Recommendation Tool ───────────────────────────────────────────────

@dataclass
class RecommendationOutput:
    next_topics: list[str]
    rationale: str
    raw: str


async def generate_recommendations(
    employee_id: str,
    context_chunks: list[str],
) -> RecommendationOutput:
    profile_text = _profile_block(employee_id)
    context_text = _context_block(context_chunks)

    system = (
        "You are a learning path advisor. "
        "Recommend the next 3-5 topics for the user to study. "
        "IMPORTANT: Speak directly to the user using 'you' and 'your' — never use their name or third person (no 'she', 'he', 'they', or the user's name in the rationale). "
        "Base your recommendations on: "
        "1) What topics they have already completed, "
        "2) Their role, "
        "3) The project documentation available. "
        "Output valid JSON: "
        '{"next_topics": [str], "rationale": str}'
    )
    user = (
        f"USER PROFILE:\n{profile_text}\n\n"
        f"PROJECT DOCUMENTATION:\n{context_text}\n\n"
        f"What should I learn next?"
    )

    raw = await chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4,
        json_mode=True,
    )

    try:
        data = json.loads(raw)
        return RecommendationOutput(
            next_topics=data.get("next_topics", []),
            rationale=data.get("rationale", ""),
            raw=raw,
        )
    except Exception:
        return RecommendationOutput(next_topics=[], rationale=raw, raw=raw)
