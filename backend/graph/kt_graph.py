"""
graph/kt_graph.py
-----------------
LangGraph orchestration graph for KT-Agent query flow.

Nodes:
  orchestrator  → classify intent, load memory
  retrieval     → semantic search Pinecone
  planning      → roadmaps, checklists, recommendations
  evaluation    → groundedness check

Edges:
  orchestrator → retrieval (always)
  retrieval    → planning  (if intent requires planning)
  retrieval    → evaluation (direct, for question/summary)
  planning     → evaluation
  evaluation   → END
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from agents.evaluation_agent import EvaluationAgent
from agents.orchestrator_agent import OrchestratorAgent
from agents.planning_agent import PlanningAgent
from core.logger import get_logger
from core.schemas import AgentState, IntentType
from services.openai_service import chat_completion
from tools.search_documents import search_documents

logger = get_logger(__name__)

# Agent singletons (stateless)
_orchestrator = OrchestratorAgent()
_planner = PlanningAgent()
_evaluator = EvaluationAgent()

# Intents that bypass RAG entirely
_DIRECT_INTENTS = {
    IntentType.GREETING,
    IntentType.GENERAL_CHAT,
    IntentType.SECURITY_SENSITIVE,
    IntentType.GENERAL_KNOWLEDGE,
}

# Intents that require the planning agent
_PLANNING_INTENTS = {
    IntentType.ONBOARDING,
    IntentType.RECOMMENDATION,
    IntentType.CHECKLIST,
    IntentType.PLANNER,
}

_DIRECT_RESPONSE_SYSTEM = """You are a warm, professional knowledge transfer assistant.
Respond naturally to greetings and casual conversation. Keep your response brief and friendly.
Do not attempt to answer technical questions in this mode."""

_SECURITY_REFUSAL = (
    "I can't help with that. Sharing passwords, credentials, API keys, or any security secrets "
    "is outside my scope. Please follow your organisation's security protocols and use a proper "
    "secrets manager for credential access."
)

_OUT_OF_SCOPE_REFUSAL = (
    "I'm a Knowledge Transfer assistant focused purely on your project. "
    "I can't help with general questions outside that scope. "
    "Try asking me about your project's architecture, codebase, processes, or learning plans."
)


# ── Node functions ────────────────────────────────────────────────────────────

async def orchestrator_node(state: dict) -> dict:
    s = AgentState(**state)
    s = await _orchestrator.run(s)
    return s.model_dump()


async def direct_response_node(state: dict) -> dict:
    s = AgentState(**state)
    logger.info("direct_response_node", intent=s.intent)

    # Security questions → hardcoded refusal, no LLM call
    if s.intent == IntentType.SECURITY_SENSITIVE:
        s.final_answer = _SECURITY_REFUSAL
        s.groundedness_score = 1.0
        return s.model_dump()

    # General knowledge → out of scope, redirect back to project
    if s.intent == IntentType.GENERAL_KNOWLEDGE:
        s.final_answer = _OUT_OF_SCOPE_REFUSAL
        s.groundedness_score = 1.0
        return s.model_dump()

    messages: list[dict] = [{"role": "system", "content": _DIRECT_RESPONSE_SYSTEM}]
    messages.extend(s.conversation_history[-4:])
    messages.append({"role": "user", "content": s.user_message})
    s.final_answer = await chat_completion(messages=messages, model="gpt-4o-mini", temperature=0.7, max_tokens=512)
    s.groundedness_score = 1.0
    return s.model_dump()


async def retrieval_node(state: dict) -> dict:
    s = AgentState(**state)
    logger.info("retrieval_node", intent=s.intent)

    # Use the project selected in the chat session (not the profile)
    project = s.selected_project or None

    results = await search_documents(
        query=s.user_message,
        top_k=6,
        project_filter=project,
    )

    # Fallback: if the project filter returned nothing, retry across all docs
    if not results and project:
        logger.info("retrieval_fallback_unfiltered", original_project=project)
        results = await search_documents(
            query=s.user_message,
            top_k=6,
            project_filter=None,
        )

    s.retrieved_context = [r.text for r in results if r.text]
    s.source_ids = [r.filename for r in results]

    if not s.retrieved_context:
        s.draft_answer = (
            "I couldn't find any relevant knowledge in the repository yet. "
            "Please upload project documents or try another query."
        )
    elif s.intent and s.intent.value in ("question", "summary", "project_knowledge"):
        s.draft_answer = await _generate_answer(s)

    return s.model_dump()


async def planning_node(state: dict) -> dict:
    s = AgentState(**state)
    s = await _planner.run(s)
    return s.model_dump()


async def evaluation_node(state: dict) -> dict:
    s = AgentState(**state)
    # Skip evaluation when there was no retrieved context (fallback message already set)
    if not s.retrieved_context and s.draft_answer:
        s.final_answer = s.draft_answer
        s.groundedness_score = 1.0
        return s.model_dump()
    s = await _evaluator.run(s)
    return s.model_dump()


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_orchestrator(state: dict) -> str:
    s = AgentState(**state)
    if s.intent in _DIRECT_INTENTS:
        return "direct_response"
    return "retrieval"


def route_after_retrieval(state: dict) -> str:
    s = AgentState(**state)
    if s.intent in _PLANNING_INTENTS:
        return "planning"
    return "evaluation"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> Any:
    """Build and compile the KT-Agent LangGraph."""
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("direct_response", direct_response_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("evaluation", evaluation_node)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Edges
    workflow.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {"direct_response": "direct_response", "retrieval": "retrieval"},
    )
    workflow.add_edge("direct_response", END)
    workflow.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {"planning": "planning", "evaluation": "evaluation"},
    )
    workflow.add_edge("planning", "evaluation")
    workflow.add_edge("evaluation", END)

    return workflow.compile()


# ── Helper: Direct answer generation (question / summary) ─────────────────────

_QA_SYSTEM = """You are a helpful knowledge transfer assistant.
Answer the user's question using ONLY the provided context.
If the context doesn't contain enough information, say so honestly.
Be concise and precise. Format your answer in Markdown."""


async def _generate_answer(state: AgentState) -> str:
    context = "\n\n---\n\n".join(state.retrieved_context[:6])
    history = state.conversation_history[-6:]

    messages: list[dict] = [{"role": "system", "content": _QA_SYSTEM}]
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION:\n{state.user_message}",
    })

    return await chat_completion(messages=messages, temperature=0.2)
