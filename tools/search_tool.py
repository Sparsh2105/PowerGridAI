"""
search_tool.py — Tavily Search Tool

One function: tavily_search(query) → list of text snippets.
Used by weather_tool, commodity_tool, crisis_tool.
Falls back to empty list if no API key.
"""

import json
import urllib.request
from core.config import get_tavily_key


def tavily_search(query: str, max_results: int = 3) -> list[str]:
    """
    Search the web via Tavily. Returns list of text snippets.

    Args:
        query: What to search for
        max_results: How many results to return (default 3)

    Returns:
        List of strings (answer + content snippets).
        Empty list if no API key or request fails.
    """
    key = get_tavily_key()
    if not key or key == "tvly-your-key-here":
        return []

    try:
        payload = json.dumps({
            "api_key": key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": True,
        }).encode()

        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())

        results = []
        if data.get("answer"):
            results.append(data["answer"])
        for item in data.get("results", []):
            snippet = item.get("content", "")[:400]
            if snippet:
                results.append(snippet)
        return results

    except Exception as e:
        print(f"[Tavily] Search failed: {e}")
        return []