"""
core/config.py — Load .env file and expose API keys + plant data.
All other modules import from here. Never read os.environ directly elsewhere.
"""

import os
import math
from pathlib import Path

# ── Load .env ──────────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

def get_gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")

def get_tavily_key() -> str:
    return os.environ.get("TAVILY_API_KEY", "")

# ── 10 India Power Plants ──────────────────────────────────────────────────────
POWER_PLANTS = [
    {"name": "Vindhyachal STPS",   "type": "coal",    "cost": 3.2, "max_mw": 25, "current_mw": 20, "lat": 24.08, "lon": 82.66, "state": "Madhya Pradesh"},
    {"name": "Talcher STPS",        "type": "coal",    "cost": 3.5, "max_mw": 22, "current_mw": 18, "lat": 20.95, "lon": 85.22, "state": "Odisha"},
    {"name": "Kudankulam NPP",      "type": "nuclear", "cost": 2.8, "max_mw": 20, "current_mw": 18, "lat": 8.17,  "lon": 77.71, "state": "Tamil Nadu"},
    {"name": "Bhakra Nangal Dam",   "type": "hydro",   "cost": 1.5, "max_mw": 18, "current_mw": 12, "lat": 31.41, "lon": 76.43, "state": "Himachal Pradesh"},
    {"name": "Sardar Sarovar",      "type": "hydro",   "cost": 1.8, "max_mw": 15, "current_mw": 10, "lat": 21.83, "lon": 73.75, "state": "Gujarat"},
    {"name": "Bhadla Solar Park",   "type": "solar",   "cost": 2.4, "max_mw": 20, "current_mw": 8,  "lat": 27.54, "lon": 71.93, "state": "Rajasthan"},
    {"name": "Pavagada Solar Park", "type": "solar",   "cost": 2.3, "max_mw": 18, "current_mw": 7,  "lat": 14.10, "lon": 77.28, "state": "Karnataka"},
    {"name": "Muppandal Wind Farm", "type": "wind",    "cost": 2.6, "max_mw": 15, "current_mw": 6,  "lat": 8.33,  "lon": 77.44, "state": "Tamil Nadu"},
    {"name": "Jaisalmer Wind Park", "type": "wind",    "cost": 2.7, "max_mw": 12, "current_mw": 5,  "lat": 27.00, "lon": 70.93, "state": "Rajasthan"},
    {"name": "Simhadri STPS",       "type": "coal",    "cost": 3.3, "max_mw": 20, "current_mw": 16, "lat": 17.64, "lon": 83.26, "state": "Andhra Pradesh"},
]

PLANT_BY_NAME = {p["name"]: p for p in POWER_PLANTS}

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Distance in km between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)

# ── India city coordinates ─────────────────────────────────────────────────────
CITIES = {
    "delhi": (28.61, 77.21), "mumbai": (19.08, 72.88), "bangalore": (12.97, 77.59),
    "bengaluru": (12.97, 77.59), "hyderabad": (17.39, 78.49), "chennai": (13.08, 80.27),
    "kolkata": (22.57, 88.36), "pune": (18.52, 73.86), "ahmedabad": (23.02, 72.57),
    "jaipur": (26.91, 75.79), "lucknow": (26.85, 80.95), "bhopal": (23.26, 77.41),
    "nagpur": (21.15, 79.09), "indore": (22.72, 75.86), "gorakhpur": (26.76, 83.37),
    "varanasi": (25.32, 82.97), "patna": (25.59, 85.14), "kanpur": (26.45, 80.33),
    "agra": (27.18, 78.01), "surat": (21.17, 72.83), "visakhapatnam": (17.69, 83.22),
    "kochi": (9.93, 76.27), "coimbatore": (11.02, 76.96), "chandigarh": (30.73, 76.78),
    "dehradun": (30.32, 78.03), "amritsar": (31.63, 74.87), "noida": (28.54, 77.39),
    "gurgaon": (28.46, 77.03), "ranchi": (23.34, 85.31), "bhubaneswar": (20.30, 85.82),
}