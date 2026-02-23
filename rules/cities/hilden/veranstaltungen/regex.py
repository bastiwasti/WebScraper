"""JSON parser for Hilden veranstaltungen website.

Extracts events from JSON API endpoint.
Returns structured Event objects for database storage.
"""

import re
from datetime import datetime
from typing import List
from rules.base import BaseRule, Event
from rules import categories


class HildenRegex(BaseRule):
    """JSON parser for Hilden veranstaltungen events.
    
    Hilden uses a JSON API that returns structured event data.
    This parser extracts events from JSON and returns Event objects.
    """

    def __init__(self, url: str):
        super().__init__(url)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def get_regex_patterns(self) -> List:
        """Return empty list - JSON parsing is used instead."""
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse events from JSON API response.
        
        Args:
            raw_content: Raw content from scraper (JSON string).
        
        Returns:
            List of Event objects.
        """
        import json
        
        try:
            events_data = json.loads(raw_content)
            print(f"[Hilden] JSON parsing {len(events_data)} events")
        except json.JSONDecodeError as e:
            print(f"[Hilden] JSON decode error: {e}")
            return []

        events = []
        
        for event_data in events_data:
            try:
                # Extract fields from JSON
                title = event_data.get('title', '')
                
                # Parse ISO 8601 datetime (e.g., "2025-02-20T13:00")
                start_str = event_data.get('start', '')
                end_str = event_data.get('end', '')
                
                # Extract date (YYYY-MM-DD)
                date_str = start_str.split('T')[0] if 'T' in start_str else start_str
                
                # Extract time (HH:MM)
                time_str = start_str.split('T')[1][:5] if 'T' in start_str else ''
                
                # Extract location
                location_data = event_data.get('location', {})
                location = location_data.get('name', '') or location_data.get('description', '')
                
                # Extract category
                category_data = event_data.get('category', {})
                category_raw = category_data.get('name', '')
                category = categories.infer_category(category_raw, title)
                category = categories.normalize_category(category)
                
                # Extract tags for additional info
                tags = event_data.get('tags', [])
                tag_names = [tag.get('name', '') for tag in tags]
                tags_str = ', '.join(tag_names) if tag_names else ''
                
                # Combine tags and category for description
                if tags_str:
                    description = f"{category}. Tags: {tags_str}"
                else:
                    description = category
                
                # Source URL (no individual event pages, use main URL)
                source = self.url
                
                # Create Event object
                event = Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    source=source,
                    category=category,
                    origin=self.get_origin(),
                )
                events.append(event)
                
            except Exception as e:
                print(f"[Hilden] Error parsing event {event_data.get('title', 'unknown')}: {e}")
                continue
        
        print(f"[Hilden] Successfully parsed {len(events)} events")
        return events

    def extract_events(self, raw_content: str, use_llm_fallback: bool = True) -> List[Event]:
        """Extract events using regex (JSON parsing).
        
        Args:
            raw_content: Raw content from scraper (JSON string).
            use_llm_fallback: Whether to use LLM if extraction fails.
        
        Returns:
            List of Event objects.
        """
        events = self.parse_with_regex(raw_content)
        
        if not events and use_llm_fallback:
            print(f"[Hilden] No events found, trying LLM fallback...")
            events = self.parse_with_llm_fallback(raw_content)
        
        return events

    def extract_events_with_method(self, raw_content: str, use_llm_fallback: bool = True) -> tuple[List[Event], str]:
        """Extract events with method tracking.
        
        Args:
            raw_content: Raw content from scraper.
            use_llm_fallback: Whether to use LLM if JSON parsing fails.
        
        Returns:
            Tuple of (List[Event], extraction_method) where extraction_method is "regex", "llm", or "none".
        """
        events = self.parse_with_regex(raw_content)
        
        if events:
            return events, "regex"
        elif use_llm_fallback:
            events = self.parse_with_llm_fallback(raw_content)
            return events, "llm"
        else:
            return [], "none"
