"""Monheim.de-specific scraper - optimized for event calendar."""

from typing import Optional
import urllib.parse

from .base import BaseScraper, _clean_text


class MonheimScraper(BaseScraper):
    """Scraper for Monheim event pages."""

    def _fetch_terminkalender(self) -> str:
        """Fetch terminkalender events with better text extraction."""
        url = "https://www.monheim.de/freizeit-tourismus/terminkalender"
        params = {
            "tx_ewsdwhevents_events[action]": "searchResult",
            "tx_ewsdwhevents_events[controller]": "Events",
        }

        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "WeeklyMail/1.0"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "form", "select", "option", "input", "label"]):
            tag.decompose()

        for tag in soup.find_all("div"):
            classes = tag.get("class")
            if classes and isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes if c).lower()
                if any(kw in class_str for kw in ["nav", "menu", "filter", "pagination", "search", "sort"]):
                    tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        lines = []
        skip_sections = ["Kalenderübersicht", "Freitextsuche", "Kategorien", "Veranstaltungsorte", "Suche", "Terminvorschläge", "Auswahl", "Häufig gesucht", "Ihr Bild auf Monheim.de"]

        for line in all_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if any(skip_word in line for skip_word in skip_sections):
                continue

            if len(line) < 5:
                continue

            if line in lines:
                continue

            lines.append(line)

        cleaned_text = "\n".join(lines)

        return _clean_text(cleaned_text, max_chars=25000)

    def _fetch_with_playwright(self) -> str:
        """Fetch content using Playwright for dynamic pages."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Monheim scraper. "
                "Install with: pip install playwright && playwright install chromium"
            )

        CLICK_SELECTORS = [
            'button:has-text("Mehr laden")',
            'button:has-text("Mehr")',
            'a:has-text("Mehr anzeigen")',
            'button:has-text("Weiter")',
            '.ews-dwh-events button[class*="load"]',
            'button[class*="load-more"]',
        ]

        WAIT_FOR_SELECTORS = [
            '.ews-dwh-events .event-item',
            '.event-list .event',
            '[class*="event"][class*="item"]',
            '.ews-dwh-events',
        ]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")

            for selector in CLICK_SELECTORS:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        page.click(selector)
                        page.wait_for_timeout(1000)
                except Exception:
                    continue

            for wait_selector in WAIT_FOR_SELECTORS:
                try:
                    page.wait_for_selector(wait_selector, timeout=5000)
                    break
                except Exception:
                    continue

            content = page.content()
            browser.close()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text, max_chars=25000)

    @property
    def needs_browser(self) -> bool:
        """Monheim site requires Playwright for dynamic content."""
        return True

    def fetch(self) -> str:
        """Fetch content based on URL type."""
        if "terminkalender" in self.url.lower():
            return self._fetch_terminkalender()
        else:
            return self._fetch_with_playwright()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheim event pages."""
        return "monheim.de" in url and (
            "veranstaltungen" in url.lower() or "terminkalender" in url.lower()
        )
