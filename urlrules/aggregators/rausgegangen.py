"""Rausgegangen rule parser - fetch and parse Rausgegangen event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class RausgegangenRuleParser(BaseRuleParser):
    """Parser for Rausgegangen event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Rausgegangen events.

        Rausgegangen format:
        DD. MMM | HH:MM | NAME | LOCATION
        Example: 04. Feb | 19:00 | Benjamin Amaru | Im Wizemann
        """
        patterns = [
            re.compile(
                r'(\d{2}\.\s+\w{3})\s*\|\s*(\d{1,2}\.?\s*\d{2})\s*Uhr\s*\|\s*(.+?)\s*\|\s*(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Rausgegangen regex match."""
        # Group 1: date (e.g., "04. Feb")
        # Group 2: time (e.g., "19:00")
        # Group 3: event name
        # Group 4: location

        date = match[0].strip() if len(match) > 0 else ""
        time = match[1].strip() if len(match) > 1 else ""
        name = match[2].strip() if len(match) > 2 else ""
        location = match[3].strip() if len(match) > 3 else ""

        # Clean up name and location
        name = re.sub(r'\s+', ',', name)
        location = re.sub(r'\s+', ',', location)

        if not name:
            return None

        return Event(
            name=name,
            description="",
            location=location,
            date=date,
            time=time,
            source="rausgegangen.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Rausgegangen event pages."""
        return "rausgegangen.de" in url
