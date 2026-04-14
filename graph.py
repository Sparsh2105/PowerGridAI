"""
LangGraph graph — Power Grid Intelligence System
================================================
FINAL OPTIMIZED VERSION:
  - Demand agent     → Gemini (1 LLM call, short prompt, max 2 attempts)
  - Health agent     → Pure Python (0 API calls)
  - Transmission     → Pure Python (0 API calls)
  - Orchestrator     → Groq API (separate key, never exhausted!)
  - 503 fallback     → auto switches model
  - 429 rotation     → rotates across all keys
  - Episode limit    → max_steps=2 in env

.env setup:
  LLM_PROVIDER=gemini
  GEMINI_MODEL=gemini-2.0-flash
  GEMINI_MODEL_FALLBACK=gemini-1.5-flash
  GOOGLE_API_KEY=key1,key2,key3
  GROQ_API_KEY=gsk_...
  TAVILY_API_KEY=tvly-...
"""

import os
import sys
import json
import re
import time
import traceback
import operator
from typing import TypedDict, Annotated, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END

load_dotenv()

sys.path.append(os.path.dirname(__file__))
from tools.demand_supply_tools import DEMAND_SUPPLY_TOOLS
from tools.health_tools import HEALTH_TOOLS
from tools.transmission_tools import TRANSMISSION_TOOLS
from tools.orchestrator_tools import ORCHESTRATOR_TOOLS


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI KEY ROTATOR
# ─────────────────────────────────────────────────────────────────────────────

class GeminiKeyRotator:
    """
    Supports both formats:
      GOOGLE_API_KEY=key1,key2,key3   (comma separated)
      GOOGLE_API_KEY_1=key1 / _2 / _3 (numbered)
    """

    def __init__(self):
        self.keys = []

        # comma separated
        raw = os.environ.get("GOOGLE_API_KEY", "").strip()
        if raw:
            for k in raw.split(","):
                k = k.strip()
                if k and k not in self.keys:
                    self.keys.append(k)

        # numbered
        for i in range(1, 10):
            k = os.environ.get(f"GOOGLE_API_KEY_{i}", "").strip()
            if k and k not in self.keys:
                self.keys.append(k)

        if not self.keys:
            raise ValueError("No Gemini API keys found! Add GOOGLE_API_KEY=key1,key2,key3 to .env")

        self._index          = 0
        self._cooldown_until = {}
        print(f"[GEMINI ROTATOR] {len(self.keys)} key(s) loaded")
        for i, k in enumerate(self.keys):
            print(f"  Key {i+1}: ...{k[-8:]}")

    def current_key(self) -> str:
        return self.keys[self._index % len(self.keys)]

    def next_key(self, cooldown_seconds: float = 65.0) -> str:
        bad = self.current_key()
        self._cooldown_until[bad] = time.time() + cooldown_seconds
        print(f"[GEMINI ROTATOR] Key ...{bad[-6:]} cooldown {cooldown_seconds:.0f}s")

        for _ in range(len(self.keys)):
            self._index = (self._index + 1) % len(self.keys)
            candidate   = self.keys[self._index]
            if time.time() >= self._cooldown_until.get(candidate, 0):
                print(f"[GEMINI ROTATOR] Switched to ...{candidate[-6:]}")
                return candidate

        best = min(self.keys, key=lambda k: self._cooldown_until.get(k, 0))
        wait = max(0, self._cooldown_until.get(best, 0) - time.time())
        if wait > 0:
            print(f"[GEMINI ROTATOR] All exhausted → waiting {wait:.1f}s")
            time.sleep(wait + 2)
        self._index                  = self.keys.index(best)
        self._cooldown_until[best]   = 0
        return best


_gemini_rotator: Optional[GeminiKeyRotator] = None


def get_gemini_rotator() -> GeminiKeyRotator:
    global _gemini_rotator
    if _gemini_rotator is None:
        _gemini_rotator = GeminiKeyRotator()
    return _gemini_rotator


# ─────────────────────────────────────────────────────────────────────────────
# LLM FACTORIES
# ─────────────────────────────────────────────────────────────────────────────

def get_gemini_llm(api_key: Optional[str] = None, use_fallback: bool = False):
    """Gemini LLM — used for demand agent."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = (
        os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-1.5-flash")
        if use_fallback
        else os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    )
    key = api_key or get_gemini_rotator().current_key()
    print(f"[GEMINI] {model} | key ...{key[-6:]}")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=key,
        temperature=0,
        max_retries=1,
    )


def get_groq_llm():
    """Groq LLM — used for orchestrator. Free, fast, separate quota."""
    from langchain_groq import ChatGroq

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        raise ValueError("GROQ_API_KEY not found in .env")

    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    print(f"[GROQ] {model}")
    return ChatGroq(
        model=model,
        api_key=groq_key,
        temperature=0,
        max_retries=2,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SAFE AGENT RUNNER — Gemini with rotation + fallback
# ─────────────────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    m = re.search(r"```json\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
    if m:
        return m.group(1).strip()
    return text


def _run_gemini_agent(tools: list, prompt: str, name: str, max_attempts: int = 2) -> str:
    """
    Run agent with Gemini — short prompt, max 2 attempts, rotation on 429, fallback on 503.
    max_attempts=2 to save keys for other agents.
    """
    rotator      = get_gemini_rotator()
    use_fallback = False

    for attempt in range(1, max_attempts + 1):
        try:
            key   = rotator.current_key()
            llm   = get_gemini_llm(api_key=key, use_fallback=use_fallback)
            agent = create_react_agent(llm, tools)

            result  = agent.invoke({"messages": [HumanMessage(content=prompt)]})
            msgs    = result.get("messages", [])
            if not msgs:
                return json.dumps({"error": f"{name}: no messages"})

            content = ""
            for msg in reversed(msgs):
                c = getattr(msg, "content", "")
                if isinstance(c, str) and c.strip():
                    content = c
                    break

            return content or json.dumps({"error": f"{name}: empty response"})

        except Exception as e:
            estr   = str(e)
            is_429 = any(x in estr for x in ["429", "RESOURCE_EXHAUSTED", "quota"])
            is_503 = any(x in estr for x in ["503", "UNAVAILABLE", "high demand"])

            if is_503:
                print(f"[{name}] 503 → switching to fallback model")
                use_fallback = True
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                return json.dumps({"error": f"{name}: 503 model unavailable"})

            elif is_429:
                delay_m  = re.search(r"retry in (\d+(?:\.\d+)?)s", estr)
                cooldown = float(delay_m.group(1)) + 3 if delay_m else 60.0
                print(f"[{name}] 429 attempt {attempt} → rotating key")
                rotator.next_key(cooldown_seconds=cooldown)
                if attempt < max_attempts:
                    continue
                return json.dumps({"error": f"{name}: all keys exhausted"})

            else:
                print(f"[ERROR {name}] {estr[:200]}")
                return json.dumps({"error": f"{name}: {estr[:200]}"})

    return json.dumps({"error": f"{name}: max attempts reached"})


def _run_groq_agent(tools: list, prompt: str, name: str) -> str:
    """Run agent with Groq — separate quota, fast, reliable."""
    try:
        llm   = get_groq_llm()
        agent = create_react_agent(llm, tools)

        result  = agent.invoke({"messages": [HumanMessage(content=prompt)]})
        msgs    = result.get("messages", [])
        if not msgs:
            return json.dumps({"error": f"{name}: no messages"})

        content = ""
        for msg in reversed(msgs):
            c = getattr(msg, "content", "")
            if isinstance(c, str) and c.strip():
                content = c
                break

        return content or json.dumps({"error": f"{name}: empty"})

    except Exception as e:
        print(f"[GROQ ERROR {name}] {str(e)[:200]}")
        return json.dumps({"error": f"{name}: groq failed: {str(e)[:100]}"})


# ─────────────────────────────────────────────────────────────────────────────
# STATE SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

class PowerGridState(TypedDict):
    user_query:          str
    rl_action:           int
    current_observation: list
    demand_decisions:    Optional[str]
    health_report:       Optional[str]
    transmission_report: Optional[str]
    unified_report:      Optional[dict]
    final_decisions:     Optional[str]
    rl_reward:           Optional[float]
    next_observation:    Optional[list]
    messages:            Annotated[list, operator.add]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT NODES
# ─────────────────────────────────────────────────────────────────────────────

def demand_agent_node(state: PowerGridState) -> dict:
    """Demand agent — Gemini LLM, short prompt, max 2 attempts."""
    print("\n[AGENT] ► Demand & Supply Agent (Gemini)")
    rl  = state.get("rl_action", 1)
    lbl = ["conservative", "balanced", "aggressive"][rl]

    # SHORT prompt — saves tokens
    prompt = f"""Demand Agent. RL={rl} ({lbl}).

Tools to call:
- get_plant_capacity_tool: PLANT_001,PLANT_002,PLANT_003,PLANT_004,PLANT_005,PLANT_006
- get_supply_chain_status_tool: coal,gas,nuclear,solar
- get_regional_demand_forecast_tool: "North Zone","West Zone","South Zone"

Return ONLY JSON array:
[{{"plant_id":"PLANT_001","action":"increase","reason":"...","recommended_output_mw":450}},
 {{"plant_id":"PLANT_002","action":"maintain","reason":"...","recommended_output_mw":273}},
 {{"plant_id":"PLANT_003","action":"maintain","reason":"...","recommended_output_mw":520}},
 {{"plant_id":"PLANT_004","action":"maintain","reason":"...","recommended_output_mw":110}},
 {{"plant_id":"PLANT_005","action":"decrease","reason":"...","recommended_output_mw":300}},
 {{"plant_id":"PLANT_006","action":"increase","reason":"...","recommended_output_mw":90}}]"""

    out = _run_gemini_agent(DEMAND_SUPPLY_TOOLS, prompt, "demand_agent", max_attempts=2)
    print(f"[AGENT] Demand done ({len(out)} chars)")
    return {"demand_decisions": _extract_json(out), "messages": []}


def health_agent_node(state: PowerGridState) -> dict:
    """Health agent — pure Python, zero API calls."""
    print("\n[AGENT] ► Health Tracker (pure Python)")

    try:
        from tools.health_tools import (
            get_all_plants_health_tool,
            calculate_health_score_tool,
            schedule_maintenance_tool,
        )

        all_health          = get_all_plants_health_tool.invoke({})
        plant_scores        = []
        maintenance_actions = []

        for plant in all_health:
            plant_id     = plant["plant_id"]
            score_result = calculate_health_score_tool.invoke({"plant_id": plant_id})
            health_score = score_result.get("health_score", 50)
            risk_level   = score_result.get("risk_level", "medium")

            plant_scores.append({
                "plant_id":           plant_id,
                "health_score":       health_score,
                "risk_level":         risk_level,
                "maintenance_status": plant.get("maintenance_status", "ok"),
                "fault_count":        plant.get("fault_count", 0),
            })

            if health_score < 40:
                date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                schedule_maintenance_tool.invoke({
                    "plant_id": plant_id, "maintenance_type": "emergency", "date": date
                })
                maintenance_actions.append({"plant_id": plant_id, "action": "emergency", "date": date})
                print(f"[HEALTH] {plant_id} EMERGENCY → {date}")
            elif health_score < 60:
                date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                schedule_maintenance_tool.invoke({
                    "plant_id": plant_id, "maintenance_type": "routine", "date": date
                })
                maintenance_actions.append({"plant_id": plant_id, "action": "routine", "date": date})
                print(f"[HEALTH] {plant_id} routine → {date}")
            else:
                print(f"[HEALTH] {plant_id} ok score={health_score}")

        report = json.dumps({"plant_scores": plant_scores, "maintenance_actions": maintenance_actions})
        print(f"[AGENT] Health done — {len(plant_scores)} plants, {len(maintenance_actions)} actions")
        return {"health_report": report, "messages": []}

    except Exception as e:
        print(f"[HEALTH ERROR] {e}")
        return {"health_report": json.dumps({"error": str(e)}), "messages": []}


def transmission_agent_node(state: PowerGridState) -> dict:
    """Transmission agent — pure Python, zero API calls."""
    print("\n[AGENT] ► Transmission Line Agent (pure Python)")

    try:
        from tools.transmission_tools import (
            get_all_transmission_lines_tool,
            calculate_transmission_loss_tool,
            get_line_distance_consumption_ratio_tool,
            flag_line_for_inspection_tool,
        )

        all_lines     = get_all_transmission_lines_tool.invoke({})
        line_scores   = []
        flagged_lines = []

        for line in all_lines:
            line_id      = line["line_id"]
            loss_result  = calculate_transmission_loss_tool.invoke({"line_id": line_id})
            efficiency   = loss_result.get("efficiency_score", 0)
            loss_pct     = loss_result.get("loss_percent", 0)
            ratio_result = get_line_distance_consumption_ratio_tool.invoke({"line_id": line_id})

            line_scores.append({
                "line_id":          line_id,
                "efficiency_score": efficiency,
                "power_loss_mw":    loss_result.get("power_loss_mw", 0),
                "loss_percent":     loss_pct,
                "status":           loss_result.get("status", "unknown"),
                "from_plant":       line.get("from_plant", ""),
                "to_zone":          line.get("to_zone", ""),
                "mw_per_km":        ratio_result.get("mw_per_km_ratio", 0),
            })

            if efficiency < 75 or loss_pct > 12:
                reason = f"efficiency={efficiency}% loss={loss_pct}%"
                flag_line_for_inspection_tool.invoke({"line_id": line_id, "reason": reason})
                flagged_lines.append(line_id)
                print(f"[TX] {line_id} FLAGGED → {reason}")
            else:
                print(f"[TX] {line_id} ok efficiency={efficiency}%")

        report = json.dumps({"line_scores": line_scores, "flagged_lines": flagged_lines})
        print(f"[AGENT] Transmission done — {len(line_scores)} lines, {len(flagged_lines)} flagged")
        return {"transmission_report": report, "messages": []}

    except Exception as e:
        print(f"[TX ERROR] {e}")
        return {"transmission_report": json.dumps({"error": str(e)}), "messages": []}


def orchestrator_node(state: PowerGridState) -> dict:
    """
    Orchestrator — tries Groq first (separate quota!), falls back to pure Python.
    Never touches Gemini keys so demand agent always has keys available.
    """
    print("\n[ORCHESTRATOR] ► Main Orchestrator")

    rl  = state.get("rl_action", 1)
    lbl = ["conservative", "balanced", "aggressive"][rl]
    d   = (state.get("demand_decisions")    or "[]")[:150]
    h   = (state.get("health_report")       or "{}")[:150]
    t   = (state.get("transmission_report") or "{}")[:150]

    rl_reward        = None
    next_observation = None

    # Try Groq first (separate quota — doesn't touch Gemini keys!)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        prompt = f"""Orchestrator. RL={rl} ({lbl}).
DEMAND:{d}
HEALTH:{h}
TX:{t}

Call: compute_reward_tool(), compute_next_state_tool()

Return ONLY JSON:
{{"rl_reward":2.5,"next_observation":[0.72,0.84,0.76,0.28,0.70,0.51],"summary":"..."}}"""

        out     = _run_groq_agent(ORCHESTRATOR_TOOLS, prompt, "orchestrator")
        cleaned = _extract_json(out)

        try:
            p                = json.loads(cleaned)
            rl_reward        = float(p.get("rl_reward", 0.0))
            next_observation = p.get("next_observation")
            if not next_observation or len(next_observation) != 6:
                next_observation = None
            if rl_reward:
                print(f"[ORCHESTRATOR] Groq reward={rl_reward}")
        except Exception:
            print("[ORCHESTRATOR] Groq parse failed → pure Python fallback")
    else:
        print("[ORCHESTRATOR] No GROQ_API_KEY → pure Python fallback")
        out = "{}"

    # Pure Python fallback — always works, reads from database
    if rl_reward is None or next_observation is None:
        try:
            from tools.orchestrator_tools import compute_reward_tool, compute_next_state_tool

            r                = compute_reward_tool.invoke({})
            rl_reward        = float(r.get("reward", 1.0))
            n                = compute_next_state_tool.invoke({})
            next_observation = n.get("next_observation", [0.72, 0.83, 0.76, 0.28, 0.70, 0.51])
            print(f"[ORCHESTRATOR] Python fallback reward={rl_reward} obs={next_observation}")
        except Exception as fe:
            print(f"[ORCHESTRATOR] Python fallback error: {fe}")
            rl_reward        = 1.0
            next_observation = [0.72, 0.83, 0.76, 0.28, 0.70, 0.51]

    final = json.dumps({
        "rl_reward":        rl_reward,
        "next_observation": next_observation,
        "rl_action":        rl,
        "rl_action_label":  lbl,
    })

    print(f"[ORCHESTRATOR] done reward={rl_reward}")
    return {
        "unified_report":   {"summary": final},
        "final_decisions":  final,
        "rl_reward":        rl_reward,
        "next_observation": next_observation,
        "messages":         [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(PowerGridState)
    g.add_node("demand_agent",         demand_agent_node)
    g.add_node("health_agent",         health_agent_node)
    g.add_node("transmission_agent",   transmission_agent_node)
    g.add_node("orchestrator_collect", orchestrator_node)

    g.add_edge(START,                  "demand_agent")
    g.add_edge("demand_agent",         "health_agent")
    g.add_edge("health_agent",         "transmission_agent")
    g.add_edge("transmission_agent",   "orchestrator_collect")
    g.add_edge("orchestrator_collect", END)

    return g.compile()


POWER_GRID_GRAPH = build_graph()