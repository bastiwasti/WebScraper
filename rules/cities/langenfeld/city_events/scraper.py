"""Scraper for Langenfeld city events URL."""

from typing import Optional
import requests

from rules.base import BaseScraper


class CityEventsScraper(BaseScraper):
    """Scraper for Langenfeld city event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Langenfeld city event pages."""
        return "langenfeld.de" in url and "Veranstaltungen.htm" in url

    def fetch(self) -> str:
        """Fetch content from Langenfeld city events URL.

        Uses standard requests for Active-City CMS content.
        Returns raw HTML for HTML-based parsing.
        """
        return self._fetch_raw_html()

    def _fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        Returns full HTML with all elements intact.
        """
        try:
            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()
            print(f"[CityEvents] Fetched {len(resp.text)} chars of raw HTML")
            return resp.text
        except Exception as e:
            print(f"[CityEvents] Failed to fetch HTML: {e}")
            raise

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        This is used by regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        return self._fetch_raw_html()
