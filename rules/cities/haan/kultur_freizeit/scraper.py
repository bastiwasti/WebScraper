"""Scraper for Haan Kultur-Freizeit URL."""

from typing import Optional

from rules.base import BaseScraper


class HaanScraper(BaseScraper):
    """Scraper for Haan event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Haan event pages."""
        return "haan.de" in url and "Veranstaltungen" in url

    def fetch(self) -> str:
        """Fetch content from Haan URL.

        Uses standard requests for static HTML.
        """
        return self._fetch_with_requests()
