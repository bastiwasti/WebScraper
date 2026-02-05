# Scraper Guide

This guide explains how the scraper agent works and how to add new event sources.

## Table of Contents

- [How the Scraper Works](#how-the-scraper-works)
- [URL Rules System](#url-rules-system)
- [Adding a New Event Source](#adding-a-new-event-source)
- [Scraper Implementation](#scraper-implementation)
- [Regex Patterns](#regex-patterns)
- [Debugging Scrapers](#debugging-scrapers)

---

## How the Scraper Works

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

- **Scraper Agent** (`agents/scraper_agent.py:78`): Orchestrates the scraping process
- **URL Rules** (`rules/registry.py`): Maps URLs to specific scrapers/parsers
- **Base Classes** (`rules/base.py`): `BaseScraper` for fetching, `BaseRule` for parsing
- **Scraper Classes** (`rules/aggregators/*/scraper.py`): Per-site fetching logic
- **Regex Classes** (`rules/aggregators/*/regex.py`): Per-site parsing logic

---

## URL Rules System

The rules system provides a registry of URL-specific handlers. Each URL has:

1. **Scraper class**: Fetches content from the URL
2. **Regex class**: Parses content to extract events

### Registry Structure

```
rules/
├── base.py              # BaseScraper, BaseRule, Event dataclass
├── registry.py          # URL -> RuleEntry mapping
├── urls.py              # CITY_URLS, AGGREGATOR_URLS constants
├── aggregators/         # Aggregator scrapers + regex
│   ├── eventbrite/
│   │   ├── scraper.py
│   │   └── regex.py
│   ├── meetup/
│   │   ├── scraper.py
│   │   └── regex.py
│   └── rausgegangen/
│       ├── scraper.py
│       └── regex.py
└── cities/              # City-specific scrapers + regex
    └── {city_name}/
        ├── scraper.py
        └── regex.py
```

### Auto-Discovery

The registry automatically discovers all `scraper.py` and `regex.py` files from:
- `rules/cities/*/scraper.py` and `rules/cities/*/regex.py`
- `rules/aggregators/*/scraper.py` and `rules/aggregators/*/regex.py`

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

### Step 1: Define the URL

Add the URL to `rules/urls.py`:

```python
# For a new city
CITY_URLS = {
    "duesseldorf": {
        "stadt": "https://www.duesseldorf.de/termine/"
    }
}

# For a new aggregator
AGGREGATOR_URLS = {
    "eventim": "https://www.eventim.de/de/veranstaltungen"
}
```

### Step 2: Create Scraper Class

Create `rules/cities/duesseldorf/stadt/scraper.py`:

```python
from rules.base import BaseScraper

class DuesseldorfStadtScraper(BaseScraper):
    """Scraper for duesseldorf.de event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle duesseldorf.de URLs."""
        return "duesseldorf.de" in url

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return False  # or True if dynamic content

    def fetch(self) -> str:
        """Fetch content from the URL."""
        return self._fetch_with_requests()
        # Or: return self._fetch_with_playwright()
```

### Step 3: Create Regex Class

Create `rules/cities/duesseldorf/stadt/regex.py`:

```python
import re
from typing import List
from rules.base import BaseRule, Event

class DuesseldorfStadtRule(BaseRule):
    """Regex parser for duesseldorf.de events."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle duesseldorf.de URLs."""
        return "duesseldorf.de" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns to extract events."""
        return [
            re.compile(
                r'(?P<name>[^|]+)\|'
                r'(?P<date>\d{2}\.\d{2}\.\d{4})\s*'
                r'(?P<time>\d{2}:\d{2})?\s*\|'
                r'(?P<location>[^|]+)\|'
                r'(?P<description>[^|]+)'
            )
        ]

    def _create_event_from_match(self, match: tuple) -> Event:
        """Create Event object from regex match."""
        name, date, time, location, description = match

        return Event(
            name=name.strip(),
            date=date.strip(),
            time=time.strip() if time else "",
            location=location.strip(),
            description=description.strip(),
            source=self.url,
            category=self._infer_category(description, name)
        )
```

### Step 4: Test the Rule

```python
from rules import fetch_events_from_url

# Test the new rule
events = fetch_events_from_url("https://www.duesseldorf.de/termine/")
for event in events:
    print(f"{event.date}: {event.name} at {event.location}")
```

### Step 5: Run Full Pipeline

```bash
python main.py --cities duesseldorf
```

---

## Scraper Implementation

### BaseScraper Interface

All scrapers inherit from `BaseScraper` (`rules/base.py:38`):

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

### When to Use Playwright

Use Playwright when:
- Content is loaded via JavaScript
- Events require clicking buttons to load
- Calendar interfaces need navigation
- "Load more" buttons exist

Don't use Playwright when:
- Static HTML contains all needed information
- Page is simple and loads all content immediately
- Resource usage is a concern (browser is heavier)

---

## Regex Patterns

### Pattern Requirements

Regex patterns should extract these named groups:

| Group | Required | Description | Example |
|-------|----------|-------------|---------|
| `name` | Yes | Event title | "Jazz Concert" |
| `date` | Yes | Event date | "2025-02-01" or "01.02.2025" |
| `time` | No | Event time | "19:00" or "all day" |
| `location` | Yes | Event venue | "City Hall" |
| `description` | Yes | Event details | "Open to public" |

### Example Patterns

**Simple pipe-separated:**

```python
re.compile(
    r'(?P<name>[^|]+)\|'
    r'(?P<date>\d{2}\.\d{2}\.\d{4})\s*'
    r'(?P<time>\d{2}:\d{2})?\s*\|'
    r'(?P<location>[^|]+)\|'
    r'(?P<description>[^|]+)'
)
```

**HTML-based:**

```python
re.compile(
    r'<h3[^>]*>(?P<name>[^<]+)</h3>.*?'
    r'<time[^>]*>(?P<date>[^<]+)</time>.*?'
    r'<span class="location"[^>]*>(?P<location>[^<]+)</span>.*?'
    r'<p class="desc"[^>]*>(?P<description>[^<]+)</p>',
    re.DOTALL
)
```

### Multiple Patterns

Return multiple patterns to try in order:

```python
def get_regex_patterns(self) -> List[re.Pattern]:
    return [
        # Try detailed pattern first
        re.compile(detailed_pattern, re.DOTALL),
        # Fallback to simple pattern
        re.compile(simple_pattern),
    ]
```

---

## Debugging Scrapers

### Enable Verbose Logging

```bash
python main.py --cities monheim -v
```

### Check Raw Summary

```bash
# List all summaries
python main.py --list-summaries

# View specific summary
python main.py --load-summary 1
```

### Test Individual URL

```python
from rules import fetch_events_from_url

# Test a single URL
events = fetch_events_from_url("https://example.com/events")
print(f"Found {len(events)} events")

# Check LLM fallback (disable regex)
events = fetch_events_from_url("https://example.com/events", use_llm_fallback=True)
```

### Inspect Scraper Selection

```python
from rules import get_rule

rule = get_rule("https://example.com/events")
print(f"Scraper: {rule.scraper_class.__name__}")
print(f"Regex: {rule.regex_class.__name__}")
```

### Common Issues

| Issue | Solution |
|-------|----------|
| No events extracted | Check regex patterns match the actual HTML |
| Browser needed but not used | Set `needs_browser = True` in scraper |
| LLM fallback slow | Improve regex patterns for better extraction |
| URL 404 error | Verify the URL is correct in `rules/urls.py` |
| Cookie consent blocking | Use Playwright to accept cookies |

### Debug Tools

```bash
# View logs
cat logs/scrape_*.log

# Check database
sqlite3 data/events.db "SELECT * FROM raw_summaries ORDER BY id DESC LIMIT 1"

# Test scraper directly
python -c "
from rules import fetch_events_from_url
events = fetch_events_from_url('https://rausgegangen.de/')
print([e.name for e in events[:5]])
"
```

---

## Performance Tips

1. **Use regex when possible** - 100x faster than LLM extraction
2. **Cache frequently-accessed URLs** - Add caching to `_fetch_with_requests()`
3. **Limit URL count** - Use `--fetch-urls` to control scraping scope
4. **Parallel requests** - Consider async fetching for multiple URLs
5. **Filter irrelevant content** - Skip navigation/headers in scrapers

---

## Resources

- **Base Classes**: `rules/base.py`
- **Registry**: `rules/registry.py`
- **Scraper Agent**: `agents/scraper_agent.py`
- **Example Aggregator**: `rules/aggregators/meetup/scraper.py`
- **Example Regex**: `rules/aggregators/meetup/regex.py`
