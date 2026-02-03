"""Regex parser for Lust-Auf-Leverkusen website.

Event structure:
- Title: Event name in listings
- Date: Shown in various formats (DD.MM.YYYY, DD.MM., etc.)
- Location: Venue name
- Description: Event description
- Category: Film, Konzert, Theater, etc.
"""

import re
from typing import List
from datetime import datetime, timedelta

from rules.base import BaseRule, Event


class LustAufRegex(BaseRule):
    """Regex parser for Lust-Auf-Leverkusen events.
    
    Handles flexible date formats and 14-day filtering.
    """

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for lust-auf events.
        
        Matches entire <div class="sp-event"> blocks and extracts data.
        """
        patterns = [
            re.compile(
                r'<div class="sp-event"[^>]*>(.*?)</div>\s*(?=<div class="sp-event"[^>]|$)',  # Match event divs
                re.DOTALL
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf-Leverkusen pages."""
        return "lust-auf-leverkusen.de" in url

    def _parse_date(self, date_str: str) -> str:
        """Parse date from various formats to DD.MM.YYYY.
        
        Handles:
        - DD.MM.YYYY (e.g., 03.02.2026)
        - D.MM.YYYY (e.g., 3.2.2026)
        - DD.MM. (e.g., 03.02.)
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
                    # Ensure leading zeros
                    month = month.zfill(2)
                    day = day.zfill(2)
                    return f"{day}.{month}.{year}"
        except Exception:
            pass
        
        # Try D.MM.YYYY format
        try:
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str):
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    month = month.zfill(2)
                    day = day.zfill(2)
                    return f"{day}.{month}.{year}"
        except Exception:
            pass
        
        # Try DD.MM. format (no year)
        try:
            if re.match(r'\d{1,2}\.\d{1,2}', date_str):
                day, month = date_str.split('.')
                day = day.zfill(2)
                month = month.zfill(2)
                # Use current year
                return f"{day}.{month}.{self.today.year}"
        except Exception:
            pass
        
        return date_str

    def _is_within_14_days(self, date_str: str) -> bool:
        """Check if event date is within 14 days from today."""
        if not date_str:
            return True
        
        try:
            # Parse date
            parsed_date = self._parse_date(date_str)
            
            # Try to convert to datetime
            formats_to_try = ["%d.%m.%Y", "%d.%m"]
            dt = None
            for fmt in formats_to_try:
                try:
                    dt = datetime.strptime(parsed_date, fmt)
                    break
                except ValueError:
                    continue
            
            if dt:
                days_diff = (dt.date() - self.today.date()).days
                return 0 <= days_diff <= 14
            
        except Exception:
            return True
        
        return True

    def _infer_category(self, title: str, description: str) -> str:
        """Infer category from title and description."""
        text = (title + " " + description).lower()
        
        if any(word in text for word in ["film", "kino", "movie", "cinema", "kinoprogramm"]):
            return "Film"
        elif any(word in text for word in ["konzert", "concert", "musik", "band", "live-musik"]):
            return "Musik"
        elif any(word in text for word in ["theater", "theaterstück", "schauspiel", "komödie", "opera"]):
            return "Theater"
        elif any(word in text for word in ["sport", "fußball", "turnier", "lauf"]):
            return "Sport"
        elif any(word in text for word in ["ausstellung", "kunst", "galerie", "museum"]):
            return "Kunst"
        
        return "other"

    def _infer_category_from_text(self, text: str) -> str:
        """Infer category from text (simple version, no description needed)."""
        if not text:
            return "other"
        
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["film", "kino", "movie", "cinema", "kinoprogramm"]):
            return "Film"
        elif any(word in text_lower for word in ["konzert", "concert", "musik", "band", "live-musik"]):
            return "Musik"
        elif any(word in text_lower for word in ["theater", "theaterstück", "schauspiel", "komödie", "opera"]):
            return "Theater"
        elif any(word in text_lower for word in ["sport", "fußball", "turnier", "lauf"]):
            return "Sport"
        elif any(word in text_lower for word in ["ausstellung", "kunst", "galerie", "museum"]):
            return "Kunst"
        
        return "other"

    def _create_event_from_match(self, match: tuple) -> Event | None:
        """Create Event from regex match tuple."""
        title = match[0].strip() if len(match) > 0 else ""
        date_str = match[1].strip() if len(match) > 1 else ""
        time_str = match[2].strip() if len(match) > 2 else ""
        location = match[3].strip() if len(match) > 3 else ""
        
        if not title:
            return None
        
        # Parse date from datetime attribute
        date = self._parse_date(date_str)
        
        # Check if within 14 days
        if date_str and not self._is_within_14_days(date_str):
            return None
        
        # Infer category
        category = self._infer_category_from_text(title + " " + "")
        
        return Event(
            name=title,
            description="",
            location=location,
            date=date,
            time=time_str,
            source=self.url,
            category=category,
        )
