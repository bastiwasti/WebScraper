"""Scraper for Marienburg Monheim events URL."""

from typing import Optional
import requests

from rules.base import BaseScraper


class MarienburgEventsScraper(BaseScraper):
    """Scraper for Marienburg Monheim events pages."""

    MAX_PAGES = 2  # Number of pages to scrape (verified: page 1 has 12, page 2 has 6 events)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Marienburg Monheim events pages."""
        return "marienburgmonheim.de" in url and "/events" in url

    def fetch(self) -> str:
        """Fetch content from Marienburg Monheim events URL.

        Uses standard requests for static HTML content.
        Returns raw HTML for HTML-based parsing.
        """
        return self._fetch_raw_html()

    def _fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL with pagination.

        Returns full HTML with all elements intact for multiple pages.
        """
        all_html = []
        base_url = self.url

        for page in range(1, self.MAX_PAGES + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page_e8={page}"

            print(f"[MarienburgEvents] Fetching page {page}/{self.MAX_PAGES}: {url}")

            try:
                resp = requests.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"},
                )
                resp.raise_for_status()
                all_html.append(resp.text)
            except Exception as e:
                print(f"[MarienburgEvents] Failed to fetch page {page}: {e}")
                continue

        # Combine all pages with separator
        separator = "\n<!-- PAGE SEPARATOR -->\n"
        combined_html = separator.join(all_html)

        print(f"[MarienburgEvents] Fetched {len(combined_html)} chars of raw HTML")
        return combined_html

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.

        This is used by regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        return self._fetch_raw_html()
