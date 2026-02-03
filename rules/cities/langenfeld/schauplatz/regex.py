"""Regex parser for Schauplatz event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class SchauplatzRegex(BaseRule):
    """Regex parser for Schauplatz events.

    Format: Day abbr + DD.MM.YYYY + HH:MM Uhr (e.g., Fr 06.02.2026 20:00 Uhr)
    Venue names: Schauplatz Langenfeld, Schaustall, Flügelsaal
    Categories: Kabarett, Konzert, Musical, etc.
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Schauplatz events."""
        patterns = [
            re.compile(
                r'([A-Z][a-z]{2})\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+Uhr\s+([A-Za-z\s]+)\s+(.+?)(?=\n\s*[A-Z][a-z]{2}\s+\d{2}\.\d{2}\.\d{4}|\n\s*\Z)',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Schauplatz pages."""
        return "schauplatz.de" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Schauplatz regex match."""
        weekday = match[0].strip() if len(match) > 0 else ""
        date = match[1].strip() if len(match) > 1 else ""
        time = match[2].strip() if len(match) > 2 else ""
        location = match[3].strip() if len(match) > 3 else ""
        name = match[4].strip() if len(match) > 4 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location=location,
            date=date,
            time=f"{time} Uhr",
            source=self.url,
            category="other",
        )
