"""Scraper for Meetup.com URL."""

from typing import Optional

from rules.base import BaseRule


class MeetupScraper(BaseRule):
    """Scraper for Meetup.com event listings."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Meetup pages."""
        return "meetup.com" in url

    def fetch(self) -> str:
        """Fetch content from Meetup URL.

        Uses standard requests for static content.
        """
        return self._fetch_with_requests()
