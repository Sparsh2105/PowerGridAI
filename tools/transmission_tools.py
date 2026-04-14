"""
Tools for the Power Transmission Line Efficiency Agent.
Evaluates line health, calculates losses, and recommends load balancing.
"""

import sys
import os
from datetime import datetime
from langchain_core.tools import tool

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


# Benchmark: anything below this MW/km ratio is inefficient
EFFICIENCY_BENCHMARK_MW_PER_KM = 0.8
LOSS_THRESHOLD_PCT = 12.0
EFFICIENCY_SCORE_THRESHOLD = 75.0


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

@tool
def get_transmission_line_data_tool(line_id: str) -> dict:
    """
    Returns all data for a specific transmission line from the database.
    line_id must be one of: LINE_001 to LINE_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transmission_lines WHERE line_id = ?", (line_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Line {line_id} not found"}
    return dict(row)


@tool
def get_all_transmission_lines_tool() -> list:
    """
    Returns data for ALL transmission lines in the system.
    Use this for a full system overview of the transmission network.
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM transmission_lines").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@tool
def calculate_transmission_loss_tool(line_id: str) -> dict:
    """
    Calculates the actual power loss and efficiency score for a transmission line.
    Returns: power_loss_mw, efficiency_score (0-100), status (efficient/degraded/critical).
    line_id must be one of: LINE_001 to LINE_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transmission_lines WHERE line_id = ?", (line_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Line {line_id} not found"}

    row = dict(row)
    load = row["current_load_mw"]
    loss_pct = row["loss_percent"]
    power_loss = round(load * loss_pct / 100, 2)
    delivered = round(load - power_loss, 2)
    efficiency_score = round((delivered / load) * 100, 1) if load > 0 else 0

    if efficiency_score >= 90:
        status = "efficient"
    elif efficiency_score >= 75:
        status = "degraded"
    else:
        status = "critical"

    return {
        "line_id": line_id,
        "from_plant": row["from_plant"],
        "to_zone": row["to_zone"],
        "current_load_mw": load,
        "power_loss_mw": power_loss,
        "delivered_power_mw": delivered,
        "loss_percent": loss_pct,
        "efficiency_score": efficiency_score,
        "status": status,
    }


@tool
def get_line_distance_consumption_ratio_tool(line_id: str) -> dict:
    """
    Computes the MW delivered per km (efficiency ratio) for a transmission line.
    Benchmark is 0.8 MW/km. Below this is considered inefficient.
    line_id must be one of: LINE_001 to LINE_006.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transmission_lines WHERE line_id = ?", (line_id.upper(),)
    ).fetchone()
    conn.close()
    if not row:
        return {"error": f"Line {line_id} not found"}

    row = dict(row)
    load = row["current_load_mw"]
    loss = load * row["loss_percent"] / 100
    delivered = load - loss
    distance = row["distance_km"]
    ratio = round(delivered / distance, 4) if distance > 0 else 0

    return {
        "line_id": line_id,
        "distance_km": distance,
        "delivered_mw": round(delivered, 2),
        "mw_per_km_ratio": ratio,
        "benchmark_mw_per_km": EFFICIENCY_BENCHMARK_MW_PER_KM,
        "is_efficient": ratio >= EFFICIENCY_BENCHMARK_MW_PER_KM,
        "gap_from_benchmark": round(ratio - EFFICIENCY_BENCHMARK_MW_PER_KM, 4),
    }


@tool
def recommend_load_balancing_tool(zone: str) -> dict:
    """
    Analyzes all lines feeding a demand zone and recommends load shifts from degraded to efficient lines.
    zone must be one of: North Zone, West Zone, East Zone, South Zone, Central Zone.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM transmission_lines WHERE to_zone = ?", (zone,)
    ).fetchall()
    conn.close()

    if not rows:
        return {"error": f"No transmission lines found for zone: {zone}"}

    lines = [dict(r) for r in rows]
    efficient = []
    degraded = []

    for line in lines:
        load = line["current_load_mw"]
        loss = load * line["loss_percent"] / 100
        delivered = load - loss
        eff_score = round((delivered / load) * 100, 1) if load > 0 else 0
        line["efficiency_score"] = eff_score
        headroom = line["max_capacity_mw"] - load

        if eff_score >= 85 and headroom > 20:
            efficient.append({**line, "headroom_mw": headroom})
        elif eff_score < 75:
            degraded.append({**line, "efficiency_score": eff_score})

    recommendations = []
    for d_line in degraded:
        for e_line in efficient:
            shift = min(d_line["current_load_mw"] * 0.20, e_line["headroom_mw"])
            if shift > 5:
                recommendations.append({
                    "shift_from_line": d_line["line_id"],
                    "shift_to_line": e_line["line_id"],
                    "suggested_load_shift_mw": round(shift, 1),
                    "reason": f"{d_line['line_id']} efficiency={d_line['efficiency_score']}% is degraded",
                })

    return {
        "zone": zone,
        "total_lines": len(lines),
        "efficient_lines": len(efficient),
        "degraded_lines": len(degraded),
        "recommendations": recommendations,
    }


@tool
def flag_line_for_inspection_tool(line_id: str, reason: str) -> str:
    """
    Flags a transmission line for inspection and logs it in the database.
    line_id must be one of: LINE_001 to LINE_006.
    reason: short description of why the line is being flagged.
    """
    conn = get_connection()
    now = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        "INSERT INTO transmission_inspections (line_id, reason, flagged_date, status, notes) "
        "VALUES (?, ?, ?, 'pending', 'Flagged by transmission efficiency agent')",
        (line_id.upper(), reason, now)
    )
    conn.execute(
        "UPDATE transmission_lines SET status = 'flagged' WHERE line_id = ?",
        (line_id.upper(),)
    )
    conn.commit()
    conn.close()
    return f"Line {line_id} flagged for inspection. Reason: {reason}. Date: {now}"


@tool
def get_flagged_lines_tool() -> list:
    """
    Returns all transmission lines currently flagged for inspection.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT ti.line_id, tl.from_plant, tl.to_zone, ti.reason, ti.flagged_date, ti.status "
        "FROM transmission_inspections ti "
        "JOIN transmission_lines tl ON ti.line_id = tl.line_id "
        "WHERE ti.status = 'pending' ORDER BY ti.flagged_date DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Export
TRANSMISSION_TOOLS = [
    get_transmission_line_data_tool,
    get_all_transmission_lines_tool,
    calculate_transmission_loss_tool,
    get_line_distance_consumption_ratio_tool,
    recommend_load_balancing_tool,
    flag_line_for_inspection_tool,
    get_flagged_lines_tool,
]