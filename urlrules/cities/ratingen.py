"""Ratingen rule parser - fetch and parse Ratingen event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class RatingenRuleParser(BaseRuleParser):
    """Parser for Ratingen event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Ratingen events.

        Ratingen appears to have minimal content,
        use generic pattern
        """
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s*(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Ratingen regex match."""
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
            source="ratingen.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen event pages."""
        return "ratingen.de" in url
