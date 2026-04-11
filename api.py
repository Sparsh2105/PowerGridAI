"""
api.py — GridMind FastAPI Server

Endpoints:
  POST /chat             → natural language input — parses city + context automatically
  POST /run              → structured input — just pass city
  GET  /plants           → list all 10 power plants
  GET  /memory/decisions → recent decisions from SQLite
  GET  /memory/signals   → recent signals from SQLite
  GET  /health           → server health check

Run:
  uvicorn api:app --reload --port 8000

Swagger docs:
  http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

from agent.flow      import build_graph
from agent.grid_agent import parse_user_intent
from core.config     import POWER_PLANTS
from core.memory     import GridMemory


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="GridMind AI",
    description=(
        "Multi-agent LangGraph power grid controller for India.\n\n"
        "**Two ways to use:**\n\n"
        "`POST /chat` — send anything in plain English:\n"
        "> *'heavy rain in Mumbai today'*\n"
        "> *'coal prices are very high, check Bhopal grid'*\n"
        "> *'there is a storm near Chennai power plants'*\n\n"
        "`POST /run` — structured call, just pass city name.\n\n"
        "**Agent pipeline:** location → sensor → demand → supply → decision → apply → memory → report"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(
        description="Anything in plain English — city, situation, weather, prices, crisis etc.",
        examples=[
            "heavy rain in Mumbai today",
            "coal prices are very high, check Bhopal",
            "there is a cyclone near Chennai",
            "what is the grid status for Delhi?",
            "Gorakhpur",
        ]
    )

class RunRequest(BaseModel):
    city: str = Field(
        default="Delhi",
        description="Any Indian city name",
        examples=["Delhi", "Mumbai", "Bhopal", "Gorakhpur", "Chennai"]
    )
    user_context: Optional[str] = Field(
        default="",
        description="Optional extra context — weather situation, price info, crisis etc.",
        examples=["coal prices are very high today", "heavy rain expected"]
    )

class RunResponse(BaseModel):
    city:             str
    demand_mw:        float
    supply_mw:        float
    balance_mw:       float
    status:           str
    agent_source:     str
    demand_breakdown: dict
    supply_breakdown: dict
    signals:          dict
    plants:           list
    decisions:        list
    summary:          str
    analysis:         str

class ChatResponse(BaseModel):
    parsed_intent:    dict   # what Gemini understood from the message
    report:           RunResponse


# ── Helper ─────────────────────────────────────────────────────────────────────

def _run_pipeline(city: str, user_context: str = "", urgency: str = "normal") -> dict:
    """Shared pipeline runner used by both /run and /chat."""
    memory = GridMemory()
    graph  = build_graph(memory)

    initial = {
        "city":              city,
        "lat":               0.0,
        "lon":               0.0,
        "demand_mw":         70.0,
        "demand_breakdown":  {},
        "total_supply_mw":   0.0,
        "supply_breakdown":  {},
        "balance_mw":        0.0,
        "plants":            [],
        "signals":           {"weather": {}, "commodity": {}, "crisis": {}},
        "decisions":         [],
        "decision_summary":  "",
        "decision_analysis": "",
        "applied_changes":   [],
        "agent_source":      "none",
        "route":             "",
        "report":            {},
        "user_context":      user_context,
        "urgency":           urgency,
    }

    result = graph.invoke(initial)
    memory.close()
    return result.get("report") or {}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    """Check if the server is alive."""
    return {"status": "ok", "service": "GridMind AI v2"}


@app.post("/chat", response_model=ChatResponse, tags=["Grid"])
def chat(req: ChatRequest):
    """
    **Natural language endpoint** — send anything, GridMind figures out the rest.

    Examples of what you can send:
    - `"heavy rain in Mumbai today"`
    - `"coal prices are very high, check Bhopal grid"`
    - `"there is a cyclone warning near Chennai"`
    - `"is Delhi grid okay?"`
    - `"Gorakhpur"` ← just a city name also works

    GridMind will:
    1. Parse your message to extract city, context, urgency and intent
    2. Run the full 9-agent LangGraph pipeline
    3. Return the grid report + what it understood from your message
    """
    try:
        # Step 1: Parse natural language → structured intent
        intent = parse_user_intent(req.message)
        print(f"[Chat] Intent parsed: city={intent['city']} urgency={intent['urgency']} type={intent['intent_type']}")

        # Step 2: Run full pipeline with extracted context
        report = _run_pipeline(
            city=intent["city"],
            user_context=intent.get("context", req.message),
            urgency=intent.get("urgency", "normal"),
        )

        if not report:
            raise HTTPException(status_code=500, detail="Pipeline returned no report")

        return {"parsed_intent": intent, "report": report}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run", response_model=RunResponse, tags=["Grid"])
def run_grid(req: RunRequest):
    """
    **Structured endpoint** — pass city + optional context directly.

    Use this when you already know the city and want to optionally
    pass extra context like weather or price situation.

    **Agent pipeline:**
    location → sensor → demand → supply → decision → apply → memory → report
    """
    try:
        report = _run_pipeline(
            city=req.city,
            user_context=req.user_context or "",
            urgency="normal",
        )
        if not report:
            raise HTTPException(status_code=500, detail="Pipeline returned no report")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plants", tags=["Grid"])
def list_plants():
    """List all 10 power plants with type, capacity, cost and location."""
    return [
        {
            "name":   p["name"],
            "type":   p["type"],
            "max_mw": p["max_mw"],
            "cost":   p["cost"],
            "state":  p["state"],
            "lat":    p["lat"],
            "lon":    p["lon"],
        }
        for p in POWER_PLANTS
    ]


@app.get("/memory/decisions", tags=["Memory"])
def get_decisions(limit: int = Query(default=10, ge=1, le=100)):
    """Return the most recent grid decisions from SQLite."""
    mem  = GridMemory()
    rows = mem.get_all_decisions(limit=limit)
    mem.close()
    return {"count": len(rows), "decisions": rows}


@app.get("/memory/signals", tags=["Memory"])
def get_signals(limit: int = Query(default=10, ge=1, le=100)):
    """Return the most recent sensor signals from SQLite."""
    mem  = GridMemory()
    rows = mem.get_all_signals(limit=limit)
    mem.close()
    return {"count": len(rows), "signals": rows}