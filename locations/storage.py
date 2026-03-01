"""PostgreSQL storage for the locations/Ausflüge feature.

Uses the same webscraper schema in the shared Postgres database.
"""

from datetime import datetime
from typing import Optional

from storage import get_connection, _execute
from locations.models import Location


def init_locations_db(conn=None) -> None:
    """Create the locations table if it does not exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS locations (
                id SERIAL PRIMARY KEY,
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
        _execute(conn, "CREATE INDEX IF NOT EXISTS idx_locations_category ON locations(category)")
        _execute(conn, "CREATE INDEX IF NOT EXISTS idx_locations_city ON locations(city)")
        _execute(conn, "CREATE INDEX IF NOT EXISTS idx_locations_distance ON locations(distance_km)")
        _execute(conn, "CREATE INDEX IF NOT EXISTS idx_locations_source ON locations(source)")
        _execute(conn, "CREATE UNIQUE INDEX IF NOT EXISTS idx_locations_source_id ON locations(source, source_id)")
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def upsert_location(loc: Location, conn=None) -> int:
    """Insert or update a location by source + source_id. Returns the row id."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        now = datetime.now().isoformat()
        # Try update first if source_id exists
        if loc.source_id:
            cur = _execute(conn,
                "SELECT id FROM locations WHERE source = %s AND source_id = %s",
                (loc.source, loc.source_id),
            )
            existing = cur.fetchone()
            if existing:
                _execute(conn, """
                    UPDATE locations SET
                        name=%s, description=%s, address=%s, city=%s, postal_code=%s,
                        latitude=%s, longitude=%s, category=%s, subcategory=%s,
                        opening_hours=%s, opening_hours_json=%s, website_url=%s, phone=%s,
                        rating=%s, distance_km=%s, updated_at=%s
                    WHERE id=%s
                """, (
                    loc.name, loc.description, loc.address, loc.city, loc.postal_code,
                    loc.latitude, loc.longitude, loc.category, loc.subcategory,
                    loc.opening_hours, loc.opening_hours_json, loc.website_url, loc.phone,
                    loc.rating, loc.distance_km, now, existing["id"],
                ))
                conn.commit()
                return existing["id"]

        # Insert new
        cur = _execute(conn, """
            INSERT INTO locations (
                name, description, address, city, postal_code,
                latitude, longitude, category, subcategory,
                opening_hours, opening_hours_json, website_url, phone,
                rating, source, source_id, distance_km,
                url_status, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'unchecked', %s, %s)
            RETURNING id
        """, (
            loc.name, loc.description, loc.address, loc.city, loc.postal_code,
            loc.latitude, loc.longitude, loc.category, loc.subcategory,
            loc.opening_hours, loc.opening_hours_json, loc.website_url, loc.phone,
            loc.rating, loc.source, loc.source_id, loc.distance_km,
            now, now,
        ))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    finally:
        if own_conn:
            conn.close()


def upsert_locations(locations: list[Location]) -> int:
    """Bulk upsert locations. Returns count of inserted/updated rows."""
    conn = get_connection()
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
    conn = get_connection()
    try:
        query = "SELECT * FROM locations WHERE 1=1"
        params = []
        if category:
            query += " AND category = %s"
            params.append(category)
        if city:
            query += " AND city = %s"
            params.append(city)
        if max_distance_km is not None:
            query += " AND distance_km <= %s"
            params.append(max_distance_km)
        query += " ORDER BY category, distance_km"
        cur = _execute(conn, query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_locations_with_urls() -> list[dict]:
    """Get all locations that have a website_url (for health checking)."""
    conn = get_connection()
    try:
        cur = _execute(conn,
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
    conn = get_connection()
    try:
        now = datetime.now().isoformat()
        _execute(conn,
            "UPDATE locations SET rating = %s, updated_at = %s WHERE id = %s",
            (rating, now, location_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_url_status(location_id: int, status: str) -> None:
    """Update the URL health status for a location."""
    conn = get_connection()
    try:
        _execute(conn,
            "UPDATE locations SET url_status = %s, url_last_checked = %s, updated_at = %s WHERE id = %s",
            (status, datetime.now().isoformat(), datetime.now().isoformat(), location_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_location_stats() -> list[dict]:
    """Get location counts grouped by category and city."""
    conn = get_connection()
    try:
        cur = _execute(conn, """
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
    conn = get_connection()
    try:
        cur = _execute(conn, "SELECT COUNT(*) AS total FROM locations")
        total = cur.fetchone()["total"]
        cur = _execute(conn,
            "SELECT category, COUNT(*) as count FROM locations GROUP BY category ORDER BY count DESC"
        )
        by_category = cur.fetchall()
        cur = _execute(conn,
            "SELECT source, COUNT(*) as count FROM locations GROUP BY source ORDER BY count DESC"
        )
        by_source = cur.fetchall()
        cur = _execute(conn,
            "SELECT COUNT(*) AS cnt FROM locations WHERE url_status = 'broken'"
        )
        url_broken = cur.fetchone()["cnt"]
        return {
            "total": total,
            "by_category": {row["category"]: row["count"] for row in by_category},
            "by_source": {row["source"]: row["count"] for row in by_source},
            "broken_urls": url_broken,
        }
    finally:
        conn.close()
