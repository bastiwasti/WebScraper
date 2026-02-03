"""Hilden rule parser - fetch and parse Hilden event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class HildenRuleParser(BaseRuleParser):
    """Parser for Hilden event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Hilden events.

        Hilden format from website:
        "Layout DD/MM/YYYY - EVENT NAME"
        (similar to Langenfeld)
        """
        patterns = [
            re.compile(
                r'Layout\s*(\d{2}/\d{2}/\d{4})\s*(.+?)(?=\n|$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Hilden regex match."""
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
            source="hilden.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden event pages."""
        return "hilden.de" in url
