"""Base URL rule parser with regex support for structured event extraction."""

import re
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


def _clean_text(text: str, max_chars: Optional[int] = 8000) -> str:
    """Normalize whitespace and truncate to avoid token overflow."""
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


@dataclass
class Event:
    """Structured event data."""
    name: str
    description: str
    location: str
    date: str
    time: str
    source: str
    category: str = "other"


class BaseRuleParser(ABC):
    """Abstract base class for URL-specific rule parsers.

    Each rule parser:
    1. Fetches content from a specific URL
    2. Uses regex patterns to extract structured events
    3. Falls back to LLM if regex fails
    """

    def __init__(self, url: str):
        self.url = url

    @property
    def needs_browser(self) -> bool:
        """Return True if this parser requires a headless browser."""
        return False

    @abstractmethod
    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return list of regex patterns to try for extracting events.

        Each pattern should extract:
        - name (required)
        - date (required)
        - time (optional)
        - location (required, can be empty string)
        - description (required)
        - source (required)

        Returns:
            List of compiled regex patterns to try in order.
        """
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this parser can handle the given URL."""
        pass

    def fetch(self) -> str:
        """Fetch and return content from URL.

        Returns:
            Cleaned text content from the page.

        Raises:
            Exception: If fetching or parsing fails.
        """
        # Check if subclass overrides with Playwright
        if self.needs_browser:
            return self._fetch_with_playwright()

        # Default to requests
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

    def _fetch_with_playwright(self) -> str:
        """Fetch content using Playwright for dynamic pages."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required. Install with: pip install playwright && playwright install chromium"
            )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")

            content = page.content()
            browser.close()

            soup = BeautifulSoup(content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return _clean_text(text)

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse events using regex patterns.

        Tries each regex pattern in order until one produces events.

        Args:
            raw_content: Raw text content to parse.

        Returns:
            List of Event objects extracted from content.
        """
        events = []

        for pattern in self.get_regex_patterns():
            matches = pattern.findall(raw_content)
            if matches:
                for match in matches:
                    try:
                        event = self._create_event_from_match(match)
                        if event and event.name:
                            events.append(event)
                    except Exception as e:
                        print(f"Warning: Failed to create event from match: {e}")
                        continue

                if events:
                    break

        return events

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event object from regex match tuple.

        Subclasses can override to customize field extraction.

        Args:
            match: Tuple containing named groups or positional matches.

        Returns:
            Event object or None if required fields missing.
        """
        return None

    def _infer_category(self, description: str, name: str = "") -> str:
        """Infer category from event description and name."""
        text = (description + " " + name).lower()

        category_keywords = {
            "family": ["familie", "kinder", "jugend", "kind", "baby", "schule", "eltern", "familien"],
            "adult": ["erwachsen", "adult", "senior", "abend", "nacht", "bar", "club", "party"],
            "sport": ["sport", "fitness", "laufen", "schwimmen", "rad", "fußball", "tennis", "yoga"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                return category

        return "other"
