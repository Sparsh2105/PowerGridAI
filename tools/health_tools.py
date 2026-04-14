"""
Tools for the Plant Health Tracker Agent.
Uses SQLite to read plant sensor data and schedule maintenance.
"""

import sys
import os
from datetime import datetime, timedelta
from langchain_core.tools import tool

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _calculate_health_score(runtime: float, last_maintenance: str,
                              fault_count: int, vibration: float,
                              temperature: float, capacity_pct: float) -> float:
    """Compute a 0-100 health score from plant sensor readings."""
    score = 100.0

    # Penalize for long runtime since last maintenance
    try:
        last_date = datetime.strptime(last_maintenance, "%Y-%m-%d")
        days_since = (datetime.now() - last_date).days
        if days_since > 365:
            score -= min(30, (days_since - 365) / 10)
    except Exception:
        score -= 10

    # Penalize for total runtime hours (wear and tear)
    if runtime > 15000:
        score -= 20
    elif runtime > 10000:
        score -= 10
    elif runtime > 7000:
        score -= 5

    # Penalize for fault count
    score -= min(25, fault_count * 4)

    # Penalize for high vibration (0=good, 1=critical)
    score -= vibration * 30

    # Penalize for high temperature (> 90°C is risky)
    if temperature > 90:
        score -= 15
    elif temperature > 80:
        score -= 8

    # Capacity percent over 95 = overloaded
    if capacity_pct > 95:
        score -= 10

    return max(0.0, min(100.0, round(score, 1)))


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@tool
def get_plant_runtime_tool(plant_id: str) -> dict:
    """
    Fetches runtime hours, fault count, and last maintenance date for a plant from the database.
    plant_id must be one of: PLANT_001 to PLANT_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT plant_id, plant_name, total_runtime_hours, last_maintenance_date, fault_count, maintenance_status "
        "FROM plant_health WHERE plant_id = ?", (plant_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Plant {plant_id} not found"}
    return dict(row)


@tool
def get_plant_sensor_data_tool(plant_id: str) -> dict:
    """
    Fetches live sensor readings for a plant: vibration index, temperature, and capacity percent.
    plant_id must be one of: PLANT_001 to PLANT_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT plant_id, plant_name, vibration_index, temperature_celsius, "
        "current_capacity_percent, current_output_mw, max_capacity_mw "
        "FROM plant_health WHERE plant_id = ?", (plant_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Plant {plant_id} not found"}
    return dict(row)


@tool
def calculate_health_score_tool(plant_id: str) -> dict:
    """
    Calculates a composite health score (0-100) for a plant.
    Returns health_score, risk_level (low/medium/high/critical), and recommended_action.
    plant_id must be one of: PLANT_001 to PLANT_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM plant_health WHERE plant_id = ?", (plant_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Plant {plant_id} not found"}

    row = dict(row)
    score = _calculate_health_score(
        runtime=row["total_runtime_hours"],
        last_maintenance=row["last_maintenance_date"],
        fault_count=row["fault_count"],
        vibration=row["vibration_index"],
        temperature=row["temperature_celsius"],
        capacity_pct=row["current_capacity_percent"],
    )

    if score >= 75:
        risk = "low"
        action = "continue normal operation"
    elif score >= 55:
        risk = "medium"
        action = "schedule maintenance within 30 days"
    elif score >= 35:
        risk = "high"
        action = "schedule maintenance within 7 days, reduce load"
    else:
        risk = "critical"
        action = "immediate maintenance required, take offline"

    return {
        "plant_id": plant_id,
        "plant_name": row["plant_name"],
        "health_score": score,
        "risk_level": risk,
        "recommended_action": action,
        "fault_count": row["fault_count"],
        "vibration_index": row["vibration_index"],
        "temperature_celsius": row["temperature_celsius"],
    }


@tool
def schedule_maintenance_tool(plant_id: str, maintenance_type: str, date: str) -> str:
    """
    Schedules maintenance for a plant and updates the database.
    plant_id: PLANT_001 to PLANT_006.
    maintenance_type: 'routine', 'emergency', 'inspection', 'overhaul'.
    date: ISO format date string YYYY-MM-DD.
    """
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO maintenance_log (plant_id, maintenance_type, scheduled_date, completed_date, notes, created_at) "
        "VALUES (?, ?, ?, NULL, 'Scheduled by health tracker agent', ?)",
        (plant_id.upper(), maintenance_type, date, now)
    )

    # Update plant health table
    if maintenance_type == "emergency":
        status = "urgent"
    elif maintenance_type == "overhaul":
        status = "scheduled"
    else:
        status = "scheduled"

    conn.execute(
        "UPDATE plant_health SET maintenance_status = ?, next_maintenance_date = ? WHERE plant_id = ?",
        (status, date, plant_id.upper())
    )
    conn.commit()
    conn.close()
    return f"Maintenance scheduled for {plant_id}: type={maintenance_type}, date={date}, status={status}"


@tool
def get_maintenance_schedule_tool() -> list:
    """
    Returns all upcoming scheduled maintenances sorted by date.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT ml.plant_id, ph.plant_name, ml.maintenance_type, ml.scheduled_date, ml.notes "
        "FROM maintenance_log ml JOIN plant_health ph ON ml.plant_id = ph.plant_id "
        "WHERE ml.completed_date IS NULL ORDER BY ml.scheduled_date ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@tool
def get_plants_needing_maintenance_tool() -> list:
    """
    Returns all plants that need maintenance based on:
    health_score < 60, fault_count > 3, or runtime > 10000 hours, or maintenance_status in (urgent, scheduled).
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT plant_id, plant_name, total_runtime_hours, fault_count, "
        "maintenance_status, vibration_index, temperature_celsius, current_capacity_percent "
        "FROM plant_health WHERE fault_count > 3 OR total_runtime_hours > 10000 "
        "OR maintenance_status IN ('urgent', 'scheduled')"
    ).fetchall()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        score = _calculate_health_score(
            runtime=r["total_runtime_hours"],
            last_maintenance="2024-01-01",
            fault_count=r["fault_count"],
            vibration=r["vibration_index"],
            temperature=r["temperature_celsius"],
            capacity_pct=r["current_capacity_percent"],
        )
        r["health_score"] = score
        results.append(r)
    return results


@tool
def get_all_plants_health_tool() -> list:
    """
    Returns health scores for ALL plants in the system. Use this for a full system overview.
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM plant_health").fetchall()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        score = _calculate_health_score(
            runtime=r["total_runtime_hours"],
            last_maintenance=r["last_maintenance_date"],
            fault_count=r["fault_count"],
            vibration=r["vibration_index"],
            temperature=r["temperature_celsius"],
            capacity_pct=r["current_capacity_percent"],
        )
        results.append({
            "plant_id": r["plant_id"],
            "plant_name": r["plant_name"],
            "health_score": score,
            "maintenance_status": r["maintenance_status"],
            "fault_count": r["fault_count"],
        })
    return results


# Export
HEALTH_TOOLS = [
    get_plant_runtime_tool,
    get_plant_sensor_data_tool,
    calculate_health_score_tool,
    schedule_maintenance_tool,
    get_maintenance_schedule_tool,
    get_plants_needing_maintenance_tool,
    get_all_plants_health_tool,
]