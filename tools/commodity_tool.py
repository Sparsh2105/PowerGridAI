"""
commodity_tool.py — Live Commodity Price Tool

Fetches coal, gas, oil prices via Tavily search.
Converts to a 0-1 cost pressure score for the agent.
"""

import re
from tools.search_tool import tavily_search


def _extract_price(texts: list[str], keywords: list[str], default: float) -> float:
    """Find a number near any keyword in combined text."""
    combined = " ".join(texts)
    for kw in keywords:
        pattern = rf"{kw}.{{0,50}}?(\d+\.?\d*)"
        m = re.search(pattern, combined, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if val > 0:
                    return val
            except ValueError:
                pass
    return default


def get_commodity_signal() -> dict:
    """
    Search for current coal, gas, oil prices.

    Returns:
        {
          "score": float (0-1),
          "label": str,
          "coal_usd": float,
          "gas_usd": float,
          "oil_usd": float,
          "summary": str,
          "source": "live" or "default"
        }
    """
    texts = tavily_search(
        "coal price USD per tonne natural gas price brent crude oil price today",
        max_results=3
    )

    if not texts:
        return {
            "score": 0.5, "label": "NORMAL",
            "coal_usd": 100.0, "gas_usd": 3.0, "oil_usd": 75.0,
            "summary": "No live data — using baseline prices", "source": "default"
        }

    coal = _extract_price(texts, ["coal"], 100.0)
    gas  = _extract_price(texts, ["gas", "henry hub", "ttf"], 3.0)
    oil  = _extract_price(texts, ["brent", "crude", "oil"], 75.0)

    # Score coal (most important for India grid)
    if coal > 180:   coal_score = 1.0
    elif coal > 140: coal_score = 0.75
    elif coal > 110: coal_score = 0.5
    elif coal > 80:  coal_score = 0.25
    else:            coal_score = 0.0

    # Score gas
    if gas > 12:    gas_score = 1.0
    elif gas > 7:   gas_score = 0.75
    elif gas > 4:   gas_score = 0.5
    elif gas > 2:   gas_score = 0.25
    else:           gas_score = 0.0

    # Score oil
    if oil > 120:   oil_score = 1.0
    elif oil > 95:  oil_score = 0.75
    elif oil > 75:  oil_score = 0.5
    elif oil > 55:  oil_score = 0.25
    else:           oil_score = 0.0

    # Weighted: coal 50%, gas 30%, oil 20%
    score = coal_score * 0.5 + gas_score * 0.3 + oil_score * 0.2

    if score >= 0.8:   label = "WORST"
    elif score >= 0.6: label = "BAD"
    elif score >= 0.35: label = "NORMAL"
    elif score >= 0.15: label = "GOOD"
    else:               label = "BEST"

    return {
        "score": round(score, 3),
        "label": label,
        "coal_usd": coal,
        "gas_usd": gas,
        "oil_usd": oil,
        "summary": f"Coal ${coal:.0f}/t | Gas ${gas:.1f}/MMBtu | Oil ${oil:.0f}/bbl",
        "source": "live"
    }