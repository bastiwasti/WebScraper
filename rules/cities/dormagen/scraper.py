"""Scraper for Dormagen (placeholder - URL needs verification)."""

from typing import Optional

from rules.base import BaseScraper


class DormagenScraper(BaseScraper):
    """Scraper for Dormagen event pages (placeholder)."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url

    def fetch(self) -> str:
        """Fetch content from Dormagen URL."""
        return self._fetch_with_requests()
