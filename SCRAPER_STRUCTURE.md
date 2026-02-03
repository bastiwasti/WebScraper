# WebScraper URL-Specific Scraper Structure

## Overview

The scraper module now supports per-URL scraping logic, allowing different strategies for different websites.

## Architecture

```
scrapers/
├── __init__.py           # Empty init
├── base.py               # BaseScraper abstract class
├── static.py             # Default static HTML scraper (requests + BeautifulSoup)
├── monheim.py           # Monheim.de scraper (optimized for terminkalender)
├── registry.py           # URL → scraper mapping
└── README.md            # Documentation
```

## How It Works

1. **Registry Pattern:** `get_scraper(url)` returns the appropriate scraper instance
2. **Priority-Based:** Scrapers checked in order, first match wins
3. **Extensible:** Add new scrapers by creating a class and registering it

## Monheim Scraper - Details

**URL Pattern:** `monheim.de` with `veranstaltungen` or `terminkalender`

**Strategy:**
- For `terminkalender`: Uses TYPO3 extension searchResult action API
- For other URLs: Falls back to Playwright for dynamic content

**Results:** Successfully extracts 27 events with:
- Full date/time: "Dienstag, 03. Februar 2026 16.00 Uhr"
- Event names: "Chorproben für Kinder, Jugendliche und Erwachsene"
- Categories: "Kategorie: Familie, Jugend, Kinder, Musik"
- Locations: "Beim Bunten Chor Monheim"

## Adding a New Scraper

1. Create file: `scrapers/mycity.py`
```python
from .base import BaseScraper

class MyCityScraper(BaseScraper):
    @property
    def needs_browser(self) -> bool:
        return True  # or False

    def fetch(self) -> str:
        # Implement your custom fetch logic
        pass

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "mycity.de" in url
```

2. Register in `scrapers/registry.py`:
```python
from .mycity import MyCityScraper

_SCRAPER_CLASSES = [
    MyCityScraper,  # Add at top for priority
    MonheimScraper,
    StaticScraper,
]
```

3. Update `agents/tools.py`:
   - `fetch_page(url)` already uses `get_scraper(url)`, no changes needed
   - Scraper automatically routes to correct handler

## Current Scrapers

| Scraper | URL Pattern | Method | Needs Browser |
|----------|-------------|---------|--------------|
| MonheimScraper | monheim.de/\*(veranstaltungen\|terminkalender) | API/Playwright | Yes (optional) |
| StaticScraper | all http/https URLs | requests + BeautifulSoup | No |

## Dependencies

- `requirements.txt` includes: `playwright>=1.40.0`
- Install Playwright browsers: `playwright install chromium`

## Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Test Monheim scraper
python3 -c "
from scrapers.registry import get_scraper
scraper = get_scraper('https://www.monheim.de/freizeit-tourismus/terminkalender')
content = scraper.fetch()
print(f'Got {len(content)} characters')
"
```
