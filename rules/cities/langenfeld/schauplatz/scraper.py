"""Scraper for Schauplatz Langenfeld URL."""

from typing import Optional

from rules.base import BaseRule


class SchauplatzScraper(BaseRule):
    """Scraper for Schauplatz event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Schauplatz pages."""
        return "schauplatz.de" in url

    def fetch(self) -> str:
        """Fetch content from Schauplatz URL.

        Uses standard requests for WordPress + Ztix content.
        """
        return self._fetch_with_requests()
