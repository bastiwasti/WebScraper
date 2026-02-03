"""Regex parser for Monheimer Kulturwerke event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class KulturwerkeRegex(BaseRule):
    """Regex parser for Monheimer Kulturwerke events.

    Format: D.M.YYYY (no leading zeros, e.g., 4.2.2026)
    """

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Kulturwerke events."""
        patterns = [
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)(?:\s+(\d{2}:\d{2})?\s+Uhr)?',
                re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Kulturwerke regex match."""
        date = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""
        time = match[2].strip() if len(match) > 2 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location="",
            date=date,
            time=time + " Uhr" if time else "",
            source=self.url,
            category="other",
        )
