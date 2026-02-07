"""Scraper for Ratingen veranstaltungskalender website."""

from rules.base import BaseScraper


class VeranStaltungskalenderScraper(BaseScraper):
    """Scraper for Ratingen veranstaltungskalender page.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen pages."""
        return "ratingen.de" in url and "veranstaltungskalender" in url

    def fetch(self) -> str:
        """Fetch content from veranstaltungskalender URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
