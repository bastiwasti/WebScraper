"""Scraper for Hilden veranstaltungen website."""

import requests
import json
from rules.base import BaseScraper

class HildenScraper(BaseScraper):
    """Scraper for Hilden veranstaltungen page.
    
    Uses JSON API instead of HTML scraping.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hilden veranstaltungen pages."""
        return "hilden.de" in url and "veranstaltungen/" in url

    def fetch(self) -> str:
        """Fetch events from Hilden JSON API and format as text.
        
        JSON API endpoint returns structured event data.
        This method parses JSON and formats it as text for LLM extraction.
        Limits to first 50 events to stay within token limits.
        """
        json_url = "https://www.hilden.de/de/kalender/veranstaltungen/jahre/events.json?weekends=false&tagMode=ANY"
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON
        try:
            events = json.loads(response.text)
        except json.JSONDecodeError:
            # Return raw JSON if parsing fails
            return response.text
        
        # Limit to first 50 events to avoid token overflow
        events = events[:50]
        
        # Format as text for LLM parsing
        source_url = "https://www.hilden.de/de/veranstaltungen/"
        formatted_events = []
        
        for event in events:
            title = event.get('title', '')
            start = event.get('start', '')
            end = event.get('end', '')
            location_obj = event.get('location', {})
            location = location_obj.get('name', '') if location_obj else ''
            website = event.get('website', '')
            category_obj = event.get('category', {})
            category = category_obj.get('name', '') if category_obj else ''
            
            # Format event for LLM
            formatted_event = f"""Event: {title}
Datum: {start}
Enddatum: {end}
Ort: {location}
Website: {website if website else 'Nicht angegeben'}
Kategorie: {category if category else 'Nicht angegeben'}
Quelle: {source_url}
---"""
            formatted_events.append(formatted_event)
        
        return '\n'.join(formatted_events)
