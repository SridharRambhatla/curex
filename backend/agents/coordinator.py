"""
Sidequest — Coordinator (Supervisor Agent)

LangGraph StateGraph that orchestrates all 5 agents in the correct order:
1. Discovery → 2. Cultural Context + Community (parallel) → 3. Plot-Builder → 4. Budget → Done

Uses Vertex AI Gemini models throughout.
"""

import uuid
import asyncio
from datetime import datetime

from state.schemas import AgentState, ItineraryRequest, ItineraryResponse
from agents.discovery_agent import run_discovery
from agents.cultural_context_agent import run_cultural_context
from agents.community_agent import run_community
from agents.plot_builder_agent import run_plot_builder
from agents.budget_agent import run_budget_optimizer


def _create_initial_state(request: ItineraryRequest) -> AgentState:
    """Convert an API request into the initial agent state."""
    return AgentState(
        # User inputs
        user_query=request.query,
        social_media_urls=request.social_media_urls,
        city=request.city,
        budget_range=(request.budget_min, request.budget_max),
        num_people=request.num_people,
        solo_preference=request.solo_preference,
        interest_pods=request.interest_pods,
        crowd_preference=request.crowd_preference,
        start_date=request.start_date or "",
        end_date=request.end_date or "",
        time_available_hours=request.time_available_hours or 8.0,  # Default to 8 hours
        start_time=request.start_time or "10:00",  # Default to 10 AM
        # Agent outputs (initialized empty)
        discovered_experiences=[],
        cultural_context={},
        narrative_itinerary="",
        budget_breakdown={},
        social_scaffolding={},
        collision_suggestion={},
        # Metadata
        agent_trace=[],
        errors=[],
        session_id=str(uuid.uuid4()),
    )


def _state_to_response(state: AgentState) -> ItineraryResponse:
    """Convert final agent state into an API response."""
    # Build experience items from discovered experiences
    experiences = []
    for exp in state.get("discovered_experiences", []):
        experiences.append({
            "name": exp.get("name", ""),
            "category": exp.get("category", ""),
            "timing": exp.get("timing", ""),
            "budget": exp.get("budget", 0),
            "location": exp.get("location", ""),
            "solo_friendly": exp.get("solo_friendly", False),
            "source": exp.get("source", ""),
            "lore": exp.get("lore", ""),
            "description": exp.get("description", ""),
        })

    # Build budget breakdown
    budget = state.get("budget_breakdown", {})
    budget_obj = None
    if budget:
        budget_obj = {
            "total_estimate": budget.get("total_estimate", 0),
            "breakdown": budget.get("breakdown", []),
            "deals": budget.get("deals", []),
            "within_budget": budget.get("within_budget", True),
        }

    # Build collision suggestion
    collision = state.get("collision_suggestion", {})
    collision_obj = None
    if collision and collision.get("title"):
        collision_obj = {
            "title": collision.get("title", ""),
            "experiences": collision.get("experiences", []),
            "why": collision.get("why", ""),
        }

    return ItineraryResponse(
        narrative_itinerary=state.get("narrative_itinerary", ""),
        experiences=experiences,
        cultural_context=state.get("cultural_context", {}),
        budget_breakdown=budget_obj,
        social_scaffolding=state.get("social_scaffolding", {}),
        collision_suggestion=collision_obj,
        agent_trace=state.get("agent_trace", []),
        session_id=state.get("session_id", ""),
    )


async def run_workflow(request: ItineraryRequest) -> ItineraryResponse:
    """
    Execute the full agent workflow (OPTIMIZED for latency).

    Pipeline:
    1. Discovery Agent — find experiences (sequential, needed by all others)
    2. Cultural Context + Community + Budget — all in parallel (Budget only needs discovery)
    3. Plot-Builder — craft narrative (needs context + community output)

    All agents use Vertex AI Gemini models via langchain-google-vertexai.
    """
    state = _create_initial_state(request)

    workflow_start = datetime.now()
    state["agent_trace"].append({
        "agent": "coordinator",
        "status": "started",
        "timestamp": workflow_start.isoformat(),
        "query": request.query,
        "city": request.city,
    })

    # ── Step 1: Discovery ──────────────────────────────────
    discovery_start = datetime.now()
    discovery_result = run_discovery(state)
    discovery_latency = (datetime.now() - discovery_start).total_seconds() * 1000
    
    # Merge discovery results into state
    state["discovered_experiences"] = discovery_result.get("discovered_experiences", [])
    if "error" in discovery_result:
        state["errors"].append({
            "agent": "discovery",
            "error": discovery_result["error"],
            "timestamp": datetime.now().isoformat(),
        })
    # Add trace entry for discovery
    state["agent_trace"].append({
        "agent": "discovery",
        "status": "success" if discovery_result.get("discovered_experiences") else "error",
        "experiences_found": len(discovery_result.get("discovered_experiences", [])),
        "latency_ms": discovery_latency,
        "timestamp": datetime.now().isoformat(),
    })

    # ── Step 2: Cultural Context + Community + Budget (ALL PARALLEL) ──
    # Budget only needs discovered_experiences, so it can run alongside enrichment
    # This saves ~2-3 seconds by not waiting for plot builder to finish first
    results = await asyncio.gather(
        run_cultural_context(dict(state)),
        run_community(dict(state)),
        run_budget_optimizer(dict(state)),
        return_exceptions=True  # Don't fail fast - collect all results
    )

    # Merge parallel results back into state
    cultural_state, community_state, budget_state = results
    
    # Handle potential exceptions
    if isinstance(cultural_state, Exception):
        state["errors"].append({"agent": "cultural_context", "error": str(cultural_state)})
        cultural_state = {"cultural_context": {}, "agent_trace": [], "errors": []}
    if isinstance(community_state, Exception):
        state["errors"].append({"agent": "community", "error": str(community_state)})
        community_state = {"social_scaffolding": {}, "agent_trace": [], "errors": []}
    if isinstance(budget_state, Exception):
        state["errors"].append({"agent": "budget", "error": str(budget_state)})
        budget_state = {"budget_breakdown": {}, "agent_trace": [], "errors": []}
    
    state["cultural_context"] = cultural_state.get("cultural_context", {})
    state["social_scaffolding"] = community_state.get("social_scaffolding", {})
    state["budget_breakdown"] = budget_state.get("budget_breakdown", {})
    
    # Merge traces from parallel agents
    for parallel_state in [cultural_state, community_state, budget_state]:
        for trace in parallel_state.get("agent_trace", []):
            if trace not in state["agent_trace"]:
                state["agent_trace"].append(trace)
        state["errors"].extend(parallel_state.get("errors", []))

    # ── Step 3: Plot-Builder ───────────────────────────────
    # Runs after cultural context + community since it needs their output
    state = await run_plot_builder(state)

    # ── Finalize ───────────────────────────────────────────
    workflow_end = datetime.now()
    total_latency = (workflow_end - workflow_start).total_seconds() * 1000
    state["agent_trace"].append({
        "agent": "coordinator",
        "status": "completed",
        "total_latency_ms": total_latency,
        "timestamp": workflow_end.isoformat(),
        "agents_succeeded": sum(
            1 for t in state["agent_trace"]
            if t.get("status") == "success"
        ),
        "agents_failed": sum(
            1 for t in state["agent_trace"]
            if t.get("status") == "error"
        ),
    })

    return _state_to_response(state)


def create_workflow():
    """
    Factory function to verify the workflow is importable.
    Returns the run_workflow coroutine for testing.
    """
    return run_workflow
