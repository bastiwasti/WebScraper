"""Static rule parser - fallback for generic/static event pages."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event


class StaticRuleParser(BaseRuleParser):
    """Fallback parser for static/generic event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return generic regex patterns for events."""
        patterns = [
            re.compile(r'Event:\s*(.+?)\s*Date:\s*(.+?)', re.DOTALL),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from generic regex match."""
        name = match[0].strip() if len(match) > 0 else ""
        date = match[1].strip() if len(match) > 1 else ""

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

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle any URL (fallback)."""
        return True
