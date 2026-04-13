# WebScraper

Event scraper and rating pipeline for family-friendly events near Monheim am Rhein.

## Table of Contents

- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Learn More](#learn-more)

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set DEEPSEEK_API_KEY or OLLAMA_BASE_URL
```

### 3. Run

```bash
# Scrape all cities and save to DB
python main.py --agent all --full-run

# Rate unrated events (next 7 days)
python main.py --rate-events --days 7

# Rate with local Ollama (lightweight)
python main.py --rate-events --simple --batch-size 3 --days 7
```

---

## Usage

### CLI Options

```bash
python main.py [OPTIONS]

Scraping:
  --agent [scraper|analyzer|all]  Run specific agent (default: all)
  --cities TEXT                   Cities to scrape (default: all)
  --url TEXT                      Scrape a single URL directly
  --search-queries TEXT           Custom search queries
  --max-search INTEGER            Max search results (default: 8)
  --full-run                      Scrape + analyze in one pass
  --no-db                         Skip saving to database
  -v, --verbose                   Verbose output
  --model TEXT                    Override LLM model

Rating:
  --rate-events                   Run the rating agent
  --simple                        Lightweight mode for Ollama (rating + reason only)
  --batch-size INTEGER            Events per batch (default: 25, simple: 3)
  --days INTEGER                  Only rate events within next N days
  --date-filter YYYY-MM-DD        Only rate events on this date
  --today-only                    Only rate today's events
  --tomorrow-only                 Only rate tomorrow's events
  --max-events INTEGER            Cap total events to rate

Database:
  --list-runs                     List pipeline runs with event counts
  --list-summaries                List saved raw summaries
  --load-summary INTEGER          Load specific raw summary by ID
  --reset-db                      Reset database (careful!)
  --reanalyze-run INTEGER         Re-run analyzer on a saved run

Locations (Ausflüge):
  --locations [discover|check-urls|list|stats]
```

### Common Workflows

```bash
# Full daily run (scrape all + rate next 7 days)
python main.py --agent all --full-run && python main.py --rate-events --simple --batch-size 3 --days 7

# Scrape specific cities only
python main.py --cities monheim langenfeld

# Rate with DeepSeek (full sub-criteria)
python main.py --rate-events --days 30

# Rate with Ollama (fast, rating + reason only)
python main.py --rate-events --simple --batch-size 3 --days 7

# List recent runs
python main.py --list-runs

# Debug single URL
python main.py --url https://www.monheim.de/freizeit-tourismus/terminkalender -v
```

---

## Configuration

### Environment Variables (.env)

```bash
# LLM Provider: "deepseek" or "ollama"
LLM_PROVIDER=deepseek

# DeepSeek (default, cloud)
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Ollama (local, optional)
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=gemma2:2b

# PostgreSQL
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=vmpostgres
PG_USER=webscraper
PG_PASSWORD=webscraper
PG_SCHEMA=webscraper
```

### Supported Cities & Aggregators

**Cities**: monheim_am_rhein, langenfeld, leverkusen, hilden, dormagen, hitdorf, leichlingen, burscheid, duesseldorf

**Aggregators**: eventim.de (JSON API), rausgegangen.de (HTML) — run automatically alongside city scrapers

**2-Level Scraping** (fetches detail pages for enriched data): monheim terminkalender, langenfeld schauplatz, leverkusen stadt_erleben, leverkusen lust_auf, dormagen feste_veranstaltungen

---

## Project Structure

```
WebScraper/
├── main.py                # CLI entry point
├── pipeline.py            # Agent orchestration
├── storage.py             # PostgreSQL operations
├── config.py              # Environment config
├── requirements.txt
│
├── agents/
│   ├── scraper_agent.py   # Agent 1: fetch + extract events via LLM
│   ├── analyzer_agent.py  # Agent 2: structure + categorize events
│   ├── rating_agent.py    # Agent 3: rate events (DeepSeek or Ollama)
│   └── tools.py           # Web search + fetch tools
│
├── rules/                 # Scraping rules per city/aggregator
│   ├── base.py            # BaseScraper, Event dataclass
│   ├── registry.py        # URL → rule auto-discovery
│   ├── urls.py            # CITY_URLS, AGGREGATOR_URLS
│   ├── categories.py      # Category inference
│   ├── utils.py           # Date/time normalization
│   ├── cities/            # 9 cities, 17+ scrapers
│   └── aggregators/       # eventim, rausgegangen
│
├── locations/             # Ausflüge feature (family-friendly places)
│   ├── cli.py
│   ├── models.py
│   ├── storage.py
│   └── sources/           # Google Places, Overpass, manual
│
├── scripts/
│   ├── init_postgres.sql  # DB schema + permissions
│   ├── benchmark_rating.py
│   └── fix_city_variations.py
│
├── docs/                  # See docs/00_DOCUMENTATION_INDEX.md
├── docker/                # Dockerfile, entrypoint, crontab
└── .github/workflows/     # CI/CD (test + build + push to ghcr.io)
```

---

## Database Schema

PostgreSQL (`vmpostgres` database, `webscraper` schema):

| Table | Purpose |
|-------|---------|
| `events` | All scraped events (name, description, location, date, category) |
| `events_distinct` | Deduplicated view (best row per name+start_datetime+origin) |
| `event_ratings` | Agent ratings (rating 1-5, reason, sub-criteria) |
| `runs` | Pipeline run tracking |
| `status` | Run metrics (duration, event counts) |
| `raw_summaries` | Raw scraper output for debugging |
| `locations` | Family-friendly places (Ausflüge feature) |

---

## Rating Modes

| Mode | LLM | Output | Speed |
|------|-----|--------|-------|
| Default (tool-calling) | DeepSeek | 6 sub-criteria + reason | ~25/batch |
| `--simple` | Ollama (local) | rating + reason only | ~200/h |

---

## Tech Stack

- **LangChain** — LLM orchestration
- **DeepSeek** — Cloud LLM (default)
- **Ollama** — Local LLM (optional, `--simple` mode)
- **Requests + BeautifulSoup** — HTTP + HTML parsing
- **Playwright** — Dynamic content rendering
- **PostgreSQL** — Storage
- **Rich** — Terminal UI
- **Docker + cron** — Automated daily/weekly runs

## Learn More

- [docs/01_agent_guide.md](docs/01_agent_guide.md) — Scraper & analyzer agent internals
- [docs/01_setup_guide.md](docs/01_setup_guide.md) — How to add new city scrapers
- [docs/11_architecture.md](docs/11_architecture.md) — System architecture and data flow
- [AGENTS.md](AGENTS.md) — Full AI assistant context
