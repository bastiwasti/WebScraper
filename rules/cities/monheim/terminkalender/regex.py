"""Regex parser for Monheim terminkalender event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class TerminkalenderRegex(BaseRule):
    """Regex parser for Monheim terminkalender events."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Monheim events."""
        patterns = [
            re.compile(
                r'\*\s+\*\*Event:\*\*\s*(.+?)\s+\*\*Date/Time:\*\*\s*(.+?)(?:\s+\*\*Location/Venue:\*\*\s*(.+?))?\s+\*\*Description/Category:\*\*\s*(.+?)\s+\*\*Source:\*\*\s*(.+?)(?=\n\*   \*\*Event:|\Z)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheim terminkalender pages."""
        return "monheim.de" in url and "terminkalender" in url.lower()

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Monheim regex match."""
        name = match[0].strip() if len(match) > 0 else ""
        date_time = match[1].strip() if len(match) > 1 else ""
        location = match[2].strip() if len(match) > 2 else ""
        description = match[3].strip() if len(match) > 3 else ""
        source = match[4].strip() if len(match) > 4 else ""

        date = date_time
        time = ""

        date_time_clean = re.sub(r'\s*\([^)]*\)', '', date_time)
        parts = [p.strip() for p in date_time_clean.split(",")]

        if len(parts) >= 2:
            date = parts[1]

            if len(parts) >= 3:
                time = parts[2]
            else:
                time = ""

        if location in ["Not specified in snippet.", "Not specified"]:
            location = ""

        if not name or not date or not source:
            return None

        category = self._infer_category(description, name)

        return Event(
            name=name,
            description=description,
            location=location,
            date=date,
            time=time,
            source=source,
            category=category,
        )
