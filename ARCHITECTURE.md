# Architecture

This document describes the WebScraper system architecture, data flow, and component interactions.

## Table of Contents

- [System Overview](#system-overview)
- [Pipeline Flow](#pipeline-flow)
- [Component Architecture](#component-architecture)
- [Data Models](#data-models)
- [Agent Communication](#agent-communication)
- [Database Schema](#database-schema)
- [File Organization](#file-organization)

---

## System Overview

WebScraper is a two-agent LLM-powered pipeline for discovering and structuring local events:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   CLI Entry     │─────▶│   Pipeline      │─────▶│   Storage       │
│   (main.py)     │      │   Orchestrator  │      │   (SQLite)      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │  Scraper    │    │  Analyzer   │    │  Database   │
     │  Agent 1    │────▶│  Agent 2    │────▶│   Layer     │
     └─────────────┘    └─────────────┘    └─────────────┘
            │                   │
            ▼                   ▼
     ┌─────────────┐    ┌─────────────┐
     │  URL Rules  │    │    LLM      │
     │   System    │    │  Provider   │
     └─────────────┘    └─────────────┘
```

### Core Components

| Component | Purpose | File |
|-----------|---------|------|
| **CLI Entry** | Command-line interface and argument parsing | `main.py` |
| **Pipeline Orchestrator** | Coordinates agent execution | `pipeline.py` |
| **Scraper Agent** | Fetches and summarizes event sources | `agents/scraper_agent.py` |
| **Analyzer Agent** | Extracts structured event data | `agents/analyzer_agent.py` |
| **URL Rules System** | Maps URLs to scrapers/parsers | `rules/registry.py` |
| **Storage Layer** | SQLite database operations | `storage.py` |
| **LLM Provider** | DeepSeek integration | `config.py` |

---

## Pipeline Flow

### Complete Pipeline Execution

```python
# pipeline.py:6
def run_pipeline(
    location: str,
    max_search: int,
    fetch_urls: int,
    model: str,
    save_to_db: bool,
    cities: list[str],
    search_queries: list[str],
) -> tuple[str, list[dict]]:
```

#### Step 1: Scraper Agent

```
1. Get URLs from rules system (cities + aggregators)
2. For each URL:
   - Create scraper instance (based on URL matching)
   - Fetch content (requests or Playwright)
   - Parse events with regex patterns
   - Fall back to LLM if regex fails
3. Aggregate all events
4. Generate raw summary with LLM
5. Save to database (raw_summaries table)
```

**Output**: Raw event summary text

#### Step 2: Analyzer Agent

```
1. Receive raw summary from scraper
2. Split into chunks (if too large)
3. For each chunk:
   - Send to LLM with extraction prompt
   - Parse JSON response
   - Extract events into structured format
4. Merge all events from chunks
5. Validate each event (name, date, location, source)
6. Infer category from description/name
7. Save to database (events table)
8. Update run status with metrics
```

**Output**: List of structured event dictionaries

### Individual Agent Execution

Agents can also run independently:

```bash
# Run only scraper
python main.py --agent scraper --cities monheim

# Run only analyzer (requires manual input)
python main.py --agent analyzer
```

---

## Component Architecture

### Scraper Agent

```
┌─────────────────────────────────────────────────────┐
│                ScraperAgent                        │
│  (agents/scraper_agent.py:78)                     │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                  │
│  - Collect URLs from rules system                  │
│  - Fetch content from each URL                     │
│  - Extract events via regex or LLM                 │
│  - Generate raw summary with LLM                   │
│  - Track metrics (time, events per URL)            │
└─────────────────────────────────────────────────────┘
            │
            ├──▶ URL Rules System (rules/registry.py)
            │    - URL → RuleEntry mapping
            │    - Auto-discovery of scrapers/parsers
            │
            ├──▶ Scrapers (rules/aggregators/*/scraper.py)
            │    - BaseScraper subclasses
            │    - Content fetching (requests/Playwright)
            │
            ├──▶ Regex Parsers (rules/aggregators/*/regex.py)
            │    - BaseRule subclasses
            │    - Event extraction patterns
            │
            ├──▶ LLM (DeepSeek)
            │    - Raw summary generation
            │    - LLM fallback for extraction
            │
            └──▶ Rich UI (progress bars, tables)
```

### Analyzer Agent

```
┌─────────────────────────────────────────────────────┐
│               AnalyzerAgent                         │
│  (agents/analyzer_agent.py:30)                     │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                  │
│  - Parse raw event text from scraper               │
│  - Extract structured events via LLM               │
│  - Validate event data                             │
│  - Infer categories                                │
│  - Save events to database                         │
└─────────────────────────────────────────────────────┘
            │
            ├──▶ LLM Prompts (system + user)
            │    - JSON extraction instructions
            │    - Category definitions
            │
            ├──▶ JSON Parser
            │    - Handle various output formats
            │    - Code fence removal
            │
            ├──▶ Category Inference
            │    - Keyword-based classification
            │    - Default: family, adult, sport, other
            │
            ├──▶ Chunking Strategy
            │    - Split large texts
            │    - Avoid token limits
            │
            └──▶ Storage Layer (storage.py)
                 - Insert events
                 - Update run status
```

### URL Rules System

```
┌─────────────────────────────────────────────────────┐
│              Rules Registry                         │
│          (rules/registry.py)                        │
├─────────────────────────────────────────────────────┤
│  Auto-Discovery:                                    │
│  - rules/cities/*/scraper.py                        │
│  - rules/cities/*/regex.py                          │
│  - rules/aggregators/*/scraper.py                   │
│  - rules/aggregators/*/regex.py                     │
│                                                     │
│  Registry: URL → RuleEntry                          │
│  - scraper_class: BaseScraper subclass              │
│  - regex_class: BaseRule subclass                  │
└─────────────────────────────────────────────────────┘
            │
            ├──▶ BaseScraper (rules/base.py:38)
            │    - fetch() method
            │    - _fetch_with_requests()
            │    - _fetch_with_playwright()
            │    - needs_browser property
            │
            └──▶ BaseRule (rules/base.py:117)
                 - get_regex_patterns()
                 - parse_with_regex()
                 - parse_with_llm_fallback()
                 - extract_events()
```

---

## Data Models

### Event Object

```python
# rules/base.py:26
@dataclass
class Event:
    name: str
    description: str
    location: str
    date: str
    time: str
    source: str
    category: str = "other"
```

### Rule Entry

```python
# rules/registry.py:19
class RuleEntry:
    url: str
    scraper_class: Type[BaseScraper]
    regex_class: Type[BaseRule]
```

### Structured Event (DB)

```python
{
    "name": str,
    "description": str,
    "location": str,
    "date": str,
    "time": str,
    "category": str,
    "source": str,
    "created_at": str (ISO timestamp),
    "run_id": int (foreign key)
}
```

---

## Agent Communication

### Scraper → Analyzer

**Data Transfer**: Raw text summary

```python
# pipeline.py:32
raw_summary = scraper.run(...)

# pipeline.py:46
structured_events = analyzer.run(raw_summary, scraper_run_id=scraper_run_id)
```

**Run Linking**: Analyzer tracks scraper run ID

```python
# pipeline.py:50
analyzer_run_id = create_run("analyzer", loc, raw_summary_id)
```

### Agent → Storage

**Scraper writes**:
- `runs` table: Scraper run metadata
- `raw_summaries` table: Raw event text
- `status` table: Scraping metrics

**Analyzer writes**:
- `runs` table: Analyzer run metadata
- `events` table: Structured event data
- `status` table: Analysis metrics

---

## Database Schema

### Tables

#### `runs` - Pipeline run tracking

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `agent` | TEXT | Agent type (comma-separated: "scraper, analyzer") |
| `cities` | TEXT | Cities scraped (comma-separated) |
| `created_at` | TEXT | ISO timestamp |
| `raw_summary_id` | INTEGER | FK to raw_summaries (analyzer only) |

#### `status` - Run status metrics

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `run_id` | INTEGER | FK to runs |
| `linked_run_id` | INTEGER | FK to related run (analyzer → scraper) |
| `urls` | TEXT | JSON array of URLs scraped |
| `start_time` | TEXT | ISO timestamp |
| `end_time` | TEXT | ISO timestamp |
| `duration` | REAL | Duration in seconds |
| `events_found` | INTEGER | Total events extracted |
| `valid_events` | INTEGER | Events with required fields |

#### `events` - Structured event data

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `run_id` | INTEGER | FK to runs (analyzer) |
| `name` | TEXT | Event title |
| `description` | TEXT | Event description |
| `location` | TEXT | Event venue |
| `date` | TEXT | Event date |
| `time` | TEXT | Event time |
| `category` | TEXT | Event category |
| `source` | TEXT | Source URL/site |
| `created_at` | TEXT | ISO timestamp |

#### `raw_summaries` - Scraper output for debugging

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `run_id` | INTEGER | FK to runs (scraper) |
| `location` | TEXT | Location for summary |
| `max_search` | INTEGER | Max search results |
| `fetch_urls` | INTEGER | URLs fetched |
| `cities` | TEXT | JSON array of cities |
| `search_queries` | TEXT | JSON array of queries |
| `raw_summary` | TEXT | Raw event text |
| `created_at` | TEXT | ISO timestamp |

### Relationships

```
runs (1) ───────┬──▶ (N) events
    │            │
    │            └──▶ (1) status
    │
    └──▶ (0..1) raw_summaries (scraper only)
         │
         └──▶ (1) runs (analyzer) via raw_summary_id

runs (1) ───────▶ (0..1) runs (linked_run_id)
    (analyzer)       (scraper)
```

---

## File Organization

```
WebScraper/
├── config.py              # Configuration and LLM setup
├── main.py                # CLI entry point
├── pipeline.py            # Pipeline orchestration
├── storage.py             # SQLite operations
├── requirements.txt       # Dependencies
│
├── agents/                # Agent implementations
│   ├── __init__.py
│   ├── scraper_agent.py   # Scraper (Agent 1)
│   ├── analyzer_agent.py  # Analyzer (Agent 2)
│   └── tools.py          # LangChain tools (search, fetch)
│
├── rules/                 # URL rules and scrapers
│   ├── __init__.py       # Unified interface
│   ├── base.py            # Base classes
│   ├── registry.py        # URL → RuleEntry mapping
│   ├── urls.py            # CITY_URLS, AGGREGATOR_URLS
│   │
│   ├── aggregators/       # Aggregator scrapers
│   │   ├── __init__.py
│   │   ├── eventbrite/
│   │   │   ├── scraper.py
│   │   │   └── regex.py
│   │   ├── meetup/
│   │   │   ├── scraper.py
│   │   │   └── regex.py
│   │   └── rausgegangen/
│   │       ├── scraper.py
│   │       └── regex.py
│   │
│   └── cities/           # City-specific scrapers
│       └── {city}/
│           ├── scraper.py
│           └── regex.py
│
├── data/                  # Database storage
│   └── events.db          # SQLite database (created on run)
│
└── logs/                  # Timestamped logs
    └── scrape_*.log
```

---

## LLM Integration

### Supported Providers

| Provider | Model | Configuration |
|----------|-------|---------------|
| **DeepSeek** | `deepseek-chat` | `LLM_PROVIDER=deepseek` (default) |

### LLM Usage

**Scraper Agent**:
- Raw summary generation (low temperature: 0.2)
- LLM fallback for event extraction (when regex fails)

**Analyzer Agent**:
- Structured event extraction (low temperature: 0.1)
- JSON output parsing
- Category inference (keyword-based)

### Prompt Engineering

Prompts are defined in agent files and can be customized:
- Scraper: `agents/scraper_agent.py:56` (SYSTEM_PROMPT)
- Analyzer: `agents/analyzer_agent.py:13` (SYSTEM_PROMPT)

---

## Error Handling

### Scraper Failures

- **URL 404**: Logged, skipped
- **Regex no match**: Falls back to LLM
- **LLM timeout**: Logged, returns empty events

### Analyzer Failures

- **Invalid JSON**: Logged, returns empty events
- **Missing fields**: Event filtered (not saved)
- **Token limit**: Text split into chunks

### Database Errors

- **Connection errors**: Logged, retries attempted
- **Constraint violations**: Logged, event skipped
- **Migration issues**: Auto-initializes schema

---

## Performance Characteristics

### Scraper

| Metric | Typical Value |
|--------|--------------|
| Per URL (regex) | ~1-2 seconds |
| Per URL (LLM) | ~5-10 seconds |
| Per city (3 URLs) | ~10-30 seconds |
| Full pipeline | ~1-2 minutes |

### Analyzer

| Metric | Typical Value |
|--------|--------------|
| Per event | ~0.1-0.5 seconds |
| Per 10 events | ~1-5 seconds |
| Per 50 events | ~5-15 seconds |

### Bottlenecks

1. **LLM calls**: Slowest component
2. **Network requests**: Dependent on website response
3. **Playwright**: Heavier than requests

---

## Extensibility

### Adding New Agents

```python
# Create new agent
class MyAgent:
    def __init__(self, model: str):
        self.llm = ...

    def run(self, input_data):
        # Implementation
        return output

# Register in pipeline
def run_my_agent(input_data):
    agent = MyAgent()
    return agent.run(input_data)
```

### Adding New Scrapers

See [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md#adding-a-new-event-source)

### Custom Storage Backends

Replace `storage.py` with your own implementation:

```python
def insert_events(events, run_id):
    # Your storage logic
    pass
```

---

## Security Considerations

### API Keys

- Stored in `.env` file (not in git)
- Loaded via `python-dotenv`
- Never logged or exposed in output

### URL Safety

- Only processes HTTP/HTTPS URLs
- User-Agent header for identification
- Timeout limits (15 seconds default)

### LLM Safety

- Low temperature for deterministic output
- Input sanitization before LLM calls
- Output validation (JSON parsing)

---

## Resources

- **Source Code**: https://github.com/your-repo/WebScraper
- **Dependencies**: `requirements.txt`
- **Configuration**: `config.py`
- **SCRAPER_GUIDE**: [SCRAPER_GUIDE.md](SCRAPER_GUIDE.md)
- **ANALYZER_GUIDE**: [ANALYZER_GUIDE.md](ANALYZER_GUIDE.md)
- **TROUBLESHOOTING**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
