"""Scraper for Monheimer Kulturwerke calendar URL."""

from typing import Optional

from rules.base import BaseScraper


class KulturwerkeScraper(BaseScraper):
    """Scraper for Monheimer Kulturwerke event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url

    def fetch(self) -> str:
        """Fetch content from Kulturwerke URL.

        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
