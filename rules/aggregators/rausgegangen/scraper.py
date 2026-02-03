"""Scraper for Rausgegangen.de URL."""

from typing import Optional

from rules.base import BaseRule


class RausgegangenScraper(BaseRule):
    """Scraper for Rausgegangen.de event listings."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Rausgegangen pages."""
        return "rausgegangen.de" in url

    def fetch(self) -> str:
        """Fetch content from Rausgegangen URL.

        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
