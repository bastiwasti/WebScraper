"""Meetup rule parser - fetch and parse Meetup event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class MeetupRuleParser(BaseRuleParser):
    """Parser for Meetup event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Meetup events.

        Meetup format:
        DATE | TIME | LOCATION | EVENT NAME
        Example: 04. Feb. 2026 19:00 | von Nürnberg | Midweek Social Circle
        """
        patterns = [
            re.compile(
                r'(\d{2}\.\s+\w{3})\s+(\d{4})\s+Uhr\s+\|\s+(.+?)\s+\|\s+(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Meetup regex match."""
        # Group 1: date (e.g., "04. Feb. 2026")
        # Group 2: time (e.g., "19:00")
        # Group 3: location
        # Group 4: event name

        date = match[0].strip() if len(match) > 0 else ""
        time = match[1].strip() if len(match) > 1 else ""
        location = match[2].strip() if len(match) > 2 else ""
        name = match[3].strip() if len(match) > 3 else ""

        if not name:
            return None

        return Event(
            name=name,
            description="",
            location=location,
            date=date,
            time=time,
            source="meetup.com",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Meetup event pages."""
        return "meetup.com" in url
