"""Regex parser for Langenfeld city events pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class CityEventsRegex(BaseRule):
    """Regex parser for Langenfeld city events.

    Format: Day abbr + DD.MM.YYYY (e.g., Di 03.02.2026)
    Full addresses included in location field.
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Langenfeld city events."""
        patterns = [
            re.compile(
                r'([A-Z][a-z]{2})\s+(\d{2}\.\d{2}\.\d{4})\s+(.+?)(?=\n\s*[A-Z][a-z]{2}\s+\d{2}\.\d{2}\.\d{4}|\n\s*Veranstaltungsort:|Z\s*$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Langenfeld city event pages."""
        return "langenfeld.de" in url and "Veranstaltungen.htm" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Langenfeld city events regex match."""
        weekday = match[0].strip() if len(match) > 0 else ""
        date = match[1].strip() if len(match) > 1 else ""
        content = match[2].strip() if len(match) > 2 else ""

        if not content or not date:
            return None

        name = ""
        location = ""
        description = ""

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "Veranstaltungsort:" in line:
                location = line.replace("Veranstaltungsort:", "").strip()
            elif not name:
                name = line
            elif not description:
                description = line

        if not name:
            return None

        return Event(
            name=name,
            description=description,
            location=location,
            date=date,
            time="",
            source=self.url,
            category="other",
        )
