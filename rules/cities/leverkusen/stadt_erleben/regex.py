"""Regex parser for Leverkusen stadt-erleben calendar.

Event structure:
- Title: <h2 class="SP-Headline__small SP-Teaser__headline">
- Category: <span class="SP-Kicker__text">
- Date: <time class="SP-Scheduling__date" datetime="YYYY-MM-DD...">
  OR <time datetime>DD.MM.YYYY</time>
  OR <span class="SP-EventInformation__time">HH:MM</span>
- Location: <span class="SP-EventInformation__location">
- Description: <div class="SP-Paragraph SP-Teaser__paragraph">
"""

import re
from typing import List, Optional
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
                r'<div class="SP-Teaser"[^>]*>\s*'
                r'<div class="SP-Teaser__image"[^>]*>.*?</div>\s*'  # Skip image divs
                r'<span class="SP-Kicker__text">([^<]+)</span>\s*'
                r'<h2 class="SP-Headline__small SP-Teaser__headline"[^>]*>\s*<a[^>]*>\s*([^<]+)\s*</a>\s*</h2>\s*'
                r'<time class="SP-Scheduling__date"[^>]+datetime="([^"]+)"[^>]*>(?:<span[^>]*class="SP-Scheduling__day"[^>]*>(\d+)</span>\s*<span[^>]*class="SP-Scheduling__month"[^>]*>([A-Za-z]+)</span>)?(?:<time[^>]*datetime="([^"]+)"[^>]*>(\d{1,2})\.(\d{1,2})\.(\d{4}))?'
                r'<span class="SP-EventInformation__time">(\d{2}:\d{2})</span>\s*'
                r'<span class="SP-EventInformation__location">([^<]+)</span>\s*'
                r'<div class="SP-Paragraph SP-Teaser__paragraph"[^>]*>\s*<p[^>]*>([^<]+)</p>\s*</div>',
                re.DOTALL
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt-erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def _parse_date_from_datetime(self, date_str: str, day: str, month: str) -> str:
        """Parse date from datetime attribute or day/month text.
        
        Args:
            date_str: Full datetime like "2026-02-03T18:00:00+01:00"
            day: Day number like "03"
            month: Month name like "März"
        
        Returns:
            DD.MM.YYYY format
        """
        # Try to parse from datetime string first
        if date_str and date_str.strip():
            try:
                # Remove timezone info
                clean_date = date_str.split('+')[0]
                # Parse ISO format
                dt = datetime.fromisoformat(clean_date)
                return dt.strftime("%d.%m.%Y")
            except (ValueError, AttributeError):
                pass
        
        # Fallback to day/month
        if day and month:
            # Map German month names to numbers
            month_map = {
                'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4, 'Mai': 5, 'Juni': 6,
                'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
            }
            
            month_num = month_map.get(month, 1)
            if month_num:
                try:
                    # Use current year
                    dt = datetime(self.today.year, month_num, int(day))
                    return dt.strftime("%d.%m.%Y")
                except ValueError:
                    pass
        
        # Default to today
        return self.today.strftime("%d.%m.%Y")

    def _is_within_14_days(self, date_str: str, day: str, month: str) -> bool:
        """Check if event date is within 14 days from today."""
        try:
            date = self._parse_date_from_datetime(date_str, day, month)
            event_date = datetime.strptime(date, "%d.%m.%Y")
            
            # Calculate days difference
            days_diff = (event_date.date() - self.today.date()).days
            
            return 0 <= days_diff <= 14
        except Exception:
            # Default to include if parsing fails
            return True

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from regex match tuple.
        
        Args:
            match: Tuple containing all captured groups from regex
            
        Returns:
            Event object or None if date not within 14 days.
        """
        # Extract fields from regex match
        category = match[0].strip() if len(match) > 0 and match[0] else ""
        title = match[1].strip() if len(match) > 1 else ""
        date_str = match[2] if len(match) > 2 else None
        day = match[3] if len(match) > 3 else None
        month = match[4] if len(match) > 4 else None
        raw_date = match[5] if len(match) > 5 else ""
        time_str = match[6].strip() if len(match) > 6 else ""
        location = match[7].strip() if len(match) > 7 else ""
        description = match[8].strip() if len(match) > 8 else ""
        
        # Parse date
        date_str = match[2] if len(match) > 2 else None
        day = match[3] if len(match) > 3 else None
        month = match[4] if len(match) > 4 else None
        
        # Parse date
        date = self._parse_date_from_datetime(date_str, day, month)
        
        # Check if within 14 days
        if not self._is_within_14_days(date_str, day, month):
            return None
        
        # Clean up category
        category_clean = category
        if category_clean == "-":
            category_clean = ""
        
        # Clean up title (remove HTML entities)
        title = re.sub(r'&[a-z]+;', ' ', title)
        title = title.replace('&quot;', '"').replace('&apos;', "'")
        
        # Clean up description
        description = re.sub(r'&[a-z]+;', ' ', description)
        
        # Determine time format
        time = match[6].strip() if len(match) > 6 and match[6].strip() else ""
        
        if not title or not date:
            return None
        
        # Infer category from text
        category_lower = category_clean.lower()
        if "kino" in category_lower or "film" in category_lower:
            category_clean = "Film"
        elif "theater" in category_lower or "komödie" in category_lower:
            category_clean = "Theater"
        elif "sport" in category_lower:
            category_clean = "Sport"
        elif "musical" in category_lower or "musik" in category_lower:
            category_clean = "Musik"
        
        return Event(
            name=title,
            description=description,
            location=location,
            date=date,
            time=time,
            source=self.url,
            category=category_clean,
        )
