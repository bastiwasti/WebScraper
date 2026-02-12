"""Scraper for Monheimer Kulturwerke calendar URL."""

from typing import Optional

from playwright.sync_api import sync_playwright
from rules.base import BaseScraper


class KulturwerkeScraper(BaseScraper):
    """Scraper for Monheimer Kulturwerke event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url

    @property
    def needs_browser(self) -> bool:
        """This scraper needs a browser to execute JavaScript."""
        return True

    def fetch(self) -> str:
        """Fetch content from Kulturwerke URL.

        Uses Playwright for JavaScript-rendered SPA content.
        """
        content = self._fetch_with_playwright()
        print(f"[Kulturwerke Scraper] Fetched {len(content)} chars")
        return content
