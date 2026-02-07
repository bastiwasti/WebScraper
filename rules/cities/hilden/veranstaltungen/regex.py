"""Dummy regex parser for Hilden veranstaltungen website.

Since Hilden now uses a JSON API that returns structured events,
we don't need regex parsing. This module exists to satisfy
the registry system's requirement for a regex parser.
"""

from rules.base import BaseRule


class HildenRegex(BaseRule):
    """Dummy regex parser for Hilden veranstaltungen events.
    
    Hilden now uses a JSON API that returns structured event data.
    This parser extracts events directly from JSON without regex matching.
    """

    def get_regex_patterns(self) -> list:
        """Return empty list - JSON API doesn't need regex patterns."""
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> list:
        """Extract events from JSON API response.
        
        The scraper fetches JSON directly, which contains structured event data.
        This method returns empty list since scraper handles JSON extraction.
        
        Args:
            raw_content: Raw content from scraper (JSON string).
            use_llm_fallback: Whether to use LLM if extraction fails.
        
        Returns:
            Empty list (scraper handles JSON parsing via LLM).
        """
        return []
