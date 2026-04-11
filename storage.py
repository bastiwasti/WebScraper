"""PostgreSQL storage for scraped events. Used for automation and by the next agents.

IMPORTANT: All tables are in the 'webscraper' schema, not 'public'. The 'public' schema has been renamed to 'Jobsearch'.
"""

import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Any
import json

from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, PG_SCHEMA


def get_connection() -> psycopg2.extensions.connection:
    """Open connection to the Postgres DB (webscraper schema)."""
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE,
        user=PG_USER, password=PG_PASSWORD,
        cursor_factory=RealDictCursor,
    )
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET search_path TO %s, public", (PG_SCHEMA,))
    return conn


def _execute(conn, sql, params=None):
    """Execute SQL via cursor (psycopg2 requires cursor-based execution)."""
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the webscraper schema."""
    cur = _execute(conn,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
        (PG_SCHEMA, table_name))
    return cur.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    cur = _execute(conn,
        "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s",
        (PG_SCHEMA, table_name, column_name))
    return cur.fetchone() is not None


def _migrate_status_table(conn) -> None:
    """Migrate status table to add new columns if they don't exist."""
    try:
        if not _table_exists(conn, 'status'):
            return

        if not _column_exists(conn, 'status', 'events_regex'):
            _execute(conn, "ALTER TABLE status ADD COLUMN events_regex INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'events_llm'):
            _execute(conn, "ALTER TABLE status ADD COLUMN events_llm INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'events_rated'):
            _execute(conn, "ALTER TABLE status ADD COLUMN events_rated INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'ratings_failed'):
            _execute(conn, "ALTER TABLE status ADD COLUMN ratings_failed INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'input_tokens'):
            _execute(conn, "ALTER TABLE status ADD COLUMN input_tokens INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'output_tokens'):
            _execute(conn, "ALTER TABLE status ADD COLUMN output_tokens INTEGER DEFAULT 0")
            conn.commit()

        if not _column_exists(conn, 'status', 'agent_type'):
            _execute(conn, "ALTER TABLE status ADD COLUMN agent_type TEXT")
            conn.commit()

        if not _column_exists(conn, 'status', 'filters'):
            _execute(conn, "ALTER TABLE status ADD COLUMN filters TEXT")
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to migrate status table: {e}")
        conn.rollback()


def _migrate_events_table(conn) -> None:
    """Migrate events table to add origin column if it doesn't exist."""
    try:
        if not _table_exists(conn, 'events'):
            return

        if not _column_exists(conn, 'events', 'origin'):
            _execute(conn, "ALTER TABLE events ADD COLUMN origin TEXT")
            conn.commit()
            print("Added 'origin' column to events table")

        _execute(conn, "CREATE INDEX IF NOT EXISTS idx_events_origin ON events(origin)")
        conn.commit()
        print("Added index on 'origin' column")
    except Exception as e:
        print(f"Warning: Failed to migrate events table: {e}")
        conn.rollback()


def _migrate_runs_table(conn) -> None:
    """Migrate runs table to drop deprecated agent column if it exists."""
    try:
        if not _table_exists(conn, 'runs'):
            return

        if _column_exists(conn, 'runs', 'agent'):
            _execute(conn, "ALTER TABLE runs DROP COLUMN agent")
            conn.commit()
            print("Dropped deprecated 'agent' column from runs table")
    except Exception as e:
        print(f"Warning: Failed to migrate runs table: {e}")
        conn.rollback()



_weekend_dates_cache = None
_weekend_dates_cache_time = None
from datetime import datetime, timedelta as _dt_timedelta, date as _dt_date


def _get_weekend_dates_with_unrated(conn, num_weekends: int, user_email: str = "deepseek", use_cache: bool = True) -> list[str]:
    """Calculate dates for next N weekends that have unrated events.
    
    Args:
        conn: Database connection
        num_weekends: Number of weekends to find
        user_email: User email to check for existing ratings
        use_cache: Whether to use cached weekend dates (default True)
    
    Returns:
        List of date strings in YYYY-MM-DD format
    """
    global _weekend_dates_cache, _weekend_dates_cache_time
    
    current_time = datetime.now()
    cache_age = (current_time - _weekend_dates_cache_time).total_seconds() if _weekend_dates_cache_time else float('inf')
    
    if use_cache and _weekend_dates_cache and cache_age < 60:
        return _weekend_dates_cache
    
    weekend_dates = []
    current_date = _dt_date.today()
    
    # Find next Saturday
    days_until_saturday = (5 - current_date.weekday()) % 7
    if days_until_saturday == 0 and current_date.weekday() == 5:
        days_until_saturday = 7
    saturday = current_date + _dt_timedelta(days=days_until_saturday)
    
    cur = conn.cursor()
    
    # Find weekends with unrated events
    week_num = 0
    while len(weekend_dates) < num_weekends * 2 and week_num < 10:
        saturday_date = saturday + _dt_timedelta(weeks=week_num)
        sunday_date = saturday_date + _dt_timedelta(days=1)
        
        saturday_str = saturday_date.strftime('%Y-%m-%d')
        sunday_str = sunday_date.strftime('%Y-%m-%d')
        
        # Check if there are unrated events on these dates
        placeholders = ','.join(['%s'] * 2)
        sql = f"""
            SELECT COUNT(*) as count
            FROM events_distinct e
            LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = %s
            WHERE e.start_datetime::date IN ({placeholders})
            AND r.event_id IS NULL
        """
        cur.execute(sql, [user_email, saturday_str, sunday_str])
        count_result = cur.fetchone()
        
        if count_result and count_result['count'] > 0:
            weekend_dates.append(saturday_str)
            weekend_dates.append(sunday_str)
        
        week_num += 1
    
    if use_cache:
        _weekend_dates_cache = weekend_dates
        _weekend_dates_cache_time = current_time
    
    return weekend_dates


def _get_weekend_dates(num_weekends: int) -> list[str]:
    """Calculate dates for next N weekends (Saturday and Sunday).
    
    Args:
        num_weekends: Number of weekends to calculate
    
    Returns:
        List of date strings in YYYY-MM-DD format
    """
    from datetime import date, timedelta
    
    weekend_dates = []
    current_date = date.today()
    
    # Find next Saturday
    days_until_saturday = (5 - current_date.weekday()) % 7
    if days_until_saturday == 0 and current_date.weekday() == 5:
        days_until_saturday = 7
    saturday = current_date + timedelta(days=days_until_saturday)
    
    # Generate dates for N weekends
    for week_num in range(num_weekends):
        saturday_date = saturday + timedelta(weeks=week_num)
        sunday_date = saturday_date + timedelta(days=1)
        weekend_dates.append(saturday_date.strftime('%Y-%m-%d'))
        weekend_dates.append(sunday_date.strftime('%Y-%m-%d'))
    
    return weekend_dates


def init_db(conn=None) -> None:
    """Create events, raw_summaries, runs, and status tables if they do not exist."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    
    required_tables = ['runs', 'status', 'events', 'raw_summaries']
    all_tables_exist = all(_table_exists(conn, table) for table in required_tables)
    
    if all_tables_exist:
        return
    
    try:
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS runs (
                id SERIAL PRIMARY KEY,
                cities TEXT,
                created_at TEXT NOT NULL,
                raw_summary_id INTEGER
            )
        """)
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS status (
                id SERIAL PRIMARY KEY,
                run_id INTEGER NOT NULL,
                linked_run_id INTEGER,
                urls TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration REAL,
                events_found INTEGER DEFAULT 0,
                valid_events INTEGER DEFAULT 0,
                events_regex INTEGER DEFAULT 0,
                events_llm INTEGER DEFAULT 0,
                events_rated INTEGER DEFAULT 0,
                ratings_failed INTEGER DEFAULT 0,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                agent_type TEXT,
                filters TEXT,
                full_run INTEGER DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (linked_run_id) REFERENCES runs(id)
            )
        """)
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                run_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_datetime TIMESTAMP,
                end_datetime TIMESTAMP,
                category TEXT,
                source TEXT,
                city TEXT,
                created_at TEXT NOT NULL,
                event_url TEXT,
                detail_scraped INTEGER DEFAULT 0,
                detail_page_html TEXT,
                detail_location TEXT,
                detail_description TEXT,
                detail_full_description TEXT,
                raw_data TEXT,
                origin TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_start_datetime
            ON events(start_datetime)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_end_datetime
            ON events(end_datetime)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_category
            ON events(category)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_run_id
            ON events(run_id)
        """)
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS raw_summaries (
                id SERIAL PRIMARY KEY,
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
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_raw_summaries_created_at
            ON raw_summaries(created_at)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_raw_summaries_run_id
            ON raw_summaries(run_id)
        """)

        # Migrate existing tables to add new columns if needed
        _migrate_status_table(conn)
        _migrate_events_table(conn)
        _migrate_runs_table(conn)

        conn.commit()
    finally:
        if own_conn:
            conn.close()


def create_run(
    cities: list[str] | None = None,
    raw_summary_id: int | None = None,
    linked_run_id: int | None = None,
    conn=None,
) -> int:
    """Create a new pipeline run and return run_id."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"

        # Convert cities list to comma-separated string
        cities_str = ",".join(cities) if cities else None

        # Check if agent column still exists (old schema)
        agent_column_exists = _column_exists(conn, 'runs', 'agent')

        if not agent_column_exists:
            # New schema: no agent column
            cur = _execute(conn,
                """
                INSERT INTO runs (cities, created_at, raw_summary_id)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (cities_str, now, raw_summary_id),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0
        else:
            # Old schema: agent column still exists, must provide a value
            cur = _execute(conn,
                """
                INSERT INTO runs (agent, cities, created_at, raw_summary_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                ('rating', cities_str, now, raw_summary_id),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0
    finally:
        if own_conn:
            conn.close()


def update_run_cities(run_id: int, cities: list[str], conn=None) -> None:
    """Update cities column with list of cities (comma-separated)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cities_str = ",".join(cities) if cities else None
        _execute(conn,
            "UPDATE runs SET cities = %s WHERE id = %s",
            (cities_str, run_id),
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def get_runs(limit: int = 20, conn=None) -> list[dict[str, Any]]:
    """Get recent runs with their counts."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cur = _execute(conn,
            """
            SELECT r.id, r.cities, r.created_at,
                    s.start_time, s.end_time, s.duration, s.events_found, s.valid_events, s.linked_run_id,
                    (SELECT COUNT(*) FROM events WHERE events.run_id = r.id) as event_count
            FROM runs r
            LEFT JOIN status s ON s.run_id = r.id
            ORDER BY r.id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": r["id"],
                "cities": r["cities"] or "",
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


def reset_database(conn=None) -> None:
    """Drop and recreate all tables (start from scratch)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        _execute(conn, "DROP TABLE IF EXISTS events CASCADE")
        _execute(conn, "DROP TABLE IF EXISTS raw_summaries CASCADE")
        _execute(conn, "DROP TABLE IF EXISTS status CASCADE")
        _execute(conn, "DROP TABLE IF EXISTS runs CASCADE")
        conn.commit()
        print("Database tables dropped successfully")

        # Recreate tables
        init_db(conn)
        print("Database tables recreated successfully")
    except Exception as e:
        print(f"Warning: Failed to reset database: {e}")
        conn.rollback()
    finally:
        if own_conn:
            conn.close()


def _parse_datetime(date_str: str, time_str: str, end_time_str: str | None = None, city: str = "", url: str = "") -> tuple[datetime | None, datetime | None]:
    """Parse date and time strings into datetime objects.

    Returns:
        (start_datetime, end_datetime) tuple
        - start_datetime: Combined date + time, or None if invalid
        - end_datetime: Combined date + end_time, or None if not provided/invalid

    Rules:
        - All-day events (no time): 00:00:00 for both start and end
        - No end time: start_datetime only, end_datetime = None
        - Multi-day events: Parse date ranges (e.g., "24.01. – 21.02.2026")
        - Smart year inference: Infer year from current date context
        - Handles German date formats, ISO formats, month names
        - Time formats: HH:MM, HH.MM, HH:MM Uhr, time ranges (HH:MM – HH:MM Uhr)
        - Date formats: Weekday prefix, day abbreviation prefix, month names
    """
    import re
    from datetime import datetime

    # Current date context for smart year inference
    CURRENT_DATE = datetime.now()
    CURRENT_YEAR = CURRENT_DATE.year
    CURRENT_MONTH = CURRENT_DATE.month

    # Helper function for smart year inference
    def _infer_year(month_num: int) -> int:
        """Smart year inference based on current month.

        If month >= current month, use current year.
        If month < current month, use current year - 1.

        Edge case: If current month is Dec and parsed month is Jan,
        assume it's for next year (Jan 2027 if Dec 2026).
        """
        if CURRENT_MONTH >= 11 and month_num == 1:
            # December context, January event -> next year
            return CURRENT_YEAR + 1
        elif CURRENT_MONTH <= 2 and month_num == 12:
            # Jan/Feb context, December event -> previous year
            return CURRENT_YEAR - 1
        elif month_num >= CURRENT_MONTH:
            # Month is current or future -> current year
            return CURRENT_YEAR
        else:
            # Month is past -> previous year
            return CURRENT_YEAR - 1

    # German month mapping
    month_map = {
        'januar': 1, 'jan': 1, 'februar': 2, 'feb': 2,
        'märz': 3, 'mrz': 3, 'maerz': 3, 'april': 4, 'apr': 4,
        'mai': 5, 'juni': 6, 'jun': 6, 'juli': 7, 'jul': 7,
        'august': 8, 'aug': 8, 'september': 9, 'sept': 9, 'oktober': 10, 'okt': 10,
        'november': 11, 'nov': 11, 'dezember': 12, 'dez': 12,
        'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6, 'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    }

    # Helper function to parse date from components
    def _parse_date_from_components(day: int, month: int, year: int) -> datetime | None:
        """Parse date from day/month/year components."""
        try:
            return datetime(year=year, month=month, day=day)
        except ValueError:
            return None

    # ========== PHASE 1: Time Range Parsing ==========
    # Handle time ranges like "20:00 – 23:30 Uhr"
    time_range_match = re.match(r'^(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*(?:Uhr)?$', str(time_str))
    if time_range_match:
        # Use first time as start time
        time_str = time_range_match.group(1)

    # Parse time
    if not time_str or time_str.lower() in ["ganzer tag", "ganzen tag", "ganzertag", "", "nicht im text angegeben"]:
        hour = 0
        minute = 0
    else:
        cleaned_time = re.sub(r'\s*Uhr', '', str(time_str).strip())
        cleaned_time = cleaned_time.strip()

        time_match = None
        for pattern in [
            r'^(\d{1,2}):(\d{2})$',  # HH:MM
            r'^(\d{1,2})\.(\d{2})$',  # HH.MM
        ]:
            time_match = re.match(pattern, cleaned_time)
            if time_match:
                break

        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
        else:
            city_url = f" [City: {city}]" if city else ""
            source_url = f" [Source: {url}]" if url else ""
            print(f"Warning{city_url}{source_url}: Could not parse time '{time_str}' - defaulting to 00:00")
            hour = 0
            minute = 0

    # ========== PHASE 2: Date Range Parsing (Multi-day events) ==========
    def _parse_date_range(date_str: str) -> tuple[datetime | None, datetime | None]:
        """Parse date range and return (start_date, end_date).

        Examples:
        - "24.01. – 21.02.2026" -> (2026-01-24, 2026-02-21)
        - "26.-27.06.2026" -> (2026-06-26, 2026-06-27)
        - "08 Feb. – 20 Dez." -> (smart inferred dates)
        """
        # Pattern 1: DD.MM. – DD.MM.YYYY
        # Updated pattern to be more flexible with separator
        range_match1 = re.match(r'^(\d{1,2}\.\d{2}\.)\s*[–-]\s*(\d{1,2}\.\d{2}\.\d{4})$', date_str)
        if range_match1:
            start_date_str = range_match1.group(1)  # "24.01."
            end_date_str = range_match1.group(2)    # "21.02.2026"

            # Parse end date
            end_date = None
            cleaned_end = re.sub(r'\s*Uhr', '', end_date_str.strip())
            match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', cleaned_end)
            if match:
                try:
                    end_day, end_month, end_year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    end_date = _parse_date_from_components(end_day, end_month, end_year)
                except ValueError:
                    pass

            # If end date parsed, infer year for start date
            if end_date and start_date_str.count('.') == 2:
                try:
                    start_day, start_month, _ = map(int, start_date_str.split('.'))
                    start_date = _parse_date_from_components(start_day, start_month, end_date.year)
                    return start_date, end_date
                except (ValueError, TypeError):
                    pass

            # If range parsing partially fails, return None to try other patterns
            return None, None

        # Pattern 2: DD.-DD.MM.YYYY
        range_match2 = re.match(r'^(\d{1,2})\.-\s*(\d{1,2})\.(\d{2})\.(\d{4})$', date_str)
        if range_match2:
            start_day = int(range_match2.group(1))
            end_day = int(range_match2.group(2))
            month = int(range_match2.group(3))
            year = int(range_match2.group(4))

            start_date = _parse_date_from_components(start_day, month, year)
            end_date = _parse_date_from_components(end_day, month, year)
            return start_date, end_date

        # Pattern 3: Month name ranges with year inference
        # "08 Feb. – 20 Dez." with year inference
        range_match3 = re.match(r'^(\d{1,2})\.([A-Za-z]{3})\.?\s*[–-]\s*(\d{1,2})\.([A-Za-z]{3})\.?$', date_str)
        if range_match3:
            start_day = int(range_match3.group(1))
            start_month_abbr = range_match3.group(2)
            end_day = int(range_match3.group(3))
            end_month_abbr = range_match3.group(4)

            start_month_lower = start_month_abbr.lower()
            end_month_lower = end_month_abbr.lower()

            if start_month_lower in month_map and end_month_lower in month_map:
                start_month_num = month_map[start_month_lower]
                end_month_num = month_map[end_month_lower]

                # Infer year for start month
                inferred_start_year = _infer_year(start_month_num)
                inferred_end_year = _infer_year(end_month_num)

                city_url = f" [City: {city}]" if city else ""
                source_url = f" [Source: {url}]" if url else ""
                print(f"Warning{city_url}{source_url}: No year in date range '{date_str}' - inferring years {inferred_start_year} / {inferred_end_year} (smart inference based on month)")

                start_date = _parse_date_from_components(start_day, start_month_num, inferred_start_year)
                end_date = _parse_date_from_components(end_day, end_month_num, inferred_end_year)
                return start_date, end_date

        return None, None

    # Check for date ranges first
    parsed_start_date, parsed_end_date = _parse_date_range(date_str)

    # ========== PHASE 3 & 4: Date Parsing with Weekday/Day Abbr Prefixes and Smart Year Inference ==========
    if parsed_end_date:
        # Multi-day event detected
        start_datetime = parsed_start_date.replace(hour=hour, minute=minute, second=0, microsecond=0) if parsed_start_date else None
        end_datetime = parsed_end_date.replace(hour=23, minute=59, second=59, microsecond=999999) if parsed_end_date else None
        return start_datetime, end_datetime

    # If not a date range, parse as single date
    parsed_date = None

    # Check for empty/incomplete dates first
    if not date_str or date_str.strip() == "":
        print(f"Warning: Date is empty - skipping event")
        return None, None

    # Remove "Uhr" if present from date
    cleaned_date = re.sub(r'\s*Uhr', '', str(date_str).strip())
    cleaned_date = re.sub(r'\s*Uhr$', '', cleaned_date)

    # Try ISO format with time: YYYY-MM-DDTHH:MM:SS
    if 'T' in cleaned_date:
        try:
            parsed_date = datetime.fromisoformat(cleaned_date.replace('Z', '+00:00'))
        except ValueError:
            pass

    # Pattern 1: YYYY-MM-DD (ISO)
    if not parsed_date:
        match = re.match(r'^(\d{4})-(\d{1,2})-(\d{1,2})$', cleaned_date)
        if match:
            try:
                year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
                parsed_date = _parse_date_from_components(day, month, year)
            except ValueError:
                pass

    # Pattern 2: Day abbreviation + DD.MM.YYYY (e.g., "So 08.02.2026")
    if not parsed_date:
        match = re.match(r'^[A-Z][a-z]{1,2}\s+(\d{1,2}\.\d{2}\.\d{4})$', cleaned_date)
        if match:
            date_part = match.group(1)
            try:
                day, month, year = map(int, date_part.split('.'))
                parsed_date = _parse_date_from_components(day, month, year)
            except (ValueError, TypeError):
                pass

    # Pattern 3: Full weekday + DD. MonthName YYYY (e.g., "Donnerstag, 12. Februar 2026")
    if not parsed_date:
        match = re.match(r'^[A-Z][a-z]+,\s*(\d{1,2})\.\s*(\w+)\s+(\d{4})$', cleaned_date)
        if match:
            day_str, month_name, year_str = match.groups()
            month_lower = month_name.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    parsed_date = _parse_date_from_components(int(day_str), month_num, int(year_str))
                except ValueError:
                    pass

    # Pattern 4: DD.MM.YYYY (German standard)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', cleaned_date)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                parsed_date = _parse_date_from_components(day, month, year)
            except ValueError:
                pass

    # Pattern 5: DD/MM/YYYY (European)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', cleaned_date)
        if match:
            try:
                day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                parsed_date = _parse_date_from_components(day, month, year)
            except ValueError:
                pass

    # Pattern 6: DD. MonthName YYYY (German month name)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})[\s.]+(\w+)[\s.]+(\d{4})$', cleaned_date)
        if match:
            day_str, month_name, year_str = match.groups()
            month_lower = month_name.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    parsed_date = _parse_date_from_components(int(day_str), month_num, int(year_str))
                except ValueError:
                    pass

    # Pattern 7: DD[. ]MonthName (dot OR space separator, no year - smart inference)
    # Matches: "8. Februar", "08. Feb", "8. Januar", "18 Mär"
    # Combines dot and space separators in one pattern
    if not parsed_date:
        match = re.match(r'^(\d{1,2})[.\s]+(\w+)$', cleaned_date)
        if match:
            day_str, month_name = match.groups()
            month_lower = month_name.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    city_url = f" [City: {city}]" if city else ""
                    source_url = f" [Source: {url}]" if url else ""
                    print(f"Warning{city_url}{source_url}: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month)")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # Pattern 7b: DD. MonthName. (dot separator + trailing dot, no year)
    # Matches: "08. Feb." (dot before month and trailing dot)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})\.(\w+)\.$', cleaned_date)
        if match:
            day_str, month_name = match.groups()
            month_lower = month_name.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    city_url = f" [City: {city}]" if city else ""
                    source_url = f" [Source: {url}]" if url else ""
                    print(f"Warning{city_url}{source_url}: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month) [Pattern 7b matched]")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # Pattern 7c: DD. MonthName (space separator, no year - smart inference)
    # Matches: "08. Feb" or "8. Feb" (space before month)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})\s+(\w+)$', cleaned_date)
        if match:
            day_str, month_name = match.groups()
            month_lower = month_name.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    print(f"Warning: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month) [Pattern 7c matched]")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # Pattern 7d: DD MonthName. (space separator + trailing dot, no year - smart inference)
    # Matches: "08 Feb." (space before month and trailing dot)
    if not parsed_date:
        match = re.match(r'^(\d{1,2})\s+([A-Za-z]{3})\.$', cleaned_date)
        if match:
            day_str, month_abbr = match.groups()
            month_lower = month_abbr.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    print(f"Warning: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month) [Pattern 7d matched]")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # Pattern 7b: DD. MonthName. (no year, with trailing dot - smart inference)
    # Handles "08 Feb." where trailing dot is part of abbreviation, not separator
    if not parsed_date:
        # Match: "08 Feb." where month is abbreviation (3 chars)
        match = re.match(r'^(\d{1,2})\s+([A-Za-z]{3})\.$', cleaned_date)
        if match:
            day_str, month_abbr = match.groups()
            month_lower = month_abbr.lower()
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    city_url = f" [City: {city}]" if city else ""
                    source_url = f" [Source: {url}]" if url else ""
                    print(f"Warning{city_url}{source_url}: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month)")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # Pattern 7b: DD. MonthName. (no year, with trailing dot - smart inference)
    # Handles "08 Feb." where the dot is trailing, not part of the abbreviation
    if not parsed_date:
        match = re.match(r'^(\d{1,2})\.\s*(\w+)\.$', cleaned_date)
        if match:
            day_str, month_name = match.groups()
            month_lower = month_name.lower()
            # Check if month_name is in month_map (handles both full names and abbreviations)
            if month_lower in month_map:
                try:
                    month_num = month_map[month_lower]
                    inferred_year = _infer_year(month_num)
                    city_url = f" [City: {city}]" if city else ""
                    source_url = f" [Source: {url}]" if url else ""
                    print(f"Warning{city_url}{source_url}: No year in date '{date_str}' - inferring year {inferred_year} (smart inference based on month)")
                    parsed_date = _parse_date_from_components(int(day_str), month_num, inferred_year)
                except ValueError:
                    pass

    # ========== PHASE 5: Incomplete Date Detection ==========
    # Pattern: "14. 02." (incomplete - missing year)
    # incomplete_match = re.match(r'^(\d{1,2})\.\s*(\d{2})\.$', cleaned_date)
    # if incomplete_match and not parsed_date:
    #     city_url = f" [City: {city}]" if city else ""
    #     source_url = f" [Source: {url}]" if url else ""
    #     print(f"Warning{city_url}{source_url}: Could not parse date '{date_str}' - incomplete date format (missing year). Expected: DD.MM.YYYY or DD. MonthName YYYY")
        return None, None

    if not parsed_date:
        city_url = f" [City: {city}]" if city else ""
        source_url = f" [Source: {url}]" if url else ""
        print(f"Warning{city_url}{source_url}: Could not parse date '{date_str}' - returning None")
        return None, None

    # Create start datetime
    start_datetime = parsed_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Parse end time if provided (separate from date ranges)
    if end_time_str and not parsed_end_date:
        cleaned_end_time = re.sub(r'\s*Uhr', '', str(end_time_str).strip())
        cleaned_end_time = cleaned_end_time.strip()

        # Handle time ranges in end_time
        end_time_range_match = re.match(r'^(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})\s*(?:Uhr)?$', cleaned_end_time)
        if end_time_range_match:
            cleaned_end_time = end_time_range_match.group(1)

        end_time_match = None
        for pattern in [
            r'^(\d{1,2}):(\d{2})$',
            r'^(\d{1,2})\.(\d{2})$',
        ]:
            end_time_match = re.match(pattern, cleaned_end_time)
            if end_time_match:
                break

        if end_time_match:
            end_hour = int(end_time_match.group(1))
            end_minute = int(end_time_match.group(2))
            end_datetime = parsed_date.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            return start_datetime, end_datetime

    # All-day event or no end time: same for both
    return start_datetime, start_datetime


def create_run_status(
    run_id: int,
    urls: list[str],
    full_run: bool = False,
    start_time: str | None = None,
    events_regex: int = 0,
    events_rated: int = 0,
    conn=None,
) -> int:
    """Create a status row for a run."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = start_time if start_time else datetime.utcnow().isoformat() + "Z"
        urls_json = json.dumps(urls)
        full_run_int = 1 if full_run else 0
        
        # Check if events_rated column exists
        events_rated_exists = _column_exists(conn, 'status', 'events_rated')
        
        if events_rated_exists:
            # New schema: include events_rated
            cur = _execute(conn,
                """
                INSERT INTO status (run_id, urls, start_time, full_run, events_regex, events_rated)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (run_id, urls_json, now, full_run_int, events_regex, events_rated),
            )
        else:
            # Old schema: don't include events_rated (for backward compatibility)
            cur = _execute(conn,
                """
                INSERT INTO status (run_id, urls, start_time, full_run, events_regex)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (run_id, urls_json, now, full_run_int, events_regex),
            )
        
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    finally:
        if own_conn:
            conn.close()


def update_run_status_complete(
    run_id: int,
    end_time: str | None = None,
    conn=None,
) -> None:
    """Update status row with end time when pipeline completes."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if end_time:
            _execute(conn,
                """
                UPDATE status
                SET end_time = %s
                WHERE run_id = %s
                """,
                (end_time, run_id),
            )
        _execute(conn,
            """
            UPDATE status
            SET duration = EXTRACT(EPOCH FROM NOW() - start_time::timestamp)
            WHERE run_id = %s
            """,
            (run_id,),
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def update_run_status_analyzed(
    run_id: int,
    events_found: int,
    valid_events: int,
    events_regex: int = 0,
    events_llm: int = 0,
    events_rated: int = 0,
    linked_run_id: int | None = None,
    conn=None,
) -> None:
    """Update status row with analyzer results (ADD to existing values)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        # Get current values
        cur = _execute(conn,
            "SELECT events_found, valid_events, events_regex, events_llm, events_rated, linked_run_id FROM status WHERE run_id = %s",
            (run_id,)
        )
        row = cur.fetchone()
        if row:
            current_events_found = row["events_found"] or 0
            current_valid_events = row["valid_events"] or 0
            current_events_regex = row["events_regex"] or 0
            current_events_llm = row["events_llm"] or 0
            current_events_rated = row["events_rated"] or 0
            current_linked_run_id = row["linked_run_id"]

            # Calculate new values (ADD, not REPLACE)
            new_events_found = current_events_found + events_found
            new_valid_events = current_valid_events + valid_events
            new_events_regex = current_events_regex + events_regex
            new_events_llm = current_events_llm + events_llm
            new_events_rated = current_events_rated + events_rated
            new_linked_run_id = linked_run_id if linked_run_id else current_linked_run_id

            _execute(conn,
                """
                UPDATE status
                SET events_found = %s,
                    valid_events = %s,
                    events_regex = %s,
                    events_llm = %s,
                    events_rated = %s,
                    linked_run_id = %s
                WHERE run_id = %s
                """,
                (new_events_found, new_valid_events, new_events_regex, new_events_llm, new_events_rated, new_linked_run_id, run_id),
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to update run status: {e}")
        conn.rollback()
    finally:
        if own_conn:
            conn.close()


def create_rating_status(
    run_id: int,
    filters: dict | None = None,
    conn=None,
) -> int:
    """Create a status row for rating agent."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        
        # Convert filters dict to JSON string
        filters_json = json.dumps(filters) if filters else None
        
        # Check which schema we're using
        agent_type_exists = _column_exists(conn, 'status', 'agent_type')
        filters_exists = _column_exists(conn, 'status', 'filters')
        
        if agent_type_exists and filters_exists:
            # New schema: agent_type and filters columns exist
            cur = _execute(conn,
                """
                INSERT INTO status (run_id, agent_type, filters, start_time)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (run_id, 'rating', filters_json, now),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0
        else:
            # Old schema: agent_type and filters columns don't exist yet, use urls column
            cur = _execute(conn,
                """
                INSERT INTO status (run_id, urls, start_time)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (run_id, filters_json, now),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"] if row else 0
    except Exception as e:
        print(f"Warning: Failed to create rating status: {e}")
        if own_conn:
            conn.rollback()
        return 0
    finally:
        if own_conn:
            conn.close()


def update_rating_status_complete(
    run_id: int,
    events_rated: int,
    ratings_failed: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    conn=None,
) -> None:
    """Update rating status row with completion metrics."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        
        # Check which schema we're using
        events_rated_exists = _column_exists(conn, 'status', 'events_rated')
        agent_type_exists = _column_exists(conn, 'status', 'agent_type')
        
        if events_rated_exists and agent_type_exists:
            # New schema: all columns exist
            _execute(conn,
                """
                UPDATE status
                SET events_rated = %s,
                    ratings_failed = %s,
                    input_tokens = %s,
                    output_tokens = %s,
                    end_time = %s,
                    duration = EXTRACT(EPOCH FROM NOW() - start_time::timestamp)
                WHERE run_id = %s AND agent_type = 'rating'
                """,
                (events_rated, ratings_failed, input_tokens, output_tokens,
                 datetime.utcnow().isoformat() + "Z", run_id),
            )
            conn.commit()
        else:
            # Old schema: new columns don't exist yet
            _execute(conn,
                """
                UPDATE status
                SET end_time = %s,
                    duration = EXTRACT(EPOCH FROM NOW() - start_time::timestamp)
                WHERE run_id = %s
                """,
                (datetime.utcnow().isoformat() + "Z", run_id),
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to update rating status: {e}")
        if own_conn:
            conn.rollback()
    finally:
        if own_conn:
            conn.close()


def insert_events(
    events: list[dict[str, Any]],
    run_id: int | None = None,
    conn=None,
) -> int:
    """
    Insert structured events (name, description, location, start_datetime, end_datetime, source, city).
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
            # Level 1 date is always available from calendar listing
            # Level 2 detail_date is only used for validation, not as primary date source
            date_to_parse = e.get("date") or ""

            # Parse date (Level 1 date as primary)
            start_datetime, end_datetime = _parse_datetime(
                date_to_parse,
                e.get("time") or "",
                e.get("end_time"),
                e.get("city", ""),
                e.get("source", ""),
            )

            if not start_datetime:
                # Event has no parseable date from either Level 1 or Level 2
                # Don't skip - use empty date as indicator of missing info
                print(f"Warning: Event has no parseable date: {name[:50]}")
                start_datetime = None
                end_datetime = None

            # Extract Level 2 data for database columns
            raw_data_dict = e.get("raw_data")
            detail_description = ""
            detail_full_description = ""
            detail_location = ""
            detail_page_html = ""
            detail_end_time = ""

            if raw_data_dict and isinstance(raw_data_dict, dict):
                detail_description = raw_data_dict.get("detail_description", "")
                detail_full_description = raw_data_dict.get("detail_full_description", "")
                detail_location = raw_data_dict.get("detail_location", "")
                detail_page_html = raw_data_dict.get("html", "")
                detail_end_time = raw_data_dict.get("detail_end_time", "")

            # Get event URL if available
            event_url = e.get("event_url", "")

            # Use Level 2 data when available, otherwise fall back to Level 1
            # Priority: Level 2 > Level 1
            desc_to_use = detail_description if detail_description else (e.get("description") or "").strip()
            loc_to_use = detail_location if detail_location else (e.get("location") or "").strip()
            time_to_use = detail_end_time if detail_end_time else (e.get("end_time") or "")
            level1_time = e.get("time") or ""

            # Combine Level 1 time with Level 2 end_time if available
            if detail_end_time and level1_time:
                # Level 2 has end_time, Level 1 has start time - use both
                pass  # Already handled in end_datetime parsing
            elif level1_time:
                time_to_use = level1_time


            _execute(conn,
                """
                    INSERT INTO events (run_id, name, description, location, start_datetime, end_datetime, category, source, city, created_at, event_url, detail_scraped, detail_page_html, detail_description, detail_location, detail_full_description, origin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        name,
                        desc_to_use,
                        loc_to_use,
                        start_datetime.isoformat() if start_datetime else None,
                        end_datetime.isoformat() if end_datetime else None,
                        (e.get("category") or "other").strip(),
                        (e.get("source") or "").strip(),
                        (e.get("city") or "").strip(),
                        now,
                        event_url,
                        1 if detail_page_html else 0,
                        detail_page_html,
                        detail_description[:2000],
                        detail_location[:500],
                        detail_full_description,
                        e.get("origin", ""),
                    ),
            )
            count += 1
        conn.commit()
        return count
    finally:
        if own_conn:
            conn.close()


def init_events_distinct_db(conn=None) -> None:
    """Create the events_distinct table if it doesn't exist.

    This table holds deduplicated events with stable IDs for ratings and ML.
    Dedup key: (name, start_datetime, origin) — location is NOT part of the key
    so that Level 2 enrichment doesn't create duplicates.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    
    if _table_exists(conn, 'events_distinct'):
        return
    
    try:
        _execute(conn, """
            CREATE TABLE IF NOT EXISTS events_distinct (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_datetime TIMESTAMP,
                end_datetime TIMESTAMP,
                category TEXT,
                source TEXT,
                city TEXT,
                origin TEXT,
                event_url TEXT,
                detail_description TEXT,
                detail_full_description TEXT,
                rating NUMERIC(3,1) CHECK(rating IS NULL OR (rating >= 1 AND rating <= 5)),
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                seen_count INTEGER DEFAULT 1,
                UNIQUE(name, start_datetime, origin)
            )
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_distinct_start
            ON events_distinct(start_datetime)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_distinct_category
            ON events_distinct(category)
        """)
        _execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_events_distinct_city
            ON events_distinct(city)
        """)
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def rebuild_events_distinct(conn=None) -> int:
    """Rebuild events_distinct from the raw events table.

    Upserts all unique events (by name + start_datetime + origin).
    Picks the most informative row per group (prefers rows with
    detail_description, then latest created_at).
    Preserves user-set ratings — only scraper-derived fields are updated.

    Returns number of rows in events_distinct after rebuild.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        # Save ratings before rebuild
        saved_ratings = []
        if _table_exists(conn, 'events_distinct'):
            cur = _execute(conn,
                "SELECT name, start_datetime, rating FROM events_distinct WHERE rating IS NOT NULL")
            saved_ratings = cur.fetchall()

        init_events_distinct_db(conn)

        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events_distinct")
        before = cur.fetchone()["cnt"]

        # Use CTE to pick the best (most informative) row per group,
        # then join with aggregated counts for first/last seen.
        _execute(conn, """
            WITH ranked AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY name, start_datetime, origin
                        ORDER BY
                            CASE WHEN detail_description IS NOT NULL AND detail_description != '' THEN 0 ELSE 1 END,
                            created_at DESC
                    ) AS rn
                FROM events
                WHERE name IS NOT NULL AND name != ''
            ),
            best AS (
                SELECT * FROM ranked WHERE rn = 1
            ),
            counts AS (
                SELECT name, start_datetime, origin,
                    MIN(created_at) AS first_seen_at,
                    MAX(created_at) AS last_seen_at,
                    COUNT(*) AS seen_count
                FROM events
                WHERE name IS NOT NULL AND name != ''
                GROUP BY name, start_datetime, origin
            )
            INSERT INTO events_distinct (
                name, description, location, start_datetime, end_datetime,
                category, source, city, origin, event_url,
                detail_description, detail_full_description,
                first_seen_at, last_seen_at, seen_count
            )
            SELECT
                best.name,
                best.description,
                best.location,
                best.start_datetime,
                best.end_datetime,
                best.category,
                best.source,
                best.city,
                best.origin,
                best.event_url,
                best.detail_description,
                best.detail_full_description,
                counts.first_seen_at,
                counts.last_seen_at,
                counts.seen_count
            FROM best
            JOIN counts ON best.name = counts.name
                AND best.start_datetime = counts.start_datetime
                AND COALESCE(best.origin, '') = COALESCE(counts.origin, '')
            ON CONFLICT(name, start_datetime, origin) DO UPDATE SET
                description = COALESCE(NULLIF(excluded.description, ''), events_distinct.description),
                location = COALESCE(NULLIF(excluded.location, ''), events_distinct.location),
                end_datetime = COALESCE(excluded.end_datetime, events_distinct.end_datetime),
                category = COALESCE(NULLIF(excluded.category, ''), events_distinct.category),
                source = COALESCE(NULLIF(excluded.source, ''), events_distinct.source),
                city = COALESCE(NULLIF(excluded.city, ''), events_distinct.city),
                event_url = COALESCE(NULLIF(excluded.event_url, ''), events_distinct.event_url),
                detail_description = COALESCE(NULLIF(excluded.detail_description, ''), events_distinct.detail_description),
                detail_full_description = COALESCE(NULLIF(excluded.detail_full_description, ''), events_distinct.detail_full_description),
                last_seen_at = excluded.last_seen_at,
                seen_count = excluded.seen_count
        """)

        # Fill empty fields from other rows in the same group
        # (the "best" row may lack some fields that older rows have, e.g. city)
        _execute(conn, """
            UPDATE events_distinct SET
                city = COALESCE(NULLIF(city, ''), (
                    SELECT city FROM events
                    WHERE events.name = events_distinct.name
                        AND events.start_datetime = events_distinct.start_datetime
                        AND city IS NOT NULL AND city != ''
                    LIMIT 1
                ))
            WHERE city IS NULL OR city = ''
        """)

        # Restore saved ratings
        if saved_ratings:
            for row in saved_ratings:
                _execute(conn,
                    "UPDATE events_distinct SET rating = %s WHERE name = %s AND start_datetime = %s",
                    (row["rating"], row["name"], row["start_datetime"]),
                )
            print(f"  Restored {len(saved_ratings)} user ratings")

        conn.commit()

        cur = _execute(conn, "SELECT COUNT(*) AS cnt FROM events_distinct")
        after = cur.fetchone()["cnt"]
        new_events = after - before
        print(f"  events_distinct: {after} unique events ({new_events} new)")
        return after
    finally:
        if own_conn:
            conn.close()


def get_events(
    since_days: int | None = None,
    limit: int = 200,
    conn=None,
) -> list[dict[str, Any]]:
    """
    Load events for newsletter. If since_days is set, only return events
    created in last N days; otherwise return latest by created_at.
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if since_days is not None:
            cur = _execute(conn,
                """
                SELECT id, name, description, location, start_datetime, end_datetime, category, source, city, created_at, origin
                FROM events
                WHERE created_at::date >= CURRENT_DATE - %s * INTERVAL '1 day'
                ORDER BY start_datetime DESC
                LIMIT %s
                """,
                (since_days, limit),
            )
        else:
            cur = _execute(conn,
                """
                SELECT id, name, description, location, start_datetime, end_datetime, category, source, city, created_at, origin
                FROM events
                ORDER BY start_datetime DESC
                LIMIT %s
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
                "start_datetime": r["start_datetime"].isoformat() if r["start_datetime"] else None,
                "end_datetime": r["end_datetime"].isoformat() if r["end_datetime"] else None,
                "category": r["category"] or "other",
                "source": r["source"] or "",
                "city": r["city"] or "",
                "created_at": r["created_at"],
                "origin": r["origin"] or "",
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def row_to_dict(row: dict) -> dict[str, Any]:
    """Convert DB row to dict for writer (name, description, location, start_datetime, end_datetime, category, source)."""
    return {
        "name": row["name"],
        "description": row["description"] or "",
        "location": row["location"] or "",
        "start_datetime": row["start_datetime"],
        "end_datetime": row["end_datetime"],
        "category": row["category"] or "other",
        "source": row["source"] or "",
    }


def insert_raw_summary(
    location: str,
    max_search: int,
    raw_summary: str,
    run_id: int | None = None,
    conn=None,
    cities: list[str] | None = None,
    search_queries: list[str] | None = None,
    fetch_urls: int = 0,
) -> int:
    """Store raw summary for debugging. Returns inserted row ID."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = datetime.utcnow().isoformat() + "Z"
        cities_json = json.dumps(cities) if cities else None
        queries_json = json.dumps(search_queries) if search_queries else None
        cur = _execute(conn,
            """
            INSERT INTO raw_summaries (run_id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (run_id, location or "", max_search, fetch_urls, cities_json, queries_json, raw_summary, now),
        )
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0
    finally:
        if own_conn:
            conn.close()


def get_raw_summaries(
    location: str | None = None,
    limit: int = 10,
    conn=None,
) -> list[dict[str, Any]]:
    """Retrieve raw summaries for debugging."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if location:
            cur = _execute(conn,
                """
                SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
                FROM raw_summaries
                WHERE location = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (location, limit),
            )
        else:
            cur = _execute(conn,
                """
                SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
                FROM raw_summaries
                ORDER BY created_at DESC
                LIMIT %s
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


def get_raw_summary_by_id(summary_id: int, conn=None) -> dict[str, Any] | None:
    """Get a single raw summary by ID."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cur = _execute(conn,
            """
            SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
            FROM raw_summaries
            WHERE id = %s
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


def get_raw_summary_by_run_id(run_id: int, conn=None) -> dict[str, Any] | None:
    """Get raw summary associated with a specific run ID."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        cur = _execute(conn,
            """
            SELECT id, location, max_search, fetch_urls, cities, search_queries, raw_summary, created_at
            FROM raw_summaries
            WHERE run_id = %s
            """,
            (run_id,),
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


def count_unrated_events(
    date_filter: str | None = None,
    days_filter: int | None = None,
    today_only: bool = False,
    tomorrow_only: bool = False,
    weekends_filter: int | None = None,
    user_email: str = "deepseek",
    conn=None
) -> int:
    """Count unrated events from events_distinct with optional date filters.
    
    Args:
        date_filter: Only events on this specific date (YYYY-MM-DD)
        days_filter: Only events within next N days
        today_only: Only events from today
        tomorrow_only: Only events from tomorrow
        weekends_filter: Only events for next N weekends
        user_email: User email to check for existing ratings (default: "deepseek")
        conn: Optional database connection
    
    Returns:
        Count of unrated events
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        sql = """
            SELECT COUNT(*)
            FROM events_distinct e
            LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = %s
            WHERE r.event_id IS NULL
        """
        params = [user_email]

        if date_filter:
            sql += " AND e.start_datetime::date = %s"
            params.append(date_filter)
        elif days_filter:
            sql += " AND e.start_datetime::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL %s"
            params.append(f"'{days_filter} days'")
        elif today_only:
            sql += " AND e.start_datetime::date = CURRENT_DATE"
        elif tomorrow_only:
            sql += " AND e.start_datetime::date = CURRENT_DATE + INTERVAL '1 day'"
        elif weekends_filter:
            weekend_dates = _get_weekend_dates_with_unrated(conn, weekends_filter, user_email)
            if weekend_dates:
                placeholders = ','.join(['%s'] * len(weekend_dates))
                sql += f" AND e.start_datetime::date IN ({placeholders})"
                params.extend(weekend_dates)
            else:
                return 0

        cur = _execute(conn, sql, params)
        row = cur.fetchone()
        return row["count"] if row else 0
    finally:
        if own_conn:
            conn.close()


def get_unrated_events(
    limit: int = 20,
    offset: int = 0,
    date_filter: str | None = None,
    days_filter: int | None = None,
    today_only: bool = False,
    tomorrow_only: bool = False,
    weekends_filter: int | None = None,
    user_email: str = "deepseek",
    conn=None
) -> list[dict]:
    """Fetch unrated events from events_distinct with optional date filters.
    
    Args:
        limit: Max events to return
        offset: Pagination offset
        date_filter: Only events on this specific date (YYYY-MM-DD)
        days_filter: Only events within next N days
        today_only: Only events from today
        tomorrow_only: Only events from tomorrow
        weekends_filter: Only events for next N weekends
        user_email: User email to check for existing ratings (default: "deepseek")
        conn: Optional database connection
    
    Returns:
        List of event dicts with id, name, description, category, location, city, start_datetime
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        sql = """
            SELECT e.id, e.name, e.description, e.category, e.location, e.city, e.start_datetime
            FROM events_distinct e
            LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = %s
            WHERE r.event_id IS NULL
        """
        params = [user_email]

        if date_filter:
            sql += " AND e.start_datetime::date = %s"
            params.append(date_filter)
        elif days_filter:
            sql += " AND e.start_datetime::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL %s"
            params.append(f"'{days_filter} days'")
        elif today_only:
            sql += " AND e.start_datetime::date = CURRENT_DATE"
        elif tomorrow_only:
            sql += " AND e.start_datetime::date = CURRENT_DATE + INTERVAL '1 day'"
        elif weekends_filter:
            weekend_dates = _get_weekend_dates_with_unrated(conn, weekends_filter, user_email, use_cache=False)
            if weekend_dates:
                placeholders = ','.join(['%s'] * len(weekend_dates))
                sql += f" AND e.start_datetime::date IN ({placeholders})"
                params.extend(weekend_dates)
            else:
                return []

        sql += " ORDER BY e.id ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur = _execute(conn, sql, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        if own_conn:
            conn.close()


def insert_event_rating(
    event_id: int,
    rating: float,
    rating_inhaltlich: float | None = None,
    rating_ort: float | None = None,
    rating_ausstattung: float | None = None,
    rating_interaktion: float | None = None,
    rating_kosten: float | None = None,
    rating_reason: str | None = None,
    user_email: str = "deepseek",
    conn=None
) -> bool:
    """Insert a rating into event_ratings table with detailed criteria.

    Args:
        event_id: Event ID from events_distinct
        rating: Overall rating value (1-5)
        rating_inhaltlich: Content suitability rating (1-5)
        rating_ort: Location/accessibility rating (1-5)
        rating_ausstattung: Facilities for small children rating (1-5)
        rating_interaktion: Interaction level rating (1-5)
        rating_kosten: Cost rating (1-5)
        rating_reason: Short explanation for the rating
        user_email: User email (default: "deepseek")
        conn: Optional database connection

    Returns:
        True if inserted successfully, False otherwise
    """
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        _execute(conn, """
            INSERT INTO event_ratings (
                event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung,
                rating_interaktion, rating_kosten, rating_reason, user_email, rated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (event_id, user_email) DO UPDATE
            SET
                rating = EXCLUDED.rating,
                rating_inhaltlich = EXCLUDED.rating_inhaltlich,
                rating_ort = EXCLUDED.rating_ort,
                rating_ausstattung = EXCLUDED.rating_ausstattung,
                rating_interaktion = EXCLUDED.rating_interaktion,
                rating_kosten = EXCLUDED.rating_kosten,
                rating_reason = EXCLUDED.rating_reason,
                rated_at = EXCLUDED.rated_at
        """, (
            event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung,
            rating_interaktion, rating_kosten, rating_reason, user_email
        ))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        if own_conn:
            conn.close()


__all__ = [
    "get_connection",
    "init_db",
    "create_run",
    "get_runs",
    "update_run_cities",
    "create_run_status",
    "update_run_status_complete",
    "update_run_status_analyzed",
    "insert_events",
    "get_events",
    "row_to_dict",
    "insert_raw_summary",
    "get_raw_summaries",
    "reset_database",
    "_parse_datetime",
    "get_raw_summary_by_id",
    "get_raw_summary_by_run_id",
    "count_unrated_events",
    "get_unrated_events",
    "insert_event_rating",
    "create_rating_status",
    "update_rating_status_complete",
]
