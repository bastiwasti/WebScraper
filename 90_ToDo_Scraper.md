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

---

## Scrapers Requiring 2-Level Integration

| City | Subfolder | URL | Why Needs 2-Level? | Implementation Notes |
|-------|-----------|-----|---------------------|--------------------|
| **Langenfeld** | city_events | https://www.langenfeld.de/Startseite/Aktuelles-und-Information/Veranstaltungen.htm | Links to detail pages | Check if detail pages exist, extract URLs, fetch |
| **Langenfeld** | schauplatz | https://schauplatz.de/ | Event pages may have more details | Similar to Langenfeld city_events |
| **Haan** | kultur_freizeit | https://www.haan.de/Kultur-Freizeit/Veranstaltungen | Richer detail data possible | Check for individual event links |
| **Leverkusen** | lust_auf | https://lust-auf-leverkusen.de/ | Event detail pages | Check if individual event pages exist |
| **Leverkusen** | stadt_erleben | https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/ | Calendar structure | May need detail page extraction |
| **Hilden** | veranstaltungen | https://www.hilden.de/de/veranstaltungen/ | Detail pages exist | Check for event detail links |
| **Ratingen** | veranstaltungskalender | https://www.stadt-ratingen.de/kultur-und-tourismus/kulturprogramm-aktuell | Rich calendar data | May have individual event pages |
| **Solingen** | live | https://live.solingen.de/ | Event pages | Check for detail page links |
| **Dormagen** | - | - | Needs scraper first | Implement Level 1, then add Level 2 |

## Scrapers Already Supporting 2-Level

| City | Subfolder | Status |
|-------|-----------|--------|
| Monheim | terminkalender | ✅ Complete |
| Monheim | kulturwerke | ❌ No detail pages |

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

1. **Extract detail URLs**:
   - Parse Level 1 HTML to find links to detail pages
   - Create mapping: event_name → detail_url

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
   - For 50 events = ~2 minutes additional time
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

## Implementation Checklist

For each scraper:

- [ ] Analyze calendar page structure
- [ ] Identify detail page links
- [ ] Extract detail URL mapping
- [ ] Implement `fetch_level2_data()` in regex.py
- [ ] Parse detail pages (extract location, description, end_time)
- [ ] Merge Level 2 data with Level 1 events
- [ ] Test Level 2 scraping
- [ ] Verify database storage
- [ ] Update documentation in 20_setup_guide.md (Working Scrapers Reference)

## When Complete

When all scrapers support 2-level scraping (or are evaluated as not suitable), this file can be deleted.

---

## See Also

- [refactor_scraping.md](refactor_scraping.md) - Monheim terminkalender 2-level implementation
- [20_setup_guide.md](20_setup_guide.md) - Complete scraper setup instructions
- [10_agent_guide.md](10_agent_guide.md) - URL rules system documentation
