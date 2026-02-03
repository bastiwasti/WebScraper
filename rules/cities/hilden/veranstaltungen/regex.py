"""Regex parser for Hilden veranstaltungen website.

Event structure:
- Form-based calendar with date input fields
- Date filter support (next 14 days from today)
"""

import re
from typing import List
from datetime import datetime, timedelta

from rules.base import BaseRule, Event


class HildenRegex(BaseRule):
    """Regex parser for Hilden veranstaltungen events.
    
    Handles flexible date formats and 14-day filtering.
    """

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for hilden events."""
        patterns = [
            re.compile(
                r'<div class="event-item"[^>]*>\s*'  # Event items
                r'<h2[^>]*class="event-title"[^>]*>([^<]+)</h2>\s*'  # Event title
                r'<div class="event-date"[^>]*>\s*(\d{1,2})\.'  # Day
                r'(\d{1,2})\.\s*([A-Z][a-zäöüß]+)'  # Month name
                r'(\d{4})\s*'  # Year
                r'<div class="event-location"[^>]*>\s*<span class="location"[^>]*>([^<]+)</span>\s*'  # Location
                r'<div class="event-time"[^>]*>\s*<span[^>]*class="time"[^>]*>([^<]+)</span>\s*'  # Time
                r'<div class="event-description"[^>]*>\s*<div class="description"[^>]*>\s*<p[^>]*>([^<]+)</p>\s*</div>\s*</div>'  # Description
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def _parse_date(self, day: str, month: str, year: str) -> str:
        """Parse date from day, month, year components.
        
        Returns:
            DD.MM.YYYY format
        """
        if not day or not month or not year:
            return ""
        
        try:
            day_num = int(day)
            month_num = month_map.get(month.capitalize(), 1)
            year_num = int(year)
            dt = datetime(year_num, month_num, day_num)
            return dt.strftime("%d.%m.%Y")
        except (ValueError, AttributeError):
            pass
        
        return ""
    
    def _is_within_14_days(self, day: str, month: str, year: str) -> bool:
        """Check if event date is within 14 days from today."""
        if not day or not month or not year:
            return True
        
        try:
            day_num = int(day)
            month_num = month_map.get(month.capitalize(), 1)
            year_num = int(year)
            event_date = datetime(year_num, month_num, day_num)
            days_diff = (event_date.date() - self.today.date()).days
            return 0 <= days_diff <= 14
        except Exception:
            return True

    def _infer_category(self, title: str, description: str) -> str:
        """Infer category from title and description."""
        text = (title + " " + description).lower()
        
        if any(word in text for word in ["film", "kino", "movie", "cinema"]):
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
        day = match[1].strip() if len(match) > 1 else ""
        month = match[2].strip() if len(match) > 2 else ""
        year = match[3].strip() if len(match) > 3 else ""
        location = match[4].strip() if len(match) > 4 else ""
        time_str = match[5].strip() if len(match) > 5 else ""
        description = match[6].strip() if len(match) > 6 else ""
        
        if not title:
            return None
        
        # Parse date
        date = self._parse_date(day, month, year)
        
        # Check if within 14 days
        if not self._is_within_14_days(day, month, year):
            return None
        
        return Event(
            name=title,
            description=description,
            location=location,
            date=date,
            time=time_str,
            source=self.url,
            category=self._infer_category(title, description),
        )
