"""Unified base classes for URL rules - handles fetching and parsing.

Each rule consists of:
1. A scraper class that fetches content from a specific URL
2. A regex class that parses content to extract events
3. LLM fallback when regex extraction fails
"""

import re
from abc import ABC, abstractmethod
from typing import List, Optional
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
    end_time: str = ""
    category: str = "other"
    city: str = ""
    event_url: str = ""
    raw_data: dict | None = None
    origin: str = ""


class BaseScraper(ABC):
    """Abstract base class for URL-specific scrapers (fetching only).

    Each scraper:
    1. Fetches content from a specific URL
    """

    def __init__(self, url: str):
        self.url = url

    @property
    def needs_browser(self) -> bool:
        """Return True if this scraper requires a headless browser."""
        return False

    def get_origin(self) -> str:
        """Get origin identifier for this scraper."""
        from rules.registry import get_origin_for_url
        return get_origin_for_url(self.url)

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this scraper can handle the given URL."""
        pass

    @abstractmethod
    def fetch(self) -> str:
        """Fetch and return content from URL.

        Returns:
            Cleaned text content from the page.

        Raises:
            Exception: If fetching or parsing fails.
        """
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


class BaseRule(ABC):
    """Abstract base class for URL-specific regex parsers (parsing only).

    Each parser:
    1. Uses regex patterns to extract structured events
    2. Falls back to LLM if regex fails
    """

    def __init__(self, url: str):
        self.url = url

    def get_origin(self) -> str:
        """Get origin identifier for this parser."""
        from rules.registry import get_origin_for_url
        return get_origin_for_url(self.url)

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool:
        """Return True if this parser can handle the given URL."""
        pass

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
        """Infer category from event description and name.

        Uses centralized categories module for consistent category inference
        across all scrapers.

        Args:
            description: Event description text.
            name: Event name/title (optional).

        Returns:
            Category ID (e.g., "family", "sport", "culture").
        """
        try:
            from rules.categories import infer_category
            return infer_category(description, name)
        except ImportError:
            # Fallback to basic inference if categories module not available
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

    def parse_with_llm_fallback(self, raw_content: str) -> List[Event]:
        """Fallback to LLM if regex extraction fails.

        Args:
            raw_content: Raw text content to parse.

        Returns:
            List of Event objects extracted via LLM.
        """
        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import ChatPromptTemplate

            from config import LLM_PROVIDER, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

            if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
                from langchain_openai import ChatOpenAI

                from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model=DEEPSEEK_MODEL,
                        api_key=str(DEEPSEEK_API_KEY),
                        base_url=DEEPSEEK_BASE_URL,
                        temperature=0.0,
                    )
                except Exception:
                    print("Warning: LLM fallback failed - cannot initialize DeepSeek client")
                    return []
            else:
                return []

            prompt = ChatPromptTemplate.from_messages([
                ("system", "Extrahieren Sie Ereignisinformationen aus dem folgenden Text. Geben Sie sie als strukturierte Daten zurück. Verwenden Sie EXAKT dieselben Wörter wie im Original - kein Übersetzen, kein Umformulieren."),
                ("human", "Text:\n{content}\n\nExtrahieren Sie alle Veranstaltungen mit: name, datum, uhrzeit, ort, beschreibung, quelle (nutzen Sie '{source}')."),
            ])

            chain = prompt | llm | StrOutputParser()
            result = chain.invoke({"content": raw_content[:10000], "source": self.url})

            return [Event(
                name=result,
                description="",
                location="",
                date="",
                time="",
                source=self.url,
                category="other",
                origin="llm_fallback",
            )]
        except Exception as e:
            print(f"Warning: LLM fallback failed: {e}")
            return []

    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> List[Event]:
        """Main extraction method: Try regex, fallback to LLM.
        
        Args:
            raw_content: Raw text content to parse.
            use_llm_fallback: Whether to use LLM if regex fails (default: True).
        
        Returns:
            List of Event objects extracted from content.
        """
        events = self.parse_with_regex(raw_content)
        
        if not events and use_llm_fallback:
            events = self.parse_with_llm_fallback(raw_content)
        
        return events
    
    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Optional method to fetch Level 2 detail data for events.
        
        This method can be overridden by subclasses (e.g., TerminkalenderRegex)
        to fetch event detail pages and enrich events with additional information.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Optional raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data merged in (raw_data field).
            By default, returns events unchanged.
        """
        return events

    def extract_events_with_method(self, raw_content: str, use_llm_fallback: bool = True) -> tuple[List[Event], str]:
        """Main extraction method that returns events and extraction method.

        Args:
            raw_content: Raw text content to parse.
            use_llm_fallback: Whether to use LLM if regex fails (default: True).

        Returns:
            Tuple of (List[Event], extraction_method) where extraction_method is "regex" or "llm".
        """
        events = self.parse_with_regex(raw_content)

        if events:
            return events, "regex"
        elif use_llm_fallback:
            events = self.parse_with_llm_fallback(raw_content)
            return events, "llm"
        else:
            return events, "none"
