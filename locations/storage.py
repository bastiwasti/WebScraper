"""SQLite storage for the locations/Ausflüge feature.

Uses the same events.db database so the MCP server can query locations
without any configuration changes.
"""

import sqlite3
from datetime import datetime
from typing import Optional

from config import DB_PATH
from locations.models import Location


def _get_connection() -> sqlite3.Connection:
    from pathlib import Path
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_locations_db(conn: sqlite3.Connection | None = None) -> None:
    """Create the locations table if it does not exist."""
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                address TEXT,
                city TEXT,
                postal_code TEXT,
                latitude REAL,
                longitude REAL,
                category TEXT NOT NULL,
                subcategory TEXT,
                opening_hours TEXT,
                opening_hours_json TEXT,
                website_url TEXT,
                phone TEXT,
                rating REAL,
                source TEXT NOT NULL,
                source_id TEXT,
                distance_km REAL,
                url_status TEXT DEFAULT 'unchecked',
                url_last_checked TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_category ON locations(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_city ON locations(city)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_distance ON locations(distance_km)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_source ON locations(source)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_source_id ON locations(source, source_id)")
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def upsert_location(loc: Location, conn: sqlite3.Connection | None = None) -> int:
    """Insert or update a location by source + source_id. Returns the row id."""
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        # Try update first if source_id exists
        if loc.source_id:
            cur = conn.execute(
                "SELECT id FROM locations WHERE source = ? AND source_id = ?",
                (loc.source, loc.source_id),
            )
            existing = cur.fetchone()
            if existing:
                conn.execute("""
                    UPDATE locations SET
                        name=?, description=?, address=?, city=?, postal_code=?,
                        latitude=?, longitude=?, category=?, subcategory=?,
                        opening_hours=?, opening_hours_json=?, website_url=?, phone=?,
                        rating=?, distance_km=?, updated_at=?
                    WHERE id=?
                """, (
                    loc.name, loc.description, loc.address, loc.city, loc.postal_code,
                    loc.latitude, loc.longitude, loc.category, loc.subcategory,
                    loc.opening_hours, loc.opening_hours_json, loc.website_url, loc.phone,
                    loc.rating, loc.distance_km, now, existing["id"],
                ))
                conn.commit()
                return existing["id"]

        # Insert new
        cur = conn.execute("""
            INSERT INTO locations (
                name, description, address, city, postal_code,
                latitude, longitude, category, subcategory,
                opening_hours, opening_hours_json, website_url, phone,
                rating, source, source_id, distance_km,
                url_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unchecked', ?, ?)
        """, (
            loc.name, loc.description, loc.address, loc.city, loc.postal_code,
            loc.latitude, loc.longitude, loc.category, loc.subcategory,
            loc.opening_hours, loc.opening_hours_json, loc.website_url, loc.phone,
            loc.rating, loc.source, loc.source_id, loc.distance_km,
            now, now,
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        if own_conn:
            conn.close()


def upsert_locations(locations: list[Location]) -> int:
    """Bulk upsert locations. Returns count of inserted/updated rows."""
    conn = _get_connection()
    try:
        init_locations_db(conn)
        count = 0
        for loc in locations:
            upsert_location(loc, conn)
            count += 1
        return count
    finally:
        conn.close()


def get_locations(
    category: Optional[str] = None,
    city: Optional[str] = None,
    max_distance_km: Optional[float] = None,
) -> list[dict]:
    """Query locations with optional filters."""
    conn = _get_connection()
    try:
        query = "SELECT * FROM locations WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if city:
            query += " AND city = ?"
            params.append(city)
        if max_distance_km is not None:
            query += " AND distance_km <= ?"
            params.append(max_distance_km)
        query += " ORDER BY category, distance_km"
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_locations_with_urls() -> list[dict]:
    """Get all locations that have a website_url (for health checking)."""
    conn = _get_connection()
    try:
        cur = conn.execute(
            "SELECT id, name, website_url, url_status FROM locations "
            "WHERE website_url IS NOT NULL AND website_url != ''"
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def update_location_rating(
    location_id: int,
    rating: float,
    user_rating_count: Optional[int] = None,
    google_maps_url: str = "",
) -> None:
    """Update a location's rating from Google Places enrichment."""
    conn = _get_connection()
    try:
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE locations SET rating = ?, updated_at = ? WHERE id = ?",
            (rating, now, location_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_url_status(location_id: int, status: str) -> None:
    """Update the URL health status for a location."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE locations SET url_status = ?, url_last_checked = ?, updated_at = ? WHERE id = ?",
            (status, datetime.now().isoformat(), datetime.now().isoformat(), location_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_location_stats() -> list[dict]:
    """Get location counts grouped by category and city."""
    conn = _get_connection()
    try:
        cur = conn.execute("""
            SELECT category, city, COUNT(*) as count
            FROM locations
            GROUP BY category, city
            ORDER BY category, city
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_location_summary() -> dict:
    """Get a high-level summary of all locations."""
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COUNT(*) as count FROM locations GROUP BY category ORDER BY count DESC"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source, COUNT(*) as count FROM locations GROUP BY source ORDER BY count DESC"
        ).fetchall()
        url_broken = conn.execute(
            "SELECT COUNT(*) FROM locations WHERE url_status = 'broken'"
        ).fetchone()[0]
        return {
            "total": total,
            "by_category": {row["category"]: row["count"] for row in by_category},
            "by_source": {row["source"]: row["count"] for row in by_source},
            "broken_urls": url_broken,
        }
    finally:
        conn.close()
