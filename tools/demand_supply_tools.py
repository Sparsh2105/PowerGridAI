"""
Tools for the Demand & Supply Management Agent.
Each tool is a standalone function decorated with @tool.
"""

import os
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults


# ---------------------------------------------------------------------------
# Static lookup data
# ---------------------------------------------------------------------------

PLANT_LOCATIONS = {
    "PLANT_001": {"zone": "North Zone",   "city": "Delhi"},
    "PLANT_002": {"zone": "West Zone",    "city": "Mumbai"},
    "PLANT_003": {"zone": "East Zone",    "city": "Kolkata"},
    "PLANT_004": {"zone": "South Zone",   "city": "Chennai"},
    "PLANT_005": {"zone": "Central Zone", "city": "Bhopal"},
    "PLANT_006": {"zone": "West Zone",    "city": "Jaipur"},
}

DISTANCE_TABLE = {
    ("PLANT_001", "North Zone"):   120,
    ("PLANT_001", "West Zone"):    420,
    ("PLANT_001", "East Zone"):    560,
    ("PLANT_001", "South Zone"):   1800,
    ("PLANT_001", "Central Zone"): 680,
    ("PLANT_002", "West Zone"):    80,
    ("PLANT_002", "North Zone"):   1400,
    ("PLANT_002", "South Zone"):   1100,
    ("PLANT_002", "East Zone"):    1900,
    ("PLANT_002", "Central Zone"): 750,
    ("PLANT_003", "East Zone"):    95,
    ("PLANT_003", "North Zone"):   1300,
    ("PLANT_003", "West Zone"):    2100,
    ("PLANT_003", "South Zone"):   1650,
    ("PLANT_003", "Central Zone"): 1100,
    ("PLANT_004", "South Zone"):   110,
    ("PLANT_004", "West Zone"):    1300,
    ("PLANT_004", "East Zone"):    1700,
    ("PLANT_004", "North Zone"):   2200,
    ("PLANT_004", "Central Zone"): 1000,
    ("PLANT_005", "Central Zone"): 90,
    ("PLANT_005", "North Zone"):   580,
    ("PLANT_005", "West Zone"):    700,
    ("PLANT_005", "East Zone"):    1050,
    ("PLANT_005", "South Zone"):   900,
    ("PLANT_006", "West Zone"):    280,
    ("PLANT_006", "North Zone"):   240,
    ("PLANT_006", "Central Zone"): 310,
    ("PLANT_006", "East Zone"):    1300,
    ("PLANT_006", "South Zone"):   1400,
}

PLANT_CAPACITY_DATA = {
    "PLANT_001": {"max_capacity_mw": 500,  "current_output_mw": 390, "capacity_percent": 78.0,  "fuel_type": "coal"},
    "PLANT_002": {"max_capacity_mw": 300,  "current_output_mw": 273, "capacity_percent": 91.0,  "fuel_type": "gas"},
    "PLANT_003": {"max_capacity_mw": 800,  "current_output_mw": 520, "capacity_percent": 65.0,  "fuel_type": "nuclear"},
    "PLANT_004": {"max_capacity_mw": 200,  "current_output_mw": 110, "capacity_percent": 55.0,  "fuel_type": "solar"},
    "PLANT_005": {"max_capacity_mw": 400,  "current_output_mw": 352, "capacity_percent": 88.0,  "fuel_type": "hydro"},
    "PLANT_006": {"max_capacity_mw": 150,  "current_output_mw": 63,  "capacity_percent": 42.0,  "fuel_type": "wind"},
}

DEMAND_ZONE_FORECAST = {
    "North Zone":   {"forecast_24h_mw": 1800, "peak_hour": "18:00", "trend": "rising"},
    "West Zone":    {"forecast_24h_mw": 2200, "peak_hour": "19:00", "trend": "stable"},
    "East Zone":    {"forecast_24h_mw": 1400, "peak_hour": "17:00", "trend": "falling"},
    "South Zone":   {"forecast_24h_mw": 1600, "peak_hour": "20:00", "trend": "rising"},
    "Central Zone": {"forecast_24h_mw": 900,  "peak_hour": "18:30", "trend": "stable"},
}

SUPPLY_CHAIN_STATUS = {
    "coal":    {"disruption_index": 0.72, "status": "high disruption",  "reason": "port strikes in eastern region"},
    "gas":     {"disruption_index": 0.45, "status": "moderate",         "reason": "pipeline maintenance scheduled"},
    "nuclear": {"disruption_index": 0.10, "status": "normal",           "reason": "stable domestic supply"},
    "solar":   {"disruption_index": 0.20, "status": "low disruption",   "reason": "panel import delays"},
    "hydro":   {"disruption_index": 0.05, "status": "normal",           "reason": "reservoir levels adequate"},
    "wind":    {"disruption_index": 0.15, "status": "normal",           "reason": "turbine parts available"},
}

MATERIAL_PRICES = {
    "coal":        {"price_per_ton_usd": 145.0, "trend": "rising",  "30d_change_pct": 12.5},
    "natural_gas": {"price_per_mmbtu_usd": 3.80, "trend": "stable", "30d_change_pct": -1.2},
    "uranium":     {"price_per_lb_usd": 91.0,    "trend": "rising", "30d_change_pct": 8.3},
    "silicon":     {"price_per_kg_usd": 2.85,    "trend": "falling","30d_change_pct": -5.1},
}


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@tool
def get_distance_tool(plant_id: str, demand_zone: str) -> dict:
    """
    Returns the transmission distance in km between a power plant and a demand zone.
    plant_id must be one of: PLANT_001 to PLANT_006.
    demand_zone must be one of: North Zone, West Zone, East Zone, South Zone, Central Zone.
    """
    key = (plant_id.upper(), demand_zone)
    distance = DISTANCE_TABLE.get(key)
    if distance is None:
        return {"error": f"No distance data for {plant_id} → {demand_zone}"}
    return {
        "plant_id": plant_id,
        "demand_zone": demand_zone,
        "distance_km": distance,
        "transmission_cost_factor": round(distance / 1000, 3),
    }


@tool
def get_supply_chain_status_tool(fuel_type: str) -> dict:
    """
    Returns the current global supply chain disruption status for a given fuel type.
    fuel_type must be one of: coal, gas, nuclear, solar, hydro, wind.
    disruption_index ranges 0.0 (no disruption) to 1.0 (complete disruption).
    """
    data = SUPPLY_CHAIN_STATUS.get(fuel_type.lower())
    if not data:
        return {"error": f"Unknown fuel type: {fuel_type}"}
    return {"fuel_type": fuel_type, **data}


@tool
def get_raw_material_prices_tool(material: str) -> dict:
    """
    Returns the current price and 30-day trend for a raw material.
    material must be one of: coal, natural_gas, uranium, silicon.
    """
    data = MATERIAL_PRICES.get(material.lower())
    if not data:
        return {"error": f"Unknown material: {material}. Use: coal, natural_gas, uranium, silicon"}
    return {"material": material, **data}


@tool
def get_plant_capacity_tool(plant_id: str) -> dict:
    """
    Returns the current capacity details for a given power plant.
    Returns max_capacity_mw, current_output_mw, capacity_percent, fuel_type.
    """
    data = PLANT_CAPACITY_DATA.get(plant_id.upper())
    if not data:
        return {"error": f"Unknown plant_id: {plant_id}"}
    return {"plant_id": plant_id, **data}


@tool
def get_regional_demand_forecast_tool(zone: str) -> dict:
    """
    Returns the 24-hour demand forecast for a given demand zone.
    zone must be one of: North Zone, West Zone, East Zone, South Zone, Central Zone.
    """
    data = DEMAND_ZONE_FORECAST.get(zone)
    if not data:
        return {"error": f"Unknown zone: {zone}"}
    return {"zone": zone, **data}


@tool
def get_weather_impact_tool(location: str) -> dict:
    """
    Fetches real current weather for a location using Tavily web search
    and returns a demand_impact_factor (0.5 to 2.0).
    Higher factor means weather is driving demand up (extreme heat/cold).
    """
    try:
        searcher = TavilySearchResults(max_results=2)
        results = searcher.invoke(f"current weather {location} temperature today")
        summary = results[0]["content"] if results else "Weather data unavailable"

        # Simple heuristic: look for temperature keywords
        text = summary.lower()
        if any(w in text for w in ["extreme heat", "heatwave", "40°", "45°", "above 40"]):
            factor = 1.8
            condition = "extreme heat"
        elif any(w in text for w in ["cold wave", "freezing", "below 5°", "0°", "snow"]):
            factor = 1.6
            condition = "cold wave"
        elif any(w in text for w in ["hot", "warm", "35°", "38°"]):
            factor = 1.3
            condition = "hot"
        elif any(w in text for w in ["rain", "storm", "cloudy"]):
            factor = 0.9
            condition = "rainy/cloudy"
        else:
            factor = 1.0
            condition = "normal"

        return {
            "location": location,
            "condition": condition,
            "demand_impact_factor": factor,
            "raw_summary": summary[:300],
        }
    except Exception as e:
        return {
            "location": location,
            "condition": "unknown",
            "demand_impact_factor": 1.0,
            "error": str(e),
        }


# Export all tools as a list for easy import
DEMAND_SUPPLY_TOOLS = [
    get_distance_tool,
    get_supply_chain_status_tool,
    get_raw_material_prices_tool,
    get_plant_capacity_tool,
    get_regional_demand_forecast_tool,
    get_weather_impact_tool,
]