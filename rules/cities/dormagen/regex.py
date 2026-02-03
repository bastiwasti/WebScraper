"""Regex parser for Dormagen event pages (placeholder)."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class DormagenRegex(BaseRule):
    """Regex parser for Dormagen events (placeholder - needs URL verification)."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Dormagen events."""
        patterns = [
            re.compile(
                r'Nächster Termin:\s*(.+?)\s*\n*(.+?)(?=\n|mehr »|$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Dormagen regex match."""
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
            source=self.url,
            category="other",
        )
