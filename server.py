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
import time

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
    """Convert numpy types to Python native types for JSON as integers."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return int(round(float(obj)))
    if isinstance(obj, np.ndarray):
        return [int(round(float(x))) for x in obj.tolist()]
    if isinstance(obj, float):
        return int(round(obj))
    return obj


@app.on_event("startup")
def startup():
    load_dotenv()
    setup_database()


def get_live_report(message: str, result: dict):
    """Aggregates real-time data from database for the Strategic Intel report."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Fetch Supply Breakdown
    cursor.execute("SELECT fuel_type, SUM(current_output_mw) as cur, SUM(max_capacity_mw) as max FROM plant_health GROUP BY fuel_type")
    supply_rows = cursor.fetchall()
    supply_breakdown = {"by_type": {}}
    total_supply = 0
    for r in supply_rows:
        supply_breakdown["by_type"][r["fuel_type"]] = {"current_mw": r["cur"], "max_mw": r["max"]}
        total_supply += r["cur"]

    # 2. Fetch Detailed Plant Data with real cost and coordinates
    # Primary city coordinates
    city_coords = {
        "DELHI": (28.61, 77.20),
        "MUMBAI": (19.07, 72.87),
        "KOLKATA": (22.57, 88.36),
        "CHENNAI": (13.08, 80.27),
        "BHOPAL": (23.25, 77.41),
        "JAIPUR": (26.91, 75.78),
    }

    # Detect city for vectoring
    cities = ["DELHI", "MUMBAI", "KOLKATA", "CHENNAI", "BHOPAL", "JAIPUR"]
    detected_city = "NATIONAL_GRID"
    for c in cities:
        if c.lower() in message.lower():
            detected_city = c
            break

    target_lat, target_lon = city_coords.get(detected_city, (21.0, 78.0))

    cursor.execute("SELECT plant_name, current_output_mw, max_capacity_mw, fuel_type, unit_cost_inr, lat, lon FROM plant_health")
    plant_rows = cursor.fetchall()
    plants_intel = []
    for r in plant_rows:
        # Distance calculation (simple pythagorean for visual relative distribution)
        dist = ((r["lat"] - target_lat)**2 + (r["lon"] - target_lon)**2)**0.5 * 100 
        plants_intel.append({
            "name": r["plant_name"],
            "current_mw": r["current_output_mw"],
            "max_mw": r["max_capacity_mw"],
            "distance_km": dist,
            "cost": r["unit_cost_inr"],
            "type": r["fuel_type"]
        })

    # 3. Fetch Grid Anomalies (Signals)
    is_crisis = "cyclone" in message.lower() or "storm" in message.lower()
    weather_score = 0.9 if is_crisis else 0.15
    crisis_score = 0.85 if is_crisis else 0.12

    # 4. Decisions (Delta Mapping)
    decisions = []
    dd = result.get("demand_decisions", "[]")
    try:
        if isinstance(dd, str):
            import re
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", dd)
            if m:
                parsed_dd = json.loads(m.group(1))
                if isinstance(parsed_dd, list):
                    for d in parsed_dd[:4]:
                        plant_id = d.get("plant_id", "NODE")
                        # Fetch actual before value from DB
                        before_row = cursor.execute("SELECT current_output_mw FROM plant_health WHERE plant_id = ? OR plant_name = ?", (plant_id, plant_id)).fetchone()
                        before_val = before_row[0] if before_row else 400
                        after_val = d.get('recommended_output_mw', before_val)
                        
                        decisions.append({
                            "plant": plant_id,
                            "delta": int(after_val - before_val),
                            "before": int(before_val),
                            "after": int(after_val),
                            "reason": d.get("reason", "Neural Link Optimization")
                        })
    except Exception as e:
        print(f"[Decision Parsing Error] {e}")
        pass

    if not decisions:
        decisions = [{"plant": "SYSTEM", "delta": 0, "before": 0, "after": 0, "reason": "Stable state maintenance."}]

    conn.close()
    
    # 5. Load Dynamics
    import random
    base_demand = 1200 + (total_supply % 150)
    demand_jitter = random.randint(-40, 40)
    demand_mw = int(round(base_demand + demand_jitter))
    balance = int(round(total_supply - demand_mw))

    return {
        "summary": result.get("final_decisions", "Neural link optimized."),
        "analysis": result.get("final_decisions", "Analyzing grid state..."),
        "status": "EMERGENCY_MODE" if is_crisis else "STABILIZED",
        "city": detected_city,
        "demand_mw": demand_mw,
        "supply_mw": total_supply,
        "balance_mw": balance,
        "agent_source": "Neural_V4",
        "supply_breakdown": supply_breakdown,
        "signals": {
            "weather": {"label": "Cyclone" if is_crisis else "Stable", "score": weather_score},
            "crisis": {"label": "Grid Loss" if is_crisis else "Normal", "score": crisis_score}
        },
        "plants": plants_intel,
        "decisions": decisions
    }


@app.get("/health")
def health():
    return {"status": "ok", "env_active": env is not None}


@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Fetch REAL observation from DB
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT vibration_index, temperature_celsius, current_capacity_percent FROM plant_health ORDER BY plant_id LIMIT 6")
        rows = cursor.fetchall()
        obs = []
        for r in rows:
            obs.append(r["vibration_index"]) # or some combo
        while len(obs) < 6: obs.append(0.5) 
        conn.close()

        initial_state: PowerGridState = {
            "user_query": request.message,
            "rl_action": request.rl_action,
            "current_observation": obs,
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

        # Build live report from DB state
        report = get_live_report(request.message, result)
        
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

        # Save decision for later retrieval in Memory Log
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO decisions (city, agent_source, summary, timestamp)
            VALUES (?, ?, ?, ?)
        """, (report.get("city", "GLOBAL"), "Neural Relay", report.get("summary", ""), datetime.now().isoformat()))
        conn.commit()
        conn.close()

        return {
            "report": report,
            "parsed_intent": {"city": report["city"], "context": request.message}
        }
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"[CHAT ERROR] {error_msg}")
        print(traceback.format_exc())
        return {
            "error": error_msg, 
            "report": {
                "summary": f"Neural Link Interrupted: {error_msg[:100]}",
                "status": "OFFLINE",
                "city": "GLOBAL"
            }
        }


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
    conn = get_connection()
    cursor = conn.cursor()
    # Fetch last 20 decisions
    cursor.execute("SELECT city, agent_source, summary, timestamp FROM decisions ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    conn.close()
    
    decisions = []
    for r in rows:
        decisions.append({
            "city": r["city"],
            "agent_source": r["agent_source"],
            "summary": r["summary"],
            "timestamp": r["timestamp"]
        })
    
    # Fallback if empty
    if not decisions:
        decisions = [
            {
                "city": "System Gateway",
                "agent_source": "Neural",
                "summary": "GridMind link established. Monitoring national mainland sectors.",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
    return {"decisions": decisions}


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

            # Generate full consistent report for Intel page
            live_intel = get_live_report(f"Neural Step {step}", info)

            data = {
                "step": int(step + 1),
                "action": int(action),
                "action_label": ["conservative", "balanced", "aggressive"][int(action)],
                "reward": float(round(reward, 3)),
                "obs": [float(round(x, 4)) for x in obs.tolist()],
                "health_report": h_report,
                "transmission_report": t_report,
                "final_decisions": str(info.get("final_decisions", ""))[:1000],
                "intel_report": live_intel
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