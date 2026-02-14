"""
Sidequest State Schemas

Pydantic models for API requests/responses and TypedDict for LangGraph agent state.
"""

from typing import Optional, Any, Annotated
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# ──────────────────────────────────────────────
# API Request / Response Models (Pydantic)
# ──────────────────────────────────────────────

class ItineraryRequest(BaseModel):
    """Request body for itinerary generation."""

    query: str = Field(
        ...,
        description="User's natural language query or experience description",
        examples=["Solo-friendly pottery workshop for complete beginners in Bangalore"],
    )
    social_media_urls: list[str] = Field(
        default_factory=list,
        description="Instagram Reel or YouTube URLs to extract experiences from",
    )
    city: str = Field(
        default="Bangalore",
        description="Target city for experiences",
    )
    budget_min: int = Field(
        default=200,
        description="Minimum budget in INR",
    )
    budget_max: int = Field(
        default=5000,
        description="Maximum budget in INR",
    )
    num_people: int = Field(
        default=1,
        description="Number of people",
    )
    solo_preference: bool = Field(
        default=True,
        description="Whether to prioritize solo-friendly experiences",
    )
    interest_pods: list[str] = Field(
        default_factory=list,
        description="User's interest categories",
        examples=[["food_nerd", "craft_explorer", "heritage_walker"]],
    )
    crowd_preference: str = Field(
        default="relatively_niche",
        description="Crowd preference: crowded, relatively_niche, super_niche",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Trip start date (YYYY-MM-DD)",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Trip end date (YYYY-MM-DD)",
    )
    time_available_hours: Optional[float] = Field(
        default=None,
        description="Total hours available for the itinerary (e.g., 4, 6, 8). If not specified, defaults to a full day.",
    )
    start_time: Optional[str] = Field(
        default=None,
        description="Preferred start time (HH:MM format, e.g., '14:00' for 2 PM)",
    )


class ExperienceItem(BaseModel):
    """A single discovered experience."""

    name: str
    category: str
    timing: str
    budget: int
    location: str
    solo_friendly: bool = False
    source: str = ""
    lore: str = ""
    description: str = ""


class BudgetBreakdown(BaseModel):
    """Cost breakdown for an itinerary."""

    total_estimate: int
    breakdown: list[dict[str, Any]]
    deals: list[str] = Field(default_factory=list)
    within_budget: bool = True


class CollisionSuggestion(BaseModel):
    """Cross-pod experience recommendation."""

    title: str
    experiences: list[str]
    why: str


# ──────────────────────────────────────────────
# Discovery API Models (for /api/discover)
# ──────────────────────────────────────────────

class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float
    lng: float


class ExperienceLocation(BaseModel):
    """Location details for a discovery experience."""
    neighborhood: str
    coordinates: Coordinates


class ExperienceTiming(BaseModel):
    """Timing details for a discovery experience."""
    type: str = Field(default="flexible", description="flexible, scheduled, or time_sensitive")
    duration_hours: float = 2.0
    advance_booking_required: bool = False
    advance_days_minimum: Optional[int] = None


class ExperienceBudget(BaseModel):
    """Budget range for an experience."""
    min: int
    max: int
    currency: str = "INR"


class SoloFriendly(BaseModel):
    """Solo-friendliness assessment."""
    is_solo_sure: bool
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)


class CrowdLevel(BaseModel):
    """Current crowd level assessment."""
    current: str = Field(default="moderate", description="low, moderate, or high")
    updated_at: str


class WeatherSuitability(BaseModel):
    """Weather suitability for the experience."""
    indoor: bool
    outdoor: bool
    current_match: str = Field(default="good", description="perfect, good, fair, or poor")


class Availability(BaseModel):
    """Current availability status."""
    status: str = Field(default="available", description="available, limited, or sold_out")
    urgency_level: str = Field(default="low", description="low, medium, or high")


class DiscoveryExperienceResponse(BaseModel):
    """A single discovery experience with full metadata for the explore page."""
    
    id: str
    name: str
    category: str
    description_short: str
    image_url: str
    location: ExperienceLocation
    timing: ExperienceTiming
    operating_days: list[str] = Field(default_factory=lambda: ["daily"])
    operating_hours: Optional[str] = None
    budget: ExperienceBudget
    solo_friendly: SoloFriendly
    crowd_level: CrowdLevel
    weather_suitability: WeatherSuitability
    availability: Availability
    rating: Optional[float] = None
    review_count: Optional[int] = None
    bookmarked: bool = False


class DiscoverRequest(BaseModel):
    """Request body for discovery endpoint."""
    
    query: Optional[str] = Field(
        default=None,
        description="Optional search query to filter experiences"
    )
    city: str = Field(
        default="Bangalore",
        description="Target city for experiences"
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Filter by categories (e.g., ['Food & Drink', 'Nature'])"
    )
    budget_min: int = Field(
        default=0,
        description="Minimum budget in INR"
    )
    budget_max: int = Field(
        default=10000,
        description="Maximum budget in INR"
    )
    time_of_day: Optional[str] = Field(
        default=None,
        description="Filter by time: morning, afternoon, evening, night"
    )
    solo_friendly_only: bool = Field(
        default=False,
        description="Only return solo-friendly experiences"
    )
    limit: int = Field(
        default=25,
        ge=1,
        le=50,
        description="Maximum number of experiences to return"
    )
    fast_mode: bool = Field(
        default=False,
        description="If true, return curated data only (instant). If false, combine curated + agent-generated."
    )


class DiscoverResponse(BaseModel):
    """Response body for discovery endpoint."""
    
    experiences: list[DiscoveryExperienceResponse]
    total_count: int
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    curated_count: int = Field(default=0, description="Number of curated experiences in response")
    agent_count: int = Field(default=0, description="Number of agent-generated experiences in response")
    source: str = Field(default="curated", description="Source: 'curated', 'agent', or 'hybrid'")


class ItineraryResponse(BaseModel):
    """Response body for itinerary generation."""

    narrative_itinerary: str = Field(
        description="Plot-first narrative itinerary with story arc"
    )
    experiences: list[ExperienceItem] = Field(
        default_factory=list,
        description="Discovered experiences used in the itinerary"
    )
    cultural_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Cultural context annotations per experience"
    )
    budget_breakdown: Optional[BudgetBreakdown] = None
    social_scaffolding: dict[str, Any] = Field(
        default_factory=dict,
        description="Solo-sure and social scaffolding info"
    )
    collision_suggestion: Optional[CollisionSuggestion] = None
    agent_trace: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Agent execution trace for demo visualization"
    )
    session_id: str = Field(
        default="",
        description="Session ID for trace retrieval"
    )


# ──────────────────────────────────────────────
# LangGraph Agent State (TypedDict)
# ──────────────────────────────────────────────

class AgentState(TypedDict):
    """Shared state flowing through the LangGraph agent pipeline."""

    # User inputs
    user_query: str
    social_media_urls: list[str]
    city: str
    budget_range: tuple[int, int]
    num_people: int
    solo_preference: bool
    interest_pods: list[str]
    crowd_preference: str
    start_date: str
    end_date: str
    time_available_hours: float  # Hours available for the itinerary
    start_time: str  # Preferred start time (HH:MM format)

    # Agent outputs
    discovered_experiences: list[dict[str, Any]]
    cultural_context: dict[str, Any]
    narrative_itinerary: str
    budget_breakdown: dict[str, Any]
    social_scaffolding: dict[str, Any]
    collision_suggestion: dict[str, Any]

    # Metadata
    agent_trace: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    session_id: str
