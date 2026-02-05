"""Scraper for Langenfeld city events URL."""

from typing import Optional

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
        """
        return self._fetch_with_requests()
