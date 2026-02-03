"""Leverkusen rule parser - fetch and parse Leverkusen event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event, _clean_text


class LeverkusenRuleParser(BaseRuleParser):
    """Parser for Leverkusen event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Leverkusen events.

        Leverkusen format from website:
        DATE | EVENT NAME
        (many entries in a continuous format)
        """
        patterns = [
            re.compile(
                r'(\d{2}\.\d{2}\.\d{4})\s*(.+?)(?=\n|$)',
                re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Leverkusen regex match."""
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
            source="leverkusen.de",
            category="other",
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen event pages."""
        return "leverkusen.de" in url
