"""
routes/chat.py
--------------
Main chat endpoint — runs the full LangGraph pipeline.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from core.logger import get_logger
from core.schemas import AgentState, ChatRequest, ChatResponse
from graph.kt_graph import build_graph
from memory.conversation_memory import ConversationMemory

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)

# Compile the graph once at module load
_graph = build_graph()


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    """
    Process a chat message through the full multi-agent pipeline.
    """
    session_id = payload.session_id or ConversationMemory.new_session_id()
    logger.info("chat_request", employee_id=payload.employee_id, session=session_id)

    initial_state = AgentState(
        employee_id=payload.employee_id,
        session_id=session_id,
        user_message=payload.message,
        selected_project=payload.selected_project,
    ).model_dump()

    try:
        result = await _graph.ainvoke(initial_state)
    except Exception as exc:
        logger.error("graph_error", error=str(exc))
        raise HTTPException(500, f"Agent pipeline error: {exc}")

    final_answer = result.get("final_answer") or result.get("draft_answer") or "I could not generate a response."

    # Store assistant response in conversation memory
    ConversationMemory.add_message(
        session_id=session_id,
        employee_id=payload.employee_id,
        role="assistant",
        content=final_answer,
    )

    return ChatResponse(
        session_id=session_id,
        intent=result.get("intent", "question"),
        answer=final_answer,
        groundedness_score=result.get("groundedness_score", 0.0),
        sources=result.get("source_ids", []),
        planning_used=result.get("planning_used", False),
    )


@router.get("/{session_id}/history")
async def get_history(session_id: str):
    messages = ConversationMemory.get_history(session_id)
    return [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    ConversationMemory.clear_session(session_id)
    return {"message": "Session cleared."}
