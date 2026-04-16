# Database Schema Documentation

This document provides complete documentation of the WebScraper PostgreSQL database structure, relationships, and usage patterns.

## Overview

The WebScraper database uses the `webscraper` schema within the `vmpostgres` PostgreSQL database. It stores scraped events, pipeline metadata, ratings, and supporting data.

**Database**: `vmpostgres`  
**Schema**: `webscraper`  
**Connection**: `postgresql://webscraper:webscraper@192.168.178.160:5432/vmpostgres`

## Table Relationships

```
┌─────────────┐      ┌─────────────┐      ┌─────────────────┐
│   runs      │─────▶│   events    │      │ event_ratings   │
│             │      │  (108,874)  │      │    (3,271)      │
│   (187)     │      │             │◀─────│                 │
└─────────────┘      └─────────────┘      └─────────────────┘
      │                   │                       │
      │                   ▼                       │
      │            ┌─────────────┐               │
      │            │events_distinct│              │
      │            │  (12,627)   │               │
      └────────────│             │               │
                   │   UNIQUE:   │               │
                   │  (name,     │               │
                   │  start_dt,  │               │
                   │  origin)    │               │
                   └─────────────┘               │
                                                   │
┌─────────────┐                                  │
│ raw_summaries│                                  │
│    (19)     │                                  │
└─────────────┘                                  │
      │                                          │
      └──────────────────────────────────────────┘

┌─────────────┐      ┌─────────────────┐
│   status    │      │   locations     │
│   (149)     │      │    (2,021)      │
└─────────────┘      └─────────────────┘

┌──────────────────┐      ┌─────────────────────┐
│ city_coordinates  │      │ city_road_distances  │
│     (30)         │      │      (405)          │
└──────────────────┘      └─────────────────────┘
```

## Core Event Tables

### 1. `events` - Raw Scraped Events

**Purpose**: Stores all scraped events including duplicates across different pipeline runs.

**Record Count**: 108,874

**Schema**:
```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
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
    origin TEXT NOT NULL
);
```

**Key Fields**:
- `id`: Unique identifier for this specific event record
- `run_id`: Pipeline run that created this event record
- `name`, `start_datetime`, `origin`: Used for deduplication
- `created_at`: When this specific record was created
- `origin`: Data source identifier (e.g., "leverkusen_lust_auf", "rausgegangen_monheim_am_rhein")

**Indexes**:
- `events_pkey`: PRIMARY KEY (id)
- `idx_events_start_datetime`: (start_datetime)
- `idx_events_end_datetime`: (end_datetime)
- `idx_events_category`: (category)
- `idx_events_run_id`: (run_id)

**Usage**:
- Primary storage for all scraped events
- Contains duplicates (same event scraped multiple times)
- Source for `events_distinct` deduplication
- NOT used for rating (use `events_distinct` instead)

---

### 2. `events_distinct` - Unique Events

**Purpose**: Deduplicated view of events for display and rating. Each unique event appears once.

**Record Count**: 12,627

**Deduplication Logic**: Unique on `(name, start_datetime, origin)`

**Schema**:
```sql
CREATE TABLE events_distinct (
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
);
```

**Key Fields**:
- `id`: Unique identifier (independent from `events.id`)
- `rating`: Manual rating field (1-5, NULL for unrated)
- `first_seen_at`: When this event was first scraped
- `last_seen_at`: When this event was last seen
- `seen_count`: How many times this event has been scraped

**Indexes**:
- `events_distinct_pkey`: PRIMARY KEY (id)
- `events_distinct_name_start_datetime_origin_key`: UNIQUE (name, start_datetime, origin)
- `idx_events_distinct_start`: (start_datetime)
- `idx_events_distinct_category`: (category)
- `idx_events_distinct_city`: (city)
- `idx_events_distinct_rating`: (rating)

**Usage**:
- **Primary table for rating**: Ratings reference `events_distinct.id`
- Display purposes: Shows unique events without duplicates
- Tracking: Monitors event changes over time via `seen_count`
- Manual rating field: Can be manually rated (separate from agent ratings)

**Important**: 
- This table has its own ID sequence (not related to `events.id`)
- IDs do NOT match between `events` and `events_distinct`
- Always use `events_distinct` for rating queries

---

### 3. `event_ratings` - Agent Ratings

**Purpose**: Stores family-friendliness ratings from AI agents (DeepSeek, Ollama).

**Record Count**: 3,271

**Schema**:
```sql
CREATE TABLE event_ratings (
    user_email TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    rating NUMERIC,
    rating_reason TEXT,
    rated_at TIMESTAMP DEFAULT now(),
    rating_inhaltlich NUMERIC,
    rating_ort NUMERIC,
    rating_ausstattung NUMERIC,
    rating_interaktion NUMERIC,
    rating_kosten NUMERIC,
    PRIMARY KEY (user_email, event_id),
    FOREIGN KEY (event_id) REFERENCES events(id)
);
```

**Key Fields**:
- `user_email`: Agent identifier ("deepseek", "ollama", or user email)
- `event_id`: **References `events_distinct.id`** (not `events.id`)
- `rating`: Overall rating (1-5)
- `rating_*`: Sub-criteria ratings (1-5 each)
- `rated_at`: When the rating was created

**Sub-Criteria**:
- `rating_inhaltlich`: Content suitability
- `rating_ort`: Location/accessibility
- `rating_ausstattung`: Facilities for small children
- `rating_interaktion`: Interaction level
- `rating_kosten`: Cost for family

**Indexes**:
- `event_ratings_new_pkey`: PRIMARY KEY (user_email, event_id)

**Foreign Key**: `event_id → events.id` (NOTE: This is misleading - actual usage is `events_distinct.id`)

**Usage**:
- **Always query from `events_distinct`**: JOIN with `events_distinct` to get event details
- Track which agent rated which event
- Store detailed sub-criteria for analysis
- Multiple users/agents can rate the same event

---

## Pipeline Tracking Tables

### 4. `runs` - Pipeline Runs

**Purpose**: Tracks each pipeline execution (scraper, analyzer, rating).

**Record Count**: 187

**Schema**:
```sql
CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    cities TEXT,
    created_at TEXT NOT NULL,
    raw_summary_id INTEGER REFERENCES raw_summaries(id)
);
```

**Key Fields**:
- `id`: Unique run identifier
- `cities`: Comma-separated list of cities processed
- `created_at`: Run timestamp
- `raw_summary_id`: Link to scraper output (for analyzer runs)

**Usage**:
- Links all event records to their pipeline run
- Tracks execution history
- Enables debugging and replay

---

### 5. `status` - Run Metrics

**Purpose**: Stores performance metrics for each pipeline run.

**Record Count**: 149

**Schema**:
```sql
CREATE TABLE status (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES runs(id),
    linked_run_id INTEGER REFERENCES runs(id),
    urls TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration REAL,
    events_found INTEGER DEFAULT 0,
    valid_events INTEGER DEFAULT 0,
    events_regex INTEGER,
    events_llm INTEGER,
    full_run INTEGER DEFAULT 0,
    events_rated INTEGER DEFAULT 0,
    ratings_failed INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    agent_type TEXT,
    filters TEXT
);
```

**Key Fields**:
- `run_id`: Primary run this status belongs to
- `linked_run_id`: Linked run (analyzer → scraper)
- `events_found`: Total events extracted
- `valid_events`: Events with required fields
- `events_rated`: Number of events rated (for rating agent)
- `input_tokens`/`output_tokens`: LLM usage metrics

**Usage**:
- Performance monitoring
- Cost tracking (tokens)
- Debugging failed runs
- Historical analysis

---

### 6. `raw_summaries` - Scraper Output

**Purpose**: Stores raw text summaries from scraper agent for debugging.

**Record Count**: 19

**Schema**:
```sql
CREATE TABLE raw_summaries (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES runs(id),
    location TEXT,
    max_search INTEGER,
    fetch_urls INTEGER,
    cities TEXT,
    search_queries TEXT,
    raw_summary TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

**Usage**:
- Debugging scraper issues
- Re-running analyzer on saved data
- Historical reference

---

## Supporting Tables

### 7. `locations` - Family-Friendly Places (Ausflüge)

**Purpose**: Stores permanent family-friendly places for the Ausflüge feature.

**Record Count**: 2,021

**Schema**:
```sql
CREATE TABLE locations (
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
);
```

**Usage**:
- Independent from events pipeline
- Permanent places (not time-bound events)
- Categories: playground, museum, park, zoo, pool, etc.

---

### 8. `city_coordinates` - City Coordinates

**Purpose**: Stores latitude/longitude for target cities.

**Record Count**: 30

**Schema**:
```sql
CREATE TABLE city_coordinates (
    city_name TEXT PRIMARY KEY,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Usage**:
- Distance calculations
- Geographic queries

---

### 9. `city_road_distances` - Road Distances

**Purpose**: Pre-computed road distances between cities.

**Record Count**: 405

**Schema**:
```sql
CREATE TABLE city_road_distances (
    home_city TEXT NOT NULL,
    city TEXT NOT NULL,
    km REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (home_city, city)
);
```

**Usage**:
- Fast distance lookups
- Avoiding repeated API calls to mapping services

---

## Critical Relationships

### Event Rating Flow

```
events (raw, with duplicates)
    ↓
    [Deduplication: name + start_datetime + origin]
    ↓
events_distinct (unique events)
    ↓
    [Rating Agent]
    ↓
event_ratings (ratings reference events_distinct.id)
```

**Key Points**:
1. `events` contains all scraped data including duplicates
2. `events_distinct` contains unique events (deduplicated)
3. `event_ratings.event_id` references `events_distinct.id`, NOT `events.id`
4. IDs are independent between `events` and `events_distinct`

### Finding Unrated Events

**Correct Query**:
```sql
SELECT e.id, e.name, e.start_datetime
FROM events_distinct e
LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = 'ollama'
WHERE r.event_id IS NULL
ORDER BY e.id
LIMIT 50;
```

**Wrong Query** (what I initially did):
```sql
-- ❌ This uses events table instead of events_distinct
SELECT e.id, e.name, e.start_datetime
FROM events e
LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = 'ollama'
WHERE r.event_id IS NULL
```

---

## Common Query Patterns

### Get Unrated Events for Rating

```sql
-- Get 50 unrated events from events_distinct
SELECT e.id, e.name, e.description, e.category, e.location, e.city, e.start_datetime
FROM events_distinct e
LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = 'ollama'
WHERE r.event_id IS NULL
ORDER BY e.id
LIMIT 50;
```

### Get Events Rated by Specific Agent

```sql
-- Get all events rated by Ollama
SELECT e.*, r.rating, r.rating_reason, r.rated_at
FROM events_distinct e
JOIN event_ratings r ON e.id = r.event_id
WHERE r.user_email = 'ollama'
ORDER BY r.rated_at DESC;
```

### Check Event Duplication

```sql
-- See how many times an event has been scraped
SELECT 
    name, 
    start_datetime, 
    origin, 
    COUNT(*) as times_scraped,
    MIN(created_at) as first_scraped,
    MAX(created_at) as last_scraped
FROM events
WHERE name IS NOT NULL
GROUP BY name, start_datetime, origin
ORDER BY times_scraped DESC
LIMIT 10;
```

### Get Recent Unrated Events

```sql
-- Get unrated events happening in the next 7 days
SELECT e.id, e.name, e.start_datetime, e.location
FROM events_distinct e
LEFT JOIN event_ratings r ON e.id = r.event_id AND r.user_email = 'ollama'
WHERE r.event_id IS NULL
  AND e.start_datetime::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY e.start_datetime
LIMIT 50;
```

---

## MCP Integration

### Available MCP Tools

| Tool | Description | Example |
|------|-------------|---------|
| `webscraper_db_read_query` | Execute SELECT queries | `SELECT COUNT(*) FROM events_distinct` |
| `webscraper_db_write_query` | Execute INSERT/UPDATE/DELETE | `UPDATE events SET ...` |
| `webscraper_db_list_tables` | List all tables | - |
| `webscraper_db_describe_table` | Get table schema | Table: `events_distinct` |
| `webscraper_db_export_query` | Export as CSV/JSON | Export ratings to CSV |

### MCP Query Examples

```sql
-- Count unrated events
SELECT COUNT(*) 
FROM events_distinct e
LEFT JOIN event_ratings r ON e.id = r.event_id 
WHERE r.event_id IS NULL;

-- Get family events rated highly
SELECT e.name, e.location, r.rating
FROM events_distinct e
JOIN event_ratings r ON e.id = r.event_id
WHERE e.category = 'family' AND r.rating >= 4
ORDER BY r.rating DESC;

-- Most recent ratings
SELECT e.name, r.rating, r.user_email, r.rated_at
FROM events_distinct e
JOIN event_ratings r ON e.id = r.event_id
ORDER BY r.rated_at DESC
LIMIT 10;
```

---

## Statistics

### Current Data (as of 2026-04-16)

| Table | Records | Notes |
|-------|---------|-------|
| `events` | 108,874 | Raw events with duplicates |
| `events_distinct` | 12,627 | Unique events (8.6x deduplication) |
| `event_ratings` | 3,271 | Total ratings (deepseek: 3,094, ollama: 173) |
| `runs` | 187 | Pipeline executions |
| `status` | 149 | Run metrics |
| `raw_summaries` | 19 | Scraper outputs |
| `locations` | 2,021 | Family-friendly places |
| `city_coordinates` | 30 | City lat/lng |
| `city_road_distances` | 405 | Inter-city distances |

### Rating Distribution

- **Total unique events rated**: 3,198
- **Unrated events**: ~9,430 (from events_distinct)
- **Rating completion**: ~25%

---

## Best Practices

### 1. Always Use events_distinct for Rating

❌ **Wrong**:
```sql
SELECT * FROM events WHERE id NOT IN (SELECT event_id FROM event_ratings)
```

✅ **Correct**:
```sql
SELECT * FROM events_distinct WHERE id NOT IN (SELECT event_id FROM event_ratings WHERE user_email = 'ollama')
```

### 2. Always Filter by user_email in event_ratings

❌ **Wrong**:
```sql
SELECT * FROM event_ratings WHERE event_id = 12345
```

✅ **Correct**:
```sql
SELECT * FROM event_ratings WHERE event_id = 12345 AND user_email = 'ollama'
```

### 3. Use DISTINCT ON for Events Table

When querying `events` directly, always deduplicate:

```sql
SELECT DISTINCT ON (name, start_datetime, origin) *
FROM events
ORDER BY name, start_datetime, origin;
```

But prefer `events_distinct` for most queries.

### 4. Check for Existing Ratings Before Inserting

```sql
INSERT INTO event_ratings (...)
SELECT ...
FROM events_distinct e
WHERE NOT EXISTS (
    SELECT 1 FROM event_ratings 
    WHERE event_id = e.id AND user_email = 'ollama'
);
```

---

## Troubleshooting

### Issue: "No unrated events found"

**Check**: Are you querying the right table?
```sql
-- Check counts
SELECT 
    (SELECT COUNT(*) FROM events_distinct) as total_distinct,
    (SELECT COUNT(*) FROM event_ratings) as total_ratings,
    (SELECT COUNT(*) FROM events_distinct e 
     LEFT JOIN event_ratings r ON e.id = r.event_id 
     WHERE r.event_id IS NULL) as unrated;
```

### Issue: Duplicate ratings

**Cause**: Missing or incorrect `user_email` filter

**Solution**: Always include `user_email` in WHERE clause

### Issue: Event not found after rating

**Cause**: Might have inserted rating with wrong event_id

**Solution**: Verify event_id exists in events_distinct before rating

---

## Schema Evolution

The database has evolved from a simple event store to a complex system:

1. **Initial**: Just `events` table
2. **Added**: `events_distinct` for deduplication
3. **Added**: `event_ratings` for AI agent ratings
4. **Added**: Pipeline tracking (`runs`, `status`, `raw_summaries`)
5. **Added**: Supporting data (`locations`, city tables)

**Note**: The foreign key constraint `event_ratings.event_id → events.id` is misleading. The actual usage is `event_ratings.event_id → events_distinct.id`. This should be corrected in a future migration.

---

## Maintenance

### Periodic Tasks

1. **Rebuild events_distinct**: After major scraper changes
2. **Clean old ratings**: Remove test ratings with user_email='test'
3. **Update city distances**: Add new cities to distance matrix
4. **Check URL health**: For locations (Ausflüge feature)

### Backups

- Database: `vmpostgres` (shared with other projects)
- Backup strategy: Via Docker host
- Recovery point: Daily backups available

---

## See Also

- [README.md](../README.md) - Quick start guide
- [docs/11_architecture.md](11_architecture.md) - System architecture
- [docs/40_mcp_postgres_setup.md](40_mcp_postgres_setup.md) - MCP configuration
- [AGENTS.md](../AGENTS.md) - AI agent documentation
