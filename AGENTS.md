# WebScraper AGENTS.md

## Project Overview

WebScraper is a Python-based three-agent LLM pipeline for scraping, analyzing, and rating local events from cities around Monheim am Rhein, Germany.

### System Type
- **Pipeline**: Scraper Agent → Analyzer Agent → Rating Agent → PostgreSQL Database
- **LLM Provider**: DeepSeek (default, cloud) or Ollama (local, `--simple` mode)
- **Scale**: 12,000+ events from 30+ sources across 9 cities

### Geography
Target cities around Monheim am Rhein:
- monheim_am_rhein
- langenfeld
- leverkusen
- hilden
- dormagen
- hitdorf
- leichlingen
- burscheid
- duesseldorf

---

## Quick Reference

| Task | Command/Documentation |
|-------|-------------------|
| Run full pipeline | `python main.py --agent all --full-run` |
| Test single URL | `python main.py --url {url} --no-db --verbose` |
| Rate events (DeepSeek) | `python main.py --rate-events --days 7` |
| Rate events (Ollama) | `python main.py --rate-events --simple --batch-size 3 --days 7` |
| Add new city scraper | See `docs/00_url_setup_prompt.md` |
| Debug scraper | See `docs/99_agent_errors.md` patterns |
| Database schema | All tables are in `webscraper` schema (not `public`) |

---

## Agent Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   CLI Entry     │─────▶│   Pipeline      │─────▶│   Storage       │
│   (main.py)     │      │   Orchestrator  │      │  (PostgreSQL)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                 │
             ┌───────────────────┼────────────────────┐
             ▼                   ▼                    ▼
      ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
      │  Scraper    │    │  Analyzer   │    │   Rating     │
      │  Agent 1    │───▶│  Agent 2    │───▶│   Agent 3    │
      └─────────────┘    └─────────────┘    └──────────────┘
             │                   │                   │
             ▼                   ▼                   ▼
      ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
      │  URL Rules  │    │    LLM      │    │  DeepSeek   │
      │   System    │    │  Provider   │    │  or Ollama  │
      └─────────────┘    └─────────────┘    └─────────────┘
```

### Agent Responsibilities

**Scraper Agent (Agent 1)**:
- Collect URLs from rules system (cities + aggregators)
- Fetch content from each URL (requests or Playwright)
- Extract events using regex patterns
- Fall back to LLM if regex fails
- Generate raw summary with LLM
- Track metrics (time, events per URL)
- **Level 2 Scraping**: Optional - fetches event detail pages for richer data

**Analyzer Agent (Agent 2)**:
- Parse raw event text from scraper
- Extract structured events via LLM
- Validate event data (name, date, location, source)
- Infer categories using keyword-based system
- Save events to database
- Track metrics (events found, valid events, duration)

**Rating Agent (Agent 3)**:
- Rates events for family-friendliness (family with 2 kids under 6, Monheim am Rhein)
- **Tool-calling mode** (default, DeepSeek): structured function calls, 5 sub-criteria per event
- **Simple mode** (`--simple`, Ollama): lightweight prompt, rating + reason only, batch size 3
- Scores 1-5 across: content suitability, location, toddler amenities, interaction, cost
- Stores results in `event_ratings` table (user_email = `deepseek` or `ollama`)
- Run separately from scrape pipeline via `--rate-events`

---

## Data Models

### Event Dataclass

```python
# rules/base.py:26
@dataclass
class Event:
    name: str           # Required: Event name/title
    description: str    # Required: Event description
    location: str       # Required: Event location/venue
    date: str           # Required: Event date (format: DD.MM.YYYY)
    time: str           # Required: Event time (empty if all-day)
    source: str         # Required: Source URL
    category: str       # Created by analyzer (not set by scraper)
    city: str = ""      # Optional: City name
    event_url: str = "" # Optional: Event detail page URL
    raw_data: dict | None = None  # Optional: Raw data from Level 2 scraping
    origin: str = ""    # REQUIRED: Data origin identifier (e.g., "leverkusen_lust_auf")
```

**Important**: The `origin` field identifies the data source (e.g., "monheim_am_rhein_kulturwerke", "eventim_leverkusen"). This is set by `self.get_origin()` which calls `get_origin_for_url()` from the registry.

### Run Tracking

- **runs table**: Pipeline run metadata (agent type, cities, timestamps)
- **status table**: Performance metrics (duration, events found, valid events)
- **raw_summaries table**: Raw scraper output for debugging
- **events table**: Final structured event data

---

## Registry System

### Auto-Discovery

The registry automatically discovers all `scraper.py` and `regex.py` files from:
- `rules/cities/{city}/{subfolder}/scraper.py`
- `rules/cities/{city}/{subfolder}/regex.py`
- `rules/aggregators/{aggregator}/{subfolder}/scraper.py`
- `rules/aggregators/{aggregator}/{subfolder}/regex.py`

**Important**: Each URL must have its own subfolder. City-level scrapers (directly in `rules/cities/{city}/`) are NOT allowed.

### URL → Origin Mapping

The `get_origin_for_url()` function generates origin identifiers:

**Aggregators**: `"{aggregator}_{city}"`
- Example: `rausgegangen_monheim_am_rhein`
- Example: `eventim_leverkusen`

**Cities**: `"{city}_{subfolder}"`
- Example: `monheim_am_rhein_terminkalender`
- Example: `langenfeld_city_events`

**LLM Fallback**: `"{city}_{subfolder}"` (uses correct origin, NOT hardcoded "llm_fallback")

---

## 7 Proven Implementation Patterns

From `docs/00_url_setup_prompt.md`:

| # | Pattern | Reference Example | When to Use | Key Characteristics |
|---|---------|------------------|---------------------|
| 1 | REST API (JSON) | `rules/cities/leverkusen/lust_auf/` | URL has `/api/`, `/wp-json/`, `tribe/events` | Fastest, parse JSON response |
| 2 | Static HTML | `rules/cities/langenfeld/city_events/` | Plain HTML, no JavaScript | Use BeautifulSoup, fast |
| 3 | Static + 2-Level | `rules/cities/langenfeld/schauplatz/` | Detail page links available | Main page + detail pages |
| 4 | Dynamic + Load More | `rules/cities/monheim/terminkalender/` | JavaScript + "Load More" buttons | Use Playwright, click until 14 days |
| 5 | Static + Pagination | `rules/cities/dormagen/feste_veranstaltungen/` | URL parameters `?page=` in pagination | **CRITICAL: Verify page 1 ≠ page 2** |
| 6 | 2-Level Extraction | Most city scrapers | Detail pages with richer data | Override `fetch_level2_data()` |
| 7 | Custom HTML Parsing | `rules/cities/monheim/terminkalender/regex.py` | Non-standard structures | Custom regex patterns |

### Pagination Verification (CRITICAL)

Before implementing pagination (Patterns 4 or 5), you MUST verify it actually works:

**Why This Matters:**
Many sites have pagination URLs that return identical content to page 1. This causes:
- Duplicate events (770 "events" from 10 pages when there are only 77 unique events)
- Wasted scraping time
- Incorrect event counts in summaries

**Verification Steps:**
1. Fetch page 1 and page 2 content
2. Compare event count or titles
3. If identical → Use `MAX_PAGES=1` (all events on first page)
4. If different → Implement pagination with appropriate `MAX_PAGES` setting

---

## Level 2 Scraping

### When to Use 2-Level Scraping

- Calendar pages that link to individual event detail pages
- Detail pages contain richer data (location, description, end_time)
- Example: Monheim terminkalender links to individual event detail pages

### How It Works

1. **Level 1**: Main calendar page is scraped
   - Extracts events with: name, date, time, location, description
   - Extracts event detail URLs from links

2. **Level 2**: For each event, detail page is fetched
   - Extracts: `detail_location`, `detail_description`, `detail_full_description`
   - Merges into Event object in `raw_data` field

3. **Data Priority**: Level 2 data is used when available, Level 1 data as fallback

### Implementation Details

- `rules/base.py` provides `fetch_level2_data()` method for subclasses to override
- `Event` dataclass includes `event_url` and `raw_data` fields
- `rules/__init__.py` automatically calls Level 2 scraping after regex extraction

**See Also**: `docs/01_agent_guide.md#2-level-scraping` for detailed guide

---

## Category System

### 10 Standard Categories

| ID | Name (DE) | Name (EN) | Priority |
|----|-------------|-------------|----------|
| `family` | Familie | Family | 1 |
| `education` | Bildung | Education | 2 |
| `sport` | Sport | Sport | 3 |
| `culture` | Kultur | Culture | 4 |
| `market` | Markt | Market | 5 |
| `festival` | Fest | Festival | 6 |
| `adult` | Erwachsene | Adult | 7 |
| `community` | Gemeinschaft | Community | 8 |
| `nature` | Natur | Nature | 9 |
| `other` | Sonstiges | Other | 10 |

### Category Inference Logic

Uses **first-match priority**:
1. Searches German keywords (in priority order)
2. Searches English keywords (in priority order)
3. Returns `"other"` if no match

**Priority Order**: family → education → sport → culture → market → festival → adult → community → nature → other

**Usage**:
```python
from rules import categories

# Infer category from text
category = categories.infer_category(description, name)

# Normalize to standard ID
category = categories.normalize_category(category)
```

**IMPORTANT**: All scrapers use centralized category system from `rules/categories.py`. Do NOT implement custom category inference.

---

## Critical Requirements

### 14-Day Rule

**ALL scrapers MUST implement navigation to load 14 days of events from webpage.**

If page only shows limited events by default, you MUST:
- Click "Load More" buttons until 14 days of events are loaded
- Navigate through pagination to get all 14 days
- Set date filters to include 14 days from today
- Click "Next Month" or similar navigation to access future dates

### Required Event Fields

Scraper regex MUST extract:
- `name` (required): Event name/title
- `date` (required): Event date (format: DD.MM.YYYY)
- `time` (required): Event time (empty string if all-day)
- `location` (required): Event location/venue
- `description` (required): Event description
- `source` (required): Set to `self.url`

### Origin Field

**MUST set correct origin** - do NOT hardcode `"llm_fallback"`:

**Correct**:
```python
# In parse_with_llm_fallback()
return [Event(
    name=result,
    description="",
    location="",
    date="",
    time="",
    source=self.url,
    category="other",
    origin=self.get_origin(),  # ✅ Uses proper origin
)]
```

**Incorrect**:
```python
return [Event(
    ...
    origin="llm_fallback",  # ❌ Hardcoded - loses source identity
)]
```

---

## Common Issues & Solutions

From `docs/99_agent_errors.md`:

| Issue | Pattern | Root Cause | Solution |
|--------|----------|-------------|----------|
| Regex no match | Pattern too restrictive | Capture broadly, then clean (better than precise matching) |
| LLM timeout on large prompts | No explicit timeout + no chunking | Add 600s timeout + adaptive chunking + pre-structured extraction bypass |
| LangChain type errors | `api_key` expects SecretStr, not str | Wrap with `lambda: DEEPSEEK_API_KEY` |
| Pagination duplicates | Page 1 = Page 2 content | Verify pagination works, set `MAX_PAGES=1` if identical |
| None value handling | Required fields get None | Use `x or ""` idiom, validate early |
| Event loss in DB insert | Dict reference issues | Verify data flow, check database values directly |
| Origin field hardcoded | "llm_fallback" loses source | Use `self.get_origin()` instead of hardcoded string |

---

## Testing Procedures

### Test Single URL

```bash
# Test without saving to database
python main.py --url {url} --no-db --verbose

# Example:
python main.py --url "https://www.langenfeld.de/Startseite/Aktuelles-und-Information/Veranstaltungen.htm" --no-db --verbose
```

### Test Specific City

```bash
# Test city scrapers without DB
python main.py --cities {city} --no-db --verbose

# Example:
python main.py --cities langenfeld --no-db --verbose
```

### Test Regex Extraction

```python
from rules import fetch_events_from_url

# Test a single URL
events = fetch_events_from_url("https://example.com/events")
print(f"Found {len(events)} events")

# Check LLM fallback (disable regex)
events = fetch_events_from_url("https://example.com/events", use_llm_fallback=True)
```

### Debug Scrapers

```bash
# Enable verbose output
python main.py --cities {city} --verbose

# Check scraper selection
python -c "from rules import get_rule; r = get_rule('https://example.com'); print(r.scraper_class.__name__, r.regex_class.__name__)"
```

---

## Database Access

**IMPORTANT**: All tables are in the `webscraper` schema, not `public`.

### Tables

| Table | Description |
|--------|-------------|
| `events` | All scraped events (12,000+) |
| `events_distinct` | Deduplicated view (best row per name+start_datetime+origin) |
| `event_ratings` | Agent ratings (user_email = `deepseek` or `ollama`) |
| `runs` | Pipeline run tracking |
| `status` | Run metrics and performance data |
| `raw_summaries` | Raw scraper outputs for debugging |
| `city_coordinates` | City lat/lng for distance calculations |
| `city_road_distances` | Road distances between cities |

### Direct DB Access (via container)

```bash
docker exec webscraper python3 -c "
import psycopg2
conn = psycopg2.connect(host='postgres', dbname='vmpostgres', user='webscraper', password='webscraper', port=5432)
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM webscraper.events_distinct')
print(cur.fetchone())
"
```

### MCP Setup

No MCP configuration is currently active. See `docs/40_mcp_postgres_setup.md` for setup instructions if needed.

---

## Project Structure

```
WebScraper/
├── config.py              # Configuration and LLM setup
├── main.py                # CLI entry point
├── pipeline.py            # Pipeline orchestration
├── storage.py             # PostgreSQL database operations
├── requirements.txt       # Dependencies
│
├── agents/                # Agent implementations
│   ├── __init__.py
│   ├── scraper_agent.py   # Scraper (Agent 1)
│   ├── analyzer_agent.py  # Analyzer (Agent 2)
│   ├── rating_agent.py    # Rating (Agent 3) — DeepSeek + Ollama
│   └── tools.py          # LangChain tools (search, fetch)
│
├── rules/                 # URL rules and scrapers
│   ├── __init__.py       # Unified interface (fetch_events_from_url)
│   ├── base.py            # BaseScraper, BaseRule, Event dataclass
│   ├── registry.py        # URL → RuleEntry mapping
│   ├── urls.py            # CITY_URLS, AGGREGATOR_URLS constants
│   ├── categories.py       # Category inference and normalization
│   ├── utils.py          # Date/time normalization utilities
│   │
│   ├── aggregators/       # Aggregator scrapers
│   │   ├── eventim/
│   │   └── rausgegangen/
│   │
│   └── cities/           # City-specific scrapers (9 cities)
│       └── {city}/
│           └── {subfolder}/
│               ├── scraper.py
│               └── regex.py
│
├── locations/             # Ausflüge feature (family-friendly places)
│   ├── cli.py
│   ├── models.py
│   ├── storage.py
│   └── sources/
│
├── scripts/               # Database scripts
│   ├── init_postgres.sql  # Schema + permissions setup
│   ├── benchmark_rating.py
│   └── fix_city_variations.py
│
├── docker/                # Container setup
│   ├── entrypoint.sh
│   └── crontab            # Daily scrape + rating schedule
│
├── logs/                  # Timestamped logs
│   └── scrape_*.log
│
└── docs/                  # Full documentation
    ├── 00_DOCUMENTATION_INDEX.md  # Navigation
    ├── 01_agent_guide.md          # Agent workflows
    ├── 01_setup_guide.md          # City scraper setup guide
    ├── 11_architecture.md         # System internals
    ├── 14_categories.md          # Category system
    ├── 00_url_setup_prompt.md    # URL setup (7 patterns)
    └── 99_agent_errors.md         # Historical errors
```

---

## Code Style

### Conventions

- **No Comments**: Unless explicitly requested
- **Follow Patterns**: Use existing scraper implementations as templates
- **Existing Libraries**: Check `requirements.txt` before adding new dependencies
- **Testing**: Always test with `python main.py --url {url} --no-db --verbose`

### Common Patterns

**Scraper Implementation:**
```python
from rules.base import BaseScraper

class MyScraper(BaseScraper):
    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "mysite.com" in url

    def fetch(self) -> str:
        return self._fetch_with_requests()
        # OR return self._fetch_with_playwright()
```

**Regex Implementation:**
```python
from rules.base import BaseRule, Event

class MyRegex(BaseRule):
    def get_regex_patterns(self) -> List:
        return [re.compile(pattern, re.MULTILINE)]

    def extract_events(self, raw_content: str) -> List[Event]:
        events = self.parse_with_regex(raw_content)
        return events
```

---

## Important Files Quick Access

| File | Purpose |
|-------|----------|
| **AGENTS.md** | This file - AI assistant context |
| **README.md** | Main entry point and quick start |
| **docs/00_DOCUMENTATION_INDEX.md** | Documentation navigation |
| **docs/01_agent_guide.md** | Agent detailed workflows |
| **docs/01_setup_guide.md** | City scraper setup guide |
| **docs/11_architecture.md** | System architecture deep dive |
| **docs/14_categories.md** | Category system details |
| **docs/00_url_setup_prompt.md** | URL setup (7 proven patterns) |
| **docs/99_agent_errors.md** | Historical error patterns |
| **rules/base.py** | BaseScraper, BaseRule, Event dataclass |
| **rules/registry.py** | URL registration and auto-discovery |
| **rules/urls.py** | CITY_URLS, AGGREGATOR_URLS constants |
| **rules/categories.py** | Category inference and normalization |
| **agents/scraper_agent.py** | Scraper agent implementation |
| **agents/analyzer_agent.py** | Analyzer agent implementation |
