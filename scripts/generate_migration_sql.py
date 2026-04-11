#!/usr/bin/env python3
"""Generate SQL migration commands for altering rating columns to NUMERIC(3,1).

This script prints the SQL commands that need to be run as the table owner (jobsearch).

Usage:
    # Run this script to get the SQL commands
    python3 scripts/generate_migration_sql.py

    # Then run the output as the jobsearch user
    psql -U jobsearch -d vmpostgres
    # (paste the SQL commands)
"""

def generate_migration_sql():
    """Generate SQL commands for migration."""
    
    sql = """-- Rating Column Migration to NUMERIC(3,1)
-- Run this as the jobsearch user (table owner)

-- Connect to the database
-- \\c vmpostgres

-- Step 1: Check current column types
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'webscraper' 
    AND table_name = 'event_ratings' 
    AND column_name LIKE 'rating%'
ORDER BY ordinal_position;

-- Step 2: Create backups
DROP TABLE IF EXISTS webscraper.event_ratings_backup CASCADE;
CREATE TABLE webscraper.event_ratings_backup AS 
SELECT * FROM webscraper.event_ratings;

DROP TABLE IF EXISTS webscraper.events_distinct_backup CASCADE;
CREATE TABLE webscraper.events_distinct_backup AS 
SELECT * FROM webscraper.events_distinct;

-- Step 3: Drop foreign key constraint from event_ratings
ALTER TABLE webscraper.event_ratings DROP CONSTRAINT IF EXISTS event_ratings_event_id_fkey;

-- Step 4: Drop existing tables
DROP TABLE IF EXISTS webscraper.event_ratings CASCADE;
DROP TABLE IF EXISTS webscraper.events_distinct CASCADE;

-- Step 5: Recreate events_distinct with NUMERIC(3,1) rating column
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
);

-- Create indexes for events_distinct
CREATE INDEX idx_events_distinct_start ON webscraper.events_distinct(start_datetime);
CREATE INDEX idx_events_distinct_category ON webscraper.events_distinct(category);
CREATE INDEX idx_events_distinct_city ON webscraper.events_distinct(city);

-- Step 6: Recreate event_ratings with NUMERIC(3,1) rating columns
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
);

-- Step 7: Copy data to events_distinct (without ID to let it regenerate)
INSERT INTO webscraper.events_distinct 
(name, description, category, city, location, start_datetime, end_datetime, 
 origin, event_url, detail_description, detail_full_description, rating, 
 first_seen_at, last_seen_at, seen_count)
SELECT name, description, category, city, location, start_datetime, end_datetime,
       origin, event_url, detail_description, detail_full_description, rating,
       first_seen_at, last_seen_at, seen_count
FROM webscraper.events_distinct_backup;

-- Step 8: Copy data to event_ratings (recreating event_id references)
INSERT INTO webscraper.event_ratings 
(event_id, rating, rating_inhaltlich, rating_ort, rating_ausstattung,
 rating_interaktion, rating_kosten, rating_reason, user_email, rated_at)
SELECT ed.id, er.rating, er.rating_inhaltlich, er.rating_ort, er.rating_ausstattung,
       er.rating_interaktion, er.rating_kosten, er.rating_reason, er.user_email, er.rated_at
FROM webscraper.event_ratings_backup er
JOIN webscraper.events_distinct_backup edb ON er.event_id = edb.id
JOIN webscraper.events_distinct ed ON edb.name = ed.name 
    AND edb.start_datetime = ed.start_datetime 
    AND edb.origin = ed.origin;

-- Step 9: Verify migration
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'webscraper' 
    AND table_name = 'event_ratings' 
    AND column_name LIKE 'rating%'
ORDER BY ordinal_position;

SELECT COUNT(*) as events_count FROM webscraper.events_distinct;
SELECT COUNT(*) as ratings_count FROM webscraper.event_ratings;

-- Step 10: After verification, drop backups (optional)
-- DROP TABLE webscraper.event_ratings_backup;
-- DROP TABLE webscraper.events_distinct_backup;
"""
    
    return sql

if __name__ == "__main__":
    print(generate_migration_sql())
