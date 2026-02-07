# Agent Guide

This guide explains how the scraper and analyzer agents work, and how to extend the system.

## Table of Contents

- [Scraper Agent](#scraper-agent)
- [Analyzer Agent](#analyzer-agent)
- [URL Rules System](#url-rules-system)
- [Adding a New Event Source](#adding-a-new-event-source)
- [LLM Integration](#llm-integration)
- [Performance Optimization](#performance-optimization)
- [Debugging](#debugging)

---

## Scraper Agent

The scraper agent (`agents/scraper_agent.py`) is the first agent in the pipeline. Its job is to:

1. **Collect URLs** from city-specific event pages and regional aggregators
2. **Fetch content** from each URL using appropriate scraping methods
3. **Extract events** using regex patterns (or LLM fallback)
4. **Summarize results** for the analyzer agent

### Flow

```
1. Get URLs from rules system (cities + aggregators)
2. For each URL:
   a. Create scraper instance (based on URL)
   b. Fetch content (requests or Playwright)
   c. Parse events with regex patterns
   d. Fall back to LLM if regex fails
3. Aggregate all events
4. Generate raw summary with LLM
5. Save to database (raw_summaries table)
```

### Key Components

- **Scraper Agent** (`agents/scraper_agent.py`): Orchestrates the scraping process
- **URL Rules** (`rules/registry.py`): Maps URLs to specific scrapers/parsers
- **Base Classes** (`rules/base.py`): `BaseScraper` for fetching, `BaseRule` for parsing
- **Scraper Classes** (`rules/cities/*/scraper.py`): Per-site fetching logic
- **Regex Classes** (`rules/cities/*/regex.py`): Per-site parsing logic

---

## Analyzer Agent

The analyzer agent (`agents/analyzer_agent.py`) is the second agent in the pipeline. Its job is to:

1. **Receive raw event text** from the scraper agent
2. **Parse text** into structured event data using an LLM
3. **Validate events** ensuring required fields are present
4. **Save events** to database
5. **Track metrics** (events found, valid events, duration)

### Flow

```
1. Receive raw summary from scraper
2. Split into chunks (if too large)
3. For each chunk:
   a. Send to LLM with extraction prompt
   b. Parse JSON response
   c. Extract events into structured format
4. Merge all events from chunks
5. Validate each event (name, date, location, source)
6. Infer category from description/name
7. Save to database (events table)
8. Update run status with metrics
```

### Key Components

- **Analyzer Agent** (`agents/analyzer_agent.py`): Orchestrates event extraction
- **LLM Prompts**: System and user prompts for extraction
- **JSON Parser**: Handles LLM output parsing with fallbacks
- **Category Inference**: Assigns categories based on keywords
- **Chunking**: Splits large texts to avoid token limits

---

## URL Rules System

The rules system provides a registry of URL-specific handlers. Each URL has:

1. **Scraper class**: Fetches content from a URL
2. **Regex class**: Parses content to extract events

### Registry Structure

```
rules/
├── base.py              # BaseScraper, BaseRule, Event dataclass
├── registry.py          # URL -> RuleEntry mapping
├── urls.py              # CITY_URLS constants
├── cities/              # City-specific scrapers + regex
│   └── {city_name}/
│       └── {subfolder}/
│           ├── scraper.py
│           └── regex.py
```

### Auto-Discovery

The registry automatically discovers all `scraper.py` and `regex.py` files from:
- `rules/cities/{city}/{subfolder}/scraper.py`
- `rules/cities/{city}/{subfolder}/regex.py`

**Important**: Each URL must have its own subfolder. City-level scrapers (directly in `rules/cities/{city}/`) are NOT allowed.

### Accessing Rules

```python
from rules import fetch_events_from_url, list_registered_urls

# Get events from a specific URL
events = fetch_events_from_url("https://www.monheim.de/...")

# List all registered URLs
urls = list_registered_urls()
print(urls)
```

---

## Adding a New Event Source

This section explains how to add new city scrapers. For detailed step-by-step instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

### Step 1: Define the URL

Add the URL to `rules/urls.py`:

```python
CITY_URLS = {
    "newcity": {
        "subfolder_name": "https://newcity-events.com",
    },
}
```

### Step 2: Create Directory Structure

```bash
mkdir -p rules/cities/newcity/subfolder_name
touch rules/cities/newcity/__init__.py
touch rules/cities/newcity/subfolder_name/__init__.py
touch rules/cities/newcity/subfolder_name/scraper.py
touch rules/cities/newcity/subfolder_name/regex.py
```

### Step 3: Implement Scraper Class

Create `rules/cities/newcity/subfolder_name/scraper.py`:

```python
from rules.base import BaseScraper

class SubfolderNameScraper(BaseScraper):
    """Scraper for newcity.com event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle newcity.com URLs."""
        return "newcity-events.com" in url

    def fetch(self) -> str:
        """Fetch content from URL.
        
        IMPORTANT: Must implement navigation to access all events within 14 days.
        If page only shows limited events by default, you MUST:
        - Click "Load More" buttons until 14 days of events are loaded
        - Navigate through pagination to get all 14 days
        - Set date filters to include 14 days from today
        - Click "Next Month" or similar navigation to access future dates
        
        Returns:
            Cleaned text content from the page with all 14-day events loaded.
        """
        return self._fetch_with_requests()
        # OR return self._fetch_with_playwright() for dynamic content
```

### Step 4: Implement Regex Class

Create `rules/cities/newcity/subfolder_name/regex.py`:

```python
import re
from typing import List, Optional
from rules.base import BaseRule, Event

class SubfolderNameRegex(BaseRule):
    """Regex parser for newcity.com events.
    
    IMPORTANT: Regex is the PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - Regex patterns fail to extract any events
    - Regex extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: DD.MM.YYYY)
    - time (required): Event time (empty string if all-day event)
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category: Created by analyzer (not set by regex)
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "newcity-events.com" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns to extract events.
        
        Patterns are tried in order until one successfully extracts events.
        Each pattern should capture groups in this order:
        1. date (required)
        2. name (required)
        3. time (required, can be empty if all-day)
        4. location (required)
        5. description (required)
        
        If no pattern extracts events, LLM fallback will be used automatically.
        """
        patterns = [
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)(?:\s+(\d{2}:\d{2}))?(?:\s+@?\s*(.+?))?(?:\s+-\s*(.+?))?(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from regex match tuple.
        
        Args:
            match: Tuple containing matched groups from regex in order:
                   (date, name, time?, location?, description?)
        
        Returns:
            Event object or None if required fields missing.
        """
        date = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""
        time = match[2].strip() if len(match) > 2 else ""  # Empty if all-day
        location = match[3].strip() if len(match) > 3 else ""
        description = match[4].strip() if len(match) > 4 else ""
        
        # Validate required fields (time can be empty for all-day events)
        if not name or not date or not location or not description:
            return None
        
        return Event(
            name=name,
            description=description,
            location=location,
            date=date,
            time=time,  # Empty string if all-day event
            source=self.url,
            category="",  # Will be set by analyzer
        )
```

### Step 5: Test

```bash
# Run scraper for new city
python main.py --cities newcity

# Test in verbose mode to see extracted events
python main.py --cities newcity --verbose
```

The registry will automatically discover your new scraper!

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

### Analyzer LLM Prompts

#### System Prompt

```python
"""You are a data analyst. You receive a text that describes local events (from web search/summaries).
Your task is to extract every event and output a single JSON array of objects. Each object must have exactly these fields:
- "name": string (event title)
- "description": string (short summary or category)
- "location": string (venue or place)
- "date": string (e.g. "2025-02-01" or "Samstag 1. Februar")
- "time": string (e.g. "14:00" or "all day") or empty string if unknown
- "source": string (URL or website name where the event was found; required)
- "category": string - Categorize as one of: "family", "adult", "sport", "other" (based on event type, target audience, and content)

Output only JSON array, no markdown code fence, no extra text. If there are no events, output []."""
```

#### User Prompt

```python
"""Extract all events from this text into a JSON array (include source for each event):

{raw_event_text}
"""
```

### Event Categories

| Category | Description | Keywords |
|----------|-------------|----------|
| `family` | Family and children events | familie, kinder, jugend, kind, baby, schule, eltern |
| `adult` | Adult-oriented events | erwachsen, adult, senior, abend, nacht, bar, club, party |
| `sport` | Sports and fitness events | sport, fitness, laufen, schwimmen, rad, fußball, tennis, yoga |
| `other` | Uncategorized events | Default category |

**Note**: Category is created by the analyzer agent, NOT by the scraper/regex.

---

## Performance Optimization

### Chunking Strategy

Large texts are split into chunks to avoid token limits:

```python
def _split_into_chunks(self, raw_event_text: str, events_per_chunk: int = 3, max_chars: int = 5000) -> list[str]:
    """Split raw event text into chunks of events."""
    events_pattern = r'\*\s+\*\*Event:\*\*'
    event_blocks = re.split(events_pattern, raw_event_text)
    
    # Group events into chunks
    chunks = []
    for i in range(1, len(event_blocks), events_per_chunk):
        batch = event_blocks[i:i+events_per_chunk]
        chunk = '\n*   **Event:**'.join([''] + batch)
        
        # Also enforce character limit
        if len(chunk) > max_chars:
            chunks.append(chunk[:max_chars])
        else:
            chunks.append(chunk.strip())
    
    return chunks
```

### Scraper Performance

| Metric | Typical Value |
|--------|--------------|
| Per URL (regex) | ~1-2 seconds |
| Per URL (LLM) | ~5-10 seconds |
| Per city (3 URLs) | ~10-30 seconds |
| Full pipeline | ~1-2 minutes |

### Analyzer Performance

| Metric | Typical Value |
|--------|--------------|
| Per event | ~0.1-0.5 seconds |
| Per 10 events | ~1-5 seconds |
| Per 50 events | ~5-15 seconds |

### Performance Tips

1. **Use regex when possible** - 100x faster than LLM extraction
2. **Adaptive chunking** - Split by both event count AND character limit
3. **Pre-structured detection** - Bypass LLM when events are already in JSON format
4. **Cache frequently-accessed URLs** - Add caching to `_fetch_with_requests()`

---

## Debugging

### Debugging Scrapers

#### Enable Verbose Output

```bash
python main.py --cities monheim -v
```

#### Check Raw Summary

```bash
# List all summaries
python main.py --list-summaries

# View specific summary
python main.py --load-summary 1
```

#### Test Individual URL

```python
from rules import fetch_events_from_url

# Test a single URL
events = fetch_events_from_url("https://example.com/events")
print(f"Found {len(events)} events")

# Check LLM fallback (disable regex)
events = fetch_events_from_url("https://example.com/events", use_llm_fallback=True)
```

#### Inspect Scraper Selection

```python
from rules import get_rule

rule = get_rule("https://example.com/events")
print(f"Scraper: {rule.scraper_class.__name__}")
print(f"Regex: {rule.regex_class.__name__}")
```

#### Scraper Common Issues

| Issue | Solution |
|-------|----------|
| No events extracted | Check regex patterns match actual HTML |
| Browser needed but not used | Set `needs_browser = True` in scraper |
| LLM fallback slow | Improve regex patterns for better extraction |
| URL 404 error | Verify URL is correct in `rules/urls.py` |
| Cookie consent blocking | Use Playwright to accept cookies |
| Not loading 14 days of events | Implement navigation (see SETUP_GUIDE.md) |

### Debugging Analyzer

#### Inspect LLM Output

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import LLM_PROVIDER, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL

if LLM_PROVIDER == "deepseek":
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=DEEPSEEK_MODEL, api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Test extraction
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"raw_event_text": "Sample text with events"})
print(result)
```

#### Check Database

```bash
# View recent runs
python main.py --list-runs

# Query events
sqlite3 data/events.db "SELECT * FROM events ORDER BY id DESC LIMIT 10"

# Check validation stats
sqlite3 data/events.db "
SELECT
    r.id,
    r.agent,
    s.events_found,
    s.valid_events
FROM runs r
JOIN status s ON s.run_id = r.id
ORDER BY r.id DESC
LIMIT 5"
```

#### Analyzer Common Issues

| Issue | Solution |
|-------|----------|
| No events extracted | Check LLM is working, verify prompt format |
| Invalid JSON output | Use `--verbose` to see raw LLM output |
| Missing required fields | Improve prompt to emphasize required fields |
| Wrong categories | Add keywords to `_infer_category()` |
| Token limit exceeded | Reduce `chunk_size` or use larger LLM |

---

## Base Classes Reference

### BaseScraper Interface

All scrapers inherit from `BaseScraper` (`rules/base.py:39`):

```python
class BaseScraper(ABC):
    def __init__(self, url: str):
        self.url = url

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return False

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this scraper can handle the URL."""
        pass

    @abstractmethod
    def fetch(self) -> str:
        """Fetch and return cleaned text content."""
        pass
```

### Built-in Fetch Methods

**Requests + BeautifulSoup** (default, fast):

```python
def fetch(self) -> str:
    return self._fetch_with_requests()
```

**Playwright** (for dynamic content):

```python
@property
def needs_browser(self) -> bool:
    return True

def fetch(self) -> str:
    return self._fetch_with_playwright()
```

### Event Data Class

```python
@dataclass
class Event:
    name: str           # Required: Event name
    description: str    # Required: Event description
    location: str       # Required: Event location/venue
    date: str           # Required: Event date (DD.MM.YYYY)
    time: str           # Required: Event time (empty if all-day)
    source: str         # Required: Source URL
    category: str       # Created by analyzer (not set by scraper)
    city: str = ""      # Optional: City name
```

---

## Complete Example

For a complete working example of a scraper and regex parser, see the [SETUP_GUIDE.md](SETUP_GUIDE.md) file in the root directory. It provides step-by-step instructions with:

- Full file structure
- Complete scraper implementation with navigation for 14 days
- Complete regex implementation with all field extraction
- Testing instructions

---

## Resources

- **Base Classes**: `rules/base.py`
- **Registry**: `rules/registry.py`
- **URLs**: `rules/urls.py`
- **Scraper Agent**: `agents/scraper_agent.py`
- **Analyzer Agent**: `agents/analyzer_agent.py`
- **Storage**: `storage.py`
- **Config**: `config.py`
- **City Scraper Setup**: `SETUP_GUIDE.md`
- **Architecture**: `ARCHITECTURE.md`
