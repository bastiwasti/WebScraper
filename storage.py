"""SQLite storage for scraped events. Used for automation and by the next agents."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Open connection to the events DB. Creates file and table if needed."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create events table if it does not exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                location TEXT,
                date TEXT,
                time TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_at
            ON events(created_at)
        """)
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def insert_events(events: list[dict[str, Any]], conn: sqlite3.Connection | None = None) -> int:
    """
    Insert structured events (name, description, location, date, time, source).
    Returns number of rows inserted.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        count = 0
        for e in events:
            name = (e.get("name") or "").strip()
            if not name:
                continue
            conn.execute(
                """
                INSERT INTO events (name, description, location, date, time, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    (e.get("description") or "").strip(),
                    (e.get("location") or "").strip(),
                    (e.get("date") or "").strip(),
                    (e.get("time") or "").strip(),
                    (e.get("source") or "").strip(),
                    now,
                ),
            )
            count += 1
        conn.commit()
        return count
    finally:
        if own_conn:
            conn.close()


def get_events(
    since_days: int | None = None,
    limit: int = 200,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """
    Load events for the newsletter. If since_days is set, only return events
    created in the last N days; otherwise return latest by created_at.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if since_days is not None:
            # SQLite: date(created_at) >= date('now', '-N days')
            cur = conn.execute(
                """
                SELECT id, name, description, location, date, time, source, created_at
                FROM events
                WHERE date(created_at) >= date('now', ?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"-{since_days} days", limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, name, description, location, date, time, source, created_at
                FROM events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"] or "",
                "location": r["location"] or "",
                "date": r["date"] or "",
                "time": r["time"] or "",
                "source": r["source"] or "",
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert DB row to dict for writer (name, description, location, date, time, source)."""
    return {
        "name": row["name"],
        "description": row["description"] or "",
        "location": row["location"] or "",
        "date": row["date"] or "",
        "time": row["time"] or "",
        "source": row["source"] or "",
    }
