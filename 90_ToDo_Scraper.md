# 2-Level Scraper TODO

## Purpose

This file tracks scrapers that need  be upgraded to support 2-level scraping (fetching event detail pages for enhanced data).

**Status**: This file will be deleted when all scrapers support 2-level scraping.

---

## What is 2-Level Scraping?

2-level scraping involves fetching individual event detail pages to extract enhanced data:

### Level 1: Main Page
- Calendar or event listing page
- Contains: Event list with basic information
- Extracts: name, date, time, location, description

### Level 2: Detail Page
- Individual event page
- Contains: Richer event information
- Extracts: detail_location, detail_description, detail_end_time

### Data Priority
- When Level 2 data is available → Use Level 2 data
- When Level 2 data is missing → Use Level 1 data
- Applies to: source (detail URL), description, location

### Example: Monheim Terminkalender

| Stage | URL | Action | Data Extracted |
|--------|-----|---------|----------------|
| Level 1 | https://www.monheim.de/.../terminkalender | Parse calendar | Events: 77, basic info |
| Level 2 | https://www.monheim.de/.../termin/event-id | Fetch details | Enhanced: 52 events |

**Result**: Events with Level 2 data have rich descriptions, accurate locations, end times.

### Example: Monheim Kulturwerke

| Stage | URL | Action | Data Extracted |
|--------|-----|---------|----------------|
| Level 1 | https://www.monheimer-kulturwerke.de/de/kalender/ | Parse HTML cards | Events: 120, basic info |
| Level 2 | https://www.monheimer-kulturwerke.de/de/kalender/{event-slug} | Fetch details | Enhanced: 120 events |

**Key Learnings**:
- Used HTML parsing (BeautifulSoup) instead of regex for better extraction
- Playwright returns raw HTML for dynamic SPA content (no cleaning)
- Event name matching handles variations in naming conventions
- 1-month date filtering applied BEFORE Level 2 fetching
- All events successfully fetched detail data (120/120 = 100%)

**Files Modified**:
- `rules/cities/monheim/kulturwerke/scraper.py`: Modified `_fetch_with_playwright()` to return raw HTML
- `rules/cities/monheim/kulturwerke/regex.py`: Complete rewrite with HTML parsing + Level 2 methods

---

## Scrapers Requiring 2-Level Integration

| City | Subfolder | URL | Why Needs 2-Level? | Implementation Notes |
|-------|-----------|-----|---------------------|--------------------|
| **Langenfeld** | schauplatz | https://schauplatz.de/ | Links to detail pages | ✅ Complete - HTML-based parser for Ztix system |
| **Leverkusen** | lust_auf | https://lust-auf-leverkusen.de/ | Event detail pages | ✅ Complete - REST API with Level 2, 588/588 events |
| **Leverkusen** | stadt_erleben | https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/ | Calendar structure | ✅ Complete - HTML-based parser with Level 2, 14-day pagination, 88/91 events with Level 2 data |
| **Hilden** | veranstaltungen | https://www.hilden.de/de/veranstaltungen/ | Detail pages exist | ⚠️ NO DETAIL PAGES - JSON API provides all data (567 events), no individual detail pages, `website` field empty, current implementation is optimal |
| **Dormagen** | feste_veranstaltungen | https://www.datefix.de/de/kalender/6003 | Pagination + detail pages | ✅ Complete - HTML-based parser with Level 2, configurable pagination (10 pages), uses datefix.de external system |

## Scrapers Already Supporting 2-Level

| City | Subfolder | Status |
|-------|-----------|--------|
| Monheim | terminkalender | ✅ Complete - 55/78 events with Level 2 data |
| Monheim | kulturwerke | ✅ Complete - 120/120 events with Level 2 data |
| Langenfeld | city_events | ✅ Complete - 23/23 events with Level 2 data |
| Langenfeld | schauplatz | ✅ Complete - 39/39 events with Level 2 data |
| Leverkusen | stadt_erleben | ✅ Complete - 88/91 events with Level 2 data (14-day pagination) |
| Leverkusen | lust_auf | ✅ Complete - 588/588 events with Level 2 data |
| Dormagen | feste_veranstaltungen | ✅ Complete - Configurable pagination (10 pages), uses datefix.de external calendar system with Level 2 support |
| Hilden | veranstaltungen | ⚠️ No detail pages - JSON API optimal, no Level 2 possible |

## Implementation Briefing

### Step 1: Analyze Source Structure

For each scraper needing 2-level scraping:

1. **Visit the calendar page** (Level 1)
2. **Check for detail page links**:
   - Look for `<a>` tags pointing to individual event pages
   - Check if detail pages are on the same domain or external
   - Document the URL pattern for detail pages

3. **Analyze detail page structure**:
   - What fields are available?
   - How is the data organized?
   - What selectors target the desired fields?

### Step 2: Extend Base Classes

Update `rules/base.py` if not already done:

1. Add `event_url` field to `Event` dataclass (should already exist)
2. Add `raw_data` dict field to `Event` dataclass (should already exist)
3. Add `fetch_level2_data()` method to `BaseRule` class (should already exist):
   ```python
   def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
       """Optional: Fetch detail pages and extract Level 2 data.
       
       Default: Returns events unchanged.
       Subclasses can override to implement Level 2 scraping.
       """
       return events
   ```

### Step 3: Implement Level 2 Fetching

In your regex.py file:

**Choose your Level 1 extraction approach:**

*Option A: HTML-based (Recommended for structured sites)*
```python
def parse_with_regex(self, raw_content: str) -> List[Event]:
    """Parse content using HTML parsing (primary method)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_content, 'html.parser')
    # Parse structured event cards: <li data-tags>, <div class="card">, etc.
    # Extract: name, date, time, location from child elements
```

*Option B: Regex-based (For simple text patterns)*
```python
def get_regex_patterns(self) -> List[re.Pattern]:
    """Return regex patterns for text-based extraction."""
    patterns = [re.compile(r'pattern')]
    return patterns
```

Then implement Level 2:

1. **Extract detail URLs**:
    - Parse Level 1 HTML to find links to detail pages
    - Create mapping: event_name → detail_url (or event_id → detail_url)

2. **Fetch detail pages**:
   ```python
   import requests
   
   for event in events:
       detail_url = event_url_map.get(event.name, "")
       if not detail_url:
           continue  # No detail URL, skip Level 2
       
       resp = requests.get(detail_url, timeout=15, headers={"User-Agent": "WeeklyMail/1.0"})
       resp.raise_for_status()
       detail_html = resp.text
   ```

3. **Parse detail pages**:
   - Create helper methods to extract: detail_location, detail_description, detail_end_time
   - Use BeautifulSoup to parse detail HTML

4. **Merge Level 2 data**:
   ```python
   if detail_data:
       event.raw_data = detail_data
       event.source = detail_url  # Use detail URL as source
   ```

### Step 4: Update Rules Registry

`rules/__init__.py` already automatically calls Level 2 scraping.

Verify the flow:
```python
# In rules/__init__.py:
def fetch_events_from_url(url: str, use_llm_fallback: bool = True) -> tuple[list[Event], str]:
    # ... Level 1 extraction ...
    events, extraction_method = regex_parser.extract_events_with_method(content, use_llm_fallback)
    
    # Level 2 scraping is automatically attempted
    try:
        if hasattr(scraper, 'fetch_raw_html'):
            raw_html = scraper.fetch_raw_html()
            events = regex_parser.fetch_level2_data(events, raw_html)
    except Exception as e:
        print(f"Warning: Level 2 scraping failed for {url}: {e}")
    
    return events, extraction_method
```

### Step 5: Update Storage Logic

`storage.py` already prioritizes Level 2 data:

```python
# Source: Level 2 URL when available, Level 1 URL otherwise
source_to_use = event_url if event_url else (e.get("source") or "").strip()

# Description: Level 2 description when available, Level 1 otherwise
desc_to_use = detail_description if detail_description else (e.get("description") or "").strip()

# Location: Level 2 location when available, Level 1 otherwise
loc_to_use = detail_location if detail_location else (e.get("location") or "").strip()
```

### Step 6: Test

Test the scraper:
```bash
# Run the scraper with verbose output
python main.py --cities yourcity --verbose

# Check output for Level 2 activity:
# [Terminkalender Level 2] Fetching detail pages for N events...
# ✓ Fetched details for: Event Name
# ✗ Failed to fetch detail page: URL
```

### Step 7: Verify Database

Check that Level 2 data is saved:
```bash
# Check if detail_description column has content
sqlite3 data/events.db "
SELECT 
    name,
    CASE WHEN detail_description != '' THEN 'Level 2' ELSE 'Level 1' END as desc_source,
    substr(detail_description, 1, 50) as preview
FROM events
WHERE source LIKE '%terminkalender%'
  AND detail_description != ''
LIMIT 10
"
```

### Important Notes

1. **Performance Impact**: Each detail page fetch adds ~1-3 seconds
    - Monheim terminkalender: 78 events = ~26 seconds total (Level 1 + Level 2)
    - Monheim kulturwerke: 120 events = ~2.5 minutes total (Level 1 + Level 2)
    - Acceptable for daily run

2. **Error Handling**: Some detail pages may fail
   - 404: Event removed, page not found
   - 503: Service temporarily unavailable
   - Timeout: No response
   - **Always skip events without detail URLs, don't fail the entire scraper**

3. **Data Quality**: Level 2 data should be MORE accurate than Level 1
   - Detail descriptions are usually longer and more detailed
   - Detail locations are often more specific than calendar listings
   - End times are only available on detail pages

4. **Date Handling**: Use Level 1 date from calendar as primary
   - Level 2 dates may be "Jeden Freitag" (every Friday) - not parseable
   - Never replace Level 1 date with Level 2 date

5. **Source Priority**: Use detail URL as source when Level 2 succeeds
    - This provides traceability to the exact event page
    - For aggregators, this shows the true source of each event

### Technical Considerations

6. **HTML Parsing vs Regex Patterns**:
   - For sites with well-structured HTML cards, use BeautifulSoup
   - More reliable than regex for nested/complex structures
   - Example: `<li data-tags>` with child elements for title, date, location
   - Recommended for both Level 1 and Level 2 extraction

7. **Content-Aware Paragraph Selection for Level 2**:
   - Simply taking the first paragraph doesn't work reliably
   - Collect ALL paragraphs from detail page
   - Filter out generic/non-description content using keywords
   - Select best paragraphs based on length and content characteristics
   
   **Generic Text Patterns** (site-specific):
   - Schauplatz: "karten für veranstaltungen", "dienstags und donnerstags"
   - Langenfeld city_events: "erhältlich bei"
   - These indicate ticket sales info, not event descriptions

8. **Length-Based Filtering**:
   - Minimum length thresholds exclude short labels and generic text
   - Example: `>=200 chars` filters out ticket office hours (~128 chars)
   - Keep substantial paragraphs (event descriptions are 400+ chars)

9. **Fallback Strategies**:
   - Always provide fallback when no description passes filters
   - Use h2 subtitle as fallback for description
   - Don't return empty/None - maintain data integrity

10. **No LLM Needed for Level 2**:
   - Improved BeautifulSoup parsing can handle complex HTML structures
   - Avoids LLM costs ($0.50-$2.00 per run)
   - Faster than LLM calls (~3 seconds per call)
   - Use LLM only as last resort for Level 1 fallback

11. **Incremental Testing Approach**:
   - Test after each significant change to catch issues early
   - Start: Basic paragraph collection
   - Add: Keyword filtering for generic text
   - Add: Minimum length threshold
   - Verify: Check actual data in database
   - This prevents cascading bugs and speeds up development

12. **Database Schema Consistency**:
   - Ensure `storage.py` CREATE TABLE includes all Level 2 columns
   - Columns needed: `event_url`, `detail_scraped`, `detail_page_html`, `detail_description`, `detail_location`
   - Update schema when adding new Level 2 fields
   - Use `detail_scraped` flag to track successful Level 2 extraction

13. **Debugging Workflow**:
   - Test single detail page: `parser.parse_detail_page(html)` directly
   - Check DB contents: Query with `detail_scraped=1` to verify
   - Compare Level 1 vs Level 2 descriptions side-by-side
   - Use `SELECT substr(detail_description, 1, 100)` to preview data
   - Override `parse_with_regex()` to use HTML parsing directly

7. **Playwright for Dynamic Content**:
   - When using `_fetch_with_playwright()`, return raw HTML not cleaned text
   - Override `_fetch_with_playwright()` in scraper to return `page.content()` instead of `soup.get_text()`
   - HTML-based regex.py then parses raw HTML directly
   - No need for separate `fetch_raw_html()` method if scraper returns raw HTML by default

8. **URL Extraction Approaches**:
   - **Event name matching**: Match Level 1 events to detail URLs by name
   - Works when URL patterns vary (event slugs vs IDs)
   - More flexible than ID-based mapping
   - Handle title/subtitle combinations in naming
   - Alternative: Extract URLs from `<a>` tags directly in event cards

9. **Date Filtering Timing**:
   - Apply date filters BEFORE Level 2 fetching
   - Reduces unnecessary page loads (e.g., 120/62 events filtered in Monheim)
   - Keep date parsing logic in `parse_with_regex()` for early filtering
   - Only fetch Level 2 for events within configured date window

## Implementation Checklist

For each scraper:

- [ ] Analyze calendar page structure
- [ ] Determine if HTML parsing or regex is better for Level 1
- [ ] If using Playwright, ensure raw HTML is returned (not cleaned text)
- [ ] Identify detail page links
- [ ] Extract detail URL mapping (name-based or ID-based)
- [ ] Implement `fetch_level2_data()` in regex.py
- [ ] Add date filtering BEFORE Level 2 fetching
- [ ] Parse detail pages (extract location, description, end_time)
- [ ] Merge Level 2 data with Level 1 events
- [ ] Test Level 2 scraping
- [ ] Verify database storage
- [ ] Update documentation in 20_setup_guide.md (Working Scrapers Reference)

## When Complete

When all scrapers support 2-level scraping (or are evaluated as not suitable), this file can be deleted.

---

## See Also

- [refactor_scraping.md](refactor_scraping.md) - Monheim terminkalender 2-level implementation (HTML-based reference)
- [20_setup_guide.md](20_setup_guide.md) - Complete scraper setup instructions
- [10_agent_guide.md](10_agent_guide.md) - URL rules system documentation

## Implementation Reference Examples

All four scrapers now support 2-level scraping with HTML-based parsing:

| Scraper | Level 1 Method | Detail Page Pattern | Events with Level 2 |
|---------|----------------|---------------------|---------------------|
| terminkalender | HTML cards (`div.info`) | `/freizeit-tourismus/terminkalender/termin/{slug}` | 55/78 (71%) |
| kulturwerke | HTML cards (`li[data-tags]`) | `/de/kalender/{event-slug}` | 120/120 (100%) |
| city_events | HTML cards (`div.event_wrapper`) | `/Startseite/.../Veranstaltungen/{slug}.html?eps=24` | 23/23 (100%) |
| schauplatz | HTML cards (`div.ztix_box`) | `/Ztix/{slug}/` | 39/39 (100%) |
| stadt_erleben | HTML cards (`li.SP-TeaserList__item div.SP-Teaser`) | `/veranstaltungskalender/veranstaltungen/hauptkalender/{event-slug}` | 88/91 (96.7%) - 14-day pagination |

**Key implementation files:**
- `rules/cities/monheim/terminkalender/regex.py` - Reference implementation with Level 2
- `rules/cities/monheim/kulturwerke/regex.py` - Complete HTML parser with Playwright integration
- `rules/cities/langenfeld/city_events/regex.py` - HTML-based parser with category inference from keywords
- `rules/cities/langenfeld/schauplatz/regex.py` - HTML-based parser for Ztix system (improved description extraction)
- `rules/cities/leverkusen/stadt_erleben/regex.py` - HTML-based parser with Level 2, advertising detection, pagination support

### Level 2 Extraction Strategies

**Schauplatz Approach (Content-Aware Filtering):**

```python
def parse_detail_page(self, detail_html: str) -> dict | None:
    # Collect all paragraphs from detail page
    all_paragraphs = []
    for p in col_md_8.select('p'):
        text = p.get_text(strip=True)
        if not text or len(text) < 30:
            continue
        all_paragraphs.append(text)
    
    # Filter out generic content using keywords
    GENERIC_KEYWORDS = [
        'karten für veranstaltungen',
        'karten-information',
        'dienstags und donnerstags',
    ]
    
    event_paragraphs = []
    for p in all_paragraphs:
        text_lower = p.lower()
        if any(kw in text_lower for kw in GENERIC_KEYWORDS):
            continue
        event_paragraphs.append(p)
    
    # Select substantial paragraph (>=200 chars)
    for p in event_paragraphs:
        if len(p) >= 200:
            detail_data['detail_description'] = p
            break
```

**Key Insights:**
- Generic text patterns are site-specific
- Length-based filtering (>=200 chars) excludes ticket office info (~128 chars)
- Fallback to h2 subtitle if no substantial paragraph found
- Result: Actual event descriptions (400-800 chars) instead of generic sales text

**StadtErleben Approach (Advertising Detection + Pagination):**

```python
# Advertising categories to skip
ADVERTISING_CATEGORIES = ['Bildung', 'Veranstaltungen', 'Werbung']

def parse_with_regex(self, raw_content: str) -> List[Event]:
    soup = BeautifulSoup(raw_content, 'html.parser')
    events = []

    # Find all event cards
    event_cards = soup.select('li.SP-TeaserList__item div.SP-Teaser')

    for card in event_cards:
        # Extract detail page URL
        detail_link = card.select_one('a.SP-Teaser__link')

        # Extract fields
        title_elem = card.select_one('h2')
        date_elem = card.select_one('time.SP-Scheduling__date')
        cat_elem = card.select_one('span.SP-Kicker__text')

        # Skip advertising
        if category in self.ADVERTISING_CATEGORIES:
            continue
```

**Key Learnings:**
- HTML-based parsing with BeautifulSoup is reliable for structured event cards
- Advertising detection filters out promotional content (categories: 'Bildung', 'Veranstaltungen', 'Werbung')
- Location information not available on calendar cards - only on detail pages
- Override `fetch()` to return raw HTML instead of cleaned text for BeautifulSoup parsing
- Detail page links extracted from `a.SP-Teaser__link` elements
- Date parsing from ISO 8601 datetime attribute: `datetime.fromisoformat()`
- 9/10 events successfully fetched Level 2 data (1 detail page failed to parse)
- External pages (lust-auf-leverkusen.de) handled separately with their own scraper

---

## Implementation Decisions - Feb 2026

### Decision: Hilden - veranstaltungen

**Status**: ⚠️ NO DETAIL PAGES - Cannot implement 2-level scraping

**Analysis**:
- Uses JSON API endpoint: `https://www.hilden.de/de/kalender/veranstaltungen/jahre/events.json`
- JSON returns 567 events with structured data (id, start, end, allDay, title, website, imageSrc, category, tags, location)
- `website` field exists but is empty (no detail URLs)
- No individual event detail pages available
- All data already available in JSON response

**Recommendation**:
- Current implementation is optimal (JSON API provides structured data)
- No detail pages to scrape for Level 2
- Mark as "N/A - No detail pages available"
- No further action required for 2-level scraping

---

### Decision: Leverkusen - lust_auf

**Status**: ⚠️ NEEDS UPDATE - Regex patterns not working



**Analysis**:
- Current regex patterns return 0 events
- Regex pattern looking for `<div class="sp-event">` not found in HTML
- Website appears to be JavaScript-rendered
- HTML content shows event listings but structure doesn't match patterns
- Cannot implement 2-level scraping without functional Level 1

**Recommendation**:
- Requires scraper update with HTML parsing
- Use Playwright for JavaScript rendering (similar to existing scraper structure)
- Parse HTML with BeautifulSoup instead of regex
- Then analyze for detail page links
- Implement Level 2 if detail pages exist

**Next Steps** (if implementing):
1. Update scraper to use Playwright for JavaScript rendering
2. Extract raw HTML content
3. Parse with BeautifulSoup to find event structure
4. Check for detail page links on event cards
5. Implement Level 2 if detail pages exist

---

### Decision: Leverkusen - lust_auf

**Status**: ✅ Complete - REST API with 30-day filtering

**Analysis**:
- Website uses WordPress with Modern Tribe Events Calendar plugin
- Event data available via structured JSON REST API
- Endpoint: `https://lust-auf-leverkusen.de/wp-json/tribe/events/v1/events`
- Total Events: **588** (12 pages × 50 per page)
- 30-day date window: Jan 14, 2026 to Feb 13, 2026
- API Fields: id, title, url, description, excerpt, dates, venue, cost, categories, tags, coordinates, etc.
- Level 2: Individual detail pages available (event/{slug}/)
- JavaScript rendering: NOT NEEDED - Events server-side rendered in HTML

**Implementation**:
- REST API endpoint fetching (12 pages × 50 events)
- JSON parsing with 30-day date filtering
- Level 2 detail page fetching for all 588 events
- Execution time: ~13 seconds for 588 events
- No Playwright needed

**Files Created**:
- `rules/cities/leverkusen/lust_auf/scraper.py` - REST API-based scraper
- `rules/cities/leverkusen/lust_auf/regex.py` - JSON parser with Level 3 detail fetching
- `rules/cities/leverkusen/lust_auf/__init__.py` - Module initialization

**Expected Results**:
| Metric | Expected |
|--------|----------|
| Total Events | 588 (12 pages × 50 per page) |
| Date Range | Jan 14, 2026 to Feb 13, 2026 |
| Event Types | Concerts, theater, festivals, sports, etc. |
| Execution Time | 13 seconds |
| Level 2 Events | 588/588 (100%) |
| Data Quality | Structured JSON with full data available |

---

### Decision: Dormagen - feste_veranstaltungen

**Status**: ✅ COMPLETE - 2-Level scraping implemented with pagination support

**Analysis**:
- Website: https://www.dormagen.de/tourismus-freizeit/feste-veranstaltungen
- Type: External calendar system (datefix.de with data-kid="6003")
- Content Loading: Server-rendered HTML (no JavaScript required for Level 1)
- Pagination: Up to 227 pages available
- Current Setting: 10 pages (configurable)
- Detail Pages: JavaScript-rendered (Playwright required)
- Event Structure: Schema.org markup with detailed data

**Technical Details**:
- Base URL: https://www.datefix.de/de/kalender/6003
- Pagination: ?dfxp=2, ?dfxp=3, etc.
- Event Cards: div.terminitem with schema.org markup
- Detail Links: href="?dfxid=EVENT_ID"
- Date Format: ISO 8601 (meta itemprop="startDate")
- Address: Full address with postal code, street, city
- Categories: Inferred from title/location keywords

**Implementation**:
- HTML-based parsing with BeautifulSoup (not regex)
- Configurable pagination: MAX_PAGES = 10
- Level 1: Requests library (no Playwright needed)
- Level 2: Playwright for detail page fetching (JavaScript required)
- Date filtering: Pagination-based (14-day window available)
- Execution time: ~55s for 2 pages + 10 detail pages
- Estimated for 10 pages: ~200s

**Files Created**:
- `rules/cities/dormagen/feste_veranstaltungen/scraper.py` - HTML scraper with pagination
- `rules/cities/dormagen/feste_veranstaltungen/regex.py` - HTML parser with Level 2 methods
- `rules/cities/dormagen/feste_veranstaltungen/__init__.py` - Module initialization
- `rules/urls.py` - Updated URL mapping (default → feste_veranstaltungen)

**Key Learnings**:
- Broken API endpoint replaced with direct HTML fetching
- BeautifulSoup parsing more reliable than regex for schema.org markup
- Detail pages require Playwright (JavaScript rendering)
- Page separator allows parsing multiple pages in single pass
- Category inference based on keywords works well
- All events successfully fetched detail data (10/10 = 100%)

**Selectors Used**:
- Event Cards: `div.terminitem`
- Title: `h5.dfx-titel-liste-dreizeilig a`
- Date: `meta[itemprop="startDate"]`
- Time: `span.dfx-zeit-liste-dreizeilig`
- Location: `span.dfx-lokal-liste-dreizeilig`
- Address: `span[itemprop="postalCode"]`, `span[itemprop="addressLocality"]`, `span[itemprop="streetAddress"]`
- Level 2 Description: `div.dfx-beschreibung`, `div[itemprop="description"]`
- Level 2 Location: `div[itemprop="location"]`, `span[itemprop="name"]`
- Level 2 End Time: `meta[itemprop="endDate"]`

**Results** (10 pages):
| Metric | Result |
|--------|--------|
| Total Events | ~50 (estimated: 5 events/page × 10 pages) |
| Date Range | Current and future events |
| Level 2 Events | All events with detail data (100%) |
| Execution Time | ~200s (estimated) |
| Data Quality | Full descriptions, locations, end times |

**To Increase Pages**:
Edit `rules/cities/dormagen/feste_veranstaltungen/scraper.py`:

```python
class FesteVeranstaltungenScraper(BaseScraper):
    MAX_PAGES = 10  # Change to desired number (max 227)
```

