"""
weather_tool.py — Live Weather Tool

Fetches weather conditions near Indian power grid infrastructure.
Returns a structured dict with a 0-1 severity score for the agent.

Score scale (same across all tools):
  0.0 = best   0.25 = good   0.5 = normal   0.75 = bad   1.0 = worst
"""

import re
from tools.search_tool import tavily_search


def get_weather_signal() -> dict:
    """
    Search for weather warnings affecting India's power grid.

    Returns:
        {
          "score": float (0-1),
          "label": str ("BEST" / "GOOD" / "NORMAL" / "BAD" / "WORST"),
          "summary": str,
          "source": "live" or "default"
        }
    """
    texts = tavily_search(
        "India weather warning cyclone storm heat wave flood power grid today",
        max_results=3
    )

    if not texts:
        return {"score": 0.4, "label": "NORMAL", "summary": "No live data", "source": "default"}

    combined = " ".join(texts).lower()

    # Score based on keywords found
    if any(w in combined for w in ["cyclone", "hurricane", "severe flood", "extreme heat wave"]):
        score, label = 1.0, "WORST"
    elif any(w in combined for w in ["storm", "flood", "heat wave", "heavy rain"]):
        score, label = 0.75, "BAD"
    elif any(w in combined for w in ["warning", "alert", "rain", "wind"]):
        score, label = 0.5, "NORMAL"
    elif any(w in combined for w in ["clear", "sunny", "mild"]):
        score, label = 0.25, "GOOD"
    else:
        score, label = 0.4, "NORMAL"

    # Extract a short summary sentence
    summary = texts[0][:120] if texts else "Weather data fetched"

    return {
        "score": score,
        "label": label,
        "summary": summary,
        "source": "live"
    }