# WeeklyMail – Multi-Agent Event Pipeline

Three-agent pipeline: **Scraper**-> **Analyzer**-> **Writer**. Uses **LangChain** and **LLMs** (via **Ollama**, **xAI API**, **z.AI API**, **Groq**, or **DeepSeek**) to find **local events** across multiple cities in NRW, structure them (name, description, location, date, source), **store them in SQLite**, and produce an email-ready document. Suitable for **automated runs** (e.g. weekly).

## Tech stack

- **LangChain** (langchain, langchain-community, langchain-ollama, langchain-openai)
- **LLM**: Ollama (local), xAI API (cloud), z.AI API (cloud), Groq (cloud), or DeepSeek (cloud, FREE!)
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

**Option A: Ollama (local)**

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

**Option B: xAI API (cloud)**

- Get an xAI API key from [x.ai](https://x.ai/)
- Copy `.env.example` to `.env` and configure:
  ```
  LLM_PROVIDER=xai
  XAI_API_KEY=your-actual-api-key
  XAI_BASE_URL=https://api.x.ai/v1
  XAI_MODEL=grok-beta
  ```

**Option C: z.AI API (cloud)**

- Get a z.AI API key from [z.ai/model-api](https://z.ai/model-api)
- Purchase/recharge a resource package (required for API usage)
- Copy `.env.example` to `.env` and configure:
  ```
  LLM_PROVIDER=zai
  ZAI_API_KEY=your-actual-api-key
  ZAI_BASE_URL=https://api.z.ai/api/paas/v4
  ZAI_MODEL=glm-4.7
  ```
  ⚠️ Note: z.AI only offers coding plans, not general API access

**Option D: Groq API (cloud, FREE tier, very fast!) ⭐**

- Get a Groq API key from [console.groq.com](https://console.groq.com/)
- Sign up for free tier (no credit card required)
- Copy `.env.example` to `.env` and configure:
  ```
  LLM_PROVIDER=groq
  GROQ_API_KEY=your-actual-api-key
  GROQ_BASE_URL=https://api.groq.com/openai/v1
  GROQ_MODEL=llama3-70b-8192
  ```
  💡 Recommended: Fast with free tier (500+ tokens/s)
  ⚠️ Note: Console may have issues (login broken)

**Option E: DeepSeek API (cloud, COMPLETELY FREE!) 🆓 ⭐⭐⭐

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

### 3. Run the pipeline

From the project root:

```bash
python main.py --location "Berlin" --output newsletter.txt
```

**Options:**

- `-l, --location` – Location for event search (e.g. `"Munich"`, `"New York"`).
- `-m, --model` – LLM model (default: depends on provider).
- `-o, --output` – Write the email document to a file.
- `-v, --verbose` – Also print raw summary and structured events.
- `--max-search` – Max search results (default: 5).
- `--fetch-urls` – How many result URLs to fetch and scrape (default: 2).
- `--agent` – Run a specific agent: `scraper`, `analyzer`, `writer`, or `all` (default: `all`).
- `--list-summaries` – List all saved raw summaries from database (no LLM required).
- `--load-summary <id>` – Load and print a specific raw summary by ID (no LLM required).
- `--cities` – Cities to scrape (default: all). Available: `monheim`, `langenfeld`, `leverkusen`, `hilden`, `dormagen`, `ratingen`, `solingen`, `haan`.
- `--search-queries` – Custom search queries for finding events (optional).

**Note:** The model to use depends on your `LLM_PROVIDER` in `.env`:
- `LLM_PROVIDER=ollama`: Uses `LLM_MODEL` (e.g., `mistral`, `phi3`)
- `LLM_PROVIDER=xai`: Uses `XAI_MODEL` (e.g., `grok-beta`)
- `LLM_PROVIDER=zai`: Uses `ZAI_MODEL` (e.g., `glm-4.7`)
- `LLM_PROVIDER=groq`: Uses `GROQ_MODEL` (e.g., `llama3-70b-8192`)
- `LLM_PROVIDER=deepseek`: Uses `DEEPSEEK_MODEL` (e.g., `deepseek-chat`)

**Examples:**

```bash
# Default (scrapes all cities and regional aggregators)
python main.py

# Scrape specific cities
python main.py --cities monheim langenfeld leverkusen -o newsletter.txt

# Custom search queries
python main.py --search-queries "jazz concerts NRW" "rock festivals Germany" -o newsletter.txt

# Combine cities and custom search
python main.py --cities monheim langenfeld --search-queries "family events" "kids activities" -o newsletter.txt

# Specific location, save to file
python main.py -l "Munich" -o newsletter.txt

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

# Run the writer agent with structured events (interactive)
python main.py --agent writer

# List all saved raw summaries
python main.py --list-summaries

# Load and view a specific raw summary by ID
python main.py --load-summary 1
```

## Architecture

| Step | Agent        | Input                    | Output                          |
|------|--------------|--------------------------|---------------------------------|
| 1    | **Scraper**  | Cities, search queries   | Raw event summary text          |
| 2    | **Analyzer** | Raw event text           | Structured list (JSON-like)     |
| 3    | **Writer**   | Structured event list    | Email-ready text document       |

- **Scraper**: Scrapes fixed city-specific event pages and regional aggregators (rausgegangen.de, eventbrite.de, meetup.com), plus optional custom search queries via DuckDuckGo; LLM summarizes and includes **source** (URL/site) per event. Raw summaries are stored in `raw_summaries` table for debugging.
- **Analyzer**: LLM extracts events into `{name, description, location, date, time, source}` for storage and the next agent.
- **Writer**: LLM turns that list into a single email body (subject, intro, event list with source, sign-off).

Events are stored in **`data/events.db`** for automation and later use. The database contains two tables:
- `events` – Structured event data (name, description, location, date, time, source)
- `raw_summaries` – Raw text output from the scraper agent with metadata (cities, search queries) for debugging/replay

**Supported cities**: Monheim, Langenfeld, Leverkusen, Hilden, Dormagen, Ratingen, Solingen, Haan

## Project layout

```
WeeklyMail/
├── config.py           # LLM, Ollama, default location, DB path
├── main.py             # CLI entry point (supports --agent, --cities, --search-queries, --list-summaries, --load-summary)
├── pipeline.py         # Scraper-> Analyzer-> save to DB-> Writer
├── storage.py          # SQLite: events & raw_summaries tables, CRUD operations
├── data/
│   └── events.db       # Created on first run (unless --no-db)
├── agents/
│   ├── tools.py        # search_web, fetch_page
│   ├── scraper_agent.py # City-specific URLs + regional aggregators
│   ├── analyzer_agent.py
│   └── writer_agent.py
└── README.md
```

**Note**: If you have an existing `data/events.db` from a previous version, delete it before running to let the new schema be created with the `cities` and `search_queries` columns.

## Optional: sending as email later

The document from `--output` is plain text. You can:

- Paste it into Gmail/Outlook, or
- Add a small script that reads the file and uses `smtplib` / a transactional API to send it.

If you want, we can add a fourth step (e.g. “sender” agent or script) that takes the generated file and sends it via your chosen provider.
