"""Langenfeld rule parser - fetch and parse Langenfeld event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class LangenfeldRuleParser(BaseRuleParser):
    """Parser for Langenfeld event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Langenfeld events.

        Langenfeld format from website:
        "Nächster Termin: DATE"
        "EVENT NAME"
        "Ort: LOCATION"
        """
        patterns = [
            re.compile(
                r'Nächster Termin:\s*(.+?)\s*\n*(.+?)\s*Ort:\s*(.+?)(?=\n|$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Langenfeld regex match."""
        name = match[1].strip() if len(match) > 1 else ""
        date = match[0].strip() if len(match) > 0 else ""
        location = match[2].strip() if len(match) > 2 else ""

        if not name or not date:
            return None

        return Event(
            name=name,
            description="",
            location=location,
            date=date,
            time="",
            source="langenfeld.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Langenfeld event pages."""
        return "langenfeld.de" in url
