# Monheim (Marienburg Events) - Autonomous Scraper Implementation

## Task Info

**User Input:**
- Full URL: https://marienburgmonheim.de/de/events
- City Name: Monheim

**Pattern Detected:**
- Pattern 5: Static + Pagination
- Secondary: Pattern 3: Static + 2-Level

## Implementation Details

### Files Created

1. **rules/cities/monheim/marienburg_events/scraper.py**
   - Class: `MarienburgEventsScraper`
   - Fetches static HTML with pagination (2 pages)
   - Uses standard requests library

2. **rules/cities/monheim/marienburg_events/regex.py**
   - Class: `MarienburgEventsRegex`
   - HTML-based parsing using BeautifulSoup
   - Level 2: Fetches detail pages for enhanced data

3. **rules/cities/monheim/marienburg_events/__init__.py**
   - Empty init file for Python package

4. **investigation_monheim.md**
   - Phase 2 investigation report
   - Documents HTML structure, pagination, data sources

5. **rules/urls.py** (modified)
   - Added: `"monheim": {"marienburg_events": "https://marienburgmonheim.de/de/events"}`

## Test Results

### Test Command
```bash
python3 main.py --url "https://marienburgmonheim.de/de/events" --no-db --verbose
```

### Validations
- [x] URL registered in `rules/urls.py`
- [x] Scraper discovered automatically by registry
- [x] Events extracted: 18 events
- [x] All required fields populated:
  - name: ✓ All events have names
  - date: ✓ All events have dates (DD.MM.YYYY format)
  - time: ✓ All events have times (HH:MM format)
  - location: ✓ All events have locations
  - description: ✓ All events have descriptions from detail pages
  - source: ✓ All events have source URLs
- [x] Category inferred correctly:
  - culture: 6 events (Konzerte, Führungen, Brunch)
  - festival: 2 events (Grillfestival, Magische Marienburg)
  - other: 5 events (Grillen, Brunch, OFYR events)
  - community: 1 event (Vormittag auf dem Marienhof)
  - education: 1 event (Grillseminar)
  - nature: 1 event (Sparkling Spring)
  - adult: 1 event (Magische Marienburg Vol. 9)
- [x] Level 2 scraping successful: 18/18 events with detail data
- [x] Pagination verified: Page 1 has 12 events, Page 2 has 6 events

### Event Examples

1. **Vormittag auf dem Marienhof**
   - Date: 03.03.2026
   - Time: 10:00 - 12:00
   - Location: Parkplatz der Marienburg Monheim (Bleer Str. 33)
   - Category: community
   - Source: https://marienburgmonheim.de/de/events/details/vormittag-auf-dem-marienhof

2. **Grillfestival 2026**
   - Date: 25.04.2026
   - Time: 11:00
   - Location: Marienburg Monheim, Bleer Str. 33, 40789 Monheim am Rhein
   - Category: festival
   - Source: https://marienburgmonheim.de/de/events/details/grillfestival-2026

3. **Osterbrunch am Sonntag**
   - Date: 05.04.2026
   - Time: 11:00
   - Location: Marienburg Monheim, Bleer Str. 33, 40789 Monheim am Rhein
   - Category: other
   - Source: https://marienburgmonheim.de/de/events/details/osterbrunch-am-sonntag-2

## Self-Correction Attempts

### Attempt 1
**Issue:** `name 'requests' is not defined` error in `regex.py`

**Fix:** Added missing `import requests` statement at the top of `regex.py`

**Result:** ✓ Fixed, scraper now fetches detail pages correctly

## Issues Encountered

| Issue | Severity | Fix Applied | Status |
|-------|-----------|-------------|--------|
| Missing `requests` import in regex.py | Critical | Added `import requests` | ✓ Resolved |
| Type errors with BeautifulSoup attributes | Low | Added `str()` casts for attributes | ✓ Resolved |
| Duplicate events (same event name) | Low | Differentiated by detail URL | ✓ Resolved |

## Final Status

✅ **SUCCESS**

- URL: https://marienburgmonheim.de/de/events
- Events Extracted: 18
- Pattern: Pattern 5 (Static + Pagination) + Pattern 3 (Static + 2-Level)
- Files Created: 3 files (scraper.py, regex.py, __init__.py)
- Investigation File: investigation_monheim.md
- Level 2 Success Rate: 18/18 (100%)
- Execution Time: 29.50s
- Registry: Auto-discovered successfully

## Recommendations

1. **Monitor Pagination**: The site currently has 2 pages with 18 events total. Monitor for new events and adjust `MAX_PAGES` if more pages are added.

2. **Category Tuning**: Consider adding custom category keywords for Marienburg-specific events like "Grillfestival" (already matches "festival") and "Marienhof" events (could be "family" or "education").

3. **Time Format**: Some events have time ranges (e.g., "10:00 - 12:00") extracted correctly from detail pages. Ensure this is consistent across all events.

## Next Steps

1. Run full scraper test with database writing enabled:
   ```bash
   python3 main.py --url "https://marienburgmonheim.de/de/events" --verbose
   ```

2. Verify database records are saved correctly:
   ```bash
   python3 main.py --list-runs
   ```

3. Test with other Monheim URLs if needed (currently only marienburgmonheim.de is implemented)

4. Consider implementing additional Marienburg event sources if found (e.g., other sections of the marienburgmonheim.de website)
