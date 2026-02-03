"""Haan rule parser - fetch and parse Haan event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class HaanRuleParser(BaseRuleParser):
    """Parser for Haan event pages."""

    @property
    def needs_browser(self) -> bool:
        """Haan site requires Playwright for dynamic content."""
        return True

    def fetch(self) -> str:
        """Fetch content using Playwright for dynamic calendar."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Haan scraper. "
                "Install with: pip install playwright && playwright install chromium"
            )

        WAIT_FOR_SELECTORS = [
            '.event-list',
            '.event-item',
            '[class*="event"]',
            '.veranstaltung',
            '.kalender',
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")

            for selector in WAIT_FOR_SELECTORS:
                try:
                    page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue

            content = page.content()
            browser.close()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Haan events."""
        patterns = [
            re.compile(r'Event:\s*(.+?)\s*Date:\s*(.+?)', re.DOTALL),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Haan regex match."""
        name = match[0].strip() if len(match) > 0 else ""
        date = match[1].strip() if len(match) > 1 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location="",
            date=date,
            time="",
            source="haan.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Haan event pages."""
        return "haan.de" in url
