"""Scraper for Leverkusen Lust-Auf website.

Uses REST API to fetch all events with 30-day date filtering.
"""

import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rules.base import BaseScraper, Event


class LustAufScraper(BaseScraper):
    """Scraper for Leverkusen Lust-Auf website.
    
    Uses REST API to fetch all events with 30-day date filtering.
    Total: 588 events across 12 pages (50 events per page).
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf pages."""
        return "lust-auf-leverkusen.de" in url

    def fetch(self) -> str:
        """Fetch content from Lust-Auf URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()

    def _fetch_with_requests(self) -> str:
        """Fetch using requests."""
        import requests as req
        resp = req.get(
            self.url,
            timeout=30,
            headers={"User-Agent": "WeeklyMail/1.0"}
        )
        resp.raise_for_status()
        return resp.text

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        Returns full HTML for BeautifulSoup parsing.
        """
        return self._fetch_with_requests()

    def fetch_events_from_api(self, max_pages: int = 12) -> list:
        """Fetch all events via REST API with pagination.
        
        Args:
            max_pages: Maximum number of pages to fetch (default: 12).
        
        Returns:
            List of event dictionaries from API.
        """
        base_url = "https://lust-auf-leverkusen.de/wp-json/tribe/events/v1/events"
        all_events = []
        last_page = 0
        
        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        print(f"[LustAuf] Fetching events from {start_date_str} to {end_date_str}")
        
        for page in range(1, max_pages + 1):
            last_page = page
            params = {
                'page': page,
                'per_page': 50,
                'start_date': start_date_str,
                'end_date': end_date_str,
            }
            
            print(f"[LustAuf] Fetching page {page}/{max_pages}...")
            
            try:
                resp = requests.get(
                    base_url,
                    params=params,
                    timeout=30,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                data = resp.json()
                
                events = data.get('events', [])
                all_events.extend(events)
                print(f"[LustAuf] Page {page}: {len(events)} events")
            
            except Exception as e:
                print(f"[LustAuf] Failed to fetch page {page}: {e}")
                continue
         
        pages_fetched = last_page if last_page > 0 else 0
        print(f"[LustAuf] Fetched {len(all_events)} total events from {pages_fetched} pages")
        
        # Convert API response dictionaries to Event objects
        event_objects = []
        for api_event in all_events:
            event = self._convert_api_to_event(api_event)
            if event:
                event_objects.append(event)
        
        print(f"[LustAuf] Converted {len(event_objects)} events to Event objects")
        return event_objects
    
    def _convert_api_to_event(self, api_event: dict) -> Event | None:
        """Convert API response dictionary to Event object.
        
        Args:
            api_event: Dictionary from REST API response
        
        Returns:
            Event object or None if conversion fails
        """
        try:
            title = api_event.get('title', '').strip()
            description_html = api_event.get('description', '')
            
            # Strip HTML from description for cleaner text
            from bs4 import BeautifulSoup
            description = BeautifulSoup(description_html, 'html.parser').get_text(strip=True)
            
            # Get date and time
            start_date_str = api_event.get('start_date', '')
            end_date_str = api_event.get('end_date', '')
            
            # Parse date string (format: "2026-01-16 16:00:00")
            date_only = ""
            time_only = ""
            end_time_only = ""
            
            if start_date_str:
                try:
                    dt = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
                    date_only = dt.strftime("%Y-%m-%d")
                    time_only = dt.strftime("%H:%M")
                except ValueError:
                    pass
            
            if end_date_str:
                try:
                    dt = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
                    end_time_only = dt.strftime("%H:%M")
                except ValueError:
                    pass
            
            # Get venue/location
            venue = api_event.get('venue', {})
            location = ""
            
            if venue:
                # Try venue name first
                venue_name = venue.get('venue', '').strip()
                if venue_name:
                    location = venue_name
                else:
                    # Fall back to address
                    address = venue.get('address', '').strip()
                    if address:
                        location = address
            
            # Source URL
            source_url = api_event.get('url', '')
            
            # Extract city from venue
            city = ""
            if venue:
                city = venue.get('city', '').strip()
            if not city:
                city = "Leverkusen"
            
            # Build Event object
            event = Event(
                name=title,
                description=description,
                location=location,
                date=date_only,
                time=time_only,
                source=source_url,
                end_time=end_time_only,
                category="other",
                city=city,
                event_url=source_url,
                raw_data=api_event,
            )
            
            return event
            
        except Exception as e:
            print(f"[LustAuf] Failed to convert event to Event object: {e}")
            return None

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return False
