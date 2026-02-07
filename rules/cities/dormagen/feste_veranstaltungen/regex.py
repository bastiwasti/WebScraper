"""Regex parser for Dormagen feste-veranstaltungen website.

Event structure:
- Fixed events listing (next 14 days)
- Simple date format detection
"""

import re
from typing import List
from datetime import datetime, timedelta

from rules.base import BaseRule, Event


class DormagenRegex(BaseRule):
    """Regex parser for Dormagen feste-veranstaltungen events.
    
    Handles 14-day forward window from today.
    """

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for dormagen events."""
        patterns = [
            re.compile(
                r'kid":\s*"kid"\s*'
                '  # Match "kid" followed by ": " + kid (e.g. "kid": "6003")
            ),
            re.compile(r'"kid":\s*"kid"\s*'"'),
            re.compile(r'"startDate":\s*"startDate"\s*'
                '  # Match "startDate" followed by ": " + date (e.g., "startDate": "2025-02-12T08:30")
            ),
            re.compile(r'"endDate":\s*"endDate"\s*'
                '  # Match "endDate" followed by ": " + date (e.g., "endDate": "2025-02-12T10:30")
            ),
            re.compile(r'"title":\s*"title"\s*'
                '  # Match "title" followed by ": " + title
            ),
            re.compile(r'"location":\s*"location"\s*'
                '  # Match "location" followed by ": " + location
            ),
            re.compile(r'"description":\s*"description"\s*'
                '  # Match "description" followed by ": " + description
            ),
            re.compile(r'"link":\s*"link"\s*'
                '  # Match "link" followed by ": " + link
            ),
        ]
        
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url
    
    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Dormagen events (fallback only)."""
        patterns = [
            re.compile(r'"kid":\s*"kid"\s*"kid"'),
            re.compile(r'"startDate":\s*"start"\s*"end"'),
            re.compile(r'"title":\s*"title"\s*"location"\s*"description"\s*"source"\s*"category"'),
        ]
        return patterns
    
    def _create_event_from_match(self, match: tuple) -> Event | None:
        """Create Event from Dormagen regex match tuple."""
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

    def _create_event_from_match(self, match: tuple) -> Event | None:
        """Create Event from regex match tuple."""
        title = match[0].strip() if len(match) > 0 else ""
        date_str = match[1].strip() if len(match) > 1 else ""
        time_str = match[2].strip() if len(match) > 2 and ":" in match[2] else ""
        location = match[3].strip() if len(match) > 3 else ""
        description = match[4].strip() if len(match) > 4 else ""
        
        if not title:
            return None
        
        # Parse date
        date = self._parse_date(date_str)
        
        # Check if within 14 days
        if not self._is_within_14_days(date_str):
            return None
        
        # Clean up title
        title = title.replace('&nbsp;', ' ').strip()
        
        # Extract time from date_str
        time = ""
        if ":" in date_str:
            parts = date_str.split(":")
            if len(parts) == 2:
                time = parts[1].strip()
                # Update date_str to just the date part
                date_str = parts[0].strip()
        
        # Infer category
        category = self._infer_category(title, description)
        
        return Event(
            name=title,
            description=description,
            location=location,
            date=date_str,
            time=time,
            source=self.url,
            category=category,
        )
