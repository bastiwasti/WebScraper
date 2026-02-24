"""Minimal regex parser for rausgegangen.de aggregator.

Since rausgegangen uses a hybrid approach where the scraper
already provides structured event data via Level 2 (JSON-LD),
this regex parser is minimal and primarily serves as a fallback.
"""

import re
from typing import List

from rules.base import BaseRule, Event


class RausgegangenRule(BaseRule):
    """Minimal regex parser for rausgegangen.de (fallback only).
    
    The primary data extraction happens in RausgegangenScraper
    via JSON-LD schema. This parser is provided for
    compatibility with the rules system but returns empty
    results by default.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle rausgegangen.de pages."""
        return "rausgegangen.de" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return empty list - scraper provides all data.
        
        Returns:
            Empty list since Level 2 scraping handles extraction.
        """
        return []

    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> List[Event]:
        """Return empty events - scraper already provides data.
        
        This method is overridden to skip regex parsing entirely.
        The RausgegangenScraper.fetch() method returns
        structured Event objects directly.
        
        Args:
            raw_content: Raw text content (not used).
            use_llm_fallback: Whether to use LLM fallback (not used).
        
        Returns:
            Empty list - scraper handles extraction.
        """
        return []
