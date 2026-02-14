"""
Sidequest Backend — FastAPI Entry Point

API server for the Sidequest experience discovery platform.
Uses Vertex AI Gemini models via LangGraph supervisor pattern.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from state.schemas import ItineraryRequest, ItineraryResponse
from agents.coordinator import run_workflow
from logging_system import start_global_logger, stop_global_logger, get_log_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Vertex AI and logging system on startup."""
    import google.cloud.aiplatform as aiplatform

    if settings.google_cloud_project:
        aiplatform.init(
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
        print(f"✅ Vertex AI initialized: project={settings.google_cloud_project}, "
              f"location={settings.google_cloud_location}")
    else:
        print("⚠️  GOOGLE_CLOUD_PROJECT not set — Vertex AI calls will fail. "
              "Set it in .env for full functionality.")
    
    # Initialize logging system
    await start_global_logger()
    log_config = get_log_config()
    print(f"✅ Agent logging system initialized: level={log_config.log_level}, "
          f"dir={log_config.log_dir}")
    
    yield
    
    # Cleanup logging system
    await stop_global_logger()
    print("✅ Agent logging system stopped")


app = FastAPI(
    title="Sidequest API",
    description="Plot-first experience discovery powered by Vertex AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "sidequest-api"}


# ──────────────────────────────────────────────
# Core API: Itinerary Generation
# ──────────────────────────────────────────────

@app.post("/api/generate-itinerary", response_model=ItineraryResponse)
async def generate_itinerary(request: ItineraryRequest):
    """
    Generate a plot-first narrative itinerary.

    Orchestrates 5 Vertex AI agents:
    1. Discovery Agent — finds experiences
    2. Cultural Context Agent — adds localization
    3. Plot-Builder Agent — crafts narrative arc
    4. Budget Optimizer Agent — cost breakdown
    5. Community Agent — solo-sure filtering
    """
    try:
        result = await run_workflow(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Itinerary generation failed: {str(e)}"
        )


# ──────────────────────────────────────────────
# Agent Trace (for demo/observability)
# ──────────────────────────────────────────────

@app.get("/api/agent-trace/{session_id}")
async def get_agent_trace(session_id: str):
    """Retrieve agent execution trace for demo visualization."""
    # TODO: Implement trace storage/retrieval
    return {
        "session_id": session_id,
        "trace": [],
        "message": "Trace storage not yet implemented"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
    )
