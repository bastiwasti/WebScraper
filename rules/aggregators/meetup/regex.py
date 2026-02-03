"""Regex parser for Meetup.com event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class MeetupRegex(BaseRule):
    """Regex parser for Meetup.com events.

    Community-driven event platform with meetups and events.
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Meetup events."""
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Meetup pages."""
        return "meetup.com" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Meetup regex match."""
        date = match[0].strip() if len(match) > 0 else ""
        time = match[1].strip() if len(match) > 1 else ""
        name = match[2].strip() if len(match) > 2 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location="",
            date=date,
            time=f"{time} Uhr",
            source="meetup.com",
            category="other",
        )
