# WeeklyMail – Event Pipeline

Two-agent pipeline: **Scraper** -> **Analyzer**. Uses **LangChain** and **LLMs** (via **DeepSeek** (default, FREE!) or **Ollama** (local)) to find **local events** across multiple cities in NRW, structure them (name, description, location, date, source), and **store them in SQLite**. Events are then displayed in a separate app. Suitable for **automated runs** (e.g. weekly).

## Tech stack

- **LangChain** (langchain, langchain-community, langchain-ollama, langchain-openai)
- **LLM**: DeepSeek API (cloud, FREE, default) or Ollama (local)
- **Search**: DuckDuckGo (duckduckgo-search)
- **Scraping**: requests + BeautifulSoup
- **Storage**: SQLite (`data/events.db`) for scraped events and raw summaries

## Setup

### 1. Python environment

```bash
cd WeeklyMail
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Choose your LLM provider

**Option A: DeepSeek API (cloud, COMPLETELY FREE!) 🆓 ⭐⭐⭐ (DEFAULT)**

- Get a DeepSeek API key from [platform.deepseek.com](https://platform.deepseek.com/)
- Sign up for free account (completely free API access)
- Copy `.env.example` to `.env` and configure:
  ```
  LLM_PROVIDER=deepseek
  DEEPSEEK_API_KEY=your-actual-api-key
  DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
  DEEPSEEK_MODEL=deepseek-chat
  ```
  💰 Completely FREE API access
  🚀 Fast (70B model)
  🌟 Excellent quality for English

**Option B: Ollama (local)**

- Install [Ollama](https://ollama.ai/download) and start it.
- Pull a model (e.g. Mistral):

```bash
ollama pull mistral
```

- Copy `.env.example` to `.env` (or leave defaults):
  ```
  LLM_PROVIDER=ollama
  LLM_MODEL=mistral
  OLLAMA_BASE_URL=http://localhost:11434
  ```

### 3. Run pipeline

From the project root:

```bash
python main.py --location "Berlin"
```

**Options:**

- `-l, --location` – Location for event search (e.g. `"Munich"`, `"New York"`).
- `-m, --model` – LLM model (default: depends on provider).
- `-v, --verbose` – Also print raw summary and structured events.
- `--max-search` – Max search results (default: 8).
- `--fetch-urls` – How many result URLs to fetch and scrape (default: 3).
- `--agent` – Run a specific agent: `scraper`, `analyzer`, or `all` (default: `all`).
- `--list-summaries` – List all saved raw summaries from database (no LLM required).
- `--list-runs` – List all pipeline runs with event counts (no LLM required).
- `--load-summary <id>` – Load and print a specific raw summary by ID (no LLM required).
- `--cities` – Cities to scrape (default: all). Available: `monheim`, `langenfeld`, `leverkusen`, `hilden`, `dormagen`, `ratingen`, `solingen`, `haan`.
- `--search-queries` – Custom search queries for finding events (optional).

**Note:** The model to use depends on your `LLM_PROVIDER` in `.env`:
- `LLM_PROVIDER=deepseek` (default): Uses `DEEPSEEK_MODEL` (e.g., `deepseek-chat`)
- `LLM_PROVIDER=ollama`: Uses `LLM_MODEL` (e.g., `mistral`, `phi3`)

**Examples:**

```bash
# Default (scrapes all cities and regional aggregators)
python main.py

# Scrape specific cities
python main.py --cities monheim langenfeld leverkusen

# Custom search queries
python main.py --search-queries "jazz concerts NRW" "rock festivals Germany"

# Combine cities and custom search
python main.py --cities monheim langenfeld --search-queries "family events" "kids activities"

# Specific location
python main.py -l "Munich"

# Verbose + custom model
python main.py -l "Berlin" -m llama3.1 -v
```

**Debugging (run individual agents):**

```bash
# Run only the scraper agent (saves raw summary to DB)
python main.py --agent scraper --cities monheim langenfeld

# Run the scraper with custom search queries
python main.py --agent scraper --search-queries "concerts this weekend" "theater shows"

# Run the analyzer agent with saved summary (interactive)
python main.py --agent analyzer

# List all saved raw summaries
python main.py --list-summaries

# List all pipeline runs with event counts
python main.py --list-runs

# Load and view a specific raw summary by ID
python main.py --load-summary 1
```

## Architecture

| Step | Agent        | Input                    | Output                          |
|------|--------------|--------------------------|---------------------------------|
| 1    | **Scraper**  | Cities, search queries   | Raw event summary text          |
| 2    | **Analyzer** | Raw event text           | Structured list (JSON-like)     |

- **Scraper**: Scrapes fixed city-specific event pages and regional aggregators (rausgegangen.de, eventbrite.de, meetup.com), plus optional custom search queries via DuckDuckGo; LLM summarizes and includes **source** (URL/site) per event. Raw summaries are stored in `raw_summaries` table for debugging.
- **Analyzer**: LLM extracts events into `{name, description, location, date, time, category, source}` for storage.

Events are stored in **`data/events.db`** for automation and later use. The database contains three tables:
- `runs` – Pipeline runs tracking (agent, location, timestamp, event count)
- `events` – Structured event data (name, description, location, date, time, category, source, run_id)
- `raw_summaries` – Raw text output from scraper agent with metadata (cities, search queries, run_id) for debugging/replay

**Supported cities**: Monheim, Langenfeld, Leverkusen, Hilden, Dormagen, Ratingen, Solingen, Haan

## Project layout

```
WeeklyMail/
├── config.py           # LLM, Ollama, default location, DB path
├── main.py             # CLI entry point (supports --agent, --cities, --search-queries, --list-summaries, --load-summary, --list-runs)
├── pipeline.py         # Scraper -> Analyzer -> save to DB
├── storage.py          # SQLite: events, raw_summaries, runs tables, CRUD operations
├── data/
│   └── events.db       # Created on first run (unless --no-db)
├── agents/
│   ├── tools.py        # search_web, fetch_page
│   ├── scraper_agent.py # City-specific URLs + regional aggregators
│   └── analyzer_agent.py
├── scrapers/
│   ├── __init__.py
│   ├── base.py         # BaseScraper abstract class
│   ├── static.py       # Default static HTML scraper (requests + BeautifulSoup)
│   ├── monheim.py      # Monheim.de-specific scraper (Playwright for dynamic content)
│   ├── registry.py      # URL-to-scraper mapping
│   └── README.md       # Scrapers module documentation
└── README.md
```

**Note**: If you have an existing `data/events.db` from a previous version, delete it before running to let the new schema be created with the `runs` table and foreign keys.
