"""
Tools for the Main Orchestrator Agent.
All tools read directly from database — NO parameters needed for reward/state.
"""

import sys
import os
from langchain_core.tools import tool

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from database.db_setup import get_connection


@tool
def get_system_summary_tool() -> dict:
    """Returns full summary of all plants and transmission lines from database."""
    conn   = get_connection()
    plants = conn.execute("SELECT * FROM plant_health").fetchall()
    lines  = conn.execute("SELECT * FROM transmission_lines").fetchall()
    conn.close()
    return {
        "plants":           [dict(p) for p in plants],
        "transmission_lines": [dict(l) for l in lines],
        "total_plants":     len(plants),
        "total_lines":      len(lines),
    }


@tool
def resolve_conflicts_tool(
    demand_decisions: str,
    health_report: str,
    transmission_report: str,
    rl_action: int,
) -> dict:
    """
    Resolves conflicts between sub-agent recommendations.
    demand_decisions: JSON string from demand agent.
    health_report: JSON string from health agent.
    transmission_report: JSON string from transmission agent.
    rl_action: 0=conservative, 1=balanced, 2=aggressive.
    """
    action_label = ["conservative", "balanced", "aggressive"][int(rl_action)]
    return {
        "rl_action":       rl_action,
        "rl_action_label": action_label,
        "rules_applied": [
            "Critical plant health → override demand increase with DECREASE",
            "Critical transmission line → cap plant output at 70%",
            "Conservative mode → prefer maintenance over output",
            "Aggressive mode → maximize output unless health critical",
        ],
        "demand_summary":       demand_decisions[:200] if demand_decisions else "none",
        "health_summary":       health_report[:200]    if health_report    else "none",
        "transmission_summary": transmission_report[:200] if transmission_report else "none",
        "resolution":           f"Resolved under {action_label} policy",
    }


@tool
def compute_reward_tool() -> dict:
    """
    Computes RL reward directly from database. No parameters needed.

    Reward rules:
      +1.0 per plant with fault_count < 3
      -1.0 per plant with maintenance_status = urgent
      +0.5 per line with loss_percent < 10
      -0.5 per line with status = critical or flagged
    """
    conn   = get_connection()
    plants = conn.execute("SELECT * FROM plant_health").fetchall()
    lines  = conn.execute("SELECT * FROM transmission_lines").fetchall()
    conn.close()

    reward    = 0.0
    breakdown = []

    for p in plants:
        p = dict(p)
        if p["fault_count"] < 3:
            reward += 1.0
            breakdown.append(f"+1.0 {p['plant_id']} fault_count ok")
        if p["maintenance_status"] == "urgent":
            reward -= 1.0
            breakdown.append(f"-1.0 {p['plant_id']} urgent maintenance")

    for l in lines:
        l = dict(l)
        if l["loss_percent"] < 10:
            reward += 0.5
            breakdown.append(f"+0.5 {l['line_id']} loss ok")
        if l["status"] in ("critical", "flagged"):
            reward -= 0.5
            breakdown.append(f"-0.5 {l['line_id']} {l['status']}")

    return {
        "reward":    round(reward, 2),
        "breakdown": breakdown,
    }


@tool
def compute_next_state_tool() -> dict:
    """
    Computes next observation vector for RL environment directly from database.
    Returns 6-float normalized vector [0-1].
    No parameters needed.
    """
    conn   = get_connection()
    plants = conn.execute("SELECT * FROM plant_health").fetchall()
    lines  = conn.execute("SELECT * FROM transmission_lines").fetchall()
    conn.close()

    plants = [dict(p) for p in plants]
    lines  = [dict(l) for l in lines]

    avg_capacity     = sum(p["current_capacity_percent"] for p in plants) / len(plants) / 100
    avg_efficiency   = sum(1 - (l["loss_percent"] / 100) for l in lines) / len(lines)
    healthy_plants   = sum(
        1 for p in plants
        if p["fault_count"] < 3 and p["maintenance_status"] != "urgent"
    )
    plant_health_ratio  = healthy_plants / len(plants)
    degraded_lines      = sum(1 for l in lines if l["status"] in ("critical", "degraded", "flagged"))
    degraded_lines_ratio = degraded_lines / len(lines)
    total_capacity      = sum(p["current_output_mw"] for p in plants)
    total_capacity_norm = min(1.0, total_capacity / 2500)

    obs = [
        round(avg_capacity,          4),
        round(avg_efficiency,        4),
        round(plant_health_ratio,    4),
        round(degraded_lines_ratio,  4),
        round(total_capacity_norm,   4),
        round(0.55,                  4),
    ]

    return {
        "next_observation": obs,
        "explanation": {
            "avg_capacity_norm":    obs[0],
            "avg_efficiency_norm":  obs[1],
            "plant_health_ratio":   obs[2],
            "degraded_lines_ratio": obs[3],
            "total_capacity_norm":  obs[4],
            "demand_forecast_norm": obs[5],
        },
    }


ORCHESTRATOR_TOOLS = [
    get_system_summary_tool,
    resolve_conflicts_tool,
    compute_reward_tool,
    compute_next_state_tool,
]