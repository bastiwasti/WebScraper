#!/usr/bin/env python3
"""Workaround migration script that copies tables instead of altering them.

This script:
1. Creates new tables with NUMERIC(3,1) columns
2. Copies data from existing tables
3. Renames tables

Usage:
    python3 scripts/migrate_ratings_workaround.py
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def migrate_workaround():
    """Copy tables instead of altering them."""
    
    # Get database credentials from .env
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    
    DB_HOST = os.getenv("PG_HOST", "localhost")
    DB_PORT = int(os.getenv("PG_PORT", "5432"))
    DB_NAME = os.getenv("PG_DATABASE", "vmpostgres")
    DB_USER = os.getenv("PG_USER", "jobsearch_app")
    DB_PASSWORD = os.getenv("PG_PASSWORD", "")
    
    print(f"Connecting to database as {DB_USER}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()
    
    try:
        # Step 1: Create backup of existing tables
        print("\n--- Creating backups ---")
        
        # Backup event_ratings
        cur.execute("DROP TABLE IF EXISTS webscraper.event_ratings_backup CASCADE")
        cur.execute("""
            CREATE TABLE webscraper.event_ratings_backup AS 
            SELECT * FROM webscraper.event_ratings
        """)
        print("  ✓ Backed up event_ratings")
        
        # Backup events_distinct
        cur.execute("DROP TABLE IF EXISTS webscraper.events_distinct_backup CASCADE")
        cur.execute("""
            CREATE TABLE webscraper.events_distinct_backup AS 
            SELECT * FROM webscraper.events_distinct
        """)
        print("  ✓ Backed up events_distinct")
        
        # Step 2: Drop existing tables
        print("\n--- Dropping old tables ---")
        cur.execute("DROP TABLE IF EXISTS webscraper.event_ratings CASCADE")
        print("  ✓ Dropped event_ratings")
        cur.execute("DROP TABLE IF EXISTS webscraper.events_distinct CASCADE")
        print("  ✓ Dropped events_distinct")
        
        # Step 3: Recreate events_distinct with correct rating column type
        print("\n--- Recreating events_distinct with NUMERIC(3,1) ---")
        cur.execute("""
            CREATE TABLE webscraper.events_distinct (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                city TEXT,
                location TEXT,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT,
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
        print("  ✓ Created events_distinct")
        
        # Create indexes
        cur.execute("CREATE INDEX idx_events_distinct_start ON webscraper.events_distinct(start_datetime)")
        cur.execute("CREATE INDEX idx_events_distinct_category ON webscraper.events_distinct(category)")
        cur.execute("CREATE INDEX idx_events_distinct_city ON webscraper.events_distinct(city)")
        print("  ✓ Created indexes")
        
        # Step 4: Recreate event_ratings with correct rating column types
        print("\n--- Recreating event_ratings with NUMERIC(3,1) ---")
        cur.execute("""
            CREATE TABLE webscraper.event_ratings (
                id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL,
                rating NUMERIC(3,1) NOT NULL CHECK(rating >= 1 AND rating <= 5),
                rating_inhaltlich NUMERIC(3,1),
                rating_ort NUMERIC(3,1),
                rating_ausstattung NUMERIC(3,1),
                rating_interaktion NUMERIC(3,1),
                rating_kosten NUMERIC(3,1),
                rating_reason TEXT,
                user_email TEXT NOT NULL,
                rated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, user_email),
                FOREIGN KEY (event_id) REFERENCES webscraper.events_distinct(id) ON DELETE CASCADE
            )
        """)
        print("  ✓ Created event_ratings")
        
        # Step 5: Copy data back to events_distinct
        print("\n--- Restoring events_distinct data ---")
        cur.execute("""
            INSERT INTO webscraper.events_distinct 
            (id, name, description, category, city, location, start_datetime, end_datetime, 
             origin, event_url, detail_description, detail_full_description, rating, 
             first_seen_at, last_seen_at, seen_count)
            SELECT id, name, description, category, city, location, start_datetime, end_datetime,
                   origin, event_url, detail_description, detail_full_description, rating,
                   first_seen_at, last_seen_at, seen_count
            FROM webscraper.events_distinct_backup
        """)
        
        cur.execute("SELECT COUNT(*) FROM webscraper.events_distinct")
        count = cur.fetchone()
        print(f"  ✓ Restored {count['count']} events")
        
        # Step 6: Copy data back to event_ratings
        print("\n--- Restoring event_ratings data ---")
        cur.execute("""
            INSERT INTO webscraper.event_ratings 
            (id, event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung,
             rating_interaktion, rating_kosten, rating_reason, user_email, rated_at)
            SELECT id, event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung,
                   rating_interaktion, rating_kosten, rating_reason, user_email, rated_at
            FROM webscraper.event_ratings_backup
        """)
        
        cur.execute("SELECT COUNT(*) FROM webscraper.event_ratings")
        count = cur.fetchone()
        print(f"  ✓ Restored {count['count']} ratings")
        
        # Step 7: Verification
        print("\n--- Verification ---")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'webscraper' 
                AND table_name = 'event_ratings' 
                AND column_name LIKE 'rating%'
            ORDER BY ordinal_position
        """)
        
        print("  event_ratings columns:")
        for row in cur.fetchall():
            print(f"    {row['column_name']}: {row['data_type']}")
        
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'webscraper' 
                AND table_name = 'events_distinct' 
                AND column_name = 'rating'
        """)
        
        row = cur.fetchone()
        if row:
            print(f"  events_distinct.rating: {row['data_type']}")
        
        print("\n✓ Migration completed successfully!")
        print("\nBackup tables created:")
        print("  - webscraper.event_ratings_backup")
        print("  - webscraper.events_distinct_backup")
        print("\nYou can drop these backups after verification:")
        print("  DROP TABLE webscraper.event_ratings_backup;")
        print("  DROP TABLE webscraper.events_distinct_backup;")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nRolling back...")
        # Try to restore from backups
        try:
            cur.execute("DROP TABLE IF EXISTS webscraper.events_distinct CASCADE")
            cur.execute("DROP TABLE IF EXISTS webscraper.event_ratings CASCADE")
            cur.execute("ALTER TABLE webscraper.events_distinct_backup RENAME TO events_distinct")
            cur.execute("ALTER TABLE webscraper.event_ratings_backup RENAME TO event_ratings")
            print("✓ Restored original tables from backup")
        except Exception as rollback_error:
            print(f"✗ Rollback failed: {rollback_error}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_workaround()
