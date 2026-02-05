"""Regex parser for Leverkusen stadt-erleben calendar.

Event structure (based on actual HTML):
- Title: <h2 class="SP-Headline__small SP-Teaser__headline">...</h2>
- Category: <span class="SP-Kicker__text">...</span>
- Date: <time class="SP-Scheduling__date" datetime="...">...</time>
- Location: <span class="SP-EventInformation__location">...</span>
- Description: <div class="SP-Paragraph SP-Teaser__paragraph"><p>...</p></div>
"""

import re
from typing import List
from datetime import datetime, timedelta

from rules.base import BaseRule, Event


class StadtErlebenRegex(BaseRule):
    """Regex parser for Leverkusen stadt-erleben calendar events.
    
    Handles flexible date formats and 14-day filtering.
    """

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for stadt-erleben events."""
        patterns = [
            re.compile(
                r'<div class="SP-Teaser"[^>]*?>\s*<h2 class="SP-Headline__small SP-Teaser__headline">([^<]+)</h2>\s*'
                r'<span class="SP-Kicker__text">([^<]+)</span>\s*'
                r'<time class="SP-Scheduling__date"[^>]+datetime="([^"]+)"[^>]*>'
                r'<span class="SP-EventInformation__location">([^<]+)</span>\s*'
                r'<div class="SP-Paragraph SP-Teaser__paragraph"[^>]*>\s*<p[^>]*>([^<]+)</p>\s*</div>'
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt-erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def _parse_date_from_datetime(self, date_str: str = None, day: str = None, month: str = None) -> str:
        """Parse date from datetime attribute or day/month text.
        
        Args:
            date_str: Full datetime like "2026-02-03T18:00:00+01:00"
            day: Day number like "03"
            month: Month name like "März"
        
        Returns:
            DD.MM.YYYY format
        """
        if date_str:
            try:
                clean_date = date_str.split('+')[0]
                dt = datetime.fromisoformat(clean_date)
                return dt.strftime("%d.%m.%Y")
            except (ValueError, AttributeError):
                pass
        
        if day and month:
            month_map = {
                'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
                'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
            }
            month_num = month_map.get(month, 1)
            if month_num:
                try:
                    dt = datetime(self.today.year, month_num, int(day))
                    return dt.strftime("%d.%m.%Y")
                except ValueError:
                    pass
        
        return self.today.strftime("%d.%m.%Y")

    def _is_within_14_days(self, date_str: str = None, day: str = None, month: str = None) -> bool:
        """Check if event date is within 14 days from today."""
        if date_str:
            try:
                date = self._parse_date_from_datetime(date_str, day, month)
                event_date = datetime.strptime(date, "%d.%m.%Y")
                days_diff = (event_date.date() - self.today.date()).days
                return 0 <= days_diff <= 14
            except Exception:
                return True
        return True

    def _create_event_from_match(self, match: tuple) -> Event | None:
        """Create Event from regex match tuple.
        
        Args:
            match: Tuple containing all captured groups from regex.
            
        Returns:
            Event object or None if date not within 14 days.
        """
        title = match[0].strip() if len(match) > 0 else ""
        category = match[1].strip() if len(match) > 1 else ""
        date_str = match[2] if len(match) > 2 else None
        day = match[3] if len(match) > 3 else None
        month = match[4] if len(match) > 4 else None
        raw_date = match[5] if len(match) > 5 else ""
        time_str = match[6].strip() if len(match) > 6 else ""
        location = match[7].strip() if len(match) > 7 else ""
        description = match[8].strip() if len(match) > 8 else ""
        
        if not title or not date_str:
            return None
        
        date = self._parse_date_from_datetime(date_str, day, month)
        
        if not self._is_within_14_days(date_str, day, month):
            return None
        
        category_clean = category
        if category_clean == "-":
            category_clean = ""
        
        title = re.sub(r'&[a-z]+;', ' ', title)
        title = title.replace('&quot;', '"').replace('&apos;', "'")
        
        description = re.sub(r'&[a-z]+;', ' ', description)
        
        time = time_str if time_str else ""
        if ":" in time_str:
            time = time_str
        
        return Event(
            name=title,
            description=description,
            location=location,
            date=date,
            time=time,
            source=self.url,
            category=category_clean if category_clean else "other",
        )
