"""
agents/grid_agent.py — GridMind Decision Agent (Gemini)

This is the brain of the system.

What it does:
  - Receives the current grid state (demand, supply, signals, distances)
  - Reads recent memory (past decisions)
  - Calls Gemini API with all context
  - Returns a structured list of plant-wise decisions

NO reinforcement learning. The agent reasons in natural language
and returns JSON decisions directly.

Gemini model: gemini-2.0-flash (fast, cheap, good reasoning)
"""

import json
import re
import urllib.request
from core.config import get_gemini_key, POWER_PLANTS


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def call_gemini(prompt: str, system: str = "") -> str:
    """
    Call Gemini API. Returns the text response string.
    Returns empty string on failure.
    """
    key = get_gemini_key()
    if not key or key == "your-gemini-key-here":
        return ""

    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"[SYSTEM]: {system}"}]})
        contents.append({"role": "model", "parts": [{"text": "Understood."}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = json.dumps({
        "contents": contents,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800,
        }
    }).encode()

    try:
        req = urllib.request.Request(
            f"{GEMINI_URL}?key={key}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except Exception as e:
        print(f"[Agent] Gemini call failed: {e}")
        return ""


def make_grid_decision(state: dict, memory_text: str) -> dict:
    """
    Ask Gemini to decide how to adjust plant outputs.

    Args:
        state: Full grid state dict (demand, supply, signals, plants, distances)
        memory_text: Recent decisions from GridMemory.format_for_agent()

    Returns:
        {
          "decisions": [
            {"plant": str, "action": "increase"|"decrease"|"hold", "amount_mw": float, "reason": str},
            ...
          ],
          "summary": str,    # one-line human summary
          "source": "live" | "fallback"
        }
    """

    system_prompt = """You are GridMind, an AI power grid controller for India.
You control 10 real power plants. Your job:
  1. Read current grid demand vs supply
  2. Look at live signals (weather, crisis, commodity prices) — each scored 0.0 (best) to 1.0 (worst)
  3. Look at plant distances — prefer nearby cheaper plants
  4. Use past decisions from memory to avoid repeating mistakes
  5. Decide which plants to increase, decrease, or hold

RULES:
  - Keep total supply close to total demand (within 5 MW ideally)
  - When commodity score is BAD/WORST → prefer solar/hydro/nuclear over coal
  - When crisis score is BAD/WORST → increase reserve (supply slightly > demand)
  - When weather score is BAD/WORST → account for reduced solar/wind output
  - Nuclear: never go below 15 MW (baseload requirement)
  - Solar/Wind: can reduce to 0 (weather-dependent)

Return ONLY valid JSON, no markdown, no extra text:
{
  "decisions": [
    {
      "plant": "<exact plant name>",
      "action": "increase|decrease|hold",
      "amount_mw": <number>,
      "reason": "<why this plant, why this action>",
      "explanation": "<plain English explanation a non-expert can understand>"
    }
  ],
  "summary": "<one sentence explaining the overall strategy>",
  "analysis": "<2-3 sentences: what the signals mean, why these plants were chosen, what outcome is expected>"
}"""

    # Build readable signal summary
    signals = state.get("signals", {})
    wx  = signals.get("weather",   {})
    cr  = signals.get("crisis",    {})
    com = signals.get("commodity", {})

    # Build plant table for the prompt
    plant_lines = []
    for p in state.get("plants", []):
        dist = p.get("distance_km", "?")
        plant_lines.append(
            f"  {p['name']:<28} type={p['type']:<7} "
            f"current={p['current_mw']}MW max={p['max_mw']}MW "
            f"cost=₹{p['cost_per_unit']}/kWh dist={dist}km"
        )

    # Include user context and urgency if provided
    user_ctx = state.get("user_context", "")
    urgency  = state.get("urgency", "normal")
    ctx_line = f"\n  User Report   : {user_ctx}  [urgency={urgency}]" if user_ctx else ""

    prompt = f"""CURRENT GRID STATE:
  City          : {state.get('city', 'Unknown')}{ctx_line}
  Demand        : {state.get('demand_mw', 70)} MW
  Total Supply  : {state.get('total_supply_mw', 65)} MW
  Balance       : {state.get('balance_mw', -5):+.1f} MW (positive=surplus, negative=deficit)

LIVE SIGNALS (0=best, 1=worst):
  Weather   : {wx.get('score', 0.4):.2f} [{wx.get('label', 'NORMAL')}]  — {wx.get('summary', '')[:80]}
  Crisis    : {cr.get('score', 0.2):.2f} [{cr.get('label', 'GOOD')}]   — {cr.get('summary', '')[:80]}
  Commodity : {com.get('score', 0.5):.2f} [{com.get('label', 'NORMAL')}] — {com.get('summary', '')[:80]}

PLANTS (sorted by distance from {state.get('city', 'city')}):
{chr(10).join(plant_lines)}

RECENT MEMORY (past decisions):
{memory_text}

Based on all the above, decide how to adjust plant outputs to balance the grid efficiently.
"""

    raw = call_gemini(prompt, system=system_prompt)

    if not raw:
        return _fallback_decision(state)

    # Parse JSON from response
    try:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        match = re.search(r'\{.*\}', clean, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            parsed["source"] = "live"
            # ensure analysis field exists
            if "analysis" not in parsed:
                parsed["analysis"] = parsed.get("summary", "")
            return parsed
    except Exception as e:
        print(f"[Agent] JSON parse failed: {e}")

    return _fallback_decision(state)


def _fallback_decision(state: dict) -> dict:
    """
    Rule-based fallback when Gemini is unavailable.

    Simple logic:
      - If supply < demand → increase nearest cheap plant
      - If supply > demand → decrease most expensive distant plant
      - Otherwise → hold all
    """
    demand  = state.get("demand_mw", 70)
    supply  = state.get("total_supply_mw", 65)
    balance = supply - demand
    plants  = state.get("plants", [])

    decisions = []

    if balance < -5:
        candidates = [p for p in plants if p["type"] in ("hydro", "nuclear", "coal")
                      and p["current_mw"] < p["max_mw"]]
        candidates.sort(key=lambda x: (x["cost_per_unit"], x["distance_km"]))
        if candidates:
            best = candidates[0]
            decisions.append({
                "plant":       best["name"],
                "action":      "increase",
                "amount_mw":   min(3.0, best["max_mw"] - best["current_mw"]),
                "reason":      f"deficit of {abs(balance):.1f} MW — cheapest available plant selected",
                "explanation": (
                    f"The grid is short by {abs(balance):.1f} MW right now. That means consumers "
                    f"could experience voltage dips or outages if nothing changes. "
                    f"{best['name']} was chosen because it's the cheapest plant currently able to produce more "
                    f"(₹{best['cost_per_unit']}/kWh, {best.get('distance_km', '?'):.0f} km away). "
                    f"We're increasing its output by up to 3 MW to bring supply back in line with demand."
                ),
            })

    elif balance > 10:
        candidates = [p for p in plants if p["type"] == "coal" and p["current_mw"] > 4]
        candidates.sort(key=lambda x: (-x["cost_per_unit"], -x["distance_km"]))
        if candidates:
            worst = candidates[0]
            decisions.append({
                "plant":       worst["name"],
                "action":      "decrease",
                "amount_mw":   min(3.0, worst["current_mw"] - 4),
                "reason":      f"surplus of {balance:.1f} MW — cutting most expensive coal plant",
                "explanation": (
                    f"The grid is producing {balance:.1f} MW more than needed. "
                    f"Running excess capacity wastes fuel and money. "
                    f"{worst['name']} is the most expensive coal plant active right now "
                    f"(₹{worst['cost_per_unit']}/kWh), so we reduce its output by 3 MW. "
                    f"This saves cost without risking any supply shortfall."
                ),
            })

    if not decisions:
        decisions.append({
            "plant":       plants[0]["name"] if plants else "Vindhyachal STPS",
            "action":      "hold",
            "amount_mw":   0,
            "reason":      "grid is balanced — no change needed",
            "explanation": (
                f"Supply and demand are within {abs(balance):.1f} MW of each other — "
                f"well within the safe operating range. "
                f"No plant adjustments are needed this cycle. "
                f"All plants hold their current output to avoid unnecessary switching costs."
            ),
        })

    if balance < -5:
        analysis = (
            f"A deficit of {abs(balance):.1f} MW was detected — demand is outpacing supply. "
            f"The cheapest dispatchable plant was selected to cover the gap quickly. "
            f"No live signal data was available, so rule-based fallback logic was applied."
        )
    elif balance > 10:
        analysis = (
            f"A surplus of {balance:.1f} MW was detected — supply is well above demand. "
            f"The most expensive coal plant was dialled back to reduce operating costs. "
            f"No live signal data was available, so rule-based fallback logic was applied."
        )
    else:
        analysis = (
            f"The grid is balanced within {abs(balance):.1f} MW — normal operating range. "
            f"No plant changes are needed. All signals are at default levels. "
            f"Fallback rule-based logic was used (Gemini API not connected)."
        )

    return {
        "decisions": decisions,
        "summary":   (
            f"Grid balance {balance:+.1f} MW — "
            + ("deficit covered by cheapest plant" if balance < -5
               else "surplus reduced by cutting expensive coal" if balance > 10
               else "balanced, all plants holding")
        ),
        "analysis":  analysis,
        "source":    "fallback",
    }


# ── Natural Language Intent Parser ────────────────────────────────────────────

def parse_user_intent(message: str) -> dict:
    """
    Uses Gemini to parse a free-text user message into structured intent.

    Extracts:
      city        — Indian city mentioned (or "Delhi" as default)
      context     — what the user is telling us (weather, crisis, price info)
      urgency     — "low" | "normal" | "high" | "critical"
      intent_type — "grid_check" | "crisis_report" | "price_alert" | "general_query"
      clean_query — rephrased as a clear operator instruction

    Falls back to safe defaults if Gemini is unavailable.
    """
    key = get_gemini_key()

    # ── Fallback: rule-based parser ──────────────────────────────────────────
    if not key or key == "your-gemini-key-here":
        return _rule_based_intent(message)

    system = """You are a power grid operator assistant for India.
Parse the user message and return ONLY valid JSON, no markdown, no extra text:
{
  "city":        "<Indian city name, default Delhi if none mentioned>",
  "context":     "<what the user is reporting — weather, prices, crisis, etc.>",
  "urgency":     "<low | normal | high | critical>",
  "intent_type": "<grid_check | crisis_report | price_alert | general_query>",
  "clean_query": "<rephrase as a clear one-line grid operator instruction>"
}

Rules:
- If message mentions flood/cyclone/earthquake/blackout → urgency=critical
- If message mentions storm/strike/outage/shortage      → urgency=high
- If message mentions price/cost/expensive              → urgency=normal, intent_type=price_alert
- If message is just a city name or casual check        → urgency=low, intent_type=grid_check
- Always extract a real Indian city if mentioned"""

    raw = call_gemini(message, system=system)

    if raw:
        try:
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass

    return _rule_based_intent(message)


def _rule_based_intent(message: str) -> dict:
    """Fallback intent parser — no Gemini needed."""
    import re as _re
    from core.config import CITIES

    msg_lower = message.lower()

    # Extract city from message
    city = "Delhi"
    for c in CITIES:
        if c in msg_lower:
            city = c.title()
            break

    # Detect urgency
    if any(w in msg_lower for w in ["cyclone", "flood", "earthquake", "blackout", "collapse"]):
        urgency, intent_type = "critical", "crisis_report"
    elif any(w in msg_lower for w in ["storm", "outage", "strike", "shortage", "fire"]):
        urgency, intent_type = "high", "crisis_report"
    elif any(w in msg_lower for w in ["price", "cost", "expensive", "coal", "gas"]):
        urgency, intent_type = "normal", "price_alert"
    elif any(w in msg_lower for w in ["rain", "heat", "cold", "wind"]):
        urgency, intent_type = "normal", "grid_check"
    else:
        urgency, intent_type = "low", "grid_check"

    return {
        "city":        city,
        "context":     message,
        "urgency":     urgency,
        "intent_type": intent_type,
        "clean_query": f"Check grid status for {city}. User reported: {message}",
    }