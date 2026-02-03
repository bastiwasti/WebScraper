"""Default static HTML scraper - fallback for all URLs."""

from .base import BaseScraper


class StaticScraper(BaseScraper):
    """Standard scraper using requests + BeautifulSoup for static HTML pages."""

    def fetch(self) -> str:
        """Fetch static HTML content."""
        return self._fetch_with_requests()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Can handle any HTTP/HTTPS URL (fallback)."""
        return url.startswith(("http://", "https://"))
