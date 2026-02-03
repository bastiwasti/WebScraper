"""Solingen-Live.de-specific scraper - handles calendar-based event listings."""

from typing import Optional

from .base import BaseScraper, _clean_text


class SolingenScraper(BaseScraper):
    """Scraper for Solingen-Live event pages."""

    def _fetch_static(self) -> str:
        """Fetch static content with improved text extraction."""
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            self.url,
            timeout=15,
            headers={"User-Agent": "WeeklyMail/1.0"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "form"]):
            tag.decompose()

        for tag in soup.find_all("div"):
            classes = tag.get("class")
            if classes and isinstance(classes, list):
                class_str = " ".join(str(c) for c in classes if c).lower()
                if any(kw in class_str for kw in ["nav", "menu", "pagination", "search", "filter", "cookie"]):
                    tag.decompose()

        all_text = soup.get_text(separator="\n", strip=True)

        lines = []
        skip_sections = ["Kontakt", "Datenschutz", "AGB", "Impressum", "Umwelt/Klima", "Über uns", "wann?", "wer?", "Termine", "Tickets", "Gutscheine", "Service"]

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
        """Fetch content using Playwright for dynamic calendar interaction."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Solingen scraper. "
                "Install with: pip install playwright && playwright install chromium"
            )

        CLICK_SELECTORS = [
            '.event-item a',
            'a[href*="event"]',
            'a[href*="termin"]',
            '.event-card',
            '.calendar-day',
        ]

        WAIT_FOR_SELECTORS = [
            '.event-list',
            '.event-item',
            '.calendar',
            '[class*="event"]',
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
        """Solingen site may need browser for dynamic calendar."""
        return False

    def fetch(self) -> str:
        """Fetch content - static first, try browser if needed."""
        return self._fetch_static()

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Solingen-Live event pages."""
        return "solingen-live.de" in url
