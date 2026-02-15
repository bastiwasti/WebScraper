"""Scraper for Monheimer Kulturwerke calendar URL."""

import requests
from typing import Optional

from rules.base import BaseScraper


class KulturwerkeScraper(BaseScraper):
    """Scraper for Monheimer Kulturwerke event pages."""

    DISABLE_LEVEL_2 = True  # Skip Level 2 to avoid timeout (121 events × sequential requests = 30+ minutes)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url

    @property
    def needs_browser(self) -> bool:
        """This scraper uses HTTP requests (no browser needed)."""
        return False

    def _fetch_with_requests(self) -> str:
        """Fetch content using requests and return raw HTML.
        
        Returns raw HTML for HTML-based parsing.
        """
        try:
            import requests as req
            resp = req.get(
                self.url,
                timeout=30,
                headers={"User-Agent": "WeeklyMail/1.0"}
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            print(f"[Kulturwerke Scraper] Failed to fetch with requests: {e}")
            raise

    def fetch(self) -> str:
        """Fetch content from Kulturwerke URL.

        Uses HTTP requests (faster, no JavaScript needed).
        Returns raw HTML for HTML-based parsing.
        """
        content = self._fetch_with_requests()
        print(f"[Kulturwerke Scraper] Fetched {len(content)} chars of raw HTML")
        return content
    
    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from Kulturwerke URL.
        
        This is used by the regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        return self._fetch_with_requests()
