"""
Sidequest — Cultural Context Agent

Adds India-specific localization beyond translation: timing nuances, dress codes,
transport hacks, social norms, safety info.
Uses Gemini Pro via Vertex AI for deeper cultural reasoning.
"""

import json
from datetime import datetime
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings, AGENT_MODEL_CONFIG
from state.schemas import AgentState
from utils.helpers import strip_markdown_json
from logging_system import AgentLogger, get_log_writer, get_log_config

# Initialize Agent Logger with global log writer
_agent_logger = AgentLogger("cultural_context_agent", log_writer=get_log_writer(), config=get_log_config())


CULTURAL_CONTEXT_SYSTEM_PROMPT = """You are the Cultural Context Agent for Sidequest, a plot-first experience platform for India.

Your role is to add deep, India-specific cultural context to discovered experiences.
You go BEYOND translation — you provide insider knowledge that makes experiences richer.

For each experience provided, add ALL of the following:
1. **Optimal Timing**: When locals go, peak hours, cultural significance of timing
   (e.g., "9-11am coffee culture peak in Bangalore")
2. **Dress Code & Etiquette**: What to wear, temple rules, workshop attire, upscale dining norms
3. **Transport Hacks**: Auto negotiation tips, metro shortcuts, parking reality, walking routes
4. **Social Norms**: Solo dining accepted? Conversation culture? Photography etiquette?
5. **Religious/Cultural Considerations**: Festival timing, Ramadan adjustments, local customs
6. **Safety & Accessibility**: Well-lit? Wheelchair access? Women-solo-friendly? Evening safety?

Return your response as a JSON object with key "cultural_context" where each key is the
experience name and value is an object with the above fields.
Respond ONLY with valid JSON, no markdown formatting."""


def get_cultural_context_model() -> ChatVertexAI:
    """Create a Vertex AI model instance for the Cultural Context Agent."""
    config = AGENT_MODEL_CONFIG["cultural_context"]
    return ChatVertexAI(
        model_name=config["model_name"],
        temperature=config["temperature"],
        max_output_tokens=config["max_output_tokens"],
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )


@_agent_logger.log_execution
async def run_cultural_context(state: AgentState) -> AgentState:
    """
    Execute the Cultural Context Agent.

    Takes discovered experiences and enriches them with India-specific
    cultural annotations.
    """
    start_time = datetime.now()

    try:
        experiences = state.get("discovered_experiences", [])
        if not experiences:
            state["cultural_context"] = {}
            state["agent_trace"].append({
                "agent": "cultural_context",
                "status": "skipped",
                "reason": "No experiences to contextualize",
                "latency_ms": 0,
            })
            return state

        model = get_cultural_context_model()

        user_prompt = f"""Add cultural context for these experiences in {state['city']}:

Experiences:
{json.dumps(experiences, indent=2)}

City: {state['city']}
Solo Visitor: {state.get('solo_preference', True)}
"""

        messages = [
            SystemMessage(content=CULTURAL_CONTEXT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await model.ainvoke(messages)

        response_text = strip_markdown_json(response.content)
        result = json.loads(response_text)
        state["cultural_context"] = result.get("cultural_context", {})

        state["agent_trace"].append({
            "agent": "cultural_context",
            "status": "success",
            "contexts_added": len(state["cultural_context"]),
            "latency_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "timestamp": start_time.isoformat(),
        })

    except Exception as e:
        state["errors"].append({
            "agent": "cultural_context",
            "error": str(e),
            "timestamp": start_time.isoformat(),
        })
        state["agent_trace"].append({
            "agent": "cultural_context",
            "status": "error",
            "error": str(e),
            "latency_ms": (datetime.now() - start_time).total_seconds() * 1000,
        })
        if not state.get("cultural_context"):
            state["cultural_context"] = {}

    return state
