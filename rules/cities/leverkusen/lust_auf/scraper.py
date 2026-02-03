"""Scraper for Lust-Auf-Leverkusen website."""

from rules.base import BaseScraper


class LustAufScraper(BaseScraper):
    """Scraper for Lust-Auf-Leverkusen website.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf-Leverkusen pages."""
        return "lust-auf-leverkusen.de" in url

    def fetch(self) -> str:
        """Fetch content from lust-auf-leverkusen URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
