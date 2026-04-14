import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "power_grid.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS plant_health (
            plant_id TEXT PRIMARY KEY,
            plant_name TEXT,
            location TEXT,
            fuel_type TEXT,
            total_runtime_hours REAL,
            current_capacity_percent REAL,
            max_capacity_mw REAL,
            current_output_mw REAL,
            last_maintenance_date TEXT,
            fault_count INTEGER,
            vibration_index REAL,
            temperature_celsius REAL,
            maintenance_status TEXT,
            next_maintenance_date TEXT
        );

        CREATE TABLE IF NOT EXISTS maintenance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id TEXT,
            maintenance_type TEXT,
            scheduled_date TEXT,
            completed_date TEXT,
            notes TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS transmission_lines (
            line_id TEXT PRIMARY KEY,
            from_plant TEXT,
            to_zone TEXT,
            distance_km REAL,
            voltage_kv REAL,
            current_load_mw REAL,
            max_capacity_mw REAL,
            line_age_years REAL,
            loss_percent REAL,
            status TEXT
        );

        CREATE TABLE IF NOT EXISTS transmission_inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id TEXT,
            reason TEXT,
            flagged_date TEXT,
            status TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            agent_source TEXT,
            summary TEXT,
            timestamp TEXT
        );
    """)

    # Seed plant_health if empty
    cursor.execute("SELECT COUNT(*) FROM plant_health")
    if cursor.fetchone()[0] == 0:
        plants = [
            ("PLANT_001", "Northern Coal Plant",    "Delhi",     "coal",    12400, 78.0, 500, 390, "2024-06-15", 3, 0.35, 82.0,  "ok",        "2025-06-15"),
            ("PLANT_002", "Western Gas Station",    "Mumbai",    "gas",     9800,  91.0, 300, 273, "2024-11-01", 7, 0.72, 95.0,  "urgent",    "2025-04-20"),
            ("PLANT_003", "Eastern Nuclear Plant",  "Kolkata",   "nuclear", 6200,  65.0, 800, 520, "2024-09-20", 1, 0.18, 68.0,  "ok",        "2025-09-20"),
            ("PLANT_004", "Southern Solar Farm",    "Chennai",   "solar",   3100,  55.0, 200, 110, "2025-01-10", 0, 0.08, 45.0,  "ok",        "2026-01-10"),
            ("PLANT_005", "Central Hydro Station",  "Bhopal",    "hydro",   15600, 88.0, 400, 352, "2024-03-05", 9, 0.85, 74.0,  "scheduled", "2025-05-01"),
            ("PLANT_006", "Rajasthan Wind Farm",    "Jaipur",    "wind",    4500,  42.0, 150, 63,  "2024-12-01", 2, 0.25, 38.0,  "ok",        "2025-12-01"),
        ]
        cursor.executemany("""
            INSERT INTO plant_health VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, plants)

    # Seed transmission_lines if empty
    cursor.execute("SELECT COUNT(*) FROM transmission_lines")
    if cursor.fetchone()[0] == 0:
        lines = [
            ("LINE_001", "PLANT_001", "North Zone",  420,  400, 310, 400, 12.0, 8.2,  "degraded"),
            ("LINE_002", "PLANT_002", "West Zone",   280,  220, 240, 300, 5.0,  4.1,  "efficient"),
            ("LINE_003", "PLANT_003", "East Zone",   510,  400, 480, 600, 18.0, 16.5, "critical"),
            ("LINE_004", "PLANT_004", "South Zone",  190,  132, 90,  200, 3.0,  3.0,  "efficient"),
            ("LINE_005", "PLANT_005", "Central Zone",350,  220, 330, 400, 22.0, 18.9, "critical"),
            ("LINE_006", "PLANT_006", "West Zone",   240,  132, 55,  150, 4.0,  5.5,  "efficient"),
        ]
        cursor.executemany("""
            INSERT INTO transmission_lines VALUES (?,?,?,?,?,?,?,?,?,?)
        """, lines)

    conn.commit()
    conn.close()
    print("[DB] Database initialized and seeded successfully.")


if __name__ == "__main__":
    setup_database()