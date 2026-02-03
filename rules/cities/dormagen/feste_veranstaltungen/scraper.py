"""Scraper for Dormagen feste-veranstaltungen website."""

from rules.base import BaseScraper


class DormagenScraper(BaseScraper):
    """Scraper for Dormagen feste-veranstaltungen page.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url

    def fetch(self) -> str:
        """Fetch content from feste-veranstaltungen URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
