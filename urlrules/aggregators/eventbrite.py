"""Eventbrite rule parser - fetch and parse Eventbrite event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event


class EventbriteRuleParser(BaseRuleParser):
    """Parser for Eventbrite event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Eventbrite events."""
        patterns = [
            re.compile(r'Event:\s*(.+?)\s*Date:\s*(.+?)', re.DOTALL),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Eventbrite regex match."""
        name = match[0].strip() if len(match) > 0 else ""
        date = match[1].strip() if len(match) > 1 else ""

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

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Eventbrite event pages."""
        return "eventbrite.de" in url or "eventbrite.com" in url
