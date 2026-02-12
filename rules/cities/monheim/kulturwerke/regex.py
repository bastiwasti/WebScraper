"""Regex parser for Monheimer Kulturwerke event pages."""
import re
from typing import List, Optional
from datetime import datetime, timedelta
from rules.base import BaseRule, Event


class KulturwerkeRegex(BaseRule):
    """Regex parser for Monheimer Kulturwerke events.
    
    IMPORTANT: Regex is the PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - Regex patterns fail to extract any events
    - Regex extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: D.M.YYYY)
    - time (required): Event time (empty string if all-day event)
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category: Created by analyzer (not set by regex)
    
    DATE FILTERING (1-MONTH WINDOW):
    - Only events within 1 month from current date are processed
    - Events beyond 1 month are skipped
    - Level 2 scraping is NOT implemented for kulturwerke (SPA architecture)
    """
    
    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Kulturwerke events."""
        patterns = [
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+(.+?)(?:\s+(\d{2}:\d{2})?\s*Uhr)?',
                re.MULTILINE
            ),
        ]
        return patterns
    
    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url
    
    def _is_event_within_month(self, event_date: str) -> bool:
        """Check if event date is within 1 month from current date."""
        if not event_date:
            return True  # Keep events without dates
        
        try:
            event_dt = datetime.strptime(event_date, "%d.%m.%Y")
            one_month_later = datetime.now() + timedelta(days=30)
            return event_dt <= one_month_later
        except ValueError:
            # Date parsing failed, keep the event
            return True
    
    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> List[Event]:
        """Extract events using regex, then filter by date range."""
        
        # Use parent class method to get all events via regex
        events = super().extract_events(raw_content, use_llm_fallback)
        
        # Filter events to only those within 1 month
        filtered_events = []
        for event in events:
            if self._is_event_within_month(event.date):
                filtered_events.append(event)
            else:
                print(f"[Kulturwerke] Skipping event outside 1-month window: {event.name[:50]} ({event.date})")
        
        print(f"[Kulturwerke] Filtered {len(events)} events down to {len(filtered_events)} (within 1 month)")
        return filtered_events
