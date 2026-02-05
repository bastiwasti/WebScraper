"""Scraper for Solingen-Live URL."""

from typing import Optional

from rules.base import BaseScraper


class SolingenScraper(BaseScraper):
    """Scraper for Solingen-Live event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Solingen-Live pages."""
        return "solingen-live.de" in url

    def fetch(self) -> str:
        """Fetch content from Solingen-Live URL.

        Uses standard requests for static HTML.
        """
        return self._fetch_with_requests()
