# WebScraper - Agent Documentation

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
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Configure LLM

**DeepSeek (default, FREE)**

```bash
cp .env.example .env
# Edit .env and add:
# DEEPSEEK_API_KEY=your-key-from-platform.deepseek.com
```

### 3. Run the pipeline

```bash
# Scrape all cities (default)
python main.py

# Scrape specific cities
python main.py --cities monheim langenfeld

# Custom search queries
python main.py --search-queries "concerts this weekend" "jazz events"
```

---

## Usage

### CLI Options

```bash
python main.py [OPTIONS]

Options:
  -l, --location TEXT       Location for search (default: "Monheim 40789")
  --cities TEXT             Cities to scrape (default: all)
                              Available: monheim_am_rhein, langenfeld, leverkusen,
                              hilden, dormagen, hitdorf, leichlingen, burscheid
  --search-queries TEXT     Custom search queries (optional)
  --max-search INTEGER      Max search results (default: 8)
  --agent [scraper|analyzer|all] Run specific agent (default: all)
  --model TEXT              LLM model name
  -v, --verbose             Print raw summary and structured events
  --no-db                   Skip saving to database
  --list-summaries          List saved raw summaries
  --list-runs               List pipeline runs with event counts
  --load-summary INTEGER    Load specific raw summary by ID
```

### Common Workflows

**Scrape specific cities:**

```bash
python main.py --cities monheim langenfeld
```

**Run scraper only (saves to DB for later analysis):**

```bash
python main.py --agent scraper --cities monheim
```

**Run analyzer on saved summary:**

```bash
python main.py --agent analyzer
# Paste raw summary when prompted
```

**List recent runs:**

```bash
python main.py --list-runs
```

**View a specific raw summary:**

```bash
python main.py --load-summary 1
```

**Debug with verbose output:**

```bash
python main.py --cities monheim -v
```

---

## Configuration

### Environment Variables (.env)

```bash
# LLM Provider (deepseek)
LLM_PROVIDER=deepseek

# DeepSeek Configuration
DEEPSEEK_API_KEY=your-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Default location for searches
DEFAULT_LOCATION=Monheim 40789

# Focus on family/children events
FAMILY_FOCUS=true

# Database path
DB_PATH=data/events.db
```

### Supported Cities

See [docs/01_setup_guide.md](docs/01_setup_guide.md) for complete list of supported cities and how to add new ones.

**Cities**: monheim_am_rhein, langenfeld, leverkusen, hilden, dormagen, hitdorf, leichlingen, burscheid

**Aggregators**: eventim.de (public JSON API), rausgegangen.de (HTML scraping) — these run automatically alongside city scrapers

**Advanced Features**:
- **2-Level Scraping**: Monheim terminkalender, Langenfeld schauplatz, Leverkusen stadt_erleben, Leverkusen lust_auf, and Dormagen feste_veranstaltungen fetch event detail pages for enhanced data
---

## Project Structure

```
WebScraper/
├── README.md              # This file - quick start and usage
├── docs/                  # Documentation directory
│   ├── 00_DOCUMENTATION_INDEX.md  # Documentation index
│   ├── 00_url_setup_prompt.md     # URL setup prompt
│   ├── 01_agent_guide.md          # How scraper & analyzer agents work
│   ├── 01_setup_guide.md           # How to add new city scrapers
│   ├── 11_architecture.md         # System internals and data flow
│   └── ...                         # See docs/00_DOCUMENTATION_INDEX.md
├── config.py              # Configuration and environment variables
├── main.py                # CLI entry point
├── pipeline.py            # Pipeline orchestration
├── storage.py             # SQLite database operations
├── requirements.txt       # Python dependencies
├── agents/                # Agent implementations
│   ├── __init__.py
│   ├── scraper_agent.py   # Scraper agent (Agent 1)
│   ├── analyzer_agent.py  # Analyzer agent (Agent 2)
│   └── tools.py           # Web search and fetch tools
├── rules/                 # URL rules and scrapers
│   ├── base.py            # Base rule interface
│   ├── registry.py        # URL-to-rule mapping
│   ├── urls.py            # CITY_URLS, URL helper functions
│   └── cities/            # City-specific scrapers
│       └── {city}/{subfolder}/
│           ├── scraper.py
│           ├── regex.py
│           └── __init__.py
├── data/                  # Database storage
│   └── events.db          # SQLite database (created on run)
├── logs/                  # Timestamped log files
└── .env                   # Environment configuration (not in git)
```

---

## Learn More

- **[docs/01_agent_guide.md](docs/01_agent_guide.md)** - How both scraper & analyzer agents work, LLM integration
- **[docs/01_setup_guide.md](docs/01_setup_guide.md)** - Step-by-step guide to add new city scrapers with navigation
- **[docs/11_architecture.md](docs/11_architecture.md)** - System architecture, data flow, agent communication
- **[docs/00_DOCUMENTATION_INDEX.md](docs/00_DOCUMENTATION_INDEX.md)** - Full documentation overview

## Database Schema

The `data/events.db` SQLite database contains:

| Table | Purpose |
|-------|---------|
| `runs` | Pipeline run tracking (agent, location, timestamp) |
| `events` | Structured event data (name, description, location, date, etc.) |
| `raw_summaries` | Raw text from scraper (for debugging) |
| `status` | Run status with metrics (duration, event counts) |

---

## Tech Stack

- **LangChain** - LLM orchestration
- **DeepSeek** - Free cloud LLM (default)
- **DuckDuckGo Search** - Web search
- **Requests + BeautifulSoup** - HTTP and HTML parsing
- **Playwright** - Dynamic content rendering
- **SQLite** - Event storage
- **Rich** - Terminal UI and progress bars
