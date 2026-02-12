"""SQLite storage for scraped events. Used for automation and by the next agents."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
import json

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Open connection to the events DB. Creates file and table if needed."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_status_table(conn: sqlite3.Connection) -> None:
    """Migrate status table to add new columns if they don't exist."""
    try:
        # Check if status table exists
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='status'")
        table_exists = cur.fetchone() is not None
        
        if not table_exists:
            return  # Table doesn't exist yet, will be created with new columns
        
        # Check if events_regex column exists
        cur = conn.execute("PRAGMA table_info(status)")
        columns = [row["name"] for row in cur.fetchall()]
        
        if "events_regex" not in columns:
            conn.execute("ALTER TABLE status ADD COLUMN events_regex INTEGER DEFAULT 0")
            conn.commit()
        
        if "events_llm" not in columns:
            conn.execute("ALTER TABLE status ADD COLUMN events_llm INTEGER DEFAULT 0")
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to migrate status table: {e}")


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
                cities TEXT,
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
                events_regex INTEGER DEFAULT 0,
                events_llm INTEGER DEFAULT 0,
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
                start_datetime DATETIME,
                end_datetime DATETIME,
                category TEXT,
                source TEXT,
                city TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_start_datetime
            ON events(start_datetime)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_end_datetime
            ON events(end_datetime)
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
        
        # Migrate existing status table to add new columns if needed
        _migrate_status_table(conn)
        
        conn.commit()
    finally:
        if own_conn:
            conn.close()


def create_run(
    agent: str,
    cities: list[str] | None = None,
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
        
        # Convert cities list to comma-separated string
        cities_str = ",".join(cities) if cities else None
        
        cur = conn.execute(
            """
            INSERT INTO runs (agent, cities, created_at, raw_summary_id)
            VALUES (?, ?, ?, ?)
            """,
            (agent, cities_str, now, raw_summary_id),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        if own_conn:
            conn.close()


def append_to_agent(run_id: int, agent_name: str, conn: sqlite3.Connection | None = None) -> None:
    """Append agent name to agent column (comma-separated)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        # Get current agent string
        cur = conn.execute("SELECT agent FROM runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        if row and row["agent"]:
            current_agent = row["agent"]
            # Append if not already present
            if agent_name not in current_agent:
                new_agent = f"{current_agent}, {agent_name}"
                conn.execute(
                    "UPDATE runs SET agent = ? WHERE id = ?",
                    (new_agent, run_id),
                )
                conn.commit()
        else:
            # Set initial agent
            conn.execute(
                "UPDATE runs SET agent = ? WHERE id = ?",
                (agent_name, run_id),
            )
            conn.commit()
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
            SELECT r.id, r.agent, r.cities, r.created_at,
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


def reset_database(conn: sqlite3.Connection | None = None) -> None:
    """Drop and recreate all tables (start from scratch)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS events")
        conn.execute("DROP TABLE IF EXISTS raw_summaries")
        conn.execute("DROP TABLE IF EXISTS runs")
        conn.execute("DROP TABLE IF EXISTS status")
        print("✓ Database tables dropped successfully")
        
        # Recreate tables
        init_db(conn)
        print("✓ Database tables recreated successfully")
    except Exception as e:
        print(f"Warning: Failed to reset database: {e}")
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
    conn: sqlite3.Connection | None = None,
) -> int:
    """Create a status row for a run."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        now = start_time if start_time else datetime.utcnow().isoformat() + "Z"
        import json
        urls_json = json.dumps(urls)
        cur = conn.execute(
            """
            INSERT INTO status (run_id, urls, start_time, full_run, events_regex)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, urls_json, now, full_run, events_regex),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        if own_conn:
            conn.close()


def update_run_status_complete(
    run_id: int,
    end_time: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Update status row with end time when pipeline completes."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        if end_time:
            conn.execute(
                """
                UPDATE status
                SET end_time = ?
                WHERE run_id = ?
                """,
                (end_time, run_id),
            )
            conn.execute(
                """
                UPDATE status
                SET duration = strftime('%s', 'now') - strftime('%s', start_time)
                WHERE run_id = ?
                """,
                (run_id,),
            )
        else:
            conn.execute(
                """
                UPDATE status
                SET duration = strftime('%s', 'now') - strftime('%s', start_time)
                WHERE run_id = ?
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
    linked_run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Update status row with analyzer results (ADD to existing values)."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    try:
        init_db(conn)
        # Get current values
        cur = conn.execute(
            "SELECT events_found, valid_events, events_regex, events_llm, linked_run_id FROM status WHERE run_id = ?",
            (run_id,)
        )
        row = cur.fetchone()
        if row:
            current_events_found = row["events_found"] or 0
            current_valid_events = row["valid_events"] or 0
            current_events_regex = row["events_regex"] or 0
            current_events_llm = row["events_llm"] or 0
            current_linked_run_id = row["linked_run_id"]

            # Calculate new values (ADD, not REPLACE)
            new_events_found = current_events_found + events_found
            new_valid_events = current_valid_events + valid_events
            new_events_regex = current_events_regex + events_regex
            new_events_llm = current_events_llm + events_llm
            new_linked_run_id = linked_run_id if linked_run_id else current_linked_run_id

            conn.execute(
                """
                UPDATE status
                SET events_found = ?,
                    valid_events = ?,
                    events_regex = ?,
                    events_llm = ?,
                    linked_run_id = ?
                WHERE run_id = ?
                """,
                (new_events_found, new_valid_events, new_events_regex, new_events_llm, new_linked_run_id, run_id),
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to update run status: {e}")
    finally:
        if own_conn:
            conn.close()


def insert_events(
    events: list[dict[str, Any]],
    run_id: int | None = None,
    conn: sqlite3.Connection | None = None,
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
            detail_location = ""
            detail_page_html = ""
            detail_end_time = ""
            
            if raw_data_dict and isinstance(raw_data_dict, dict):
                detail_description = raw_data_dict.get("detail_description", "")
                detail_location = raw_data_dict.get("detail_location", "")
                detail_page_html = raw_data_dict.get("html", "")
                detail_end_time = raw_data_dict.get("detail_end_time", "")
            
            # Set detail_scraped flag
            detail_scraped = 1 if detail_page_html else 0
            
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


            conn.execute(
                """
                    INSERT INTO events (run_id, name, description, location, start_datetime, end_datetime, category, source, city, created_at, event_url, detail_scraped, detail_page_html, detail_description, detail_location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    Load events for newsletter. If since_days is set, only return events
    created in last N days; otherwise return latest by created_at.
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
                SELECT id, name, description, location, start_datetime, end_datetime, category, source, city, created_at
                FROM events
                WHERE date(created_at) >= date('now', ?)
                ORDER BY start_datetime DESC
                LIMIT ?
                """,
                (f"-{since_days} days", limit),
            )
        else:
            cur = conn.execute(
                """
                SELECT id, name, description, location, start_datetime, end_datetime, category, source, city, created_at
                FROM events
                ORDER BY start_datetime DESC
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
                "start_datetime": r["start_datetime"],
                "end_datetime": r["end_datetime"],
                "category": r["category"] or "other",
                "source": r["source"] or "",
                "city": r["city"] or "",
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    finally:
        if own_conn:
            conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
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
            INSERT INTO raw_summaries (run_id, location, max_search, cities, search_queries, raw_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, location or "", max_search, cities_json, queries_json, raw_summary, now),
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


def get_raw_summary_by_run_id(run_id: int, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Get raw summary associated with a specific run ID."""
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
            WHERE run_id = ?
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
 

__all__ = [
    "get_connection",
    "init_db",
    "create_run",
    "append_to_agent",
    "get_runs",
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
]
