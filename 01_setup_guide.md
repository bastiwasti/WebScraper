# City Scraper Rules - Setup Guide

## Overview

This document explains the structure and setup of city-specific event scrapers in the WebScraper project. Each city can have multiple URLs, and each URL requires custom scraping logic to extract event information.

**Goal**: Extract all events from city event pages for dates up to 14 days in the future.

### Data Fields Extracted by Regex
Each scraper must extract events with these fields:
- **name** (required): Event name/title
- **date** (required): Event date (format: DD.MM.YYYY)
- **time** (required): Event time (e.g., "19:00", "19:00 Uhr") - empty string if all-day event
- **location** (required): Event location/venue
- **description** (required): Event description
- **source** (required): Source URL (usually `self.url`)
- **category**: Created by analyzer (not by regex/scraper)

### Extraction Strategy
- **Primary**: Regex extraction - use regex patterns to parse events from fetched content
- **Fallback**: LLM extraction - automatic fallback via DeepSeek if regex fails or returns no events

### Date Filtering Requirement
**Critical**: The scraper must implement navigation/filtering to access events for the full 14-day period.

**Examples of required actions**:
- If page shows only today's events by default → scraper must navigate to load 14 days
- If page has "Load More" button → scraper must click it until all 14 days are loaded
- If page has calendar filter → scraper must select date range for 14 days
- If page has pagination → scraper must navigate through pages to get all 14 days of events
- If page has "Next Month" button → scraper must click it to access future dates

---

## Directory Structure

```
rules/
└── cities/
    ├── __init__.py                      # Empty (module marker)
    ├── monheim/
    │   ├── __init__.py
    │   ├── terminkalender/              # Subfolder 1
    │   │   ├── __init__.py
    │   │   ├── scraper.py
    │   │   └── regex.py
    │   └── kulturwerke/                 # Subfolder 2
    │       ├── __init__.py
    │       ├── scraper.py
    │       └── regex.py
    ├── leverkusen/
    │   ├── __init__.py
    │   ├── lust_auf/                    # Subfolder
    │   │   ├── __init__.py
    │   │   ├── scraper.py
    │   │   └── regex.py
    │   └── stadt_erleben/               # Another subfolder
    │       ├── __init__.py
    │       ├── scraper.py
    │       └── regex.py
    └── [other cities]/
```

**Important**: City-level `scraper.py` and `regex.py` files (directly in the city folder, not in subfolders) are **NOT allowed** and will be removed. All scrapers must be in subfolders, one per URL.
    │       ├── scraper.py               # REQUIRED: URL-specific scraper
    │       └── regex.py                 # REQUIRED: URL-specific regex parser
    ├── monheim/
    │   ├── __init__.py
    │   ├── terminkalender/              # Subfolder 1
    │   │   ├── __init__.py
    │   │   ├── scraper.py
    │   │   └── regex.py
    │   └── kulturwerke/                 # Subfolder 2
    │       ├── __init__.py
    │       ├── scraper.py
    │       └── regex.py
    ├── leverkusen/
    │   ├── __init__.py
    │   ├── lust_auf/                    # Subfolder
    │   │   ├── __init__.py
    │   │   ├── scraper.py
    │   │   └── regex.py
    │   └── stadt_erleben/               # Another subfolder
    │       ├── __init__.py
    │       ├── scraper.py
    │       └── regex.py
    └── [other cities]/
```

---

## Core Architecture

### 1. URL Configuration (`rules/urls.py`)

All URLs are defined in the `CITY_URLS` dictionary:

```python
CITY_URLS: Dict[str, Dict[str, str]] = {
    "city_name": {                       # City key (lowercase)
        "subfolder_key": "https://url",  # Maps to subfolder in rules/cities/
        "another_key": "https://url2",
    },
}
```

**Key Rules**:
- City keys must be lowercase
- Subfolder keys must match the folder name in `rules/cities/city_name/subfolder_key/`
- Each URL maps to exactly one subfolder containing `scraper.py` and `regex.py`

**Example**:
```python
"monheim": {
    "terminkalender": "https://www.monheim.de/freizeit-tourismus/terminkalender",
    "kulturwerke": "https://www.monheimer-kulturwerke.de/de/kalender/",
},
```

This creates the mapping:
- `https://www.monheim.de/freizeit-tourismus/terminkalender` → `rules/cities/monheim/terminkalender/`
- `https://www.monheimer-kulturwerke.de/de/kalender/` → `rules/cities/monheim/kulturwerke/`

---

### 2. Base Classes (`rules/base.py`)

All scrapers and regex parsers inherit from these base classes:

#### BaseScraper
- **Purpose**: Fetches content from a URL
- **Methods to implement**:
  - `can_handle(cls, url: str) -> bool`: Return True if this scraper can handle the URL
  - `fetch() -> str`: Fetch and return cleaned content from the URL

#### BaseRule (Regex Parser)
- **Purpose**: Parses fetched content to extract events using regex patterns
- **Primary extraction method**: Regex patterns parse the fetched content to extract all event fields
- **LLM fallback**: Automatically triggered if regex extraction fails or returns no events
- **Methods to implement**:
  - `can_handle(cls, url: str) -> bool`: Return True if this parser can handle the URL
  - `get_regex_patterns() -> List[re.Pattern]`: Return regex patterns to extract events
  - `_create_event_from_match(self, match: tuple) -> Optional[Event]`: Convert regex match to Event object
- **Note**: Category is NOT set by regex/scraper - it's created by the analyzer agent

#### Event Data Class
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
    event_url: str = "" # Optional: Event detail page URL
    raw_data: dict | None = None  # Optional: Raw data from Level 2 scraping
    origin: str = ""    # NEW: Data origin identifier (e.g., "leverkusen_lust_auf")
```

---

## Required Files per URL

For each URL, create a subfolder with exactly these files:

### 1. `__init__.py`
```python
# Can be empty or exports
from .scraper import YourScraperClass
from .regex import YourRegexClass

__all__ = ['YourScraperClass', 'YourRegexClass']
```

### 2. `scraper.py`
```python
"""Description of what this scraper does."""

from rules.base import BaseScraper

class YourScraperClassName(BaseScraper):
    """Scraper for [Website/URL]."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this scraper can handle the URL."""
        return "domain.com" in url  # or any URL matching logic

    def fetch(self) -> str:
        """Fetch content from URL.
        
        IMPORTANT: Must implement navigation to access all events within 14 days.
        If the page only shows limited events by default, you MUST:
        - Click "Load More" buttons until 14 days of events are loaded
        - Navigate through pagination to get all 14 days
        - Set date filters to include 14 days from today
        - Click "Next Month" or similar navigation to access future dates
        
        Returns:
            Cleaned text content from the page with all 14-day events loaded.
        """
        return self._fetch_with_requests()
        # OR return self._fetch_with_playwright() for dynamic content with navigation
```

**Key Methods Available**:
- `self._fetch_with_requests()`: Uses `requests` + `BeautifulSoup` for static pages
- `self._fetch_with_playwright()`: Uses Playwright headless browser for dynamic pages
- `self.needs_browser` (property): Override to return `True` if page needs JavaScript

**Custom Fetch with Navigation Examples**:

#### Example 1: Clicking "Load More" Button
```python
from playwright.sync_api import sync_playwright

def fetch(self) -> str:
    """Fetch with Load More button clicks."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        # Keep clicking "Load More" until no more events or 14 days loaded
        max_clicks = 10
        for _ in range(max_clicks):
            load_more = page.locator("button.load-more, a.load-more")
            if load_more.count() == 0:
                break
            load_more.click()
            page.wait_for_timeout(1000)
        
        content = page.content()
        browser.close()
        
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return _clean_text(text)
```

#### Example 2: Date Range Filter
```python
from datetime import datetime, timedelta

def fetch(self) -> str:
    """Fetch with date range filter set."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        # Calculate 14-day date range
        today = datetime.now()
        end_date = today + timedelta(days=14)
        
        # Select start date
        page.click("input[name='startDate']")
        page.select_option(f"option[value*='{today.strftime('%Y-%m-%d')}']")
        
        # Select end date
        page.click("input[name='endDate']")
        page.select_option(f"option[value*='{end_date.strftime('%Y-%m-%d')}']")
        
        # Click search/apply button
        page.click("button[type='submit']")
        page.wait_for_timeout(2000)
        
        content = page.content()
        browser.close()
        
        # Parse and return...
```

#### Example 3: Pagination Navigation
```python
def fetch(self) -> str:
    """Fetch with pagination navigation."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        all_content = []
        max_pages = 10
        
        for page_num in range(max_pages):
            content = page.content()
            all_content.append(content)
            
            # Check if next page exists
            next_button = page.locator("a.next-page, button[aria-label='Next']")
            if next_button.count() == 0:
                break
            
            next_button.click()
            page.wait_for_timeout(1000)
        
        browser.close()
        
        # Combine all pages
        combined = "\n".join(all_content)
        soup = BeautifulSoup(combined, "html.parser")
        # ... parsing ...
```

#### Example 4: Calendar Month Navigation
```python
from datetime import datetime, timedelta

def fetch(self) -> str:
    """Fetch with calendar navigation to cover 14 days."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        # Get current month displayed
        current_month = page.locator(".calendar-month").first.inner_text()
        target_month = (datetime.now() + timedelta(days=14)).strftime("%B %Y")
        
        # Navigate until target month is reached
        max_clicks = 3
        for _ in range(max_clicks):
            if target_month in current_month:
                break
            page.click("button.next-month, .calendar-next")
            page.wait_for_timeout(1000)
            current_month = page.locator(".calendar-month").first.inner_text()
        
        content = page.content()
        browser.close()
        
        # Parse and return...
```

### 3. `regex.py`
```python
"""Description of regex patterns.
 
IMPORTANT: Regex is the PRIMARY extraction method.
LLM (DeepSeek) will ONLY be used as fallback if:
- Regex patterns fail to extract any events
- Regex extraction returns empty results
"""

import re
from typing import List, Optional
from rules.base import BaseRule, Event

class YourRegexClassName(BaseRule):
    """Regex parser for [Website/URL].
    
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
        """Return True if this parser can handle the URL."""
        return "domain.com" in url

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
        
        # Validate required fields
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

---

## 2-Level Scraping Implementation

### Overview

Some event sources provide richer data on individual event detail pages. The 2-level scraping pattern enhances event data by:
1. **Level 1**: Main calendar page → Basic event info (name, date, time, location, description)
2. **Level 2**: Event detail pages → Enhanced data (detail_location, detail_description, detail_end_time)
3. **Data Priority**: Level 2 data used when available, Level 1 as fallback

### When to Use 2-Level Scraping

Use 2-level scraping when:
- Calendar page links to individual event detail pages
- Detail pages contain richer data than calendar listings
- Events need accurate venue information, full descriptions, or end times

**Examples**:
- ✅ Monheim terminkalender: Links to `/termin/event-id` pages
- ✅ Potential: Calendar sites with "Read More" → event detail pages
- ❌ Monheim kulturwerke: No individual detail pages (LLM extraction only)

### Implementation

#### 1. Update Base Classes

`rules/base.py` provides optional Level 2 support:

```python
@dataclass
class Event:
    # ... existing fields ...
    event_url: str = ""     # URL to event detail page (Level 2)
    raw_data: dict | None = None  # Level 2 extracted data


class BaseRule:
    # ... existing methods ...
    
    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Optional: Fetch detail pages and extract Level 2 data.
        
        Default: Returns events unchanged.
        Subclasses can override to implement Level 2 scraping.
        """
        return events
```

#### 2. Implement `fetch_level2_data()` in Regex Class

Override in your `regex.py` file:

```python
def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
    """Fetch Level 2 detail data for events.
    
    Args:
        events: List of Event objects from Level 1 parsing
        raw_html: Raw HTML from main page (for URL extraction)
    
    Returns:
        List of Event objects with raw_data populated.
    """
    from bs4 import BeautifulSoup
    import requests
    
    # Extract event detail URLs from main page HTML
    soup = BeautifulSoup(raw_html, 'html.parser')
    event_url_map = {}
    
    # Parse detail URLs (depends on page structure)
    # Example for Monheim terminkalender:
    for link in soup.find_all('a', class_='url date'):
        href = link.get('href')
        title = link.get('title')
        if href and title:
            event_url_map[title] = href
    
    # Fetch detail pages
    for event in events:
        detail_url = event_url_map.get(event.name, "")
        if not detail_url:
            continue  # No detail URL, skip Level 2
        
        try:
            resp = requests.get(detail_url, timeout=15, headers={"User-Agent": "WeeklyMail/1.0"})
            resp.raise_for_status()
            detail_html = resp.text
            
            # Parse detail page
            detail_data = self._parse_detail_page(detail_html)
            
            if detail_data:
                event.raw_data = detail_data
                event.event_url = detail_url
                # Use detail URL as source when Level 2 succeeds
                event.source = detail_url
        except Exception as e:
            print(f"Failed to fetch detail page: {e}")
    
    return events
```

#### 3. Parse Detail Page

```python
def _parse_detail_page(self, detail_html: str) -> dict:
    """Parse event detail page HTML.
    
    Returns:
        Dict with keys: detail_date, detail_time, detail_end_time, 
              detail_location, detail_description
    """
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(detail_html, 'html.parser')
    
    # Extract data based on page structure
    detail_data = {
        'detail_date': self._extract_date(soup),
        'detail_time': self._extract_time(soup),
        'detail_end_time': self._extract_end_time(soup),
        'detail_location': self._extract_location(soup),
        'detail_description': self._extract_description(soup),
    }
    
    return detail_data


# Helper methods for detail page parsing
def _extract_date(self, soup) -> str:
    """Extract event date from detail page."""
    # Implementation depends on page structure
    return ""

def _extract_time(self, soup) -> str:
    """Extract event time from detail page."""
    return ""

def _extract_end_time(self, soup) -> str:
    """Extract event end time from detail page."""
    return ""

def _extract_location(self, soup) -> str:
    """Extract event location from detail page."""
    return ""

def _extract_description(self, soup) -> str:
    """Extract event description from detail page."""
    # Get text from relevant element
    return ""
```

#### 4. Automatic Level 2 Scraping

`rules/__init__.py` automatically calls Level 2 scraping:

```python
def fetch_events_from_url(url: str, use_llm_fallback: bool = True) -> tuple[list[Event], str]:
    # ... existing code ...
    events, extraction_method = regex_parser.extract_events_with_method(content, use_llm_fallback)
    
    # NEW: Attempt Level 2 scraping if scraper supports it
    try:
        if hasattr(scraper, 'fetch_raw_html'):
            raw_html = scraper.fetch_raw_html()
            events = regex_parser.fetch_level2_data(events, raw_html)
    except Exception as e:
        print(f"Warning: Level 2 scraping failed for {url}: {e}")
    
    return events, extraction_method
```

### Data Flow

```
Calendar Page → Level 1 Parser → Events + URLs → Level 2 Fetcher → Enhanced Events
                              ↓
                         Level 2 Parser → raw_data dict populated
                              ↓
                         Storage → Uses Level 2 when available
```

### Performance Considerations

- **Time**: Each detail page fetch adds ~1-3 seconds
- **Impact**: For 77 events = ~2 minutes additional time
- **Acceptable**: Daily run (once/day) makes this acceptable
- **Failures**: Some detail pages may fail (404, 503) - handle gracefully

### Storage Integration

Level 2 data is saved to database:

```python
# storage.py automatically prioritizes Level 2 data
desc_to_use = detail_description if detail_description else (e.get("description") or "").strip()
loc_to_use = detail_location if detail_location else (e.get("location") or "").strip()
source_to_use = event_url if event_url else (e.get("source") or "").strip()
```

---

## Date Filtering (14 Days) - CRITICAL REQUIREMENT

**Date filtering MUST be implemented in the scraper at the webpage level.**

### What This Means

Instead of fetching all events and then filtering by date in the regex/parser, your scraper must navigate the webpage to ensure only events within the 14-day window are loaded and extracted.

### Why This Matters

Many event websites only show a limited number of events by default:
- Only today's events
- Only current month's events
- First page of paginated results
- First 10-20 events with a "Load More" button

### Implementation Requirements

Your scraper MUST implement one or more of these navigation strategies to ensure 14 days of events are loaded:

#### 1. "Load More" Button Pattern
If the page has a "Load More" or "Show More" button:
```python
def fetch(self) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        # Calculate cutoff date (14 days from today)
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() + timedelta(days=14)
        
        # Keep clicking "Load More" until we have 14 days of events
        max_clicks = 20
        for _ in range(max_clicks):
            # Check if last event date is beyond cutoff
            last_event_date = self._get_last_event_date(page)
            if last_event_date and last_event_date > cutoff_date:
                break
            
            # Click "Load More"
            load_more = page.locator("button:has-text('Load More'), a:has-text('Mehr laden')")
            if load_more.count() == 0:
                break
            load_more.click()
            page.wait_for_timeout(1000)
        
        content = page.content()
        browser.close()
        # ... parse and return ...
```

#### 2. Date Range Filter Pattern
If the page has date filter inputs:
```python
def fetch(self) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        from datetime import datetime, timedelta
        today = datetime.now()
        end_date = today + timedelta(days=14)
        
        # Set start date filter
        page.fill("input[name='startDate']", today.strftime("%d.%m.%Y"))
        
        # Set end date filter
        page.fill("input[name='endDate']", end_date.strftime("%d.%m.%Y"))
        
        # Click search/apply
        page.click("button[type='submit'], button:has-text('Suchen')")
        page.wait_for_timeout(2000)
        
        content = page.content()
        browser.close()
        # ... parse and return ...
```

#### 3. Pagination Pattern
If the page uses pagination:

**CRITICAL: Always verify pagination actually works before implementing!**
Many sites have pagination URLs that return identical content to page 1.

```python
def fetch(self) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        # CRITICAL: Verify pagination actually works
        print("[DEBUG] Verifying pagination...")
        page1_html = page.content()
        
        # Try to find and click next button
        next_button = page.locator("a[rel='next'], .pagination-next")
        if next_button.count() > 0:
            next_button.click()
            page.wait_for_timeout(1000)
            page2_html = page.content()
            
            # Compare event counts
            page1_count = page1_html.count('<article')
            page2_count = page2_html.count('<article')
            
            if page1_count == page2_count:
                print("WARNING: Page 1 and 2 have same event count - no real pagination")
                print("Setting MAX_PAGES=1 and using page 1 only")
                max_pages = 1
            else:
                print(f"Pagination confirmed: {page1_count} events on page 1, {page2_count} on page 2")
                max_pages = 10  # or your desired page limit
        else:
            print("No next button found - all events on page 1")
            max_pages = 1
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() + timedelta(days=14)
        
        all_content = []
        
        for page_num in range(max_pages):
            # Get current page content
            content = page.content()
            all_content.append(content)
            
            # Check if we've loaded events beyond cutoff
            if self._contains_events_beyond_cutoff(content, cutoff_date):
                break
            
            # Try to go to next page
            if next_button.count() == 0:
                break
            
            next_button.click()
            page.wait_for_timeout(1000)
        
        browser.close()
        
        # Combine all pages and parse
        combined = "\n".join(all_content)
        # ... parse and return ...
```

#### 4. Calendar Month Navigation Pattern
If the page uses a calendar view:
```python
def fetch(self) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(self.url, wait_until="networkidle")
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() + timedelta(days=14)
        
        # Navigate calendar to include 14 days
        max_months = 3
        for _ in range(max_months):
            current_month_text = page.locator(".calendar-month, .month-header").first.inner_text()
            
            # Check if we've reached target month
            if cutoff_date.strftime("%B") in current_month_text:
                break
            
            # Click next month
            page.click("button.next-month, .calendar-next, .month-next")
            page.wait_for_timeout(1000)
        
        content = page.content()
        browser.close()
        # ... parse and return ...
```

### Helper Methods

Add these helper methods to your scraper:

```python
from datetime import datetime

def _get_last_event_date(self, page) -> datetime | None:
    """Extract date of the last event on the page."""
    try:
        # This depends on your page structure
        last_event = page.locator(".event-item").last
        date_text = last_event.locator(".event-date").inner_text()
        return datetime.strptime(date_text, "%d.%m.%Y")
    except Exception:
        return None

def _contains_events_beyond_cutoff(self, content: str, cutoff: datetime) -> bool:
    """Check if content contains events beyond cutoff date."""
    # Simple check - you may need more sophisticated logic
    import re
    date_pattern = r'(\d{1,2}\.\d{1,2}\.\d{4})'
    dates = re.findall(date_pattern, content)
    for date_str in dates:
        try:
            event_date = datetime.strptime(date_str, "%d.%m.%Y")
            if event_date > cutoff:
                return True
        except Exception:
            continue
    return False
```

### Testing Your Implementation

After implementing your scraper, verify it loads 14 days of events:

```python
# Test script
from rules.registry import create_scraper

url = "https://your-city-events.com"
scraper = create_scraper(url)
content = scraper.fetch()

# Count events in content
import re
events = re.findall(r'(\d{1,2}\.\d{1,2}\.\d{4})', content)
print(f"Found {len(events)} events with dates")

# Check date range
from datetime import datetime, timedelta
dates = []
for date_str in events:
    try:
        dates.append(datetime.strptime(date_str, "%d.%m.%Y"))
    except Exception:
        pass

if dates:
    print(f"Date range: {min(dates).date()} to {max(dates).date()}")
    print(f"Should cover: {datetime.now().date()} to {(datetime.now() + timedelta(days=14)).date()}")
```

---

## Dynamic Content (JavaScript)

For pages that require JavaScript to load events:

### Option 1: Set `needs_browser` Property
```python
class TerminkalenderScraper(BaseScraper):
    @property
    def needs_browser(self) -> bool:
        """This page requires Playwright."""
        return True

    def fetch(self) -> str:
        """Will use _fetch_with_playwright() automatically."""
        return self._fetch_with_playwright()
```

### Option 2: Custom Playwright Logic
```python
def fetch(self) -> str:
    """Custom Playwright fetch with waiting."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto(self.url, wait_until="networkidle")
        
        # Wait for specific element to load
        page.wait_for_selector(".event-container", timeout=10000)
        
        # Click "Load More" if needed
        if page.locator("button.load-more").count() > 0:
            page.click("button.load-more")
            page.wait_for_timeout(2000)
        
        content = page.content()
        browser.close()
        
        soup = BeautifulSoup(content, "html.parser")
        # ... parse ...
        return cleaned_text
```

---

## Adding a New City/URL

### Step 1: Add URL to `rules/urls.py`
```python
CITY_URLS: Dict[str, Dict[str, str]] = {
    # ... existing cities ...
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

### Step 3: Implement `scraper.py`

**IMPORTANT**: Must implement navigation to load 14 days of events!

```python
"""Scraper for NewCity events."""

from datetime import datetime, timedelta
from rules.base import BaseScraper

class NewcityScraper(BaseScraper):
    """Scraper for NewCity event pages.
    
    This scraper navigates the page to load all events within 14 days.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "newcity-events.com" in url

    def fetch(self) -> str:
        """Fetch content with navigation to load 14 days of events."""
        
        # First, try simple fetch
        initial_content = self._fetch_with_requests()
        
        # Check if content has 14 days of events
        if self._has_14_days_of_events(initial_content):
            return initial_content
        
        # If not, use Playwright for navigation
        return self._fetch_with_navigation()

    def _has_14_days_of_events(self, content: str) -> bool:
        """Check if content contains events for 14 days."""
        import re
        from datetime import datetime
        
        dates = re.findall(r'(\d{1,2}\.\d{1,2}\.\d{4})', content)
        if len(dates) < 14:
            return False
        
        # Parse dates and check range
        parsed_dates = []
        for date_str in dates:
            try:
                parsed_dates.append(datetime.strptime(date_str, "%d.%m.%Y"))
            except Exception:
                continue
        
        if not parsed_dates:
            return False
        
        # Check if range covers 14 days from today
        today = datetime.now()
        cutoff = today + timedelta(days=14)
        
        return min(parsed_dates) <= today and max(parsed_dates) >= cutoff

    def _fetch_with_navigation(self) -> str:
        """Fetch using Playwright with navigation for 14 days."""
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        from rules.base import _clean_text
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")
            
            # Calculate cutoff
            cutoff_date = datetime.now() + timedelta(days=14)
            
            # Implement your specific navigation logic here
            # Examples: Click "Load More", navigate pagination, set date filter, etc.
            
            # Example: Click "Load More" until we have 14 days
            max_clicks = 20
            for _ in range(max_clicks):
                load_more = page.locator("button:has-text('Mehr'), button:has-text('Load More')")
                if load_more.count() == 0:
                    break
                
                # Check if we have enough events
                content = page.content()
                if self._has_14_days_of_events(content):
                    break
                
                load_more.click()
                page.wait_for_timeout(1000)
            
            content = page.content()
            browser.close()
            
            # Parse and clean
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text)
```

### Step 4: Implement `regex.py`

```python
"""Regex parser for NewCity events.
 
PRIMARY EXTRACTION: Regex patterns extract events.
FALLBACK: LLM (DeepSeek) if regex fails.
"""

import re
from typing import List, Optional
from rules.base import BaseRule, Event

class NewcityRegex(BaseRule):
    """Regex parser for NewCity events.
    
    Extracts fields:
    - date (required): DD.MM.YYYY format
    - name (required): Event name
    - time (required): Event time (empty if all-day)
    - location (required): Event venue
    - description (required): Event details
    - source (required): self.url
    - category: Created by analyzer (not set by regex)
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "newcity-events.com" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns to extract events.
        
        Try multiple patterns in order. If none extract events,
        LLM fallback will be used automatically.
        """
        patterns = [
            # Pattern 1: Full event line with all fields
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)\s+(\d{2}:\d{2})\s+Uhr\s+(.+?)\s+-\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
            # Pattern 2: All-day event (date, name, time="", location, description)
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)\s+@?\s*(.+?)\s+-\s*(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from regex match.
        
        Args:
            match: (date, name, time?, location?, description?)
        
        Returns:
            Event or None if required fields missing.
        """
        date = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""
        time = match[2].strip() if len(match) > 2 else ""  # Empty if all-day
        location = match[3].strip() if len(match) > 3 else ""
        description = match[4].strip() if len(match) > 4 else ""
        
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
python3 main.py --cities newcity

# Test in verbose mode to see extracted events
python3 main.py --cities newcity --verbose
```

The registry will automatically discover your new scraper!

---

## Registry System (`rules/registry.py`)

The registry automatically discovers all scrapers and regex parsers:

### How It Works
1. On import, `_discover_rules()` scans all subfolders in `rules/cities/`
2. For each URL in `CITY_URLS`, it tries to import:
   - `rules.cities.{city}.{subfolder}.scraper`
   - `rules.cities.{city}.{subfolder}.regex`
3. It looks for classes ending with "Scraper" and "Rule"/"Regex"
4. Creates `RuleEntry` mappings: URL → (scraper_class, regex_class)

**Important**: Only subfolder-level scrapers are discovered. City-level scrapers are ignored and will be removed.

### Registry Functions
```python
from rules.registry import get_rule, create_scraper, create_regex, list_registered_rules

# Get rule entry for URL
rule = get_rule("https://monheim.de/freizeit-tourismus/terminkalender")

# Create scraper instance
scraper = create_scraper(url)
content = scraper.fetch()

# Create regex parser instance
regex = create_regex(url)
events = regex.extract_events(content)

# List all registered rules
rules = list_registered_rules()
for url, entry in rules.items():
    print(f"{url} -> {entry.scraper_class.__name__}, {entry.regex_class.__name__}")
```

---

## Required Packages

Install from `requirements.txt`:
```bash
pip install -r requirements.txt

# After installing Playwright, install browser
playwright install chromium
```

### Core Packages
- **requests>=2.31.0**: HTTP requests for static pages
- **beautifulsoup4>=4.12.0**: HTML parsing
- **playwright>=1.40.0**: Headless browser for dynamic content and navigation
  - Required for: JavaScript rendering, "Load More" buttons, pagination
  - After install: `playwright install chromium`

### LLM & LangChain (for LLM fallback)
- **langchain>=0.3.0**: LLM integration framework
- **langchain-community>=0.3.0**: Community integrations
- **langchain-openai**: OpenAI-compatible API client (for DeepSeek)

### Utilities
- **python-dotenv>=1.0.0**: Environment variables
- **rich>=13.0.0**: Terminal formatting

---

## Common Patterns

### Pattern 1: Static HTML Page (simplest)
```python
class SimpleScraper(BaseScraper):
    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "static-site.com" in url

    def fetch(self) -> str:
        content = self._fetch_with_requests()
        
        # Verify we have 14 days of events
        if not self._has_14_days_of_events(content):
            raise ValueError("Static page doesn't contain 14 days of events")
        
        return content
```

### Pattern 2: Dynamic JavaScript Page with Navigation
```python
class DynamicScraper(BaseScraper):
    @property
    def needs_browser(self) -> bool:
        return True

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "dynamic-site.com" in url

    def fetch(self) -> str:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")
            
            # Navigate to load 14 days of events
            self._navigate_to_14_days(page)
            
            content = page.content()
            browser.close()
            
            # Parse and clean
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text)
    
    def _navigate_to_14_days(self, page):
        """Navigate page to load 14 days of events."""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() + timedelta(days=14)
        max_clicks = 20
        
        for _ in range(max_clicks):
            # Check last event date
            content = page.content()
            if self._has_14_days_of_events(content):
                break
            
            # Click "Load More"
            load_more = page.locator("button.load-more")
            if load_more.count() == 0:
                break
            
            load_more.click()
            page.wait_for_timeout(1000)
```

### Pattern 3: Multiple Regex Patterns
```python
def get_regex_patterns(self) -> List[re.Pattern]:
    return [
        # Pattern 1: Events with full date and time
        re.compile(r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)(?:\s+(\d{2}:\d{2}))?(?:\s+@?\s*(.+?))?(?=\n|$)', re.MULTILINE),
        # Pattern 2: Events with date only
        re.compile(r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)(?=\n|$)', re.MULTILINE),
    ]
```

### Pattern 4: Custom Fetch with Date Filter Parameters
```python
def _fetch_with_date_filter(self) -> str:
    """Fetch with date range filter parameters."""
    from datetime import datetime, timedelta
    
    params = {
        "startDate": datetime.now().strftime("%Y-%m-%d"),
        "endDate": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        "action": "search",
    }
    
    resp = requests.get(self.url, params=params, timeout=15)
    resp.raise_for_status()
    
    # Parse and clean...
    return cleaned_text
```

### Pattern 5: Handling All-Day Events
```python
def _create_event_from_match(self, match: tuple) -> Optional[Event]:
    """Create Event from regex match.
    
    Time is required but can be empty string for all-day events.
    """
    date = match[0].strip() if len(match) > 0 else ""
    name = match[1].strip() if len(match) > 1 else ""
    time = match[2].strip() if len(match) > 2 else ""  # Empty = all-day
    location = match[3].strip() if len(match) > 3 else ""
    description = match[4].strip() if len(match) > 4 else ""
    
    # All required fields (time can be empty for all-day)
    if not name or not date or not location or not description:
        return None
    
    return Event(
        name=name,
        description=description,
        location=location,
        date=date,
        time=time,  # Empty string for all-day events
        source=self.url,
        category="",  # Will be set by analyzer
    )
```

### Pattern 6: "Load More" Button with Date Check
```python
def _click_load_more_until_14_days(self, page) -> None:
    """Click Load More until we have 14 days of events."""
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() + timedelta(days=14)
    max_clicks = 20
    
    for _ in range(max_clicks):
        # Get last event date
        last_event = page.locator(".event-item").last
        date_text = last_event.locator(".date").inner_text()
        last_date = datetime.strptime(date_text, "%d.%m.%Y")
        
        # Stop if we have events beyond cutoff
        if last_date >= cutoff_date:
            break
        
        # Click Load More
        load_more = page.locator("button:has-text('Mehr anzeigen')")
        if load_more.count() == 0:
            break
        
        load_more.click()
        page.wait_for_timeout(1000)
```

### Pattern 7: JSON/REST API Scraping
Some event sites provide a REST API endpoint that returns structured JSON data instead of HTML. This is the most efficient method when available.

**When to Use:**
- Website has a publicly accessible REST API
- API returns structured event data (name, date, time, location, description)
- No HTML scraping needed

**Implementation:**
```python
"""Scraper for REST API events."""

import requests
import json
from datetime import datetime, timedelta
from rules.base import BaseScraper, Event

class EventsApiScraper(BaseScraper):
    """Scraper for events via REST API.
    
    Fetches events directly from API endpoint, no HTML parsing needed.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "api.example.com" in url

    def fetch(self) -> str:
        """Fetch content from REST API.
        
        Note: Returns empty string since API events are extracted directly.
        The regex parser will be skipped - see fetch_events_from_api().
        """
        return ""

    def fetch_events_from_api(self) -> list[Event]:
        """Fetch all events directly from REST API.
        
        Returns:
            List of Event objects (bypasses regex parsing entirely).
        """
        base_url = "https://api.example.com/events"
        all_events = []

        # Calculate date range for 14 days
        end_date = datetime.now()
        start_date = datetime.now() - timedelta(days=30)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        print(f"[Events API] Fetching events from {start_date_str} to {end_date_str}")

        # Paginate through API results
        page = 1
        max_pages = 10

        while page <= max_pages:
            params = {
                'page': page,
                'per_page': 50,
                'start_date': start_date_str,
                'end_date': end_date_str,
            }

            try:
                resp = requests.get(
                    base_url,
                    params=params,
                    timeout=30,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                events_data = resp.json()

                if not events_data:
                    break  # No more events

                # Convert API data to Event objects
                for api_event in events_data:
                    event = self._convert_api_to_event(api_event)
                    if event:
                        all_events.append(event)

                # Check if we have 14 days of events
                if self._has_14_days_of_events(all_events):
                    break

                page += 1

            except Exception as e:
                print(f"[Events API] Failed to fetch page {page}: {e}")
                break

        pages_fetched = page - 1
        print(f"[Events API] Fetched {len(all_events)} total events from {pages_fetched} pages")
        return all_events

    def _convert_api_to_event(self, api_event: dict) -> Event | None:
        """Convert API response dictionary to Event object.
        
        Args:
            api_event: Dictionary from REST API response
        
        Returns:
            Event object or None if conversion fails
        """
        try:
            title = api_event.get('title', '').strip()
            description_html = api_event.get('description', '')

            # Strip HTML from description
            from bs4 import BeautifulSoup
            description = BeautifulSoup(description_html, 'html.parser').get_text(strip=True)

            # Parse date and time
            start_date_str = api_event.get('start_date', '')
            date_only = ""
            time_only = ""

            if start_date_str:
                try:
                    dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                    date_only = dt.strftime("%Y-%m-%d")
                    time_only = dt.strftime("%H:%M")
                except ValueError:
                    pass

            # Get venue/location
            venue = api_event.get('venue', {})
            location = venue.get('name', '').strip() if venue else ""

            # Source URL
            source_url = api_event.get('url', self.url)

            # Build Event object
            event = Event(
                name=title,
                description=description,
                location=location,
                date=date_only,
                time=time_only,
                source=source_url,
                category="other",
                city="",
                event_url=source_url,
                raw_data=api_event,
            )

            return event

        except Exception as e:
            print(f"[Events API] Failed to convert event: {e}")
            return None

    def _has_14_days_of_events(self, events: list[Event]) -> bool:
        """Check if events list contains 14 days of events."""
        if len(events) < 14:
            return False

        # Parse dates and check range
        dates = []
        for event in events:
            try:
                if event.date:
                    dt = datetime.strptime(event.date, "%Y-%m-%d")
                    dates.append(dt)
            except Exception:
                continue

        if not dates:
            return False

        today = datetime.now()
        cutoff = today + timedelta(days=14)

        return min(dates) <= today and max(dates) >= cutoff
```

**Key Points:**
- Override `fetch_events_from_api()` in scraper class
- Return list of `Event` objects directly
- `fetch()` returns empty string (not used)
- `rules/__init__.py` checks for this method and calls it instead of regex parsing
- Handle pagination in API calls
- Convert API dictionaries to `Event` objects

**Example Reference:**
- `rules/cities/leverkusen/lust_auf/scraper.py` - Complete REST API implementation

### Pattern 8: HTML Parsing Instead of Regex

Some websites have structured HTML that's easier to parse with BeautifulSoup than regex patterns. This is useful when event data is in nested HTML elements.

**When to Use:**
- Event data is in structured HTML (tables, divs with classes)
- Regex patterns are complex or brittle
- Multiple event formats on same page
- Better to parse DOM tree directly

**Implementation in `regex.py`:**
```python
"""HTML parser for event pages."""

import re
from typing import List, Optional
from bs4 import BeautifulSoup
from rules.base import BaseRule, Event

class EventHtmlParser(BaseRule):
    """HTML parser for event pages.
    
    Parses HTML directly instead of using regex patterns.
    Better for structured event data in HTML.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "example.com" in url and "events" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return empty list - HTML parsing is used instead."""
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse events using HTML parsing (not regex).
        
        Override BaseRule method to parse HTML directly since website
        has structured event data in HTML that's better than regex on cleaned text.
        """
        print("[HTML Parser] Using HTML parsing instead of regex")

        # Fetch raw HTML for parsing
        try:
            from bs4 import BeautifulSoup
            import requests

            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"}
            )
            resp.raise_for_status()
            html_content = resp.text
        except Exception as e:
            print(f"[HTML Parser] Failed to fetch HTML: {e}, falling back to raw content")
            html_content = raw_content

        soup = BeautifulSoup(html_content, 'html.parser')
        events = []

        # Parse events based on HTML structure
        # Example: Events in div.event-item
        for event_div in soup.find_all('div', class_='event-item'):
            try:
                # Extract event fields from HTML elements
                title_elem = event_div.find('h3', class_='event-title')
                date_elem = event_div.find('span', class_='event-date')
                time_elem = event_div.find('span', class_='event-time')
                loc_elem = event_div.find('div', class_='event-location')
                desc_elem = event_div.find('p', class_='event-description')

                name = title_elem.get_text(strip=True) if title_elem else ""
                date = date_elem.get_text(strip=True) if date_elem else ""
                time = time_elem.get_text(strip=True) if time_elem else ""
                location = loc_elem.get_text(strip=True) if loc_elem else ""
                description = desc_elem.get_text(strip=True) if desc_elem else ""

                if name and date:
                    events.append(Event(
                        name=name,
                        description=description,
                        location=location,
                        date=date,
                        time=time,
                        source=self.url,
                        category="other",
                    ))

            except Exception as e:
                print(f"[HTML Parser] Failed to parse event: {e}")
                continue

        print(f"[HTML Parser] HTML parsing returned {len(events)} events")
        return events
```

**Key Points:**
- Override `parse_with_regex()` in regex class
- Parse HTML using BeautifulSoup directly
- Return list of `Event` objects
- `get_regex_patterns()` returns empty list
- More robust than regex for complex HTML structures
- Handles nested elements and attributes easily

**Example Reference:**
- `rules/cities/monheim/terminkalender/regex.py` - Complete HTML parsing implementation
- `rules/cities/hilden/veranstaltungen/regex.py` - JSON parsing variant

### Pattern 9: Disabling Level 2 Scraping

Level 2 scraping (fetching detail pages) can be slow for sites with many events. You can disable it to improve performance.

**When to Use:**
- Level 1 calendar page already has sufficient data
- Detail pages add minimal value
- Performance is critical (many events)
- Level 2 scraping causes timeouts

**Implementation in `scraper.py`:**
```python
"""Scraper for events (Level 2 disabled for performance)."""

from rules.base import BaseScraper

class EventsScraper(BaseScraper):
    """Scraper for event pages.
    
    Level 2 scraping is disabled to avoid timeout.
    Calendar page data is sufficient.
    """

    # Set class-level flag to disable Level 2
    DISABLE_LEVEL_2 = True

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "example.com" in url

    def fetch(self) -> str:
        """Fetch content from calendar page."""
        return self._fetch_with_requests()
```

**How It Works:**
- Set `DISABLE_LEVEL_2 = True` as class attribute
- `rules/__init__.py` checks this flag before attempting Level 2
- Skips detail page fetching entirely
- Saves time (1-3 seconds per event avoided)

**When NOT to Disable:**
- Detail pages have rich descriptions needed
- Location data only available on detail pages
- End times only on detail pages
- Event URLs needed for linking

**Example Reference:**
- `rules/cities/dormagen/feste_veranstaltungen/scraper.py` - DISABLE_LEVEL_2 flag usage
- `rules/cities/monheim/kulturwerke/scraper.py` - DISABLE_LEVEL_2 flag usage

---

## Debugging Tips

### 1. Test Scraper Only
```python
from rules.registry import create_scraper

url = "https://example.com"
scraper = create_scraper(url)
content = scraper.fetch()
print(content[:1000])  # Print first 1000 chars
```

### 2. Test Regex Only
```python
from rules.registry import create_regex

url = "https://example.com"
content = "...fetched content..."
regex = create_regex(url)
events = regex.extract_events(content)
print(f"Found {len(events)} events")
for event in events:
    print(f"- {event.name} | {event.date}")
```

### 3. Check Registry
```python
from rules.registry import list_registered_rules

rules = list_registered_rules()
for url, entry in rules.items():
    print(f"{url} -> {entry}")
```

### 4. Test Specific City
```bash
# Run scraper for specific city only
python3 main.py --cities monheim

# Run scraper for multiple cities
python3 main.py --cities monheim langenfeld
```

### 5. Verbose Mode
```bash
# Show raw content and structured events
python3 main.py --cities monheim --verbose
```

---

## Naming Conventions

### Directories & Files
- **City folder**: Lowercase (e.g., `monheim`, `langenfeld`, `leverkusen`)
- **Subfolder**: Lowercase with underscores (e.g., `terminkalender`, `stadt_erleben`, `lust_auf`)
- **IMPORTANT**: Each URL MUST have its own subfolder. No city-level scrapers allowed.
- **`__init__.py`**: Required in city folder and all subfolders (can be empty)

### Class Naming
- **Scraper class**: `{Subfolder}Scraper` (e.g., `TerminkalenderScraper`, `LustAufScraper`)
- **Regex class**: `{Subfolder}Regex` (e.g., `TerminkalenderRegex`, `LustAufRegex`)

### Examples
- `rules/cities/monheim/terminkalender/scraper.py` → `class TerminkalenderScraper`
- `rules/cities/leverkusen/lust_auf/regex.py` → `class LustAufRegex`


### URL to File Mapping (in `rules/urls.py`)
```python
"monheim": {
    "terminkalender": "https://www.monheim.de/freizeit-tourismus/terminkalender",
    "kulturwerke": "https://www.monheimer-kulturwerke.de/de/kalender/",
},
```

Maps to:
- `rules/cities/monheim/terminkalender/` → `https://www.monheim.de/freizeit-tourismus/terminkalender`
- `rules/cities/monheim/kulturwerke/` → `https://www.monheimer-kulturwerke.de/de/kalender/`

---

## Troubleshooting

### Issue: Scraper not found
**Solution**: Check that:
1. URL is in `CITY_URLS` in `rules/urls.py`
2. Subfolder name matches the key in `CITY_URLS`
3. Subfolder path is correct: `rules/cities/{city}/{subfolder}/`
4. `scraper.py` and `regex.py` exist in the subfolder
5. Class names end with "Scraper" and "Rule"/"Regex"
6. No city-level `scraper.py` or `regex.py` files exist

### Issue: Not loading 14 days of events
**Solution**:
1. Check if webpage has "Load More" button - implement clicking logic
2. Check for pagination - implement navigation
3. Check for date filters - set 14-day range
4. Verify the page actually has events for 14 days
5. Add debugging prints to track navigation steps
6. Check for rate limiting or anti-bot measures

### Issue: Duplicate events across pages
**Symptoms**: Same events appearing on page 1, page 2, page 3...
**Cause**: Site has pagination URLs but returns all events on every page
**Solution**:
1. Fetch page 1 and page 2 HTML
2. Compare event counts or first few event titles
3. If identical: Set `MAX_PAGES = 1` in scraper
4. This is common with WordPress calendar themes that show full archive on every pagination URL
5. See `docs/00_url_setup_prompt.md` section "Pagination Verification (CRITICAL)" for verification code

### Issue: No events extracted
**Solution**:
1. Print the fetched content: `print(content[:5000])`
2. Verify content contains event data
3. Test regex patterns manually on the content
4. Check if page needs JavaScript (use Playwright)
5. Verify regex groups match the page structure
6. Check if LLM fallback would be triggered (regex returns no events)

### Issue: Dynamic content not loading
**Solution**:
1. Set `needs_browser = True`
2. Use `self._fetch_with_playwright()`
3. Add explicit waits: `page.wait_for_selector(".event-item")`
4. Increase wait times for slow-loading content
5. Check for JavaScript errors in browser console

### Issue: Regex patterns not matching
**Solution**:
1. Print raw content to see actual format
2. Test patterns in regex tester tools
3. Adjust pattern to match actual page structure
4. Add more patterns as fallbacks
5. Consider using LLM fallback for complex structures

### Issue: Date format not recognized
**Solution**:
1. Check actual date format in page content
2. Update regex to match correct format
3. Add date parsing logic in `_create_event_from_match()`
4. Handle multiple date formats if needed

### Issue: Events filtered out incorrectly
**Solution**:
1. Remember: filtering should happen at webpage level, not in regex
2. Implement navigation to load 14 days before extraction
3. Remove any post-extraction date filtering logic
4. Verify scraper loads full 14-day range

### Issue: Registry not discovering new scraper
**Solution**:
1. Restart Python to re-import registry
2. Check subfolder structure is correct
3. Verify `__init__.py` files exist
4. Check for Python syntax errors in new files
5. Run `python3 -c "from rules.registry import list_registered_rules; print(list_registered_rules())"`

---

## Quick Reference

### File Checklist for New URL
- [ ] Add URL to `rules/urls.py` in `CITY_URLS`
- [ ] Create `rules/cities/{city}/{subfolder}/` folder
- [ ] Create `__init__.py` in city folder (can be empty)
- [ ] Create `__init__.py` in subfolder (can be empty)
- [ ] Create `scraper.py` with `{Subfolder}Scraper` class
- [ ] Create `regex.py` with `{Subfolder}Regex` class
- [ ] Implement `can_handle()` in both classes
- [ ] Implement `fetch()` in scraper with **navigation to load 14 days of events**
- [ ] Implement `get_regex_patterns()` in regex (primary extraction method)
- [ ] Implement `_create_event_from_match()` in regex
- [ ] Test with `python3 main.py --cities {city}`

### Data Fields to Extract
All scrapers must extract these fields:
- **name** (required): Event title
- **date** (required): DD.MM.YYYY format
- **time** (required): Event time (empty string if all-day event)
- **location** (required): Venue/location
- **description** (required): Event details
- **source** (required): URL (`self.url`)
- **category**: Created by analyzer (not set by regex/scraper)

### Scraper Requirements
- Must navigate to load 14 days of events
- Handle "Load More" buttons
- Handle pagination
- Handle date filters
- Handle calendar navigation
- Use Playwright for dynamic content
- Use requests for static content

### Regex Extraction
- **Primary method**: Regex patterns
- **Fallback method**: LLM (DeepSeek) - automatic if regex fails
- Multiple patterns can be tried in order
- Patterns should extract: date, name, time?, location?, description?

### Testing Commands
```bash
# Run specific city
python3 main.py --cities monheim

# Run multiple cities
python3 main.py --cities monheim langenfeld

# Verbose mode
python3 main.py --cities monheim --verbose

# List runs
python3 main.py --list-runs
```

**IMPORTANT: Always check log files for actual progress**

The scraper writes all progress to log files. Bash stdout only shows the initial "Logging to:" message.

```bash
# Monitor log file in real-time while script runs
tail -f logs/scrape_*.log

# View completed log
cat logs/scrape_2026-02-16_XX-XX-XX.log

# Find most recent log file
ls -lt logs/ | head -2
```

**Why checking logs is critical:**
- Scripts redirect output to log files after initialization
- Bash timeouts don't mean script failure - script continues running
- Log files contain: event counts, errors, Level 2 progress, final status
- Example successful log output: `✓ https://example.com - 77 events (167.24s)`
- Example error in log: `Error fetching detail page: Timeout`

**Common mistake**: Assuming script failed when bash times out
- Bash timeout only affects the tool, not the Python script
- Script continues running in background
- All progress is logged to the log file
- Always check logs to determine actual status

---

## Example: Complete Working Scraper

This example shows a complete scraper for a URL that requires clicking "Load More" to access 14 days of events.

**URL Mapping in `rules/urls.py`**:
```python
CITY_URLS: Dict[str, Dict[str, str]] = {
    "example": {
        "events": "https://example.com/events",
    },
}
```

**File**: `rules/cities/example/events/scraper.py`
```python
"""Scraper for example.com events.
 
Navigates the page to load 14 days of events by clicking "Load More" button.
"""

from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from rules.base import BaseScraper, _clean_text

class EventsScraper(BaseScraper):
    """Scraper for example.com event pages.
    
    This scraper:
    1. Loads the initial page
    2. Clicks "Load More" until 14 days of events are loaded
    3. Extracts all event content
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "example.com" in url and "/events" in url

    def fetch(self) -> str:
        """Fetch content with navigation to load 14 days of events."""
        
        # Try initial fetch first
        initial_content = self._fetch_with_requests()
        if self._has_14_days_of_events(initial_content):
            return initial_content
        
        # Use Playwright for navigation
        return self._fetch_with_playwright_navigation()

    def _has_14_days_of_events(self, content: str) -> bool:
        """Check if content contains events for 14 days."""
        import re
        
        # Extract dates from content
        dates = re.findall(r'(\d{1,2}\.\d{1,2}\.\d{4})', content)
        
        if len(dates) < 14:
            return False
        
        # Parse dates and check range
        parsed_dates = []
        for date_str in dates:
            try:
                parsed_dates.append(datetime.strptime(date_str, "%d.%m.%Y"))
            except Exception:
                continue
        
        if not parsed_dates:
            return False
        
        # Check if range covers today + 14 days
        today = datetime.now()
        cutoff = today + timedelta(days=14)
        
        return min(parsed_dates) <= today and max(parsed_dates) >= cutoff

    def _fetch_with_playwright_navigation(self) -> str:
        """Fetch using Playwright with navigation to load 14 days of events."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")
            
            # Calculate cutoff date
            cutoff_date = datetime.now() + timedelta(days=14)
            
            # Click "Load More" until we have 14 days of events
            max_clicks = 20
            for click_num in range(max_clicks):
                # Check last event date
                last_event = page.locator(".event-item").last
                if last_event.count() > 0:
                    try:
                        date_text = last_event.locator(".event-date").inner_text()
                        last_date = datetime.strptime(date_text, "%d.%m.%Y")
                        
                        # Stop if we have events beyond cutoff
                        if last_date >= cutoff_date:
                            break
                    except Exception:
                        pass
                
                # Click "Load More" button
                load_more = page.locator("button:has-text('Mehr anzeigen'), button.load-more, a.load-more")
                if load_more.count() == 0:
                    break
                
                load_more.click()
                page.wait_for_timeout(1000)
                
                print(f"Clicked Load More ({click_num + 1}/{max_clicks})")
            
            content = page.content()
            browser.close()
            
            # Parse and clean content
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove non-event elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            # Remove pagination and navigation elements
            for tag in soup.find_all(class_=re.compile(r"pagination|nav|menu|filter")):
                tag.decompose()
            
            # Get clean text
            text = soup.get_text(separator="\n", strip=True)
            
            # Remove empty lines and duplicates
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            cleaned_text = "\n".join(line for line in lines if len(line) > 3)
            
            return _clean_text(cleaned_text, max_chars=50000)
```

**File**: `rules/cities/example/events/regex.py`
```python
"""Regex parser for example.com events.
 
PRIMARY EXTRACTION: Regex patterns extract events.
FALLBACK: LLM (DeepSeek) if regex fails.
 
Extracts fields:
- date (required): DD.MM.YYYY format
- name (required): Event name
- time (required): Event time (empty if all-day)
- location (required): Event venue
- description (required): Event details
- source (required): self.url
- category: Created by analyzer (not set by regex)
"""

import re
from typing import List, Optional
from rules.base import BaseRule, Event

class EventsRegex(BaseRule):
    """Regex parser for example.com events."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "example.com" in url and "/events" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns to extract events.
        
        Try multiple patterns in order. If none extract events,
        LLM fallback will be used automatically.
        """
        patterns = [
            # Pattern 1: Full event line (date, name, time, location, description)
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)\s+(\d{2}:\d{2})\s+Uhr\s+(.+?)\s+-\s+(.+?)(?=\n\d{1,2}\.\d{1,2}\.\d{4}|\Z)',
                re.MULTILINE
            ),
            # Pattern 2: All-day event (date, name, time="", location, description)
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)\s+@?\s*(.+?)\s+-\s*(.+?)(?=\n\d{1,2}\.\d{1,2}\.\d{4}|\Z)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from regex match.
        
        Args:
            match: (date, name, time?, location?, description?)
        
        Returns:
            Event or None if required fields missing.
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

**File**: `rules/cities/example/events/__init__.py`
```python
from .scraper import EventsScraper
from .regex import EventsRegex

__all__ = ['EventsScraper', 'EventsRegex']
```

---

## Testing Your Scraper

After creating your scraper, test it with these commands:

```bash
# Test specific city
python3 main.py --cities example

# Verbose mode to see extracted events
python3 main.py --cities example --verbose

# Test only scraper agent
python3 main.py --agent scraper --cities example

# Check if events were saved
python3 main.py --list-runs
```

**ALWAYS check log files to monitor progress and results**

The scraper writes all progress to log files. Bash stdout only shows initialization.

```bash
# View log file while script runs
tail -f logs/scrape_*.log

# View completed log file
cat logs/scrape_2026-02-16_XX-XX-XX.log

# Find most recent log file
ls -lt logs/ | head -2
```

**What log files contain:**
- Progress messages: "Fetching page 1/3", "Parsing page 2"
- Level 2 progress: "Fetching detail pages for 77 events..."
- Success messages: "✓ https://example.com - 77 events (167.24s)"
- Error messages: "Error fetching detail page: Timeout"
- Event counts and validation status

**Why checking logs is essential:**
- Bash timeouts ≠ script failures - scripts continue running
- All actual output goes to log files, not bash stdout
- Log files show true progress, errors, and success/failure status
- You cannot assess scraper functionality from bash output alone

Verify your scraper:
1. Loads 14 days of events (not just today or current month)
2. Extracts all required fields (name, date)
3. Handles "Load More" buttons, pagination, or date filters
4. Returns events in correct format (DD.MM.YYYY)
5. **Check log file** for actual results (event count, errors, runtime)

## Notes for Future Development

### Critical Requirements
- **Navigation is mandatory**: Every scraper must implement logic to load 14 days of events
- **No city-level files**: All scrapers must be in subfolders, one per URL
- **No post-extraction filtering**: Date filtering happens at webpage level via navigation
- **Regex is primary**: Always try regex extraction first; LLM is automatic fallback

### Best Practices
- Use descriptive names for subfolders (e.g., `terminkalender`, `stadt_erleben`)
- Keep regex patterns as specific as possible to avoid false matches
- Use `needs_browser` property for pages that require JavaScript
- Test scrapers individually before adding to production
- Document any unique page structures in file docstrings
- Implement robust error handling for navigation (max clicks, timeouts)
- Log navigation steps for debugging

### Common Navigation Patterns to Implement
1. **"Load More" buttons**: Click until 14 days of events loaded
2. **Pagination**: Navigate through pages until 14 days covered
3. **Date filters**: Set start/end date range to cover 14 days
4. **Calendar navigation**: Navigate to next month if needed
5. **Infinite scroll**: Scroll down until 14 days loaded

### When to Use LLM Fallback
LLM fallback is automatic when:
- Regex patterns extract zero events
- Regex patterns fail to match any content
- Complex page structure makes regex impractical

### Debugging Navigation Issues
If scraper doesn't load 14 days:
1. Check if "Load More" button selector is correct
2. Verify page has events for the full 14-day period
3. Check for rate limiting or anti-bot measures
4. Add explicit waits for content to load
5. Log navigation steps to identify where it stops
6. Manually test the webpage to understand its behavior
