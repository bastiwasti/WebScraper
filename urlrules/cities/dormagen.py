"""Dormagen rule parser - fetch and parse Dormagen event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class DormagenRuleParser(BaseRuleParser):
    """Parser for Dormagen event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Dormagen events.

        Dormagen format from website:
        "mehr »" links to event details
        Extract from event listings
        """
        patterns = [
            re.compile(
                r'Nächster Termin:\s*(.+?)\s*\n*(.+?)\s*(?=\n|mehr »|$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Dormagen regex match."""
        name = match[1].strip() if len(match) > 1 else ""
        date = match[0].strip() if len(match) > 0 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location="",
            date=date,
            time="",
            source="dormagen.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen event pages."""
        return "dormagen.de" in url
