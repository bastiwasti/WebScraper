# Implementation Plan: Leverkusen Stadt_Erleben 2-Level Scraping

## Overview

**URL**: https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/
**Events**: ~448 total events across 45 pages (10 events per page)
**Challenge**: Need pagination support + date filtering + advertising detection

---

## 1. CURRENT STATE

### Existing Files
- `rules/cities/leverkusen/stadt_erleben/scraper.py` - Basic scraper (requests-based)
- `rules/cities/leverkusen/stadt_erleben/regex.py` - Regex-based parser (to be rewritten)

### Current Limitations
- ❌ No Level 2 support
- ❌ No pagination support
- ❌ Hard-coded 14-day date filter
- ❌ Returns only ~14 days of events (448 total)
- ❌ No advertising detection

---

## 2. TARGET SPECIFICATION

### Functional Requirements
1. **Pagination Support**:
   - Fetch multiple pages (all 45 pages optional)
   - URL pattern: `?sp:page[eventSearch-1.form][0]={page_num}`
   - Max pages: 45 (all events)
   - **For now**: Fixed limit of 10 pages (first 100 events)

2. **Date Filtering**:
   - Apply date range via URL parameters
   - Pattern: `&sp:dateFrom[]=YYYY-MM-DD&sp:dateTo[]=YYYY-MM-DD`
   - **For now**: No date filtering (fetch all events on first 10 pages)

3. **Level 2 Scraping**:
   - Fetch detail pages for events
   - Extract enhanced data: full description, location, end time
   - Only for real events (skip advertising)

4. **Advertising Detection**:
   - Skip events with categories: `Bildung`, `Veranstaltungen`, `Werbung`
   - These appear to be promotional/not real events

5. **Performance Requirements**:
   - Total time: ~2-3 minutes for 10 pages
   - Level 2 requests: ~15 seconds per page
   - Acceptable for daily runs

---

## 3. ARCHITECTURE

### File: `rules/cities/leverkusen/stadt_erleben/scraper.py`

**Changes**:
```python
class StadtErlebenScraper(BaseScraper):
    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def fetch(self) -> str:
        """Fetch content from StadtErleben URL."""
        return self._fetch_with_requests()

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML for Level 2 parsing."""
        try:
            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"}
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"[StadtErleben] Failed to fetch raw HTML: {e}")
            raise

    def fetch_all_pages(self, max_pages: int = 10) -> list[Event]:
        """Fetch multiple pages with optional date filtering.
        
        Args:
            max_pages: Maximum number of pages to fetch (default: 10).
        """
        all_events = []
        page = 1
        
        while page <= max_pages:
            # Build URL with pagination
            if page == 1:
                url = self.url
            else:
                url = f"{self.url}?sp:page[eventSearch-1.form][0]={page}"
            
            print(f"[StadtErleben] Fetching page {page}/{max_pages}...")
            
            scraper = self.__class__(url)
            parser = create_regex(url)
            
            # Fetch and parse
            content = scraper.fetch_raw_html()
            events, _ = parser.parse_with_regex(content)
            
            # Apply Level 2
            if events:
                raw_html = scraper.fetch_raw_html()
                events = parser.fetch_level2_data(events, raw_html)
            
            all_events.extend(events)
            page += 1
        
        print(f"[StadtErleben] Fetched {len(all_events)} events from {page} pages")
        return all_events
```

---

### File: `rules/cities/leverkusen/stadt_erleben/regex.py`

**Complete Rewrite with HTML-based Level 1 & 2:**

```python
"""HTML-based parser for Leverkusen Stadt_Erleben events."""

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
from rules.base import BaseRule, Event
import requests


class StadtErlebenRegex(BaseRule):
    """HTML parser for Leverkusen Stadt_Erleben events.
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (DD.MM.YYYY)
    - time (required): Event time (HH:MM format)
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category (required): Inferred from event data
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping
    
    NO DATE FILTERING:
    - Fetches all events (no automatic date restriction)
    - Date filtering applied via URL parameters by scraper_agent
    
    ADVERTISING DETECTION:
    - Skips events with categories: 'Bildung', 'Veranstaltungen', 'Werbung'
    - These are promotional content, not real events
    
    PAGINATION SUPPORT:
    - Supports server-side pagination
    - URL pattern: ?sp:page[eventSearch-1.form][0]={page_num}
    """

    # Advertising categories to skip
    ADVERTISING_CATEGORIES = ['Bildung', 'Veranstaltungen', 'Werbung']
    
    def get_regex_patterns(self) -> List:
        """Return regex patterns (fallback only, HTML parsing is primary)."""
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt_erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method)."""
        soup = BeautifulSoup(raw_content, 'html.parser')
        events = []
        
        # Find all event cards
        event_cards = soup.select('li.SP-TeaserList__item div.SP-Teaser')
        
        for card in event_cards:
            try:
                # Extract detail page URL
                detail_link = card.select_one('div.SP-Teaser__content > a.SP-Link__Teaser__link')
                if not detail_link:
                    continue
                
                detail_url = detail_link.get('href', '')
                if detail_url.startswith('/'):
                    detail_url = f"https://www.leverkusen.de{detail_url}"
                
                # Extract event title
                title_elem = card.select_one('h2.SP-Headline__text')
                title = title_elem.get_text(strip=True) if title_elem else ""
                if not title:
                    continue
                
                # Extract date and time
                date_elem = card.select_one('time.SP-Scheduling__date time')
                time_elem = card.select_one('span.SP-EventInformation__time')
                
                # Parse date from datetime attribute
                date_str = ""
                time_str = ""
                if date_elem:
                    date_attr = date_elem.get('datetime', '')
                    if date_attr:
                        date_str = self._parse_datetime(date_attr)
                
                if time_elem:
                    time_str = time_elem.get_text(strip=True)
                
                # Extract location
                loc_elem = card.select_one('span.SP-EventInformation__location')
                location = loc_elem.get_text(strip=True) if loc_elem else ""
                
                # Extract category
                cat_elem = card.select_one('span.SP-Kicker__text')
                category = cat_elem.get_text(strip=True) if cat_elem else "other"
                
                # Extract description (from teaser)
                desc_elem = card.select_one('div.SP-Teaser__abstract div.SP-Paragraph')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Skip advertising
                if category in self.ADVERTISING_CATEGORIES:
                    continue
                
                events.append(Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category=category,
                    event_url=detail_url,
                ))
            
            except Exception as e:
                print(f"[StadtErleben] Failed to parse event card: {e}")
                continue
        
        print(f"[StadtErleben] HTML parsing returned {len(events)} events")
        return events
    
    def _parse_datetime(self, iso_datetime: str) -> str:
        """Parse ISO 8601 datetime to DD.MM.YYYY."""
        try:
            dt = datetime.fromisoformat(iso_datetime.split('+')[0])
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return ""
    
    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.
        
        Returns:
            Dictionary mapping event name to detail URL.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        # Find all event cards with detail links
        for card in soup.select('li.SP-TeaserList__item'):
            try:
                detail_link = card.select_one('div.SP-Teaser__content > a.SP-Link__Teaser__link')
                title_elem = card.select_one('h2.SP-Headline__text')
                
                if detail_link and title_elem:
                    title = title_elem.get_text(strip=True)
                    href = detail_link.get('href', '')
                    if href.startswith('/'):
                        href = f"https://www.leverkusen.de{href}"
                    event_url_map[title] = href
            
            except Exception as e:
                continue
        
        print(f"[StadtErleben] Extracted {len(event_url_map)} event detail URLs")
        return event_url_map
    
    def parse_internal_detail_page(self, detail_html: str) -> dict | None:
        """Parse internal leverkusen.de detail page.
        
        Args:
            detail_html: Raw HTML content from event detail page.
        
        Returns:
            Dictionary with detail information (detail_description, end_time).
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract full description
        desc_elem = soup.select_one('div.tribe-events-single-event-description')
        if desc_elem:
            paragraphs = desc_elem.select('p')
            descriptions = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    descriptions.append(text)
            
            if descriptions:
                detail_data['detail_description'] = '\n\n'.join(descriptions[:2])
        
        # Extract end time
        end_time_elem = soup.select_one('div.tribe-events-single-event-information time')
        if end_time_elem:
            time_str = end_time_elem.get_text(strip=True)
            # Parse "bis HH:MM Uhr" format
            import re
            match = re.search(r'bis\s+(\d{1,2}:\d{2})\s+Uhr', time_str)
            if match:
                hours = match.group(1)
                minutes = match.group(2)
                detail_data['end_time'] = f"{hours:02d}:{minutes}:00 Uhr"
        
        return detail_data if detail_data else None
    
    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse detail page (handles both internal and external pages)."""
        # Check if internal or external page
        if 'leverkusen.de' in detail_html:
            return self.parse_internal_detail_page(detail_html)
        
        # Handle external pages (lust-auf-leverkusen.de)
        # These are separate sites with their own scrapers - skip
        return None
    
    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data for events.
        
        For each event, fetches detail page and extracts:
        - detail_description: Full event description
        - end_time: End time (if available)
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[StadtErleben Level 2] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            detail_url = event_url_map.get(event.name, "")
            if not detail_url:
                # Skip external pages
                continue
                if 'lust-auf-leverkusen.de' in detail_url:
                    continue
            
            event.event_url = detail_url
            
            try:
                resp = requests.get(
                    detail_url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                detail_html = resp.text
                
                # Parse detail page
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
            
            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue
        
        print(f"[StadtErleben Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events
```

---

## 4. PAGINATION IMPLEMENTATION

### Approach
Server-side pagination with URL parameters

### URL Pattern
```
Page 1: https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/
Page 2: https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/?sp:page[eventSearch-1.form][0]=2
Page 3: https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/?sp:page[eventSearch-1.form][0]=3
...
```

### Integration with ScraperAgent
**In `scraper_agent.py`:**
```python
# Check if --url is a specific leverkusen stadt_erleben URL
if 'stadt-erleben' in resolved_url or 'stadterleben' in resolved_url:
    # Use direct URL fetch, bypass cities parameter
    urls_to_use = [resolved_url]
    args.cities = []  # Clear cities to prevent auto-detection
```

---

## 5. ADVERTISING DETECTION

### Categories to Skip
```python
ADVERTISING_CATEGORIES = ['Bildung', 'Veranstaltungen', 'Werbung']
```

### Detection Logic
```python
# In parse_with_regex():
if category in self.ADVERTISING_CATEGORIES:
    continue  # Skip this event
```

---

## 6. TESTING PLAN

### Test Commands
```bash
# Test single scraper (10 pages)
python3 main.py --url https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/ --no-db --verbose

# Test with folder name
python3 main.py --url stadt_erleben --no-db --verbose

# Expected Output
[StadtErleben] Fetching page 1/10...
[StadtErleben] HTML parsing returned 10 events
[StadtErleben Level 2] Fetching detail pages for 10 events...
  ✓ Fetched details for: Event Name 1
  ✓ Fetched details for: Event Name 2
  ...
[StadtErleben Level 2] Completed: 10/10 events with detail data
```

### Expected Results
- **Pages Fetched**: 10
- **Total Events**: ~96-100 (10 per page)
- **Time**: ~2-3 minutes
- **Real Events Only**: Advertising events filtered out
- **Level 2 Data**: Descriptions and end times for real events

---

## 7. IMPLEMENTATION CHECKLIST

- [ ] Create/Update `rules/cities/leverkusen/stadt_erleben/scraper.py`
  - Add `fetch_raw_html()` method
  - Add `fetch_all_pages(max_pages=10)` method
- Use requests (no Playwright needed)
  - Add `can_handle()` method check

- [ ] Complete rewrite of `rules/cities/leverkusen/stadt_erleben/regex.py`
  - HTML-based Level 1 parsing (BeautifulSoup)
  - Extract: title, date, time, location, category, description
  - Extract detail page URLs from Level 1 cards
  - Advertising detection (skip specific categories)
  - Level 2 methods: `get_event_urls_from_html()`, `parse_detail_page()`, `fetch_level2_data()`
  - Date parsing: `_parse_datetime()` for ISO 8601 to DD.MM.YYYY
  - Skip external pages (lust-auf-leverkusen.de)
  - Remove hard-coded 14-day filter

- [ ] Update `scraper_agent.py` to support folder-based URLs
  - Detect leverkusen stadt_erleben URLs
  - Pass to ScraperAgent with explicit URL
  - Override cities parameter when URL is provided

- [ ] Test with 10-page limit
  - Verify pagination works correctly
  - Verify advertising detection works
  - Count total events (expect ~96-100)
  - Verify Level 2 data (descriptions, end times)
  - Time test: Should complete in <3 minutes

- [ ] Update documentation
  - Add Leverkusen to implementation reference table in 01_setup_guide.md
  - Document pagination approach (server-side, URL parameters)
  - Document advertising detection
  - Document fixed 10-page limit

---

## 8. TIMELINE ESTIMATES

| Task | Time |
|------|------|
| Create scraper.py | 5 min |
| Rewrite regex.py | 20 min |
| Add fetch_raw_html | 5 min |
| Test implementation | 15 min |
| Debug & verify | 10 min |
| **Total**: ~55 min |

---

## 9. SUCCESS CRITERIA

- [x] Fetches multiple pages with pagination
- [x] Applies advertising filter (skips non-events)
- [ ] Implements date filtering via URL parameters (future)
- [x] Level 2 for all fetched events
- [ ] Completes in ~55 minutes
- [ ] Scrapes ~100 events instead of ~448 (testing with 10-page limit)
- [ ] HTML-based parsing (no regex, no LLM costs)
- [ ] Skips external pages (lust-auf-leverkusen.de)

---

## 10. QUESTIONS FOR USER

1. **Page Limit**: I'm proposing a fixed 10-page limit for now (instead of all 45 pages). Is this acceptable for testing?
   - Will get ~96-100 events (should cover 14 days easily)
   - Takes ~2-3 minutes

2. **Date Filtering**: For now, I'm not implementing date filtering (fetching all events). OK for testing?

3. **Advertising Categories**: Are the categories `Bildung`, `Veranstaltungen`, `Werbung` correct? Should I add more?

4. **Level 2 Fields**: Should I extract:
   - Full description (from paragraphs)
   - End time (when available)
   - Location from detail page
   - Skip external pages (lust-auf-leverkusen.de)

---

## 11. FILES TO CREATE/UPDATE

1. **`rules/cities/leverkusen/stadt_erleben/scraper.py`** (NEW)
2. **`rules/cities/leverkusen/stadt_erleben/regex.py`** (COMPLETE REWRITE)
3. **`01_setup_guide.md`** (UPDATE - add to patterns table)
4. **`rules/cities/leverkusen/__init__.py`** (UPDATE - add folder name)

---

## READY TO IMPLEMENT
Once you confirm the plan, I'll:
1. Create/rewrite scraper.py with all changes
2. Create/rewrite regex.py with HTML-based parsing + Level 2
3. Update scraper_agent.py for folder URL support
4. Test the implementation
5. Update documentation

Total estimated time: ~55 minutes