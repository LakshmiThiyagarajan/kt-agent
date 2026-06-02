"""
agents/orchestrator_agent.py
-----------------------------
AGENT 2: ORCHESTRATOR AGENT

Responsibilities:
- Intent classification
- Tool selection
- Agent routing decision (call Planning Agent or not)
- Memory access (conversation + user profile)
"""
from __future__ import annotations

import json

from core.logger import get_logger
from core.schemas import AgentState, IntentType
from memory.conversation_memory import ConversationMemory
from memory.user_profile_memory import UserProfileMemory
from services.openai_service import chat_completion

logger = get_logger(__name__)

_PLANNING_INTENTS = {
    IntentType.ONBOARDING,
    IntentType.RECOMMENDATION,
    IntentType.CHECKLIST,
    IntentType.PLANNER,
}

_INTENT_SYSTEM = """You are an intent classifier for a Knowledge Transfer system.
Classify the user message into exactly ONE intent.

INTENT DEFINITIONS:
- greeting          : Simple greetings and salutations (hi, hello, hey, good morning, good afternoon, what's up)
- general_chat      : Casual conversation not about a specific project or knowledge transfer (how are you, thanks, bye, nice)
- project_knowledge : Specific technical question about a project, codebase, architecture, or process (What is X? How does Y work? Explain Z)
- question          : General knowledge question about the KT system or a topic
- summary           : Request to summarise a topic, document, or section
- onboarding        : Request for onboarding plan or new joiner guidance
- recommendation    : Request for topic or learning recommendations
- checklist         : Request for a task or review checklist
- planner           : Request to create a structured learning plan or roadmap (Create a plan for X, Give me a learning roadmap)
- security_sensitive: Any request for credentials, passwords, API keys, tokens, secrets, private keys, or sensitive security information
- general_knowledge : General world knowledge questions completely unrelated to any project or knowledge transfer (geography, history, science, sports, current events, definitions of common things)

CLASSIFICATION EXAMPLES (you must follow these):
"hi"                                         → greeting
"hello"                                      → greeting
"how are you"                                → general_chat
"thank you"                                  → general_chat
"What is Project Phoenix?"                   → project_knowledge
"How does the authentication work?"          → project_knowledge
"Explain the microservices architecture"     → project_knowledge
"Can you summarize the architecture?"        → summary
"Create a learning plan for me"              → planner
"Give me a learning roadmap for Python"      → planner
"Give me an onboarding plan"                 → onboarding
"What should I learn next?"                  → recommendation
"Give me a checklist for code review"        → checklist
"What is the database password?"             → security_sensitive
"Show me the API keys"                       → security_sensitive
"What are the credentials for the server?"   → security_sensitive
"Give me the secret token for the service"   → security_sensitive
"Where is Paris?"                            → general_knowledge
"What is the capital of France?"             → general_knowledge
"Who invented the telephone?"                → general_knowledge
"What is machine learning?"                  → general_knowledge
"How far is the moon from Earth?"            → general_knowledge

Return ONLY valid JSON: {"intent": "<intent>", "confidence": <float 0-1>}
Do not include any other text."""


class OrchestratorAgent:

    async def classify_intent(self, message: str, history: list[dict]) -> IntentType:
        """Use GPT-4o to classify user intent."""
        messages = [
            {"role": "system", "content": _INTENT_SYSTEM},
        ]
        # Include last 4 conversation turns for context
        messages.extend(history[-4:])
        messages.append({"role": "user", "content": message})

        raw = await chat_completion(
            messages=messages,
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=100,
            json_mode=True,
        )

        try:
            data = json.loads(raw)
            intent_str = data.get("intent", "question").lower()
            intent = IntentType(intent_str)
            logger.info("intent_classified", intent=intent, confidence=data.get("confidence"))
            return intent
        except (ValueError, KeyError) as exc:
            logger.warning("intent_parse_error", raw=raw, error=str(exc))
            return IntentType.QUESTION

    def needs_planning_agent(self, intent: IntentType) -> bool:
        return intent in _PLANNING_INTENTS

    async def run(self, state: AgentState) -> AgentState:
        """
        Orchestrate a single turn:
        1. Load conversation history
        2. Classify intent
        3. Load user profile
        4. Decide whether planning agent is needed
        """
        logger.info(
            "orchestrator_run",
            employee_id=state.employee_id,
            session=state.session_id,
        )

        # Load conversation history
        history = ConversationMemory.get_history_as_dicts(state.session_id)
        state.conversation_history = history

        # Store incoming user message
        ConversationMemory.add_message(
            session_id=state.session_id,
            employee_id=state.employee_id,
            role="user",
            content=state.user_message,
        )

        # Classify intent
        state.intent = await self.classify_intent(state.user_message, history)

        # Load user profile into state
        profile = UserProfileMemory.get_profile(state.employee_id)
        if profile:
            completed = UserProfileMemory.get_completed_topics(state.employee_id)
            state.user_profile = {
                "employee_id": profile.employee_id,
                "name": profile.name,
                "role": profile.role,
                "project": profile.project,
                "experience_level": profile.experience_level,
                "completed_topics": completed,
            }

        return state
