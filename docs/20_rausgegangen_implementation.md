# Rausgegangen Aggregator Implementation

## Overview

This document describes the implementation of the rausgegangen.de aggregator using a hybrid scraping approach (Level 1 + Level 2).

## Architecture

### Directory Structure
```
rules/
  aggregators/
    __init__.py
    rausgegangen/
      __init__.py
      scraper.py      # Hybrid scraper (Level 1 + Level 2)
      regex.py        # Minimal parser (fallback only)
```

### Hybrid Approach

**Level 1: Event URL Extraction**
- Uses Playwright to load the city page
- Extracts event detail page URLs from HTML
- URL pattern: `/events/{slug}/` or `/en/events/{slug}/`
- Fixed 20km radius via URL parameters

**Level 2: Event Detail Fetching**
- Fetches each event detail page via requests
- Extracts JSON-LD schema (`<script type="application/ld+json">`)
- Parses structured data: name, dates, location, price

## City Mapping

### Configuration (`rules/utils.py`)

```python
AGGREGATOR_CITY_MAPPING = {
    "monheim am rhein": "monheim",
    "leverkusen": "leverkusen",
    "langenfeld": "langenfeld",
    "hilden": "hilden",
    "dormagen": "dormagen",
    "burscheid": "burscheid",
    "leichlingen": "leichlingen",
    "hitdorf": "hitdorf",
    "ratingen": "ratingen",
    "solingen": "solingen",
    "haan": "haan",
    "düsseldorf": "dusseldorf",
    "köln": "koeln",
}
```

### Function

```python
def map_aggregator_city(raw_city: str, default_city: str = "") -> str
```

Maps city names from aggregators to internal normalized names.

## Usage

### Command Line

```bash
# Run rausgegangen aggregator for monheim
python3 main.py --url rausgegangen/monheim

# Run with city sites only
python3 main.py --cities monheim

# Run all (includes aggregators)
python3 main.py --agent all
```

### URL Resolution

The `resolve_url()` function in `main.py` now supports:
- Full URLs: `https://rausgegangen.de/...`
- Folder names: `rausgegangen/monheim`
- Aggregator names: `rausgegangen` (returns first URL)

## Registry Integration

### Configuration (`rules/urls.py`)

```python
AGGREGATOR_URLS: Dict[str, Dict[str, str]] = {
    "rausgegangen": {
        "monheim": "https://rausgegangen.de/monheim-am-rhein/?radius=20000&lat=51.08713514258467&lng=6.884078972507269&city=monheim-am-rhein&geospatial_query_type=CENTER_AND_RADIUS",
    },
}
```

### Discovery (`rules/registry.py`)

The `_discover_rules()` function now:
1. Discovers city rules from `rules/cities/*/`
2. Discovers aggregator rules from `rules/aggregators/*/`
3. Registers all URLs with their scraper/regex classes

## Event Data Structure

### Example Event

```python
{
    "name": "Werkstatt-Angebot im Sojus 7",
    "description": "Another screw loose? Then quickly head to...",
    "location": "Sojus 7, Kapellenstraße 36 – 40",
    "date": "17.02.2026",
    "time": "16:00",
    "end_time": "20:00",
    "source": "https://rausgegangen.de/en/events/fahrradwerkstatt-209/",
    "category": "other",
    "city": "monheim",
    "event_url": "https://rausgegangen.de/en/events/fahrradwerkstatt-209/",
    "raw_data": {
        "url": "https://rausgegangen.de/en/events/fahrradwerkstatt-209/",
        "json_ld": { ... },  # JSON-LD schema data
        "html": "..."  # Full HTML of detail page
    }
}
```

## Logging

The scraper uses both `logger` and `print`:

- **Logger**: For scheduled runs (logged to `logs/scrape_*.log`)
- **Print**: For initial testing and debugging

Example log output:
```
[02/17/26 21:43:45] INFO     [Rausgegangen] Starting hybrid scraper for: ...
[Rausgegangen] Starting hybrid scraper for: ...
[02/17/26 21:43:48] INFO     [Rausgegangen] Found 401 event URLs
[Rausgegangen] Found 401 event URLs
[02/17/26 21:43:49] INFO     [Rausgegangen] Fetching event 1/401: ...
[Rausgegangen] Fetching event 1/401: ...
[02/17/26 21:43:50] INFO     [Rausgegangen] ✓ Successfully extracted data from ...
[Rausgegangen] ✓ Successfully extracted data from ...
```

## Deduplication

**Status: Not implemented** (as per user request)

Deduplication will be handled in the frontend application, not in the scraper layer. This keeps raw data intact and provides flexibility in how duplicates are handled.

## Testing

### Unit Tests

Suggested test files:

1. `tests/test_utils.py` - Test city mapping
2. `tests/test_rausgegangen.py` - Test URL patterns, JSON-LD extraction

### Integration Tests

```bash
# Test registry registration
python3 -c "from rules.registry import list_registered_rules; print(list_registered_rules())"

# Test URL resolution
python3 -c "from main import resolve_url; print(resolve_url('rausgegangen/monheim'))"

# Test city mapping
python3 -c "from rules.utils import map_aggregator_city; print(map_aggregator_city('Monheim am Rhein', 'monheim'))"

# Run scraper
python3 main.py --url rausgegangen/monheim --agent scraper
```

## Limitations

1. **Performance**: Fetching 400+ detail pages sequentially is slow
2. **No Rate Limiting**: Does not implement rate limiting or delays between requests
3. **No Caching**: Event detail pages are fetched fresh each time
4. **20km Radius Fixed**: Hardcoded, not configurable via CLI

## Future Enhancements

1. **Parallel Fetching**: Use `asyncio` or thread pool for Level 2 fetching
2. **Rate Limiting**: Add configurable delays between requests
3. **Caching**: Cache event detail pages with TTL
4. **Configurable Radius**: Allow radius parameter via CLI
5. **Incremental Fetching**: Fetch only new/updated events based on dates
6. **Error Handling**: Implement retry logic for failed requests

## Files Modified/Created

### Created (4)
- `rules/aggregators/__init__.py`
- `rules/aggregators/rausgegangen/__init__.py`
- `rules/aggregators/rausgegangen/scraper.py`
- `rules/aggregators/rausgegangen/regex.py`

### Modified (3)
- `rules/urls.py` - Added `AGGREGATOR_URLS` + updated `get_all_urls()`
- `rules/registry.py` - Added aggregator discovery logic
- `rules/utils.py` - Added `AGGREGATOR_CITY_MAPPING` + `map_aggregator_city()`
- `main.py` - Updated `resolve_url()` for aggregator syntax

## Summary

The rausgegangen aggregator is fully functional with:

- ✅ Hybrid scraping (Level 1 + Level 2)
- ✅ 20km radius (fixed for Monheim)
- ✅ City mapping for aggregator sources
- ✅ JSON-LD schema extraction
- ✅ Compatible with existing rules system
- ✅ **No deduplication** (frontend responsibility)

Total implementation: ~400 lines of code across 7 files.
