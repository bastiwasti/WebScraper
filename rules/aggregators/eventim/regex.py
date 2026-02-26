"""Minimal regex parser for eventim.de aggregator.

Since eventim uses an API-based approach where the scraper
provides structured event data directly, this regex parser
is a stub for compatibility with the rules system.
"""

import re
from typing import List

from rules.base import BaseRule, Event


class EventimRule(BaseRule):
    """Stub regex parser for eventim.de (not used).

    All data extraction happens in EventimScraper via the API.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "eventim.com" in url or "eventim.de" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        return []

    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> List[Event]:
        return []
