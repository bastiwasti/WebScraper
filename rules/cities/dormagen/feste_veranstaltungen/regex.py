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
                r'<div class="event-item"[^>]*>\s*'  # Event items
                r'<h2[^>]*class="event-title"[^>]*>([^<]+)</h2>\s*'  # Event title
                r'Nächster Termin:\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*'  # Date
                r'Am\s+(\d{2}:\d{2})\.(\d{4})\s*'  # Date with time
                r'<div class="event-location"[^>]*>\s*<span class="location"[^>]*>([^<]+)</span>\s*'  # Location
                r'<div class="event-time"[^>]*>\s*<span[^>]*class="time"[^>]*>([^<]+)</span>\s*'  # Time
                r'<div class="event-description"[^>]*>\s*<div class="description"[^>]*>\s*<p[^>]*>([^<]+)</p>\s*</div>\s*</div>'  # Description
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url

    def _parse_date(self, date_str: str) -> str:
        """Parse date from various formats to DD.MM.YYYY.
        
        Handles:
        - DD.MM.YYYY (e.g., 04.02.2026)
        - D.M.YYYY (e.g., 4.2.2026)
        """
        if not date_str:
            return ""
        
        date_str = date_str.strip()
        
        # Try DD.MM.YYYY format first
        try:
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str):
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return date_str
        except Exception:
            pass
        
        return date_str

    def _is_within_14_days(self, date_str: str) -> bool:
        """Check if event date is within 14 days from today."""
        if not date_str:
            return True
        
        try:
            parts = date_str.split('.')
            if len(parts) == 3:
                day, month, year = parts
                try:
                    dt = datetime(int(year), int(month), int(day))
                    days_diff = (dt.date() - self.today.date()).days
                    return 0 <= days_diff <= 14
                except ValueError:
                    return True
        except Exception:
            return True

    def _infer_category(self, title: str, description: str) -> str:
        """Infer category from title and description."""
        text = (title + " " + description).lower()
        
        if any(word in text for word in ["film", "kino", "film", "cinema"]):
            return "Film"
        elif any(word in text for word in ["konzert", "concert", "musik", "band"]):
            return "Musik"
        elif any(word in text for word in ["theater", "schauspiel", "oper"]):
            return "Theater"
        elif any(word in text for word in ["sport", "fußball", "turnier"]):
            return "Sport"
        elif any(word in text for word in ["ausstellung", "kunst", "auslehung", "museum"]):
            return "Kunst"
        
        return "other"

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
