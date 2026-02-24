"""Scraper for Monheim terminkalender URL - optimized for TYPO3 calendar events."""

from typing import Optional

from rules.base import BaseScraper


class TerminkalenderScraper(BaseScraper):
    """Scraper for Monheim terminkalender event pages."""

    def _fetch_with_params(self) -> str:
        """Fetch terminkalender events with better text extraction."""
        url = self.url
        params = {
            "tx_ewsdwhevents_events[action]": "searchResult",
            "tx_ewsdwhevents_events[controller]": "Events",
        }

        import requests
        from bs4 import BeautifulSoup

        from rules.base import _clean_text

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

    @property
    def needs_browser(self) -> bool:
        """Monheim site requires Playwright for dynamic content."""
        return True

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheim terminkalender pages."""
        return "monheim.de" in url and "terminkalender" in url.lower()

    def fetch(self) -> str:
        """Fetch content from terminkalender URL."""
        return self._fetch_with_params()
    
    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from terminkalender URL.
        
        This is used by the rules system for Level 2 scraping.
        """
        """Fetch raw HTML content from terminkalender URL.
        
        This is used by the regex parser when it needs to parse HTML directly.
        """
        import requests
        from bs4 import BeautifulSoup
        
        resp = requests.get(
            self.url,
            timeout=15,
            headers={"User-Agent": "WeeklyMail/1.0"},
        )
        resp.raise_for_status()
        return resp.text
