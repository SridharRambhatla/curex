# 🧭 Sidequest — Agent Architecture Documentation

> **Sidequest** is a plot-first experience discovery platform powered by 5 specialized AI agents orchestrated via a Coordinator (Supervisor) pattern. Each agent enriches user queries into narrative-driven, culturally-aware, budget-optimized itineraries.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Agent Pipeline Flow](#agent-pipeline-flow)
3. [Agent 1: Discovery Agent](#1-discovery-agent-)
4. [Agent 2: Cultural Context Agent](#2-cultural-context-agent-)
5. [Agent 3: Community Agent](#3-community-agent-)
6. [Agent 4: Plot-Builder Agent](#4-plot-builder-agent-)
7. [Agent 5: Budget Optimizer Agent](#5-budget-optimizer-agent-)
8. [Coordinator (Supervisor)](#coordinator-supervisor-)
9. [Shared State Schema](#shared-state-schema)
10. [Model Configuration](#model-configuration)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                             │
│  "Solo pottery workshop in Bangalore under ₹2000"               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     COORDINATOR        │
              │  (Supervisor Agent)    │
              └────────┬───────────────┘
                       │
          ┌────────────▼────────────┐
          │  Step 1: DISCOVERY      │  ← Sequential (all others depend on it)
          │  Find 5-10 experiences  │
          └────────────┬────────────┘
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
  ┌──────────────────┐  ┌──────────────────┐
  │ Step 2a: CULTURAL│  │ Step 2b:         │  ← Parallel (independent)
  │ CONTEXT          │  │ COMMUNITY        │
  │ India-specific   │  │ Solo-sure filter │
  │ localization     │  │ Social scaffold  │
  └────────┬─────────┘  └────────┬─────────┘
           └──────────┬──────────┘
                      ▼
          ┌────────────────────────┐
          │  Step 3: PLOT-BUILDER  │  ← Needs context + community output
          │  Narrative itinerary   │
          └────────────┬───────────┘
                       ▼
          ┌────────────────────────┐
          │  Step 4: BUDGET        │  ← Final cost analysis
          │  OPTIMIZER             │
          └────────────┬───────────┘
                       ▼
              ┌────────────────────┐
              │   API RESPONSE     │
              │   (Itinerary)      │
              └────────────────────┘
```

---

## Agent Pipeline Flow

| Step | Agent(s)                          | Execution     | Input                                      | Output                                    |
|------|-----------------------------------|---------------|--------------------------------------------|--------------------------------------------|
| 1    | Discovery Agent                   | Sequential    | User query, city, budget, interest pods    | `discovered_experiences[]`                 |
| 2a   | Cultural Context Agent            | **Parallel**  | Discovered experiences, city               | `cultural_context{}`                       |
| 2b   | Community Agent                   | **Parallel**  | Discovered experiences, city, solo pref    | `social_scaffolding{}`                     |
| 3    | Plot-Builder Agent                | Sequential    | Experiences + cultural context + scaffolding | `narrative_itinerary`, `collision_suggestion` |
| 4    | Budget Optimizer Agent            | Sequential    | Experiences, city, budget range, num_people | `budget_breakdown{}`                       |

---

## 1. Discovery Agent 🔍

**File:** `backend/agents/discovery_agent.py`  
**Model:** `gemini-2.0-flash` (via `google.generativeai` SDK)  
**Temperature:** `0.4`  
**Role:** *Find 5-10 compelling, hyperlocal experiences*

### Purpose

The Discovery Agent is the **first agent in the pipeline** and the foundation of the entire workflow. It takes the user's query, city, budget constraints, and interest categories, then uses Gemini to generate a curated list of unique, hyperlocal experiences.

### How It Works

1. **Input Extraction** — Reads `user_query`, `city`, `budget_range`, and `interest_pods` from the shared state.
2. **Interest Mapping** — Converts internal pod IDs (e.g., `food_nerd`) into human-readable categories (e.g., `"food and drinks"`) for better prompt quality.
3. **Prompt Construction** — Builds a structured prompt that includes:
   - The user's natural language query
   - Target city
   - Budget range in INR
   - Mapped interest categories (if any)
4. **Gemini API Call** — Sends the prompt to `gemini-2.0-flash` with `response_mime_type: "application/json"` to enforce structured JSON output.
5. **Response Parsing** — Parses the JSON response and extracts the `discovered_experiences` array.
6. **Metadata Injection** — Adds `search_metadata` (agent name, model, city) for observability.

### Output Schema

Each discovered experience contains:

| Field          | Type      | Description                                      |
|----------------|-----------|--------------------------------------------------|
| `name`         | `string`  | Experience name                                  |
| `category`     | `string`  | One of: food, craft, heritage, nature, art, music, fitness, shopping, networking |
| `timing`       | `string`  | Best time to visit (e.g., "Saturday 7 AM")       |
| `budget`       | `int`     | Estimated cost in INR                            |
| `location`     | `string`  | Neighborhood/area in the city                    |
| `solo_friendly`| `boolean` | Whether it's suitable for solo visitors          |
| `source`       | `string`  | Where found (instagram, blog, local_knowledge)   |
| `description`  | `string`  | 2-3 sentence vivid description with sensory details |

### Key Design Choices

- Uses the **`google.generativeai` SDK directly** (not LangChain) — this is different from the other 4 agents which all use `langchain-google-vertexai`. This is because the Discovery Agent was built first as a standalone prototype.
- **Synchronous execution** (`run_discovery_agent`) — while other agents are `async`.
- Forces **JSON output** via `response_mime_type="application/json"` for reliable parsing.

### ⚠️ Current Limitation: No Real-Time Source Search

> **The Discovery Agent does NOT currently search real external sources like Reddit, X (Twitter), Instagram, or Google Maps.** It relies entirely on Gemini's training data and knowledge to generate experience suggestions. The `source` field in the output is a self-attributed label from the LLM (e.g., "local_knowledge", "instagram") — it doesn't indicate an actual API call to those platforms.

---

## 2. Cultural Context Agent 🏛️

**File:** `backend/agents/cultural_context_agent.py`  
**Model:** `gemini-2.0-pro` (via `langchain-google-vertexai`)  
**Temperature:** `0.4`  
**Role:** *Add India-specific cultural depth beyond translation*

### Purpose

Goes beyond simple localization — this agent adds **insider cultural knowledge** that makes experiences richer and more authentic. It's specifically tuned for Indian cities.

### How It Works

1. **Receives** the list of `discovered_experiences` from the Discovery Agent.
2. **Sends** the experiences + city context to `gemini-2.0-pro` (chosen for its deeper reasoning capabilities).
3. **Returns** a `cultural_context` dictionary keyed by experience name.

### Output Schema (per experience)

| Field                        | Description                                           |
|------------------------------|-------------------------------------------------------|
| `optimal_timing`             | When locals go, peak hours, cultural timing nuances   |
| `dress_code_and_etiquette`   | What to wear, temple rules, workshop attire norms     |
| `transport_hacks`            | Auto negotiation tips, metro shortcuts, parking reality |
| `social_norms`               | Solo dining acceptance, photography etiquette          |
| `religious_cultural_considerations` | Festival timing, Ramadan adjustments, local customs |
| `safety_and_accessibility`   | Lighting, wheelchair access, women-solo-friendly info |

### Key Design Choices

- Uses **`gemini-2.0-pro`** (more expensive but better at cultural reasoning).
- Runs **in parallel** with the Community Agent (Step 2a).
- Uses `langchain-google-vertexai` with `ChatVertexAI` for async invocation.

---

## 3. Community Agent 👥

**File:** `backend/agents/community_agent.py`  
**Model:** `gemini-2.0-flash` (via `langchain-google-vertexai`)  
**Temperature:** `0.2`  
**Role:** *Solo-sure filtering and social scaffolding*

### Purpose

Analyzes the **social dynamics** of each experience to help solo visitors feel confident. Provides "solo-sure" ratings and describes how environments facilitate natural social connections.

### How It Works

1. **Receives** the `discovered_experiences` list.
2. **Analyzes** each experience for solo-friendliness and social scaffolding potential.
3. **Returns** a `social_scaffolding` dictionary keyed by experience name.

### Output Schema (per experience)

| Field              | Type      | Description                                           |
|--------------------|-----------|-------------------------------------------------------|
| `solo_friendly`    | `boolean` | Can someone come alone comfortably?                   |
| `solo_percentage`  | `string`  | Estimated % of solo attendees (e.g., "40%")           |
| `scaffolding`      | `string`  | How the environment facilitates connection             |
| `arrival_vibe`     | `string`  | What it feels like arriving alone                     |
| `beginner_energy`  | `string`  | Low/Medium/High — Welcoming to first-timers?          |

### Key Design Choices

- Uses **`gemini-2.0-flash`** (fast pattern matching sufficient for this task).
- Low temperature (`0.2`) for consistent, reliable assessments.
- Runs **in parallel** with the Cultural Context Agent (Step 2b).

---

## 4. Plot-Builder Agent 📖

**File:** `backend/agents/plot_builder_agent.py`  
**Model:** `gemini-2.0-pro` (via `langchain-google-vertexai`)  
**Temperature:** `0.7`  
**Role:** *The core creative engine — stories, not lists*

### Purpose

This is **Sidequest's core differentiator**. It transforms raw experiences + cultural context + social scaffolding into **narrative itineraries with emotional arcs** — not chronological lists.

### How It Works

1. **Receives** all enriched data: experiences, cultural context, social scaffolding.
2. **Weaves** them into a story using the **Setup → Friction → Payoff** structure.
3. **Generates** collision suggestions (cross-pod pairings for serendipity).
4. **Returns** the narrative text and collision suggestion.

### Storytelling Principles

| Principle              | Description                                              |
|------------------------|----------------------------------------------------------|
| **Setup → Friction → Payoff** | Every itinerary has narrative structure              |
| **Intentional Friction**      | Queuing, trekking, learning = memory-making moments  |
| **Lore Layering**             | Backstory, provenance, "why this matters"            |
| **Collision Suggestions**     | Mix interest pods (pottery + food + music)           |
| **Time-Fluid**                | Dawn + evening in same day (dual prime times)        |

### Output Schema

| Field                    | Type     | Description                                     |
|--------------------------|----------|-------------------------------------------------|
| `narrative_itinerary`    | `string` | Full evocative narrative with all stops          |
| `collision_suggestion`   | `object` | `{title, experiences[], why}` — cross-pod match |

### Key Design Choices

- Uses **`gemini-2.0-pro`** for its creative writing capabilities.
- **Highest temperature** (`0.7`) among all agents for creative output.
- **Largest output limit** (`8192` tokens) for rich narratives.
- Written in "you" voice with sensory details and insider warmth.

---

## 5. Budget Optimizer Agent 💰

**File:** `backend/agents/budget_agent.py`  
**Model:** `gemini-2.0-flash` (via `langchain-google-vertexai`)  
**Temperature:** `0.1`  
**Role:** *Cost transparency, deals, and booking recommendations*

### Purpose

Provides **complete cost transparency** for the itinerary — not just ticket prices but hidden costs, transport, tips, and cost-saving hacks.

### How It Works

1. **Receives** the `discovered_experiences`, city, budget range, and number of people.
2. **Calculates** detailed cost breakdowns: entry fees, average spend, transport, hidden costs.
3. **Finds** deals: early bird pricing, group discounts, BNPL options.
4. **Assesses** whether the total fits within the user's budget.
5. **Suggests** alternatives if over budget.

### Output Schema

| Field               | Type       | Description                                      |
|---------------------|------------|--------------------------------------------------|
| `total_estimate`    | `int`      | Total estimated cost in INR                      |
| `breakdown`         | `array`    | Per-experience cost items                        |
| `deals`             | `string[]` | Available discounts and offers                   |
| `tips`              | `string[]` | Cost-saving suggestions                          |
| `within_budget`     | `boolean`  | Whether total fits the budget range              |

### Key Design Choices

- Uses **`gemini-2.0-flash`** (numerical analysis doesn't need Pro).
- **Lowest temperature** (`0.1`) for accurate, deterministic cost estimates.
- Runs **last** in the pipeline (Step 4) — needs finalized experience list.
- All costs in **INR (₹)** with realistic Indian city pricing.

---

## Coordinator (Supervisor) 🎯

**File:** `backend/agents/coordinator.py`  
**Role:** *Orchestrates all 5 agents in the correct order*

### Execution Pipeline

```python
# Step 1: Discovery (sequential — all others depend on this)
discovery_result = run_discovery(state)

# Step 2: Cultural Context + Community (parallel — independent of each other)
results = await asyncio.gather(
    run_cultural_context(state),
    run_community(state)
)

# Step 3: Plot-Builder (sequential — needs context + community)
state = await run_plot_builder(state)

# Step 4: Budget Optimizer (sequential — needs finalized experiences)
state = await run_budget_optimizer(state)
```

### Key Responsibilities

1. **State Initialization** — Converts `ItineraryRequest` into `AgentState`.
2. **Pipeline Orchestration** — Runs agents in the correct dependency order.
3. **Parallel Execution** — Uses `asyncio.gather()` for Steps 2a + 2b.
4. **State Merging** — Merges parallel results back into the shared state.
5. **Trace Collection** — Gathers execution traces from all agents for observability.
6. **Response Conversion** — Transforms final `AgentState` into `ItineraryResponse`.

---

## Shared State Schema

**File:** `backend/state/schemas.py`

The `AgentState` TypedDict flows through all agents:

```python
class AgentState(TypedDict):
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

    # Agent outputs
    discovered_experiences: list[dict]
    cultural_context: dict
    narrative_itinerary: str
    budget_breakdown: dict
    social_scaffolding: dict
    collision_suggestion: dict

    # Metadata
    agent_trace: list[dict]
    errors: list[dict]
    session_id: str
```

---

## Model Configuration

**File:** `backend/config.py`

| Agent             | Model              | Temperature | Max Tokens | Reasoning                            |
|-------------------|--------------------|-------------|------------|--------------------------------------|
| Coordinator       | `gemini-2.0-flash` | 0.1         | 1,024      | Fast routing decisions               |
| Discovery         | `gemini-2.0-flash` | 0.3         | 4,096      | Speed + creative discovery balance   |
| Cultural Context  | `gemini-2.0-pro`   | 0.4         | 4,096      | Deep cultural reasoning              |
| Plot-Builder      | `gemini-2.0-pro`   | 0.7         | 8,192      | Creative narrative writing           |
| Budget            | `gemini-2.0-flash` | 0.1         | 2,048      | Deterministic cost calculation       |
| Community         | `gemini-2.0-flash` | 0.2         | 2,048      | Consistent social assessments        |

> **Flash models** are used for tasks requiring speed and pattern matching.  
> **Pro models** are used for tasks requiring deeper reasoning and creativity.

---

## API Endpoints

| Method | Endpoint                        | Description                         |
|--------|---------------------------------|-------------------------------------|
| `GET`  | `/health`                       | Health check                        |
| `POST` | `/api/generate-itinerary`       | Main itinerary generation endpoint  |
| `GET`  | `/api/agent-trace/{session_id}` | Retrieve agent execution trace      |

---

*Last updated: 2026-02-14*
