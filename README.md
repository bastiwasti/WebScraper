# WeeklyMail – Multi-Agent Event Pipeline

Three-agent pipeline: **Scraper** → **Analyzer** → **Writer**. Uses **LangChain** and a **local Mistral** (or other model) via **Ollama** to find **family- and children-friendly events** in **Monheim 40789**, structure them (name, description, location, date, source), **store them in SQLite**, and produce an email-ready document. Suitable for **automated runs** (e.g. weekly).

## Tech stack

- **LangChain** (langchain, langchain-community, langchain-ollama)
- **Local LLM**: Mistral (or any Ollama model)
- **Search**: DuckDuckGo (duckduckgo-search)
- **Scraping**: requests + BeautifulSoup
- **Storage**: SQLite (`data/events.db`) for scraped events

## Setup

### 1. Python environment

```bash
cd WeeklyMail
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Ollama + Mistral

- Install [Ollama](https://ollama.ai/download) and start it.
- Pull Mistral (or another model):

```bash
ollama pull mistral
```

- Optional: copy `.env.example` to `.env` and set `LLM_MODEL` and `OLLAMA_BASE_URL` if needed.

### 3. Run the pipeline

From the project root:

```bash
python main.py --location "Berlin" --output newsletter.txt
```

**Options:**

- `-l, --location` – Location for event search (e.g. `"Munich"`, `"New York"`).
- `-m, --model` – Ollama model (default: `mistral`).
- `-o, --output` – Write the email document to a file.
- `-v, --verbose` – Also print raw summary and structured events.
- `--max-search` – Max search results (default: 5).
- `--fetch-urls` – How many result URLs to fetch and scrape (default: 2).

**Examples:**

```bash
# Default (location from .env or empty)
python main.py

# Specific city, save to file
python main.py -l "Munich" -o newsletter.txt

# Verbose + custom model
python main.py -l "Berlin" -m llama3.1 -v
```

## Architecture

| Step | Agent        | Input                    | Output                          |
|------|--------------|--------------------------|---------------------------------|
| 1    | **Scraper**  | Location query           | Raw event summary text          |
| 2    | **Analyzer** | Raw event text           | Structured list (JSON-like)     |
| 3    | **Writer**   | Structured event list    | Email-ready text document       |

- **Scraper**: Multiple search queries (Kinder/Familie in Monheim/40789), then `fetch_page` on result URLs; LLM summarizes and includes **source** (URL/site) per event.
- **Analyzer**: LLM extracts events into `{name, description, location, date, time, source}` for storage and the next agent.
- **Writer**: LLM turns that list into a single email body (subject, intro, event list with source, sign-off).

Events are stored in **`data/events.db`** for automation and later use.

## Project layout

```
WeeklyMail/
├── config.py           # LLM, Ollama, Monheim 40789, DB path
├── main.py             # CLI entry point
├── pipeline.py         # Scraper → Analyzer → save to DB → Writer
├── storage.py          # SQLite: insert_events, get_events
├── data/
│   └── events.db       # Created on first run (unless --no-db)
├── agents/
│   ├── tools.py        # search_web, fetch_page
│   ├── scraper_agent.py
│   ├── analyzer_agent.py
│   └── writer_agent.py
└── README.md
```

## Optional: sending as email later

The document from `--output` is plain text. You can:

- Paste it into Gmail/Outlook, or
- Add a small script that reads the file and uses `smtplib` / a transactional API to send it.

If you want, we can add a fourth step (e.g. “sender” agent or script) that takes the generated file and sends it via your chosen provider.
