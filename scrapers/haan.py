"""Haan.de-specific scraper - handles culture and leisure event listings."""

from typing import Optional

from .base import BaseScraper, _clean_text


class HaanScraper(BaseScraper):
    """Scraper for Haan event pages."""

    def _fetch_kulturkalender(self) -> str:
        """Fetch Kulturkalender events with better text extraction."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            self.url,
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
                if any(kw in class_str for kw in ["nav", "menu", "filter", "pagination", "search", "cookie", "consent"]):
                    tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        lines = []
        skip_sections = ["Startseite", "Kultur & Freizeit", "Freizeit & Sport", "Veranstaltungen", "Tickets buchen", "+ mehr Infos", "Sprungziele", "Hauptmenü", "Untermenü", "Kurzmenü", "Volltextsuche", "Datenschutzerklärung", "Einverstanden", "Ausblenden", "Stadt & Rathaus", "Familie & Bildung", "Soziales & Integration", "Wirtschaft & Stadtentwicklung"]

        for line in all_text.split("\n"):
            line = line.strip()
            if not line:
                continue

            if any(skip_word in line for skip_word in skip_sections):
                continue

            if len(line) < 3:
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
                "Playwright is required for Haan scraper. "
                "Install with: pip install playwright && playwright install chromium"
            )

        CLICK_SELECTORS = [
            'a[href*="event"]',
            'a[href*="termin"]',
            '.event-item a',
            '.event-card',
            '.calendar-day',
        ]

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
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text, max_chars=25000)

    @property
    def needs_browser(self) -> bool:
        """Haan site may need browser for dynamic content."""
        return False

    def fetch(self) -> str:
        """Fetch content based on URL type."""
        if "kultur" in self.url.lower() and "veranstaltungen" in self.url.lower():
            return self._fetch_kulturkalender()
        else:
            return self._fetch_with_playwright()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Haan event pages."""
        return "haan.de" in url and (
            "kultur" in url.lower() or "freizeit" in url.lower() or "veranstaltungen" in url.lower()
        )
