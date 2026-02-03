"""Scraper for Leverkusen stadt-erleben calendar."""

from rules.base import BaseScraper


class StadtErlebenScraper(BaseScraper):
    """Scraper for Leverkusen stadt-erleben calendar page.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt-erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def fetch(self) -> str:
        """Fetch content from stadt-erleben calendar URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
