# Locations/Ausflüge Feature

Family-friendly locations (Ausflugsziele) within 30km of Monheim am Rhein, curated for **families with children under 6**. This is a separate feature from the events pipeline — locations are permanent places, discovered once and maintained.

## Overview

- **Target audience:** Families with 2 children under 6 years old
- **What:** Playgrounds, museums, parks, gardens, pools, zoos, indoor playgrounds, sport venues, family restaurants
- **Where:** 30km radius around Monheim am Rhein (51.0917, 6.8873)
- **How:** OpenStreetMap Overpass API (free) + Google Places API (ratings, restaurants, all categories)
- **Storage:** Same `data/events.db` database, separate `locations` table
- **Independence:** Locations never run as part of the events pipeline

## CLI Commands

```bash
# Discover locations (all sources: Overpass + Google + manual)
python3 main.py --locations discover

# Discover from specific source only
python3 main.py --locations discover --locations-source overpass
python3 main.py --locations discover --locations-source google
python3 main.py --locations discover --locations-source manual

# Enrich existing locations with Google ratings
python3 main.py --locations enrich

# List all locations
python3 main.py --locations list

# List filtered by category
python3 main.py --locations list --locations-category museum
python3 main.py --locations list --locations-category restaurant

# Show statistics
python3 main.py --locations stats

# Check all website URLs for broken links
python3 main.py --locations check-urls
```

## Categories

| ID | German | Examples |
|---|---|---|
| `playground` | Spielplatz | Wasserspielplatz, Abenteuerspielplatz |
| `indoor_playground` | Indoor-Spielplatz | Trampolinhalle |
| `park` | Park | Stadtpark, Naturschutzgebiet |
| `garden` | Garten | Botanischer Garten, Schlossgarten |
| `museum` | Museum | Kindermuseum, Naturkundemuseum |
| `zoo` | Zoo / Tierpark | Wildpark, Streichelzoo |
| `pool` | Schwimmbad | Freibad, Hallenbad, Erlebnisbad |
| `restaurant` | Familienrestaurant | Only 4.0+ rated (Google Places) |
| `sport` | Sport & Freizeit | Minigolf, Kletterhalle, Eislaufbahn |
| `other` | Sonstiges | Anything else |

## Data Sources

### 1. Overpass API (Primary — free)

Free OpenStreetMap API. Queries for specific amenity/leisure/tourism types within the radius. Often includes opening hours, website URLs, phone numbers, and addresses.

- Endpoint: `https://overpass-api.de/api/interpreter`
- Rate limiting: 3-second delay between queries, auto-retry on 429 with backoff
- No API key required
- **No ratings** (OSM has no review system)

### 2. Google Places API (All Categories + Ratings)

Google Places API (New) for discovering locations across all categories and enriching existing OSM entries with ratings.

- Endpoint: `POST https://places.googleapis.com/v1/places:searchNearby`
- Uses Pro tier field mask (rating, address, website, coordinates, types)
- Requires `GOOGLE_PLACES_API_KEY` in `.env`
- Search grid: 4 points covering 30km radius (15km per point, max 20 results each)
- Cost: ~$32/1K calls, free tier covers ~10K calls/month
- Each discovery run uses **36 API calls** (9 categories × 4 grid points)

**Family-friendly filtering (3 layers):**

Google's broad type matching returns many results not suitable for families with small children. Three filtering layers clean the data without additional API calls:

1. **Subcategory blocklist** — rejects places by `primaryType`: bars, hotels, spas, shopping malls, churches, dog parks, etc.
2. **Name keyword blocklist** — catches adult entertainment with acceptable subcategories: escape rooms, LaserTag, axe throwing, VR venues, BDSM studios, hookah lounges
3. **Museum subcategory filter** — blocks art museums, sculptures (not engaging for toddlers); keeps kid-friendly types like `food` (Schokoladenmuseum), `cultural_center` (AKKI), `history_museum`

**Additional filters:**
- Restaurants: only 4.0+ rated are kept
- All categories: distance filter (30km radius)
- Cross-source deduplication by coordinate proximity (100m) + name match

**Setup:**
1. Enable Places API (New) in Google Cloud Console
2. Create API key (APIs & Services > Credentials)
3. Add to `.env`: `GOOGLE_PLACES_API_KEY=AIza...`
4. Monitor usage: Console → APIs & Services → Places API (New) → Metrics

### 3. Manual Seed File

Curated locations in `locations/data/seed_locations.json` for places the APIs might miss.

Format:
```json
[
  {
    "name": "Monheimer Wasserspielplatz",
    "category": "playground",
    "address": "Rheinpromenade, 40789 Monheim am Rhein",
    "city": "Monheim am Rhein",
    "latitude": 51.0920,
    "longitude": 6.8880,
    "website_url": "https://www.monheim.de/...",
    "opening_hours": "Mo-Su 08:00-20:00",
    "description": "Playground at the Rhine promenade"
  }
]
```

All fields except `name` and `category` are optional.

## Enrichment

The `enrich` command updates existing OSM locations with Google Places ratings:

```bash
python3 main.py --locations enrich
```

This will:
1. Find locations in the DB that have coordinates but no rating
2. Search Google Places nearby (100m radius) for each
3. Match by name similarity
4. Update the rating field (doesn't overwrite other fields)
5. Limited to 200 API calls per run (cost control)

## Database Schema

```sql
CREATE TABLE locations (
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
    opening_hours TEXT,              -- free text, e.g. "Mo-Fr 09:00-18:00"
    opening_hours_json TEXT,         -- optional structured JSON
    website_url TEXT,
    phone TEXT,
    rating REAL,                     -- Google rating (1.0-5.0)
    source TEXT NOT NULL,            -- 'overpass', 'google_places', 'manual'
    source_id TEXT,                  -- external ID (e.g. "node/12345", Google place_id)
    distance_km REAL,               -- distance from Monheim center
    url_status TEXT DEFAULT 'unchecked',  -- 'ok', 'broken', 'redirect', 'unchecked'
    url_last_checked TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## MCP Queries

The `locations` table lives in the same `data/events.db` database, so MCP queries work immediately:

```sql
-- Nearby museums
SELECT name, city, distance_km, opening_hours FROM locations
WHERE category = 'museum' AND distance_km < 10 ORDER BY distance_km;

-- Top-rated restaurants
SELECT name, rating, city, distance_km FROM locations
WHERE category = 'restaurant' ORDER BY rating DESC;

-- Stats by category
SELECT category, COUNT(*) as count FROM locations GROUP BY category ORDER BY count DESC;

-- Locations with ratings
SELECT name, category, rating FROM locations
WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 20;

-- Broken URLs
SELECT name, website_url FROM locations WHERE url_status = 'broken';
```

## Discovery Pipeline

When you run `--locations discover`, the pipeline:

1. Queries Overpass API for each category (8 queries, 3s apart)
2. Queries Google Places API per category across 4 grid points (if key configured)
   - Applies 3-layer family-friendly filtering during parsing
   - Logs how many places were filtered per category
3. Loads manual seed entries from JSON
4. Calculates haversine distance from Monheim center for each location
5. Filters out locations beyond 30km
6. Deduplicates by coordinate proximity (100m) + name match
7. Upserts into database (by source + source_id)

Re-running discover updates existing entries and adds new ones — it does not create duplicates.

**Google Places category mapping:**

| Our category | Google `includedTypes` |
|---|---|
| playground | `playground` |
| indoor_playground | `amusement_center` (heavily filtered) |
| museum | `museum` (art museums excluded) |
| zoo | `zoo` |
| pool | `swimming_pool` |
| park | `park` |
| garden | `botanical_garden` |
| restaurant | `restaurant` (4.0+ rating only) |
| sport | `bowling_alley` |

## Maintenance

Run `python3 main.py --locations check-urls` periodically (e.g. monthly) to verify website URLs. It performs HTTP HEAD requests (with GET fallback) and updates the `url_status` field.

## File Structure

```
locations/
├── __init__.py              # discover_locations() + enrich_locations()
├── models.py                # Location dataclass, LOCATION_CATEGORIES
├── storage.py               # DB table creation, upsert, query, stats
├── cli.py                   # CLI command dispatch
├── maintenance.py           # URL health checker
├── sources/
│   ├── __init__.py
│   ├── overpass.py          # OpenStreetMap Overpass API
│   ├── google_places.py     # Google Places API (New)
│   └── manual.py            # Seed file loader
└── data/
    └── seed_locations.json  # Manual curated entries
```

## Configuration

In `config.py`:
```python
MONHEIM_LAT = 51.0917
MONHEIM_LNG = 6.8873
LOCATIONS_RADIUS_KM = 30
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
```
