"""Regex parser for Eventbrite.de event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class EventbriteRegex(BaseRule):
    """Regex parser for Eventbrite.de events.

    Note: Eventbrite blocks automated scraping, so this is rarely used.
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Eventbrite events."""
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Eventbrite pages."""
        return "eventbrite.de" in url or "eventbrite.com" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Eventbrite regex match."""
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
            source="eventbrite.de",
            category="other",
        )
