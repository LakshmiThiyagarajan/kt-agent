"""
agents/planning_agent.py
-------------------------
AGENT 3: PLANNING AGENT

Uses user profile + learning progress + retrieved context to produce:
- Role-specific onboarding plans
- Learning roadmaps
- Checklists
- Personalised recommendations
- Project transition plans
"""
from __future__ import annotations

from core.logger import get_logger
from core.schemas import AgentState, IntentType, LearningProgressCreate, ProgressStatus
from memory.user_profile_memory import UserProfileMemory
from tools.planning_tools import (
    generate_checklist,
    generate_recommendations,
    generate_roadmap,
)

logger = get_logger(__name__)


class PlanningAgent:

    async def run(self, state: AgentState) -> AgentState:
        logger.info(
            "planning_agent_run",
            employee_id=state.employee_id,
            intent=state.intent,
        )

        context = state.retrieved_context

        # Route to the appropriate planning tool based on intent
        if state.intent == IntentType.ONBOARDING:
            result = await self._handle_onboarding(state.employee_id, context, state)
        elif state.intent == IntentType.RECOMMENDATION:
            result = await self._handle_recommendation(state.employee_id, context)
        elif state.intent == IntentType.CHECKLIST:
            result = await self._handle_checklist(state.employee_id, context)
        else:
            # Fallback — roadmap covers summary-of-learning too
            result = await self._handle_onboarding(state.employee_id, context, state)

        state.draft_answer = result
        state.planning_used = True
        return state

    async def _handle_onboarding(
        self,
        employee_id: str,
        context: list[str],
        state: AgentState,
    ) -> str:
        """Build a full onboarding plan with roadmap + checklist."""
        profile = UserProfileMemory.get_profile(employee_id)
        if not profile:
            return "Please complete your profile setup before requesting an onboarding plan."

        # Check for project transition
        transition_note = ""
        if state.user_profile:
            current_project = state.user_profile.get("project")
            if current_project and profile.project != current_project:
                transition_note = (
                    f"\n\n> ⚠️ **Project Transition Detected**: "
                    f"You have moved from **{current_project}** to **{profile.project}**. "
                    f"This plan reflects your new project."
                )

        roadmap = await generate_roadmap(employee_id, context)
        checklist = await generate_checklist(employee_id, context, "onboarding")

        # Auto-save roadmap topics as Pending for progress tracking
        for phase in roadmap.phases:
            for topic in phase.get("topics", []):
                try:
                    UserProfileMemory.upsert_progress(LearningProgressCreate(
                        employee_id=employee_id,
                        topic=topic,
                        status=ProgressStatus.PENDING,
                    ))
                except Exception:
                    pass

        # Format the response
        lines = [
            f"## Personalised Onboarding Plan",
            f"**Role:** {profile.role} | **Project:** {profile.project} | **Level:** {profile.experience_level}",
            transition_note,
            "",
            f"### Learning Roadmap",
            roadmap.summary,
            "",
        ]

        for phase in roadmap.phases:
            lines.append(f"**{phase.get('phase', 'Phase')}** _{phase.get('duration', '')}_")
            for topic in phase.get("topics", []):
                lines.append(f"  - {topic}")
            lines.append("")

        lines.append("### Onboarding Checklist")
        for item in checklist.items:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                item.get("priority", "medium"), "•"
            )
            lines.append(f"{priority_icon} [{item.get('category', '')}] {item.get('task', '')}")

        return "\n".join(lines)

    async def _handle_recommendation(
        self,
        employee_id: str,
        context: list[str],
    ) -> str:
        recs = await generate_recommendations(employee_id, context)

        # Auto-save recommended topics as Pending so user can track them in My Profile
        for topic in recs.next_topics:
            try:
                UserProfileMemory.upsert_progress(LearningProgressCreate(
                    employee_id=employee_id,
                    topic=topic,
                    status=ProgressStatus.PENDING,
                ))
            except Exception:
                pass

        lines = [
            "## Your Recommended Next Topics",
            "",
            recs.rationale,
            "",
            "### Your Next Learning Steps:",
        ]
        for i, topic in enumerate(recs.next_topics, 1):
            lines.append(f"{i}. {topic}")

        lines += [
            "",
            "> These topics have been saved to your **My Profile** page where you can mark them as done as you progress.",
        ]

        return "\n".join(lines)

    async def _handle_checklist(
        self,
        employee_id: str,
        context: list[str],
    ) -> str:
        checklist = await generate_checklist(employee_id, context, "task")
        lines = ["## Task Checklist", ""]
        for item in checklist.items:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                item.get("priority", "medium"), "•"
            )
            lines.append(f"{priority_icon} **[{item.get('category', '')}]** {item.get('task', '')}")

        return "\n".join(lines)
