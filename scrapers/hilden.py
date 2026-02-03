"""Hilden.de-specific scraper - URL needs verification (404 error on /kultur-freizeit/veranstaltungen)."""

from .base import BaseScraper, _clean_text


class HildenScraper(BaseScraper):
    """Scraper for Hilden event pages."""

    @property
    def needs_browser(self) -> bool:
        """Hilden site may need browser."""
        return False

    def fetch(self) -> str:
        """Fetch content - URL needs verification."""
        import requests
        from bs4 import BeautifulSoup

        try:
            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text, max_chars=25000)
        except Exception as e:
            return f"Failed to fetch Hilden URL {self.url}: {e}. Please verify the URL is correct."

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden event pages."""
        return "hilden.de" in url
