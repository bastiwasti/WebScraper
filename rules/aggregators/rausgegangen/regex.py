"""Regex parser for Rausgegangen.de event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class RausgegangenRegex(BaseRule):
    """Regex parser for Rausgegangen.de events.

    Major German event aggregator with popular events.
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Rausgegangen events."""
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Rausgegangen pages."""
        return "rausgegangen.de" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Rausgegangen regex match."""
        date = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location="",
            date=date,
            time="",
            source="rausgegangen.de",
            category="other",
        )
