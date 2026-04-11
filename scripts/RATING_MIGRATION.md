# Rating Column Migration Instructions

## Changes Made

1. **agents/rating_agent.py** - Changed validation to accept decimal ratings (4.2, 3.7, etc.)
2. **storage.py** - Updated `insert_event_rating()` function signature to use float instead of int
3. **scripts/add_rating_fields.sql** - Updated to use NUMERIC(3,1) for future table creation
4. **scripts/alter_ratings_to_decimal.sql** - SQL migration to alter existing tables

## Required Database Migration

You need to run the SQL migration to alter existing rating columns from INTEGER to NUMERIC(3,1).

### Option 1: Using psql directly

```bash
psql -U jobsearch -d vmpostgres -f scripts/alter_ratings_to_decimal.sql
```

### Option 2: Using the Python migration script

```bash
python3 scripts/migrate_ratings_to_decimal.py
```

You'll need to provide the jobsearch user password when prompted, or set it via environment variable:

```bash
PGPASSWORD=your_password python3 scripts/migrate_ratings_to_decimal.py
```

### Option 3: Connect using psql and run manually

```bash
psql -U jobsearch -d vmpostgres
```

Then run:

```sql
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_inhaltlich TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ort TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_ausstattung TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_interaktion TYPE NUMERIC(3,1);
ALTER TABLE webscraper.event_ratings ALTER COLUMN rating_kosten TYPE NUMERIC(3,1);
ALTER TABLE webscraper.events_distinct ALTER COLUMN rating TYPE NUMERIC(3,1);
```

## Verification

After running the migration, verify the changes:

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'webscraper' 
    AND table_name = 'event_ratings' 
    AND column_name LIKE 'rating_%'
ORDER BY ordinal_position;
```

You should see `numeric` as the data type for all rating columns.
