"""
distance_tool.py — Dynamic Plant Distance Tool

Resolves ANY city name to real coordinates using a 3-tier approach:

  Tier 1: Local CITIES dict — instant, no network (30 major India cities)
  Tier 2: Tavily search geocoding — "coordinates of <city> India"
           Works for any city/town/village. Uses the Tavily key in .env.
  Tier 3: Delhi default — last resort if everything else fails

Then computes haversine distance to all 10 power plants + transmission loss.

Why this design:
  - Tier 1 handles 95% of common queries with zero latency
  - Tier 2 handles any unknown place using Tavily (already in the system)
  - No extra API key needed — reuses the existing Tavily key
  - Haversine math is done locally — always fast and accurate
"""

import re
import json
import urllib.request
import urllib.parse
from core.config import POWER_PLANTS, CITIES, haversine_km, get_tavily_key

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TAVILY_URL    = "https://api.tavily.com/search"


def _geocode_via_nominatim(city: str) -> tuple[float, float] | None:
    """Try Nominatim (OpenStreetMap). Returns (lat, lon) or None."""
    try:
        params = urllib.parse.urlencode({
            "q": city + ", India",
            "format": "json",
            "limit": 1,
        })
        req = urllib.request.Request(
            f"{NOMINATIM_URL}?{params}",
            headers={"User-Agent": "GridMindAI/2.0 (power-grid-controller)"}
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            results = json.loads(r.read().decode())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


def _geocode_via_tavily(city: str) -> tuple[float, float] | None:
    """
    Use Tavily to search for city coordinates.
    Query: "GPS coordinates latitude longitude of <city> India"
    Parses the first lat/lon pair found in the answer text.
    """
    key = get_tavily_key()
    if not key or key == "tvly-your-key-here":
        return None

    try:
        payload = json.dumps({
            "api_key": key,
            "query": f"GPS coordinates latitude longitude of {city} India",
            "search_depth": "basic",
            "max_results": 2,
            "include_answer": True,
        }).encode()

        req = urllib.request.Request(
            TAVILY_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())

        # Search in the AI answer + snippets for a coordinate pair
        texts = []
        if data.get("answer"):
            texts.append(data["answer"])
        for item in data.get("results", []):
            texts.append(item.get("content", "")[:300])

        combined = " ".join(texts)

        # Match patterns like: 26.7606° N, 83.3732° E  or  lat: 26.76  lon: 83.37
        # or  (26.7606, 83.3732)  or  26.7606, 83.3732
        patterns = [
            r'(\d{1,2}\.\d+)[°\s]*[Nn][,\s]+(\d{2,3}\.\d+)[°\s]*[Ee]',
            r'[Ll]at(?:itude)?[:\s]+(\d{1,2}\.\d+).*?[Ll]on(?:gitude)?[:\s]+(\d{2,3}\.\d+)',
            r'\((\d{1,2}\.\d+),\s*(\d{2,3}\.\d+)\)',
            r'(\d{1,2}\.\d{3,})[,\s]+(\d{2,3}\.\d{3,})',
        ]
        for pat in patterns:
            m = re.search(pat, combined)
            if m:
                lat = float(m.group(1))
                lon = float(m.group(2))
                # Sanity check: India is roughly lat 8-37, lon 68-97
                if 6 <= lat <= 38 and 66 <= lon <= 98:
                    return lat, lon

    except Exception as e:
        print(f"[Geocode] Tavily geocode failed: {e}")

    return None


def geocode_city(city: str) -> tuple[float, float, str]:
    """
    Resolve city name to (lat, lon) using 3-tier fallback.

    Returns:
        (lat, lon, source_label)
        source_label: "local" | "nominatim" | "tavily" | "default"
    """
    key = city.strip().lower()

    # Tier 1: Local dict — instant
    if key in CITIES:
        lat, lon = CITIES[key]
        return lat, lon, "local"

    # Partial match in local dict
    for db_city, coords in CITIES.items():
        if key in db_city or db_city in key:
            lat, lon = coords
            return lat, lon, "local"

    # Tier 2a: Nominatim (free, no key)
    result = _geocode_via_nominatim(city)
    if result:
        return result[0], result[1], "nominatim"

    # Tier 2b: Tavily search geocoding (reuses existing key)
    result = _geocode_via_tavily(city)
    if result:
        return result[0], result[1], "tavily"

    # Tier 3: Delhi default
    lat, lon = CITIES["delhi"]
    return lat, lon, "default"


def get_plant_distances(city: str) -> dict:
    """
    Get real distances from any city to all 10 power plants.

    Geocodes the city dynamically (Nominatim → Tavily → local → Delhi).
    Computes haversine distance + transmission loss estimate for each plant.

    Args:
        city: Any city name — e.g. "Gorakhpur", "Aurangabad", "Korba", "Shimla"

    Returns:
        {
          "city": str,
          "lat": float, "lon": float,
          "found": bool,
          "geocode_source": str,   # how we resolved the city
          "plants": [
            {
              "name", "type", "state", "distance_km",
              "cost_per_unit",
              "effective_cost",          # cost + distance penalty
              "transmission_loss_pct",   # approx 0.003% per km
              "current_mw", "max_mw",
              "plant_lat", "plant_lon"
            }, ... sorted nearest first
          ],
          "nearest": dict
        }
    """
    lat, lon, source = geocode_city(city)
    found = source != "default"

    print(f"[Geocode] '{city}' → ({lat:.4f}°N, {lon:.4f}°E)  [{source}]")

    plants_with_dist = []
    for p in POWER_PLANTS:
        dist = haversine_km(lat, lon, p["lat"], p["lon"])

        # Transmission loss: India grid average ~0.003% per km
        loss_pct = round(dist * 0.003, 2)

        # Effective cost = base cost + distance surcharge (per 1000 km = +0.2 Rs)
        effective_cost = round(p["cost"] + dist / 5000.0, 3)

        plants_with_dist.append({
            "name":                  p["name"],
            "type":                  p["type"],
            "state":                 p["state"],
            "distance_km":           dist,
            "cost_per_unit":         p["cost"],
            "effective_cost":        effective_cost,
            "transmission_loss_pct": loss_pct,
            "current_mw":            p["current_mw"],
            "max_mw":                p["max_mw"],
            "plant_lat":             p["lat"],
            "plant_lon":             p["lon"],
        })

    plants_with_dist.sort(key=lambda x: x["distance_km"])

    return {
        "city":           city.title(),
        "lat":            lat,
        "lon":            lon,
        "found":          found,
        "geocode_source": source,
        "plants":         plants_with_dist,
        "nearest":        plants_with_dist[0],
    }