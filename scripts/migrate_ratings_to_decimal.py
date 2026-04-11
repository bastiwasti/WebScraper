#!/usr/bin/env python3
"""Run migration to alter rating columns from INTEGER to NUMERIC(3,1).

This script requires database owner privileges to alter table columns.
Run as postgres user or with database owner credentials.

Usage:
    sudo -u postgres python3 scripts/migrate_ratings_to_decimal.py
    # or
    PGUSER=jobsearch PGPASSWORD=your_password python3 scripts/migrate_ratings_to_decimal.py
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection - can be overridden via environment variables
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_NAME = os.getenv("PGDATABASE", "vmpostgres")
DB_USER = os.getenv("PGUSER", "jobsearch")
DB_PASSWORD = os.getenv("PGPASSWORD", None)

def migrate_ratings():
    """Alter rating columns to NUMERIC(3,1)."""
    
    # Connect to database
    print(f"Connecting to {DB_NAME} as user {DB_USER}...")
    
    try:
        if DB_PASSWORD:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                cursor_factory=RealDictCursor
            )
        else:
            # Try peer authentication (works for local postgres user)
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                cursor_factory=RealDictCursor
            )
        
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Connected successfully!")
        
        # Verify current column types
        print("\n--- Current column types ---")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'webscraper' 
                AND table_name = 'event_ratings' 
                AND column_name IN ('rating', 'rating_inhaltlich', 'rating_ort', 
                                     'rating_ausstattung', 'rating_interaktion', 'rating_kosten')
            ORDER BY ordinal_position
        """)
        
        for row in cur.fetchall():
            print(f"  {row['column_name']}: {row['data_type']}")
        
        # Execute ALTER statements
        print("\n--- Altering columns ---")
        statements = [
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_inhaltlich TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ort TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ausstattung TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_interaktion TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_kosten TYPE NUMERIC(3,1)',
            'ALTER TABLE webscraper.events_distinct ALTER COLUMN rating TYPE NUMERIC(3,1)',
        ]
        
        for stmt in statements:
            print(f"  Executing: {stmt[:70]}...")
            cur.execute(stmt)
        
        print("\n--- Verification ---")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'webscraper' 
                AND table_name = 'event_ratings' 
                AND column_name IN ('rating', 'rating_inhaltlich', 'rating_ort', 
                                     'rating_ausstattung', 'rating_interaktion', 'rating_kosten')
            ORDER BY ordinal_position
        """)
        
        for row in cur.fetchall():
            print(f"  {row['column_name']}: {row['data_type']}")
        
        print("\n✓ Migration completed successfully!")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_ratings()
