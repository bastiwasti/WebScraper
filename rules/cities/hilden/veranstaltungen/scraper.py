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
        """
        json_url = "https://www.hilden.de/de/kalender/veranstaltungen/jahre/events.json?weekends=false&tagMode=ANY"
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        return response.text

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from main Hilden veranstaltungen page.
        
        Returns full HTML for potential use in Level 2 scraping.
        """
        response = requests.get(
            self.url,
            timeout=30,
            headers={"User-Agent": "WeeklyMail/1.0"}
        )
        response.raise_for_status()
        return response.text
