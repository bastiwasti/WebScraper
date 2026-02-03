"""Regex parser for Ratingen event pages (placeholder)."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class RatingenRegex(BaseRule):
    """Regex parser for Ratingen events (placeholder - needs URL verification)."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Ratingen events."""
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen pages."""
        return "ratingen.de" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Ratingen regex match."""
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
            source=self.url,
            category="other",
        )
