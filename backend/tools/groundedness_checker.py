"""
tools/groundedness_checker.py
------------------------------
EVALUATION AGENT tool.

Verifies that the generated answer is grounded in the retrieved context.
Returns a float score 0.0–1.0 and a boolean pass/fail.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from core.logger import get_logger
from services.openai_service import chat_completion

logger = get_logger(__name__)

GROUNDEDNESS_THRESHOLD = 0.6   # below this, the answer is rejected


@dataclass
class GroundednessResult:
    score: float                 # 0.0 – 1.0
    passed: bool
    reasoning: str
    revised_answer: str | None   # Only set when score < threshold


_SYSTEM_PROMPT = """You are a factual verification assistant.
You will be given:
1. A set of source passages (retrieved context)
2. A generated answer

Your job:
- Verify that every claim in the answer is supported by the source passages.
- Assign a groundedness score from 0.0 to 1.0:
    1.0 = fully supported by sources
    0.5 = partially supported (some claims have no source)
    0.0 = not supported at all

Return ONLY valid JSON with this schema:
{
  "score": <float 0.0-1.0>,
  "reasoning": "<brief explanation>",
  "supported_claims": ["<claim>", ...],
  "unsupported_claims": ["<claim>", ...]
}"""


async def check_groundedness(
    answer: str,
    context_chunks: list[str],
) -> GroundednessResult:
    """
    Check whether `answer` is grounded in `context_chunks`.
    """
    if not context_chunks:
        logger.warning("groundedness_no_context")
        return GroundednessResult(
            score=0.0,
            passed=False,
            reasoning="No context provided to verify against.",
            revised_answer=None,
        )

    context_text = "\n\n---\n\n".join(context_chunks[:8])  # cap at 8 chunks

    user_content = (
        f"SOURCE PASSAGES:\n{context_text}\n\n"
        f"GENERATED ANSWER:\n{answer}"
    )

    try:
        raw = await chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=512,
            json_mode=True,
        )
        data = json.loads(raw)
        score = float(data.get("score", 0.0))
        reasoning = data.get("reasoning", "")
    except Exception as exc:
        logger.error("groundedness_failed", error=str(exc))
        score = 0.5   # neutral fallback
        reasoning = f"Evaluation error: {exc}"

    passed = score >= GROUNDEDNESS_THRESHOLD
    revised = None

    if not passed:
        logger.warning("groundedness_failed_threshold", score=score)
        # Generate a safer, hedged version
        revised = await _generate_hedged_answer(answer, context_chunks)

    logger.info("groundedness_result", score=score, passed=passed)
    return GroundednessResult(
        score=score,
        passed=passed,
        reasoning=reasoning,
        revised_answer=revised,
    )


async def _generate_hedged_answer(original: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks[:5])
    prompt = (
        f"The following answer may not be fully supported by the provided sources.\n\n"
        f"SOURCES:\n{context}\n\n"
        f"ORIGINAL ANSWER:\n{original}\n\n"
        f"Please rewrite the answer to only include claims directly supported by the sources. "
        f"If information is missing, say so honestly."
    )
    return await chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
