"""Scraper for Burscheid event calendar API."""

from typing import Optional
import requests

from rules.base import BaseScraper


class VeranstaltungskalenderScraper(BaseScraper):
    """Scraper for Burscheid event calendar via bergisch-live.de API."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Burscheid Veranstaltungskalender pages."""
        return "burscheid.de" in url and "veranstaltungskalender" in url

    def fetch(self) -> str:
        """Fetch content from Burscheid API.

        Uses bergisch-live.de API which returns HTML with event data.
        Returns raw HTML for HTML-based parsing.
        """
        # Extract client from URL or default to burscheid.de
        client = "burscheid.de"
        
        # Build API URL
        api_url = f"https://www.bergisch-live.de/events/what=All;client={client}"
        
        try:
            resp = requests.get(
                api_url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()
            print(f"[Burscheid] Fetched {len(resp.text)} chars of HTML from API")
            return resp.text
        except Exception as e:
            print(f"[Burscheid] Failed to fetch HTML: {e}")
            raise
