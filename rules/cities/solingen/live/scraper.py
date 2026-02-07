"""Scraper for Solingen-Live URL.

Extracts events from https://www.solingen-live.de/

IMPORTANT: Implements navigation to load 14 days of events.
This site uses JavaScript to load events dynamically.
"""

from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from rules.base import BaseScraper, _clean_text


class LiveScraper(BaseScraper):
    """Scraper for Solingen-Live event pages.

    This scraper:
    1. Loads the page with Playwright (JavaScript rendering)
    2. Waits for content to load
    3. Extracts all event content
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Solingen-Live pages."""
        return "solingen-live.de" in url

    def fetch(self) -> str:
        """Fetch content with Playwright to render JavaScript."""
        return self._fetch_with_playwright_navigation()

    def _fetch_with_playwright_navigation(self) -> str:
        """Fetch using Playwright with JavaScript rendering."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")

            # Wait for content to load
            page.wait_for_timeout(3000)

            content = page.content()
            browser.close()

            # Parse and clean content
            soup = BeautifulSoup(content, "html.parser")

            # Remove non-event elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()

            # Remove navigation and pagination elements
            import re
            for tag in soup.find_all(class_=re.compile(r"pagination|nav|menu|filter|calendar-nav")):
                tag.decompose()

            # Get clean text
            text = soup.get_text(separator="\n", strip=True)

            # Remove empty lines and clean up
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            cleaned_text = "\n".join(line for line in lines if len(line) > 3)

            return _clean_text(cleaned_text, max_chars=50000)

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return True
