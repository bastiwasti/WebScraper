"""Monheim rule parser - fetch and parse Monheim event URLs."""

import re
from typing import List, Optional
from ..base import BaseRuleParser, Event


class MonheimRuleParser(BaseRuleParser):
    """Parser for Monheim event pages."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Monheim events."""
        patterns = [
            re.compile(
                r'\*\s+\*\*Event:\*\*\s*(.+?)\s+\*\*Date/Time:\*\*\s*(.+?)(?:\s+\*\*Location/Venue:\*\*\s*(.+?))?\s+\*\*Description/Category:\*\*\s*(.+?)\s+\*\*Source:\*\*\s*(.+?)(?=\n\*   \*\*Event:|\Z)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Monheim regex match."""
        name = match[0].strip()
        date_time = match[1].strip()
        location = match[2].strip() if len(match) > 2 else ""
        description = match[3].strip() if len(match) > 3 else ""
        source = match[4].strip() if len(match) > 4 else ""

        # Parse date and time from combined field
        # Format: "Dienstag, 03. Februar 2026, 16.00 Uhr"
        # Or: "Mittwoch, 04. Februar 2026 (time not specified)"
        date = date_time
        time = ""
        
        # Remove extra info in parentheses
        date_time_clean = re.sub(r'\s*\([^)]*\)', '', date_time)
        
        # Split by comma
        parts = [p.strip() for p in date_time_clean.split(",")]
        
        if len(parts) >= 2:
            # First part is weekday, skip it
            # Second part is the actual date
            date = parts[1]
            
            # Third part (if exists) is the time
            if len(parts) >= 3:
                time = parts[2]
            else:
                time = ""

        # Handle empty location
        if location in ["Not specified in snippet.", "Not specified"]:
            location = ""

        if not name or not date or not source:
            return None

        category = self._infer_category(description, name)

        return Event(
            name=name,
            description=description,
            location=location,
            date=date,
            time=time,
            source=source,
            category=category,
        )

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheim event pages."""
        return "monheim.de" in url
