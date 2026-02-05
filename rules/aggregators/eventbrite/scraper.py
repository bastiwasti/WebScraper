"""Scraper for Eventbrite.de URL."""

from typing import Optional

from rules.base import BaseScraper


class EventbriteScraper(BaseScraper):
    """Scraper for Eventbrite.de event listings."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Eventbrite pages."""
        return "eventbrite.de" in url or "eventbrite.com" in url

    def fetch(self) -> str:
        """Fetch content from Eventbrite URL.

        Eventbrite blocks automated requests (405 error).
        Returns message explaining the limitation.
        """
        import requests

        resp = requests.get(
            self.url,
            timeout=15,
            headers={
                "User-Agent": "WeeklyMail/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if resp.status_code == 405:
            return "Eventbrite blocks automated requests. Consider using manual search or API access."

        resp.raise_for_status()

        return self._fetch_with_requests()
