#!/usr/bin/env python3
"""One-time migration: copy all data from SQLite (data/events.db) to Postgres (webscraper schema).

Usage: python3 scripts/migrate_sqlite_to_postgres.py
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SQLITE_DB_PATH, PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, PG_SCHEMA


def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_conn():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE,
        user=PG_USER, password=PG_PASSWORD,
    )
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET search_path TO %s, public", (PG_SCHEMA,))
    return conn


def get_columns(sqlite_conn, table_name):
    """Get column names from SQLite table."""
    cur = sqlite_conn.execute(f"PRAGMA table_info({table_name})")
    return [row["name"] for row in cur.fetchall()]


def migrate_table(sqlite_conn, pg_conn, table_name, columns=None):
    """Migrate a single table from SQLite to Postgres."""
    if columns is None:
        columns = get_columns(sqlite_conn, table_name)

    # Read all rows from SQLite
    cur = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
    rows = cur.fetchall()

    if not rows:
        print(f"  {table_name}: 0 rows (empty)")
        return 0

    # Convert sqlite3.Row to tuples
    tuples = [tuple(row) for row in rows]

    # Build INSERT query
    cols_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    pg_cur = pg_conn.cursor()

    # Use execute_values for bulk insert (much faster)
    template = f"({placeholders})"
    query = f"INSERT INTO {table_name} ({cols_str}) VALUES %s"
    execute_values(pg_cur, query, tuples, template=template, page_size=500)

    # Reset the serial sequence to max id
    if "id" in columns:
        pg_cur.execute(f"""
            SELECT setval(pg_get_serial_sequence('{table_name}', 'id'),
                          COALESCE((SELECT MAX(id) FROM {table_name}), 1))
        """)

    pg_conn.commit()
    count = len(tuples)
    print(f"  {table_name}: {count} rows migrated")
    return count


def check_sqlite_tables(conn):
    """List all tables in SQLite database."""
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row["name"] for row in cur.fetchall()]


def main():
    print(f"SQLite source: {SQLITE_DB_PATH}")
    print(f"Postgres target: {PG_DATABASE}/{PG_SCHEMA}")
    print()

    if not os.path.exists(SQLITE_DB_PATH):
        print(f"Error: SQLite database not found at {SQLITE_DB_PATH}")
        sys.exit(1)

    sqlite_conn = get_sqlite_conn()
    pg_conn = get_pg_conn()

    try:
        # Show available SQLite tables
        tables = check_sqlite_tables(sqlite_conn)
        print(f"SQLite tables found: {tables}")
        print()

        # Migration order matters due to foreign keys
        migration_order = ["runs", "raw_summaries", "status", "events", "events_distinct", "locations"]

        # Check which tables exist in SQLite
        tables_to_migrate = [t for t in migration_order if t in tables]
        skipped = [t for t in migration_order if t not in tables]
        if skipped:
            print(f"Skipping (not in SQLite): {skipped}")

        print("Migrating tables...")

        # First ensure Postgres tables exist
        from storage import init_db, init_events_distinct_db
        from locations.storage import init_locations_db
        init_db(pg_conn)
        init_events_distinct_db(pg_conn)
        init_locations_db(pg_conn)

        total = 0
        for table_name in tables_to_migrate:
            count = migrate_table(sqlite_conn, pg_conn, table_name)
            total += count

        print(f"\nMigration complete: {total} total rows migrated across {len(tables_to_migrate)} tables")

        # Verify counts
        print("\nVerification:")
        pg_cur = pg_conn.cursor()
        for table_name in tables_to_migrate:
            sqlite_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            pg_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            pg_count = pg_cur.fetchone()[0]
            status = "OK" if sqlite_count == pg_count else "MISMATCH"
            print(f"  {table_name}: SQLite={sqlite_count}, Postgres={pg_count} [{status}]")

    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
