"""
Main entry point for the Power Grid Intelligence System.
Run: python main.py
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

load_dotenv()

sys.path.append(os.path.dirname(__file__))
from database.db_setup import setup_database
from graph import POWER_GRID_GRAPH, PowerGridState

console = Console()


def print_header():
    console.print(Panel(
        Text("⚡  POWER GRID INTELLIGENCE SYSTEM  ⚡", justify="center", style="bold yellow"),
        subtitle="LangGraph + RL Environment",
        style="yellow",
        box=box.DOUBLE_EDGE,
    ))


def print_state_table(obs: list):
    table = Table(title="RL Observation Vector", box=box.SIMPLE_HEAVY, style="cyan")
    table.add_column("Feature", style="bold white")
    table.add_column("Value", style="green")
    table.add_column("Bar", style="cyan")

    labels = [
        "avg_capacity_norm",
        "avg_efficiency_norm",
        "plant_health_ratio",
        "degraded_lines_ratio",
        "total_capacity_norm",
        "demand_forecast_norm",
    ]
    for label, val in zip(labels, obs):
        bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
        table.add_row(label, f"{val:.4f}", bar)
    console.print(table)


def run_pipeline(rl_action: int = 1):
    action_label = ["conservative", "balanced", "aggressive"][rl_action]
    console.print(f"\n[bold cyan]▶ Running pipeline with RL action=[yellow]{rl_action}[/yellow] ({action_label})[/bold cyan]\n")

    initial_state: PowerGridState = {
        "user_query": (
            f"Run full power grid analysis. RL action={rl_action} ({action_label}). "
            "Check all plants, assess health, evaluate transmission lines, and make optimal decisions."
        ),
        "rl_action": rl_action,
        "current_observation": [0.70, 0.82, 0.75, 0.30, 0.68, 0.50],
        "demand_decisions": None,
        "health_report": None,
        "transmission_report": None,
        "unified_report": None,
        "final_decisions": None,
        "rl_reward": None,
        "next_observation": None,
        "messages": [],
    }

    console.print("[bold green]► Step 1: Demand & Supply Agent[/bold green]")
    console.print("[bold green]► Step 2: Plant Health Tracker Agent[/bold green]")
    console.print("[bold green]► Step 3: Transmission Line Agent[/bold green]")
    console.print("[bold green]► Step 4: Main Orchestrator — resolving conflicts + computing reward[/bold green]\n")

    result = POWER_GRID_GRAPH.invoke(initial_state)

    # Display final report
    console.print(Panel(
        result.get("final_decisions", "No report generated.")[:2000],
        title="[bold yellow]ORCHESTRATOR FINAL REPORT[/bold yellow]",
        style="yellow",
    ))

    next_obs = result.get("next_observation", initial_state["current_observation"])
    reward = result.get("rl_reward", 0.0)

    console.print(f"\n[bold]RL Reward this step:[/bold] [bold green]{reward}[/bold green]")
    if next_obs:
        print_state_table(next_obs)

    return result


if __name__ == "__main__":
    print_header()

    console.print("\n[bold]Initializing database...[/bold]")
    setup_database()

    # Run with balanced action by default
    # Change to 0 (conservative) or 2 (aggressive) to test RL action effects
    rl_action = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    run_pipeline(rl_action=rl_action)

    console.print("\n[bold green]✓ Pipeline complete.[/bold green]")
    console.print("[dim]Tip: Run with argument 0, 1, or 2 to change RL action:[/dim]")
    console.print("[dim]  python main.py 0   # conservative[/dim]")
    console.print("[dim]  python main.py 1   # balanced (default)[/dim]")
    console.print("[dim]  python main.py 2   # aggressive[/dim]")