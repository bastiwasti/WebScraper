"""Base scraper interface and common functionality."""

import re
from abc import ABC, abstractmethod
from typing import Optional

import requests
from bs4 import BeautifulSoup


def _clean_text(text: str, max_chars: Optional[int] = 8000) -> str:
    """Normalize whitespace and truncate to avoid token overflow."""
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


class BaseScraper(ABC):
    """Abstract base class for URL-specific scrapers."""

    def __init__(self, url: str):
        self.url = url

    @property
    def needs_browser(self) -> bool:
        """Return True if this scraper requires a headless browser."""
        return False

    @abstractmethod
    def fetch(self) -> str:
        """Fetch and return content from the URL.

        Returns:
            Cleaned text content from the page.

        Raises:
            Exception: If fetching or parsing fails.
        """
        pass

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this scraper can handle the given URL."""
        pass

    def _fetch_with_requests(self) -> str:
        """Default fetch using requests + BeautifulSoup.

        Returns:
            Extracted text content from the page (cleaned, truncated if very long).
        """
        if not self.url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        resp = requests.get(
            self.url,
            timeout=15,
            headers={"User-Agent": "WeeklyMail/1.0"},
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return _clean_text(text)
