"""
crisis_tool.py — Crisis Detection Tool

Searches for human or natural crises that affect power supply:
strikes, accidents, conflicts, floods, earthquakes near plants.
"""

from tools.search_tool import tavily_search


def get_crisis_signal() -> dict:
    """
    Search for active crises affecting India's energy supply.

    Returns:
        {
          "score": float (0-1),
          "label": str,
          "events": list[str],
          "summary": str,
          "source": "live" or "default"
        }
    """
    texts = tavily_search(
        "India power plant outage coal shortage electricity crisis strike accident today 2025",
        max_results=3
    )

    if not texts:
        return {
            "score": 0.2, "label": "GOOD",
            "events": [], "summary": "No live crisis data", "source": "default"
        }

    combined = " ".join(texts).lower()

    # Detect crisis keywords by severity
    worst_kw = ["explosion", "attack", "war", "earthquake", "tsunami", "grid collapse"]
    bad_kw   = ["strike", "outage", "shutdown", "fire", "accident", "shortage", "disruption"]
    mild_kw  = ["delay", "maintenance", "reduced", "warning"]

    events_found = []
    score = 0.2  # default: good

    for kw in worst_kw:
        if kw in combined:
            score = max(score, 1.0)
            events_found.append(kw)

    for kw in bad_kw:
        if kw in combined:
            score = max(score, 0.75)
            events_found.append(kw)

    for kw in mild_kw:
        if kw in combined:
            score = max(score, 0.5)
            events_found.append(kw)

    if score >= 0.9:   label = "WORST"
    elif score >= 0.65: label = "BAD"
    elif score >= 0.4:  label = "NORMAL"
    elif score >= 0.15: label = "GOOD"
    else:               label = "BEST"

    summary = texts[0][:120] if texts else "Crisis check complete"

    return {
        "score": round(score, 3),
        "label": label,
        "events": events_found[:5],
        "summary": summary,
        "source": "live"
    }