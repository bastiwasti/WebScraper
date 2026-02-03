"""Scraper for Hilden veranstaltungen website."""

from rules.base import BaseScraper


class HildenScraper(BaseScraper):
    """Scraper for Hilden veranstaltungen page.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def fetch(self) -> str:
        """Fetch content from veranstaltungen URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
