"""
agents/evaluation_agent.py
---------------------------
AGENT 4: EVALUATION AGENT

Verifies the draft answer is grounded in retrieved context.
Rejects or revises ungrounded responses.
"""
from __future__ import annotations

from core.logger import get_logger
from core.schemas import AgentState
from tools.groundedness_checker import check_groundedness

logger = get_logger(__name__)


class EvaluationAgent:

    async def run(self, state: AgentState) -> AgentState:
        logger.info(
            "evaluation_agent_run",
            employee_id=state.employee_id,
            has_draft=bool(state.draft_answer),
        )

        draft = state.draft_answer or ""
        context = state.retrieved_context

        result = await check_groundedness(answer=draft, context_chunks=context)

        state.groundedness_score = result.score

        if result.passed:
            state.final_answer = draft
        else:
            # Use the hedged / revised answer if available
            state.final_answer = result.revised_answer or (
                f"{draft}\n\n"
                f"---\n"
                f"⚠️ *Note: Some parts of this answer could not be fully verified "
                f"against available documentation (confidence: {result.score:.0%}).*"
            )
            logger.warning(
                "answer_revised",
                score=result.score,
                reasoning=result.reasoning[:120],
            )

        return state
