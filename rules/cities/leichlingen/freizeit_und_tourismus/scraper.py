"""Scraper for Leichlingen city events URL."""

from typing import Optional
import requests

from rules.base import BaseScraper


class FreizeitUndTourismusScraper(BaseScraper):
    """Scraper for Leichlingen city event pages.
    
    The Leichlingen page uses a JavaScript widget that loads events from
    bergisch-live.de. We fetch directly from the bergisch-live API endpoint.
    
    The what=All parameter returns all 58 available events.
    Level 2 detail pages are Facebook redirects and provide no additional data.
    """

    # Disable Level 2 - detail pages are Facebook redirects with no event data
    DISABLE_LEVEL_2 = True

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leichlingen city event pages."""
        return "leichlingen.de" in url and "freizeit-und-tourismus/veranstaltungen" in url

    def fetch(self) -> str:
        """Fetch content from Leichlingen city events URL.

        The Leichlingen page uses a JavaScript widget that loads events from
        bergisch-live.de. We fetch directly from the bergisch-live API endpoint.
        The what=All parameter returns all 58 available events.

        Returns raw HTML for HTML-based parsing.
        """
        return self._fetch_raw_html()

    def _fetch_raw_html(self) -> str:
        """Fetch raw HTML content from bergisch-live.de API.
        
        The Leichlingen website uses a JavaScript widget from bergisch-live.de
        to display events. We fetch directly from the API endpoint.
        
        The what=All parameter returns all available events (no pagination needed).
        
        Returns full HTML with all elements intact.
        """
        bergisch_url = "https://www.bergisch-live.de/events/what=All;client=leichlingen.de"
        
        try:
            resp = requests.get(
                bergisch_url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()
            print(f"[FreizeitUndTourismus] Fetched {len(resp.text)} chars of raw HTML from bergisch-live.de")
            return resp.text
        except Exception as e:
            print(f"[FreizeitUndTourismus] Failed to fetch HTML: {e}")
            raise

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        This is used by regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        return self._fetch_raw_html()
