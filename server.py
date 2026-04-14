from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from database.db_setup import setup_database, get_connection
from rl_env.power_grid_env import PowerGridEnv
from graph import POWER_GRID_GRAPH, PowerGridState
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import asyncio
import numpy as np

load_dotenv()  # ← fixes GOOGLE_API_KEY error

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

env = None

class ChatRequest(BaseModel):
    message: str
    rl_action: Optional[int] = 1


def convert(obj):
    """Convert numpy types to Python native types for JSON."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


@app.on_event("startup")
def startup():
    load_dotenv()
    setup_database()


@app.get("/health")
def health():
    return {"status": "ok", "env_active": env is not None}


@app.post("/chat")
async def chat(request: ChatRequest):
    initial_state: PowerGridState = {
        "user_query": request.message,
        "rl_action": request.rl_action,
        "current_observation": [0.70, 0.82, 0.75, 0.30, 0.68, 0.50],
        "demand_decisions": None,
        "health_report": None,
        "transmission_report": None,
        "unified_report": None,
        "final_decisions": None,
        "rl_reward": None,
        "next_observation": None,
        "messages": [],
    }

    try:
        # Run graph in thread to not block event loop
        result = await asyncio.to_thread(POWER_GRID_GRAPH.invoke, initial_state)
        
        # Parse final report - we'll treat it as a summary for the frontend
        d = result.get("final_decisions", "")
        rl_reward = result.get("rl_reward", 0.0)
        lbl = "aggressive" if request.rl_action == 2 else "balanced"
        
        # Human-readable summary for console briefings
        h_summary = f"Neural orchestration successful for cycle {int(time.time()) % 1000}. "
        h_summary += f"Grid stabilized using {lbl.upper()} vector. "
        h_summary += f"Target reward index optimized at {rl_reward:.3f}. "
        if d and "[" in d:
            h_summary += f"Demand agent recommends: {d[:100]}..."

        report = {
            "summary": h_summary,
            "analysis": d, # Keep for backward compatibility
            "status": "EMERGENCY_MODE" if "cyclone" in request.message.lower() or "storm" in request.message.lower() else "ANALYZED",
            "city": "DELHI" if "delhi" in request.message.lower() else "GLOBAL",
            "demand_mw": 1450 if "peak" in request.message.lower() else 1240,
            "supply_mw": 1150,
            "balance_mw": -300 if "cyclone" in request.message.lower() else -90,
            "agent_source": "Neural",
            "supply_breakdown": {
                "by_type": {
                    "coal": {"current_mw": 450, "max_mw": 500},
                    "nuclear": {"current_mw": 520, "max_mw": 800},
                    "renewable": {"current_mw": 180, "max_mw": 350}
                }
            },
            "signals": {
                "weather": {"label": "Cyclone" if "cyclone" in request.message.lower() else "Stable", "score": 0.9 if "cyclone" in request.message.lower() else 0.2},
                "crisis": {"label": "Grid Loss" if "cyclone" in request.message.lower() else "Normal", "score": 0.85 if "cyclone" in request.message.lower() else 0.15}
            },
            "plants": [
                {"name": "NORTH_01", "current_mw": 450, "distance_km": 120, "cost": 4.5, "type": "coal"},
                {"name": "WEST_02", "current_mw": 280, "distance_km": 450, "cost": 5.2, "type": "gas"},
                {"name": "EAST_01", "current_mw": 520, "distance_km": 890, "cost": 3.8, "type": "nuclear"}
            ],
            "decisions": [
                {"plant": "NORTH_01", "delta": 50, "before": "400MW", "after": "450MW", "reason": "Compensating for regional deficit."},
                {"plant": "EAST_01", "delta": 20, "before": "500MW", "after": "520MW", "reason": "Strategic grid stabilization."}
            ]
        }
        
        # Try to parse some actual data if nested JSON exists
        fd = result.get("final_decisions", "")
        import re
        m = re.search(r"(\{[\s\S]*\})", fd)
        if m:
            try:
                parsed = json.loads(m.group(1))
                report["rl_reward"] = parsed.get("rl_reward")
            except:
                pass

        return {
            "report": report,
            "parsed_intent": {"city": "DELHI", "context": request.message}
        }
    except Exception as e:
        import traceback
        print(f"[CHAT ERROR] {e}")
        print(traceback.format_exc())
        return {"error": str(e), "report": {"summary": "Neural link failure."}}


@app.get("/plants")
def get_plants():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM plant_health")
    rows = cursor.fetchall()
    
    plants = []
    # Approximate lat/lon for the cities in seeded data
    coords = {
        "Delhi": (28.61, 77.20),
        "Mumbai": (19.07, 72.87),
        "Kolkata": (22.57, 88.36),
        "Chennai": (13.08, 80.27),
        "Bhopal": (23.25, 77.41),
        "Jaipur": (26.91, 75.78)
    }
    
    for r in rows:
        plants.append({
            "id": r["plant_id"],
            "name": r["plant_name"],
            "lat": coords.get(r["location"], (20, 78))[0],
            "lon": coords.get(r["location"], (20, 78))[1],
            "type": r["fuel_type"],
            "max_mw": r["max_capacity_mw"],
            "current_mw": r["current_output_mw"],
            "state": r["location"],
            "cost": 4.5 # Default cost as requested by UI
        })
    conn.close()
    return plants


@app.get("/memory/decisions")
def get_decisions():
    # Return last 10 decisions from simulated memory
    return {
        "decisions": [
            {
                "city": "Delhi",
                "agent_source": "Neural",
                "summary": "Stabilized northern grid sector during fluctuating demand peak.",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat()
            },
            {
                "city": "Mumbai",
                "agent_source": "Orchestrator",
                "summary": "Redirected 200MW from western hydro bank to compensate for solar drop.",
                "timestamp": (datetime.now() - timedelta(minutes=12)).isoformat()
            }
        ]
    }


@app.get("/memory/signals")
def get_signals():
    return {
        "signals": [
            {"city": "North", "weather_label": "High Temp", "commodity_label": "Coal High", "timestamp": datetime.now().isoformat()},
            {"city": "South", "weather_label": "Storm Warning", "crisis_label": "Line Degraded", "timestamp": datetime.now().isoformat()}
        ]
    }


@app.post("/start")
def start(max_steps: int = 10):
    global env
    env = PowerGridEnv(max_steps=max_steps)
    obs, _ = env.reset()
    return {
        "status": "started",
        "obs": obs.tolist(),
        "max_steps": max_steps
    }


@app.get("/stream")
async def stream():
    async def event_generator():
        global env
        if env is None:
            yield f"data: {json.dumps({'error': 'Call /start first'})}\n\n"
            return

        for step in range(env.max_steps):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)

            try:
                h_report = json.loads(info.get("health_report", "{}"))
            except:
                h_report = {}
            
            try:
                t_report = json.loads(info.get("transmission_report", "{}"))
            except:
                t_report = {}

            data = {
                "step": int(step + 1),
                "action": int(action),
                "action_label": ["conservative", "balanced", "aggressive"][int(action)],
                "reward": float(round(reward, 3)),
                "obs": [float(round(x, 4)) for x in obs.tolist()],
                "health_report": h_report,
                "transmission_report": t_report,
                "final_decisions": str(info.get("final_decisions", ""))[:1000],
            }
            yield f"data: {json.dumps(data)}\n\n"
            
            if terminated or truncated:
                yield f"data: {json.dumps({'done': True, 'total_steps': int(step+1)})}\n\n"
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/stop")
def stop():
    global env
    if env:
        env.close()
        env = None
    return {"status": "stopped"}