"""Scraper for Hilden veranstaltungen website."""

import requests
import json
from rules.base import BaseScraper

class HildenScraper(BaseScraper):
    """Scraper for Hilden veranstaltungen page.
    
    Uses JSON API instead of HTML scraping.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def fetch(self) -> str:
        """Fetch events from Hilden JSON API.
        
        JSON API endpoint returns structured event data.
        Returns empty string if no events found.
        Limits to first 50 events to avoid token overflow.
        """
        json_url = "https://www.hilden.de/de/kalender/veranstaltungen/jahre/events.json?weekends=false&tagMode=ANY"
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON
        try:
            events = json.loads(response.text)
        except json.JSONDecodeError:
            # Return raw JSON if parsing fails
            return response.text
        
        # Limit to first 50 events
        events = events[:50]
        
        # Don't format as text - return raw JSON for analyzer to parse
        # This is needed for proper event extraction
        return response.text
