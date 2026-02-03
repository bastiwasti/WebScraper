"""Regex parser for Ratingen veranstaltungskalender website.

Event structure:
- Calendar-based event listings
- 14-day filtering from today
"""

import re
from typing import List
from datetime import datetime, timedelta

from rules.base import BaseRule, Event


class RatingenRegex(BaseRule):
    """Regex parser for Ratingen veranstaltungskalender events.
    
    Handles calendar-based event structure.
    """

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for ratingen events."""
        patterns = [
            re.compile(
                r'<div class="calendar-event"[^>]*>\s*'  # Calendar events
                r'<h2[^>]*class="event-title"[^>]*>([^<]+)</h2>\s*'  # Event title
                r'<div class="event-date"[^>]*>\s*(\d{1,2}\.?\s*\d{1,2}\.?\s*\d{4})\s*'  # Date
                r'(\d{1,2}\.?\s*\d{1,2}\.?\s*\d{4})\s*(?:\s+(\d{1,2}:\d{2}:\d{4}))?\s*Uhr\s*'  # Time
                r'<div class="event-location"[^>]*>\s*<div class="location"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>\s*</div>\s*</div>\s*'  # Location
                r'<div class="event-description"[^>]*>\s*<div class="description"[^>]*>\s*<p[^>]*>([^<]+)</p>\s*</div>\s*</div>'  # Description
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen pages."""
        return "ratingen.de" in url and "veranstaltungskalender" in url

    def _parse_date(self, date_str: str, time_str: str) -> str:
        """Parse date from date and time components.
        
        Args:
            date_str: Format like "04.02.2026" or "4.2.2026"
            time_str: Format like "19:30" or "18:00 Uhr"
        
        Returns:
            DD.MM.YYYY format for date
        """
        if not date_str:
            return ""
        
        date = date_str.strip()
        
        # Try DD.MM.YYYY format
        try:
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date):
                return date_str
        except Exception:
            pass
        
        return date

    def _is_within_14_days(self, date: str) -> bool:
        """Check if event date is within 14 days from today."""
        if not date:
            return True
        
        try:
            # Parse DD.MM.YYYY
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date):
                day, month, year = date.split('.')
                dt = datetime(int(year), int(month), int(day))
                days_diff = (dt.date() - self.today.date()).days
                return 0 <= days_diff <= 14
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
        
        # Parse date and time
        date = self._parse_date(date_str, time_str)
        
        # Check if within 14 days
        if date_str and not self._is_within_14_days(date_str):
            return None
        
        # Infer category
        category = self._infer_category(title, description)
        
        return Event(
            name=title,
            description=description,
            location=location,
            date=date,
            time=time_str,
            source=self.url,
            category=category,
        )
