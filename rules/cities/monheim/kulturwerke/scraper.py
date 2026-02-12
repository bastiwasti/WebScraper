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

    def _fetch_with_playwright(self) -> str:
        """Fetch content using Playwright and return raw HTML.
        
        Returns raw HTML instead of cleaned text for HTML-based parsing.
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.url, wait_until="networkidle")
                
                html_content = page.content()
                browser.close()
                
                return html_content
        except Exception as e:
            print(f"[Kulturwerke Scraper] Failed to fetch with Playwright: {e}")
            raise

    def fetch(self) -> str:
        """Fetch content from Kulturwerke URL.

        Uses Playwright for JavaScript-rendered SPA content.
        Returns raw HTML for HTML-based parsing.
        """
        content = self._fetch_with_playwright()
        print(f"[Kulturwerke Scraper] Fetched {len(content)} chars of raw HTML")
        return content
    
    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from Kulturwerke URL.
        
        This is used by the regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        return self._fetch_with_playwright()
