"""
agent/flow.py — GridMind Multi-Agent LangGraph Flow

9-agent pipeline wired into a compiled StateGraph:

  [location_agent]   → geocodes city, ranks 10 plants by distance
         ↓
  [sensor_agent]     → fetches weather / commodity / crisis signals
         ↓
  [demand_agent]     → forecasts real-time grid demand (MW)
         ↓
  [supply_agent]     → audits current plant output, computes headroom
         ↓
  [decision_agent]   → Gemini AI or rule-based fallback → plant decisions
         ↓
  [conditional edge] → skip apply_agent if all plants holding
         ↓
  [apply_agent]      → enforces MW limits, mutates plant outputs
         ↓
  [memory_agent]     → persists signals + decisions to SQLite
         ↓
  [report_agent]     → builds the output dict (used by API + CLI)
         ↓
        END
"""

import random
import textwrap
from typing import TypedDict

from langgraph.graph import StateGraph, END

from tools.weather_tool   import get_weather_signal
from tools.commodity_tool import get_commodity_signal
from tools.crisis_tool    import get_crisis_signal
from tools.distance_tool  import get_plant_distances
from agent.grid_agent     import make_grid_decision
from core.memory          import GridMemory
from core.config          import POWER_PLANTS, PLANT_BY_NAME


# ── Typed State ────────────────────────────────────────────────────────────────

class GridState(TypedDict):
    city:              str
    lat:               float
    lon:               float

    # demand agent output
    demand_mw:         float
    demand_breakdown:  dict   # {base, weather_adj, noise, final}

    # supply agent output
    total_supply_mw:   float
    supply_breakdown:  dict   # per-type totals + headroom per plant
    balance_mw:        float

    plants:            list   # enriched: distance + current_mw + headroom
    signals:           dict   # {weather, commodity, crisis}

    # decision agent output
    decisions:         list
    decision_summary:  str
    decision_analysis: str
    applied_changes:   list
    agent_source:      str

    route:             str    # conditional edge signal
    report:            dict  # built by report_agent, consumed by FastAPI
    user_context:      str   # raw user message / extra context from /chat
    urgency:           str   # low | normal | high | critical


# ── Agent 1: Location Agent ────────────────────────────────────────────────────

def location_agent(state: GridState) -> dict:
    """
    Geocodes the city (3-tier: local dict → Nominatim → Tavily → Delhi default).
    Ranks all 10 plants by haversine distance. Scales their starting output to
    a realistic ~65 MW total so demand/supply math starts meaningful.
    """
    result    = get_plant_distances(state["city"])
    raw_total = sum(p["current_mw"] for p in result["plants"])
    scale     = 65.0 / raw_total if raw_total > 0 else 1.0
    for p in result["plants"]:
        p["current_mw"] = round(p["current_mw"] * scale, 1)

    if not result["found"]:
        print(f"[LocationAgent] '{state['city']}' not found — defaulting to Delhi")
    else:
        n = result["nearest"]
        print(f"[LocationAgent] {result['city']} ({result['geocode_source']}) "
              f"→ nearest: {n['name']} ({n['distance_km']:.0f} km)")

    return {"lat": result["lat"], "lon": result["lon"], "plants": result["plants"]}


# ── Agent 2: Sensor Agent ──────────────────────────────────────────────────────

def sensor_agent(state: GridState) -> dict:
    """
    Fetches three live signals via Tavily search (falls back to safe defaults
    if the API key is missing). Each signal returns a 0–1 severity score.
      0.0 = best conditions   1.0 = worst / crisis
    """
    print("[SensorAgent] Fetching live signals...")
    wx  = get_weather_signal()
    com = get_commodity_signal()
    cr  = get_crisis_signal()
    src = "live" if wx["source"] == "live" else "default"
    print(f"[SensorAgent] Weather={wx['label']} | Commodity={com['label']} | Crisis={cr['label']} [{src}]")
    return {"signals": {"weather": wx, "commodity": com, "crisis": cr}}


# ── Agent 3: Demand Agent ──────────────────────────────────────────────────────

def demand_agent(state: GridState) -> dict:
    """
    Dedicated demand forecasting agent.

    Models three components:
      base        — 70 MW baseline (average Indian city distribution load)
      weather_adj — bad weather (high score) pushes demand up (cooling/heating)
      noise       — ±3 MW Gaussian noise (simulates metering uncertainty)

    In production this node would call a SCADA API or load-forecasting model.
    Returns a full breakdown so the API can expose each component separately.
    """
    wx_score   = state["signals"].get("weather", {}).get("score", 0.4)
    base       = 70.0
    weather_adj = round((wx_score - 0.4) * 20, 2)   # -8 to +12 MW range
    noise      = round(random.gauss(0, 3), 2)
    final      = round(max(50, min(110, base + weather_adj + noise)), 1)

    breakdown = {
        "base_mw":        base,
        "weather_adj_mw": weather_adj,
        "noise_mw":       noise,
        "final_mw":       final,
    }

    print(f"[DemandAgent] Base={base}MW  WeatherAdj={weather_adj:+.1f}MW  "
          f"Noise={noise:+.1f}MW  →  Demand={final}MW")

    return {"demand_mw": final, "demand_breakdown": breakdown}


# ── Agent 4: Supply Agent ──────────────────────────────────────────────────────

def supply_agent(state: GridState) -> dict:
    """
    Dedicated supply auditing agent.

    For every plant it computes:
      current_mw   — how much it's generating right now
      max_mw       — rated capacity
      headroom_mw  — how much more it CAN produce (max - current)
      min_floor_mw — minimum it must stay above (nuclear=15, others=0)

    Aggregates by plant type so the decision agent sees coal/solar/hydro/
    wind/nuclear totals at a glance. Also calculates balance before decisions.
    """
    plants  = state["plants"]
    demand  = state["demand_mw"]

    # Annotate each plant with headroom
    for p in plants:
        cfg           = PLANT_BY_NAME.get(p["name"], {})
        min_floor     = 15.0 if cfg.get("type") == "nuclear" else 0.0
        p["headroom_mw"]  = round(p["max_mw"] - p["current_mw"], 1)
        p["min_floor_mw"] = min_floor

    total   = round(sum(p["current_mw"] for p in plants), 1)
    balance = round(total - demand, 1)

    # Per-type breakdown
    type_totals: dict = {}
    for p in plants:
        t = p["type"]
        if t not in type_totals:
            type_totals[t] = {"current_mw": 0.0, "max_mw": 0.0, "headroom_mw": 0.0, "count": 0}
        type_totals[t]["current_mw"]  += p["current_mw"]
        type_totals[t]["max_mw"]      += p["max_mw"]
        type_totals[t]["headroom_mw"] += p["headroom_mw"]
        type_totals[t]["count"]       += 1

    supply_breakdown = {
        "total_mw":    total,
        "balance_mw":  balance,
        "by_type":     type_totals,
        "plant_count": len(plants),
    }

    status = "SURPLUS" if balance > 5 else ("DEFICIT" if balance < -5 else "BALANCED")
    print(f"[SupplyAgent] Supply={total}MW  Demand={demand}MW  "
          f"Balance={balance:+.1f}MW  [{status}]")

    return {
        "plants":           plants,
        "total_supply_mw":  total,
        "balance_mw":       balance,
        "supply_breakdown": supply_breakdown,
        "route":            "needs_action" if abs(balance) > 5 else "balanced",
    }


# ── Agent 5: Decision Agent ────────────────────────────────────────────────────

def decision_agent(state: GridState, memory: GridMemory) -> dict:
    """
    Brain of the system. Sends full grid context to Gemini including any
    user-provided natural language context and urgency level from /chat.
    Falls back to deterministic rule engine if Gemini key is missing.
    """
    print("[DecisionAgent] Thinking...")
    ctx = state.get("user_context", "")
    if ctx:
        print("[DecisionAgent] User context: " + ctx[:80])
        print("[DecisionAgent] Urgency: " + state.get("urgency", "normal"))
    memory_text = memory.format_for_agent(n=3)
    result      = make_grid_decision(state, memory_text)
    src = "Gemini" if result.get("source") == "live" else "Fallback"
    print("[DecisionAgent] " + src + ": " + result.get("summary", "")[:80])
    return {
        "decisions":         result.get("decisions", []),
        "decision_summary":  result.get("summary", ""),
        "decision_analysis": result.get("analysis", ""),
        "agent_source":      result.get("source", "fallback"),
    }


# ── Conditional Router ─────────────────────────────────────────────────────────

def should_apply(state: GridState) -> str:
    """Skip apply_agent entirely if all decisions are hold."""
    if not state.get("decisions") or all(
        d.get("action") == "hold" for d in state.get("decisions", [])
    ):
        print("[Router] All hold — skipping apply_agent")
        return "skip_apply"
    return "apply"


# ── Agent 6: Apply Agent ───────────────────────────────────────────────────────

def apply_agent(state: GridState) -> dict:
    """
    Enforces decision agent instructions on real plant MW values.
    Respects per-plant limits: nuclear ≥ 15 MW, others ≥ 0 MW, all ≤ max_mw.
    Recalculates total supply and balance after all mutations.
    """
    changes   = []
    plant_map = {p["name"]: p for p in state["plants"]}

    for dec in state["decisions"]:
        pname  = dec.get("plant", "")
        action = dec.get("action", "hold")
        amount = float(dec.get("amount_mw", 3.0))
        if pname not in plant_map:
            continue

        plant     = plant_map[pname]
        cfg       = PLANT_BY_NAME.get(pname, {})
        before    = plant["current_mw"]
        min_floor = 15.0 if cfg.get("type") == "nuclear" else 0.0

        if action == "increase":
            after = min(before + amount, plant["max_mw"])
        elif action == "decrease":
            after = max(before - amount, min_floor)
        else:
            after = before

        after = round(after, 1)
        plant["current_mw"]  = after
        plant["headroom_mw"] = round(plant["max_mw"] - after, 1)

        changes.append({
            "plant":   pname,
            "type":    cfg.get("type", "?"),
            "before":  before,
            "after":   after,
            "delta":   round(after - before, 1),
            "dist_km": plant.get("distance_km", 0),
            "reason":  dec.get("reason", ""),
        })

    total = round(sum(p["current_mw"] for p in state["plants"]), 1)
    bal   = round(total - state["demand_mw"], 1)

    return {
        "plants":          list(plant_map.values()),
        "total_supply_mw": total,
        "balance_mw":      bal,
        "applied_changes": changes,
    }


# ── Agent 7: Memory Agent ──────────────────────────────────────────────────────

def memory_agent(state: GridState, memory: GridMemory) -> dict:
    """Persists signals + decision to SQLite for future agent context."""
    signals = state["signals"]
    memory.add({
        "type":             "signal",
        "weather_label":    signals.get("weather",   {}).get("label", "?"),
        "crisis_label":     signals.get("crisis",    {}).get("label", "?"),
        "commodity_label":  signals.get("commodity", {}).get("label", "?"),
    })
    memory.add({
        "type":          "decision",
        "city":          state["city"],
        "demand_mw":     state["demand_mw"],
        "supply_after":  state["total_supply_mw"],
        "balance_after": state["balance_mw"],
        "summary":       state["decision_summary"],
        "agent_source":  state["agent_source"],
    })
    memory.save()
    print(f"[MemoryAgent] Saved → balance={state['balance_mw']:+.1f}MW")
    return {}


# ── Agent 8: Report Agent ──────────────────────────────────────────────────────

def report_agent(state: GridState) -> dict:
    """
    Builds a structured report dict — used by both the CLI printer
    and the FastAPI response serializer.
    Also prints the terminal report.
    """
    signals  = state["signals"]
    wx       = signals.get("weather",   {})
    cr       = signals.get("crisis",    {})
    com      = signals.get("commodity", {})
    bal      = state["balance_mw"]
    bal_icon = "✅" if abs(bal) <= 5 else ("⚠️" if abs(bal) <= 15 else "🔴")
    src_tag  = "Gemini AI" if state["agent_source"] == "live" else "Rule-Based Fallback"
    W        = 66

    def box(text):
        return "\n".join(f"  {l}" for l in textwrap.wrap(text, W - 4))

    def bar(score):
        f = int(score * 10)
        return "█" * f + "░" * (10 - f)

    def sig_label(label):
        return {"BEST": "excellent", "GOOD": "favourable", "NORMAL": "average",
                "BAD": "elevated", "WORST": "critical"}.get(label, "")

    # ── Terminal print ────────────────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  GridMind AI  —  Power Grid Decision Report")
    print(f"{'═'*W}")

    print(f"\n  📍 CITY & GRID STATUS")
    print(f"  {'─'*62}")
    print(f"  City         : {state['city']}")
    print(f"  Grid Demand  : {state['demand_mw']} MW")
    print(f"  Grid Supply  : {state['total_supply_mw']} MW")
    print(f"  Balance      : {bal:+.1f} MW  {bal_icon}")
    status = "Surplus" if bal > 5 else ("Deficit" if bal < -5 else "Balanced ✓")
    print(f"  Status       : {status}")

    db = state.get("demand_breakdown", {})
    sb = state.get("supply_breakdown", {})
    if db:
        print(f"\n  📈 DEMAND BREAKDOWN")
        print(f"  {'─'*62}")
        print(f"  Base load    : {db.get('base_mw', 0)} MW")
        print(f"  Weather adj  : {db.get('weather_adj_mw', 0):+.1f} MW")
        print(f"  Noise        : {db.get('noise_mw', 0):+.1f} MW")
        print(f"  Final demand : {db.get('final_mw', 0)} MW")

    if sb and sb.get("by_type"):
        print(f"\n  ⚡ SUPPLY BREAKDOWN BY TYPE")
        print(f"  {'─'*62}")
        for ptype, vals in sb["by_type"].items():
            print(f"  {ptype:<8}  {vals['current_mw']:>6.1f} / {vals['max_mw']:.0f} MW  "
                  f"(headroom {vals['headroom_mw']:.1f} MW, {vals['count']} plant{'s' if vals['count']>1 else ''})")

    print(f"\n  📡 LIVE SIGNALS")
    print(f"  {'─'*62}")
    for lbl, sig in [("Weather", wx), ("Crisis", cr), ("Commodity", com)]:
        sc = sig.get("score", 0.0)
        print(f"  {lbl:<10} [{bar(sc)}] {sc:.2f}  {sig.get('label','?')}  — {sig_label(sig.get('label',''))}")

    print(f"\n  🏭 NEAREST PLANTS TO {state['city'].upper()}")
    print(f"  {'─'*62}")
    print(f"  {'Plant':<28} {'Type':<8} {'Dist':>6}  {'MW':>10}  {'Head':>6}")
    for p in state.get("plants", [])[:5]:
        curr = p.get("current_mw", 0)
        mx   = p.get("max_mw", 0)
        head = p.get("headroom_mw", 0)
        b    = ("█" * int(curr / mx * 8) + "░" * (8 - int(curr / mx * 8))) if mx else "░"*8
        print(f"  {p['name']:<28} {p['type']:<8} {p['distance_km']:>5.0f}km  {b} {curr}/{mx}  +{head}")

    print(f"\n  🧠 AGENT DECISIONS  [{src_tag}]")
    print(f"  {'─'*62}")
    for i, ch in enumerate(state.get("applied_changes", []), 1):
        delta = ch.get("delta", 0)
        sym   = "↑ INCREASE" if delta > 0 else ("↓ DECREASE" if delta < 0 else "→ HOLD")
        print(f"\n  {i}. {sym}  —  {ch['plant']}")
        print(f"     {ch['type']} | {ch['dist_km']:.0f} km | {ch['before']}→{ch['after']} MW ({delta:+.1f})")
        expl = next((d.get("explanation", d.get("reason",""))
                     for d in state.get("decisions",[]) if d.get("plant") == ch["plant"]), "")
        if expl:
            print(f"\n  Why:\n{box(expl)}")

    if state.get("decision_analysis"):
        print(f"\n  📊 ANALYSIS\n  {'─'*62}")
        print(box(state["decision_analysis"]))

    print(f"\n  ✅ SUMMARY\n  {'─'*62}")
    print(box(state.get("decision_summary", "")))
    print(f"\n{'═'*W}\n")

    # ── Structured dict returned into state (consumed by FastAPI) ─────────
    return {
        "report": {
            "city":             state["city"],
            "demand_mw":        state["demand_mw"],
            "supply_mw":        state["total_supply_mw"],
            "balance_mw":       bal,
            "status":           status,
            "agent_source":     state["agent_source"],
            "demand_breakdown": state.get("demand_breakdown", {}),
            "supply_breakdown": state.get("supply_breakdown", {}),
            "signals": {
                "weather":   {"score": wx.get("score"), "label": wx.get("label")},
                "crisis":    {"score": cr.get("score"), "label": cr.get("label")},
                "commodity": {"score": com.get("score"), "label": com.get("label")},
            },
            "plants": [
                {
                    "name":       p["name"],
                    "type":       p["type"],
                    "distance_km":p["distance_km"],
                    "current_mw": p["current_mw"],
                    "max_mw":     p["max_mw"],
                    "headroom_mw":p.get("headroom_mw", 0),
                    "cost":       p["cost_per_unit"],
                }
                for p in state.get("plants", [])
            ],
            "decisions": state.get("applied_changes", []),
            "summary":   state.get("decision_summary", ""),
            "analysis":  state.get("decision_analysis", ""),
        }
    }


# ── Build LangGraph ────────────────────────────────────────────────────────────

def build_graph(memory: GridMemory):
    graph = StateGraph(GridState)

    graph.add_node("location_agent", location_agent)
    graph.add_node("sensor_agent",   sensor_agent)
    graph.add_node("demand_agent",   demand_agent)
    graph.add_node("supply_agent",   supply_agent)
    graph.add_node("decision_agent", lambda s: decision_agent(s, memory))
    graph.add_node("apply_agent",    apply_agent)
    graph.add_node("memory_agent",   lambda s: memory_agent(s, memory))
    graph.add_node("report_agent",   report_agent)

    graph.set_entry_point("location_agent")
    graph.add_edge("location_agent", "sensor_agent")
    graph.add_edge("sensor_agent",   "demand_agent")
    graph.add_edge("demand_agent",   "supply_agent")
    graph.add_edge("supply_agent",   "decision_agent")

    graph.add_conditional_edges(
        "decision_agent", should_apply,
        {"apply": "apply_agent", "skip_apply": "memory_agent"}
    )

    graph.add_edge("apply_agent",  "memory_agent")
    graph.add_edge("memory_agent", "report_agent")
    graph.add_edge("report_agent", END)

    return graph.compile()


# ── Public Interface ───────────────────────────────────────────────────────────

class GridMindGraph:
    def __init__(self):
        self.memory = GridMemory()
        self._graph = build_graph(self.memory)

    def run(self, city: str = "Delhi", user_context: str = "", urgency: str = "normal") -> dict:
        initial: GridState = {
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
        return self._graph.invoke(initial)