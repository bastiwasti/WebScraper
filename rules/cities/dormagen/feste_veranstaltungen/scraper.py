"""Scraper for Dormagen feste-veranstaltungen website."""

import requests
from rules.base import BaseScraper


class DormagenScraper(BaseScraper):
    """Scraper for Dormagen feste-veranstaltungen page.
    
    Uses requests for static HTML content.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url

    def fetch(self) -> str:
        """Fetch events from datefix.de external system.
        
        The Dormagen website uses datefix.de external event system (data-kid="6003").
        
        Fetches events directly from datefix.de API.
        """
        datefix_kid = "6003"  # From HTML: data-kid="6003" data-rubrik="dormagen.de"
        
        api_url = f"https://www.datefix.de/api.php?kid={datefix_kid}&rubrik=dormagen.de&json=1&start=&end="
        
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response
        try:
            events_data = json.loads(response.text)
        if not isinstance(events_data, list):
                events_data = [events_data]
            
            formatted_events = []
            for event in events_data:
                # Get event data
                title = event.get('title', '')
                date = event.get('startDate', '') or event.get('date', '')
                time = event.get('startTime', '') or event.get('time', '')
                location = event.get('location', '')
                description = event.get('description', '')
                category = event.get('category', '')
                
                # Format as text for regex pattern matching
                formatted_event = f"""name={title}
datum={date}
uhrzeit={time}
ort={location}
beschreibung={description}
quelle={self.url}
category={category}
"""
                formatted_events.append(formatted_event)
            
            return "\n".join(formatted_events)
        except json.JSONDecodeError as e:
            return response.text
