# Scrapers Module

This module contains URL-specific scrapers with different logic for different sites.

## Structure

```
scrapers/
├── __init__.py       # Empty init file
├── base.py           # BaseScraper abstract class
├── static.py         # Default static HTML scraper (requests + BeautifulSoup)
├── monheim.py        # Monheim.de-specific scraper (Playwright for dynamic content)
└── registry.py       # URL-to-scraper mapping
```

## Adding a New Scraper

1. Create a new file (e.g., `mycity.py`):
```python
from .base import BaseScraper

class MyCityScraper(BaseScraper):
    """Scraper for MyCity event pages."""

    @property
    def needs_browser(self) -> bool:
        # Return True if you need Playwright/Selenium
        return False

    def fetch(self) -> str:
        # Implement your custom fetch logic
        # Can use self._fetch_with_requests() for static sites
        # Or Playwright for dynamic sites
        pass

    @classmethod
    def can_handle(cls, url: str) -> bool:
        # Return True if this scraper should handle the URL
        return "mycity.de" in url
```

2. Register it in `registry.py`:
```python
from .mycity import MyCityScraper

_SCRAPER_CLASSES = [
    MyCityScraper,  # Add at top for priority
    MonheimScraper,
    StaticScraper,
]
```

## Priority

Scrapers are checked in order. First match wins. Place more specific scrapers before generic ones.

## Browser Requirements

- Set `needs_browser = True` if your scraper uses Playwright
- The base class doesn't enforce this - it's metadata for callers
