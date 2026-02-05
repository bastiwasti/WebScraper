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
    """Create events, raw_summaries, runs, and status tables if they do not exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                location TEXT,
                created_at TEXT NOT NULL,
                raw_summary_id INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                linked_run_id INTEGER,
                urls TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration REAL,
                events_found INTEGER DEFAULT 0,
                valid_events INTEGER DEFAULT 0,
                full_run INTEGER DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (linked_run_id) REFERENCES runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status_run_id
            ON status(run_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                location TEXT,
                date TEXT,
                time TEXT,
                category TEXT,
                source TEXT,
                city TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created_at
            ON events(created_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_category
            ON events(category)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_run_id
            ON events(run_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                location TEXT,
                max_search INTEGER,
                fetch_urls INTEGER,
                cities TEXT,
                search_queries TEXT,
                raw_summary TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_summaries_created_at
            ON raw_summaries(created_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_raw_summaries_run_id
            ON raw_summaries(run_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status_run_id
            ON status(run_id)
        """)
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def create_run(
    agent: str,
    location: str = "",
    raw_summary_id: int | None = None,
    linked_run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Create a new pipeline run and return run_id."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        cur = conn.execute(
            """
            INSERT INTO runs (agent, location, created_at, raw_summary_id)
            VALUES (?, ?, ?, ?)
            """,
            (agent, location, now, raw_summary_id),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        if own_conn:
            conn.close()


def get_runs(limit: int = 20, conn: sqlite3.Connection | None = None) -> list[dict[str, Any]]:
    """Get recent runs with their counts."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cur = conn.execute(
            """
            SELECT r.id, r.agent, r.location, r.created_at,
                   s.start_time, s.end_time, s.duration, s.events_found, s.valid_events, s.linked_run_id,
                   (SELECT COUNT(*) FROM events WHERE events.run_id = r.id) as event_count
            FROM runs r
            LEFT JOIN status s ON s.run_id = r.id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "agent": r["agent"],
                "location": r["location"] or "",
                "created_at": r["created_at"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "duration": r["duration"],
                "events_found": r["events_found"],
                "valid_events": r["valid_events"],
                "linked_run_id": r["linked_run_id"],
                "event_count": r["event_count"],
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def create_run_status(
    run_id: int,
    urls: list[str],
    full_run: bool = False,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Create a status row for a run."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        import json
        urls_json = json.dumps(urls)
        cur = conn.execute(
            """
            INSERT INTO status (run_id, urls, start_time, full_run)
            VALUES (?, ?, ?, ?)
            """,
            (run_id, urls_json, now, 1 if full_run else 0),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        if own_conn:
            conn.close()


def update_run_status_complete(
    run_id: int,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Update status row with end time when scraper completes."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            """
            UPDATE status
            SET end_time = ?,
                duration = strftime('%s', 'now') - strftime('%s', start_time)
            WHERE run_id = ?
            """,
            (now, run_id),
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def update_run_status_analyzed(
    run_id: int,
    events_found: int,
    valid_events: int,
    linked_run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Update status row with analyzer results."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        conn.execute(
            """
            UPDATE status
            SET events_found = ?,
                valid_events = ?,
                linked_run_id = ?
            WHERE run_id = ?
            """,
            (events_found, valid_events, linked_run_id, run_id),
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def insert_events(
    events: list[dict[str, Any]],
    run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """
    Insert structured events (name, description, location, date, time, source, city).
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
                INSERT INTO events (run_id, name, description, location, date, time, category, source, city, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    name,
                    (e.get("description") or "").strip(),
                    (e.get("location") or "").strip(),
                    (e.get("date") or "").strip(),
                    (e.get("time") or "").strip(),
                    (e.get("category") or "other").strip(),
                    (e.get("source") or "").strip(),
                    (e.get("city") or "").strip(),
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
                SELECT id, name, description, location, date, time, category, source, created_at
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
                SELECT id, name, description, location, date, time, category, source, created_at
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
                "category": r["category"] or "other",
                "source": r["source"] or "",
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert DB row to dict for writer (name, description, location, date, time, category, source)."""
    return {
        "name": row["name"],
        "description": row["description"] or "",
        "location": row["location"] or "",
        "date": row["date"] or "",
        "time": row["time"] or "",
        "category": row["category"] or "other",
        "source": row["source"] or "",
    }


def insert_raw_summary(
    location: str,
    max_search: int,
    fetch_urls: int,
    raw_summary: str,
    run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
    cities: list[str] | None = None,
    search_queries: list[str] | None = None,
) -> int:
    """Store raw summary for debugging. Returns inserted row ID."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        import json
        cities_json = json.dumps(cities) if cities else None
        queries_json = json.dumps(search_queries) if search_queries else None
        cur = conn.execute(
            """
            INSERT INTO raw_summaries (run_id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, location or "", max_search, fetch_urls, cities_json, queries_json, raw_summary, now),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        if own_conn:
            conn.close()


def get_raw_summaries(
    location: str | None = None,
    limit: int = 10,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve raw summaries for debugging."""
    import json
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if location:
            cur = conn.execute(
                """
                SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
                FROM raw_summaries
                WHERE location = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (location, limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
                FROM raw_summaries
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "location": r["location"] or "",
                "max_search": r["max_search"],
                "fetch_urls": r["fetch_urls"],
                "cities": json.loads(r["cities"]) if r["cities"] else None,
                "search_queries": json.loads(r["search_queries"]) if r["search_queries"] else None,
                "raw_summary": r["raw_summary"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def get_raw_summary_by_id(summary_id: int, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Get a single raw summary by ID."""
    import json
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cur = conn.execute(
            """
            SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
            FROM raw_summaries
            WHERE id = ?
            """,
            (summary_id,),
        )
        row = cur.fetchone()
        if row:
            return {
                "id": row["id"],
                "location": row["location"] or "",
                "max_search": row["max_search"],
                "fetch_urls": row["fetch_urls"],
                "cities": json.loads(row["cities"]) if row["cities"] else None,
                "search_queries": json.loads(row["search_queries"]) if row["search_queries"] else None,
                "raw_summary": row["raw_summary"],
                "created_at": row["created_at"],
            }
        return None
    finally:
        if own_conn:
            conn.close()
