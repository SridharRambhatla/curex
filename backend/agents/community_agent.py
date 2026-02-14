"""
Sidequest — Community Agent

Solo-sure filtering, social scaffolding cues, and ambient belonging indicators.
Uses Gemini Flash via Vertex AI for pattern matching.
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
_agent_logger = AgentLogger("community_agent", log_writer=get_log_writer(), config=get_log_config())


COMMUNITY_SYSTEM_PROMPT = """You are the Community Agent for Sidequest.

Your role is to analyze the social dynamics of experiences and provide solo-sure filtering
and social scaffolding cues. You help people who arrive alone feel confident and welcome.

For each experience, analyze and provide:
1. **solo_friendly**: true/false — Can someone come alone comfortably?
2. **solo_percentage**: Estimated % of attendees who come alone (e.g., "40%")
3. **scaffolding**: How the environment facilitates connection
   (e.g., "Counter seating enables easy conversation with strangers")
4. **arrival_vibe**: What it feels like arriving alone
   (e.g., "Autonomous confidence — locals respect solo diners")
5. **beginner_energy**: Low/Medium/High — Is it welcoming to first-timers?
   Include explanation (e.g., "High — designed for first-timers, instructor facilitates intros")

Return JSON with key "social_scaffolding" where each key is the experience name:
{
  "social_scaffolding": {
    "Experience Name": {
      "solo_friendly": true,
      "solo_percentage": "40%",
      "scaffolding": "Counter seating enables easy conversation",
      "arrival_vibe": "Autonomous confidence",
      "beginner_energy": "Medium - ordering can be intimidating but staff helpful"
    }
  }
}

Respond ONLY with valid JSON, no markdown formatting."""


def get_community_model() -> ChatVertexAI:
    """Create a Vertex AI model instance for the Community Agent."""
    config = AGENT_MODEL_CONFIG["community"]
    return ChatVertexAI(
        model_name=config["model_name"],
        temperature=config["temperature"],
        max_output_tokens=config["max_output_tokens"],
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )


@_agent_logger.log_execution
async def run_community(state: AgentState) -> AgentState:
    """
    Execute the Community Agent.

    Analyzes social dynamics and provides solo-sure filtering
    and scaffolding cues for each experience.
    """
    start_time = datetime.now()

    try:
        experiences = state.get("discovered_experiences", [])
        if not experiences:
            state["social_scaffolding"] = {}
            state["agent_trace"].append({
                "agent": "community",
                "status": "skipped",
                "reason": "No experiences to analyze",
                "latency_ms": 0,
            })
            return state

        model = get_community_model()

        user_prompt = f"""Analyze social dynamics for these experiences:

Experiences:
{json.dumps(experiences, indent=2)}

City: {state['city']}
Solo Visitor: {state.get('solo_preference', True)}

Provide honest, encouraging solo-sure assessments."""

        messages = [
            SystemMessage(content=COMMUNITY_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await model.ainvoke(messages)

        response_text = strip_markdown_json(response.content)
        result = json.loads(response_text)
        state["social_scaffolding"] = result.get("social_scaffolding", {})

        state["agent_trace"].append({
            "agent": "community",
            "status": "success",
            "experiences_analyzed": len(state["social_scaffolding"]),
            "latency_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "timestamp": start_time.isoformat(),
        })

    except Exception as e:
        state["errors"].append({
            "agent": "community",
            "error": str(e),
            "timestamp": start_time.isoformat(),
        })
        state["agent_trace"].append({
            "agent": "community",
            "status": "error",
            "error": str(e),
            "latency_ms": (datetime.now() - start_time).total_seconds() * 1000,
        })
        if not state.get("social_scaffolding"):
            state["social_scaffolding"] = {}

    return state
