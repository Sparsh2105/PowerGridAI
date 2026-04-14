from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from database.db_setup import setup_database
from rl_env.power_grid_env import PowerGridEnv
from dotenv import load_dotenv
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

            data = {
                "step": int(step + 1),
                "action": int(action),
                "action_label": ["conservative", "balanced", "aggressive"][int(action)],
                "reward": float(round(reward, 3)),
                "obs": [float(round(x, 4)) for x in obs.tolist()],
                "final_decisions": str(info.get("final_decisions", ""))[:500],
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.1)

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