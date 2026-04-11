"""
core/memory.py — Agent Memory (SQLite)

Persistent memory for the GridMind agent backed by SQLite.
Replaces the old memory.json approach — data survives restarts,
can be queried, and never needs manual trimming.

DB file: gridmind.db  (created automatically at project root)

Tables:
  signals   — weather/crisis/commodity readings per run
  decisions — what the agent decided and why

No external packages needed — sqlite3 is part of Python stdlib.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "gridmind.db"


class GridMemory:
    """
    SQLite-backed memory for the GridMind agent.

    Usage:
        mem = GridMemory()
        mem.add({"type": "decision", "city": "Delhi", "summary": "..."})
        mem.add({"type": "signal", "weather_label": "BAD", ...})
        history = mem.get_recent(5)
        mem.save()   # no-op kept for API compatibility — writes are instant
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ── Schema ──────────────────────────────────────────────────────────────

    def _create_tables(self):
        """Create tables if they don't exist yet. Safe to call every run."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT NOT NULL,
                weather_label   TEXT,
                crisis_label    TEXT,
                commodity_label TEXT
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT NOT NULL,
                city          TEXT,
                demand_mw     REAL,
                supply_after  REAL,
                balance_after REAL,
                summary       TEXT,
                agent_source  TEXT
            );
        """)
        self._conn.commit()

    # ── Writing ──────────────────────────────────────────────────────────────

    def add(self, entry: dict):
        """
        Write an entry to SQLite immediately.
        Keeps the same API as the old JSON version — no save() needed.

        entry must have:
          type: "decision" | "signal"
          + relevant fields for that type
        """
        entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write(entry)

    def _write(self, entry: dict):
        t  = entry.get("type")
        ts = entry["timestamp"]

        if t == "signal":
            self._conn.execute(
                """INSERT INTO signals (timestamp, weather_label, crisis_label, commodity_label)
                   VALUES (?, ?, ?, ?)""",
                (ts,
                 entry.get("weather_label", ""),
                 entry.get("crisis_label", ""),
                 entry.get("commodity_label", ""))
            )

        elif t == "decision":
            self._conn.execute(
                """INSERT INTO decisions
                   (timestamp, city, demand_mw, supply_after, balance_after, summary, agent_source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ts,
                 entry.get("city", ""),
                 entry.get("demand_mw", 0),
                 entry.get("supply_after", 0),
                 entry.get("balance_after", 0),
                 entry.get("summary", ""),
                 entry.get("agent_source", ""))
            )

        self._conn.commit()

    # ── Reading ───────────────────────────────────────────────────────────────

    def get_recent(self, n: int = 5) -> list[dict]:
        """
        Return the n most recent entries across both tables, newest first.
        Merges signals + decisions by timestamp.
        """
        rows = self._conn.execute(
            """
            SELECT 'signal'   AS type, timestamp,
                   weather_label, crisis_label, commodity_label,
                   NULL AS city, NULL AS summary,
                   NULL AS balance_after, NULL AS agent_source
            FROM   signals
            UNION ALL
            SELECT 'decision' AS type, timestamp,
                   NULL, NULL, NULL,
                   city, summary, balance_after, agent_source
            FROM   decisions
            ORDER  BY timestamp DESC
            LIMIT  ?
            """,
            (n,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_last_decision(self) -> dict | None:
        """Return the most recent decision row, or None."""
        row = self._conn.execute(
            "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def save(self):
        """
        No-op — kept so the rest of the codebase doesn't need to change.
        SQLite commits happen immediately inside _write().
        """
        pass

    # ── Agent prompt helper ───────────────────────────────────────────────────

    def format_for_agent(self, n: int = 3) -> str:
        """
        Format recent memory as plain text for the Gemini prompt.

        Example output:
          [2026-04-11 10:30] DECISION: Increased Bhakra Nangal — deficit covered  (balance +0.7MW, src=live)
          [2026-04-11 10:25] SIGNALS: weather=BAD crisis=GOOD commodity=NORMAL
        """
        entries = self.get_recent(n)
        if not entries:
            return "No previous decisions."

        lines = []
        for e in entries:
            ts = e.get("timestamp", "")
            if e["type"] == "decision":
                bal = e.get("balance_after") or 0
                lines.append(
                    f"[{ts}] DECISION: {e.get('summary', '')}  "
                    f"(balance {bal:+.1f}MW, src={e.get('agent_source','')})"
                )
            elif e["type"] == "signal":
                lines.append(
                    f"[{ts}] SIGNALS: weather={e.get('weather_label','')} "
                    f"crisis={e.get('crisis_label','')} "
                    f"commodity={e.get('commodity_label','')}"
                )
        return "\n".join(lines)

    # ── Inspection helpers (used by --show-memory in main.py) ────────────────

    def get_all_decisions(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_signals(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM signals ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        """Close the DB connection. Call when shutting down."""
        self._conn.close()