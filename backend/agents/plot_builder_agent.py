"""
Sidequest — Plot-Builder Agent (Innovation Core)

Generates narrative itineraries with emotional arcs, lore layering, and intentional friction.
This is the core differentiator — stories, not lists.
Uses Gemini Pro via Vertex AI for creative storytelling.
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
_agent_logger = AgentLogger("plot_builder_agent", log_writer=get_log_writer(), config=get_log_config())


PLOT_BUILDER_SYSTEM_PROMPT = """You are the Plot-Builder Agent for Sidequest, the core creative engine.

Your role is to transform discovered experiences + cultural context into NARRATIVE ITINERARIES
with emotional arcs — NOT chronological lists.

**Principles**:
1. **Setup → Friction → Payoff**: Every itinerary has story structure
2. **Intentional Friction**: Queueing, trekking, learning = memory-making moments
3. **Lore Layering**: Backstory, provenance, "why this matters" for each stop
4. **Collision Suggestions**: Mix interest pods (pottery + food + music) for serendipity
5. **Time-Aware**: Respect the user's available time window — fit experiences realistically within their constraints
6. **Time-Fluid**: Dawn + evening in same day (dual prime times) when time allows

**Time Constraints**:
- ALWAYS respect the user's available time (if specified)
- Include realistic travel time between experiences (15-30 mins in city)
- Account for experience duration when planning
- If time is limited, prioritize quality over quantity — 2-3 deeply experienced stops beats 5 rushed ones
- Include specific times in the narrative (e.g., "11:30 AM — you arrive at...")

**Tone**: Evocative but grounded, "you" voice, sensory details, insider warmth.
Write as if whispering a secret to a friend who deserves this experience.

**Output Format** (return as JSON):
{
  "narrative_itinerary": "The full narrative text with all stops described evocatively...",
  "collision_suggestion": {
    "title": "Your next adventure (pod1 + pod2)",
    "experiences": ["Experience A", "Experience B"],
    "why": "Why these pair well together"
  }
}

Each stop in the narrative should include:
- Specific time + place (e.g., "2:30 PM — Mavalli Tiffin Room")
- Friction element ("queue 20 mins — locals gather here, worth the wait")
- Lore ("80-year-old institution, unchanged recipe since 1924")
- Social scaffolding ("counter seating, easy conversation starters")
- Solo-sure indicator where applicable
- Estimated duration at the stop

Open with a hook. Close with a reflection on what this day means.
Respond ONLY with valid JSON, no markdown formatting."""


def get_plot_builder_model() -> ChatVertexAI:
    """Create a Vertex AI model instance for the Plot-Builder Agent."""
    config = AGENT_MODEL_CONFIG["plot_builder"]
    return ChatVertexAI(
        model_name=config["model_name"],
        temperature=config["temperature"],
        max_output_tokens=config["max_output_tokens"],
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
    )


@_agent_logger.log_execution
async def run_plot_builder(state: AgentState) -> AgentState:
    """
    Execute the Plot-Builder Agent.

    Takes experiences + cultural context + social scaffolding and weaves them
    into a narrative itinerary with story arc.
    """
    agent_start_time = datetime.now()

    try:
        experiences = state.get("discovered_experiences", [])
        if not experiences:
            state["narrative_itinerary"] = "No experiences found to build a story around. Try a different query!"
            state["agent_trace"].append({
                "agent": "plot_builder",
                "status": "skipped",
                "reason": "No experiences available",
                "latency_ms": 0,
            })
            return state

        model = get_plot_builder_model()

        # Calculate time constraints
        time_available = state.get('time_available_hours', 8.0)
        user_start_time = state.get('start_time', '10:00')
        
        # Calculate end time
        try:
            start_hour = int(user_start_time.split(':')[0])
            start_min = int(user_start_time.split(':')[1]) if ':' in user_start_time else 0
            end_hour = start_hour + int(time_available)
            end_min = start_min + int((time_available % 1) * 60)
            if end_min >= 60:
                end_hour += 1
                end_min -= 60
            end_time = f"{end_hour:02d}:{end_min:02d}"
        except (ValueError, IndexError):
            end_time = "18:00"

        user_prompt = f"""Create a plot-first narrative itinerary from these inputs:

**User Query**: {state['user_query']}
**City**: {state['city']}
**Interest Pods**: {', '.join(state.get('interest_pods', [])) or 'open to anything'}
**Solo Experience**: {state.get('solo_preference', True)}

**TIME CONSTRAINTS** (IMPORTANT - respect these limits):
- Available Time: {time_available} hours
- Start Time: {user_start_time}
- End Time: {end_time} (must finish by this time)
- Select experiences that fit within this window
- Include travel time between stops (assume 15-30 mins in city traffic)

**Discovered Experiences**:
{json.dumps(experiences, indent=2)}

**Cultural Context**:
{json.dumps(state.get('cultural_context', {}), indent=2)}

**Social Scaffolding**:
{json.dumps(state.get('social_scaffolding', {}), indent=2)}

Craft a narrative that fits within the {time_available}-hour window starting at {user_start_time}.
Select the best 2-4 experiences that can be realistically completed in this time.
Weave them into a journey with setup, friction, and payoff."""

        messages = [
            SystemMessage(content=PLOT_BUILDER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await model.ainvoke(messages)

        response_text = strip_markdown_json(response.content)
        result = json.loads(response_text)
        state["narrative_itinerary"] = result.get("narrative_itinerary", "")
        state["collision_suggestion"] = result.get("collision_suggestion", {})

        state["agent_trace"].append({
            "agent": "plot_builder",
            "status": "success",
            "narrative_length": len(state["narrative_itinerary"]),
            "has_collision": bool(state["collision_suggestion"]),
            "latency_ms": (datetime.now() - agent_start_time).total_seconds() * 1000,
            "timestamp": agent_start_time.isoformat(),
        })

    except Exception as e:
        state["errors"].append({
            "agent": "plot_builder",
            "error": str(e),
            "timestamp": agent_start_time.isoformat(),
        })
        state["agent_trace"].append({
            "agent": "plot_builder",
            "status": "error",
            "error": str(e),
            "latency_ms": (datetime.now() - agent_start_time).total_seconds() * 1000,
        })
        if not state.get("narrative_itinerary"):
            state["narrative_itinerary"] = ""
        if not state.get("collision_suggestion"):
            state["collision_suggestion"] = {}

    return state
