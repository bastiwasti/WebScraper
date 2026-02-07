"""Regex parser for Solingen-Live event pages.

IMPORTANT: Regex is the PRIMARY extraction method.
LLM (DeepSeek) will ONLY be used as fallback if:
- Regex patterns fail to extract any events
- Regex extraction returns empty results

Extracts these fields:
- date (required): Event date (format: DD.MM.YYYY)
- name (required): Event name/title
- time (required): Event time (empty string if all-day event)
- location (required): Event location/venue
- description (required): Event description
- source (required): Set to self.url
- category: Created by analyzer (not set by regex)
"""

import re
from typing import List, Optional
from rules.base import BaseRule, Event


class LiveRegex(BaseRule):
    """Regex parser for Solingen-Live events.

    Handles calendar-based event extraction.
    Extracts events with date, name, time, location, and description.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Solingen-Live pages."""
        return "solingen-live.de" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns to extract events.

        Patterns are tried in order until one successfully extracts events.
        Each pattern should capture groups in this order:
        1. date (required)
        2. name (required)
        3. time (required, can be empty if all-day)
        4. location (required)
        5. description (required)

        If no pattern extracts events, LLM fallback will be used automatically.
        """
        patterns = [
            # Pattern 1: Event with time
            # DD.MM.YYYY EventName HH:MM Uhr Location - Description
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\S[^@]+?)\s+(\d{2}:\d{2})\s*Uhr\s+(\S[^-]+?)\s+-\s*(.+)',
                re.MULTILINE
            ),
            # Pattern 2: All-day event
            # DD.MM.YYYY EventName @ Location - Description
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(\S[^@]+?)\s+@\s+(\S[^-]+?)\s+-\s*(.+)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from regex match.

        Args:
            match: Tuple containing matched groups from regex in order:
                   (date, name, time?, location?, description?)

        Returns:
            Event object or None if required fields missing.
        """
        date = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""
        time = match[2].strip() if len(match) > 2 and match[2] else ""  # Empty if all-day
        location = match[3].strip() if len(match) > 3 and match[3] else ""
        description = match[4].strip() if len(match) > 4 and match[4] else ""

        # Validate required fields (time can be empty for all-day events)
        if not name or not date or not location or not description:
            return None

        return Event(
            name=name,
            description=description,
            location=location,
            date=date,
            time=time,  # Empty string if all-day event
            source=self.url,
            category="",  # Will be set by analyzer
        )
