"""JSON parser for Leverkusen Lust-Auf website.

Extracts ALL events from REST API with 30-day date filtering.
Includes Level 2 detail page fetching for comprehensive event data.

Total: 588 events across 12 pages (50 events per page).
"""

import re
import requests
from datetime import datetime, timedelta
from typing import List, Optional
from bs4 import BeautifulSoup
from rules.base import BaseRule, Event


class LustAufRegex(BaseRule):
    """JSON parser for Leverkusen Lust-Auf events.
    
    Extracts events from REST API:
    - Endpoint: https://lust-auf-leverkusen.de/wp-json/tribe/events/v1/events
    - Total: 588 events across 12 pages
    - 30-day date window from current date
    - Level 2 detail pages for each event
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf pages."""
        return "lust-auf-leverkusen.de" in url

    def get_regex_patterns(self) -> List:
        """Return empty list - JSON parsing is used instead."""
        return []

    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=30)
    
    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse JSON content from REST API.
        
        Args:
            raw_content: JSON string from API response.
        
        Returns:
            List of Event objects.
        """
        try:
            data = json.loads(raw_content)
            events = data.get('events', [])
            print(f"[LustAuf] JSON parsing {len(events)} events")
            
            result = []
            
            for event_data in events:
                try:
                    # Extract fields
                    title = event_data.get('title', '')
                    description = event_data.get('description', '')
                    excerpt = event_data.get('excerpt', '')
                    
                    # Combine description
                    full_description = f"{excerpt}\n\n{description}" if excerpt else description
                    
                    # Parse dates
                    start_date_str = event_data.get('start_date', '')
                    end_date_str = event_data.get('end_date', '')
                    
                    # Parse start date to DD.MM.YYYY
                    date_str = self._parse_date_from_iso(start_date_str)
                    
                    # Parse time from start_date
                    time_str = self._parse_time_from_iso(start_date_str)
                    
                    # Extract venue/location
                    venue = event_data.get('venue', {})
                    location = venue.get('venue', '') if venue else venue.get('address', '')
                    
                    # Extract categories
                    categories = event_data.get('categories', [])
                    category = ', '.join([cat.get('name', '') for cat in categories[:3]])
                    
                    # Extract URL
                    event_url = event_data.get('url', '')
                    
                    # Check if within 30 days
                    if not self._is_within_30_days(start_date_str):
                        continue
                    
                    result.append(Event(
                        name=title,
                        description=full_description,
                        location=location,
                        date=date_str,
                        time=time_str,
                        source=self.url,
                        category=category,
                        event_url=event_url,
                    ))
                
                except Exception as e:
                    print(f"[LustAuf] Failed to parse event: {e}")
                    continue
            
            print(f"[LustAuf] JSON parsing returned {len(result)} events (within 30 days)")
            return result
        
        except json.JSONDecodeError as e:
            print(f"[LustAuf] Failed to parse JSON: {e}")
            # Fallback: try to parse as HTML
            return self._parse_html_fallback(raw_content)
    
    def _parse_date_from_iso(self, iso_date: str) -> str:
        """Parse ISO datetime to DD.MM.YYYY."""
        if not iso_date:
            return ""
        
        try:
            # Try parsing with timezone info
            if 'T' in iso_date:
                iso_date = iso_date.split('T')[0]
            
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%d.%m.%Y")
        
        except Exception as e:
            print(f"[LustAuf] Failed to parse date {iso_date}: {e}")
            return ""
    
    def _parse_time_from_iso(self, iso_date: str) -> str:
        """Parse ISO datetime to HH:MM format."""
        if not iso_date:
            return ""
        
        try:
            if 'T' in iso_date:
                iso_date = iso_date.split('T')[0]
            
            dt = datetime.fromisoformat(iso_date)
            return dt.strftime("%H:%M")
        
        except Exception as e:
            print(f"[LustAuf] Failed to parse time {iso_date}: {e}")
            return ""
    
    def _is_within_30_days(self, iso_date_str: str) -> bool:
        """Check if event date is within 30 days from today."""
        if not iso_date_str:
            return False
        
        try:
            if 'T' in iso_date_str:
                iso_date = iso_date_str.split('T')[0]
            
            dt = datetime.fromisoformat(iso_date)
            days_diff = (dt.date() - self.today.date()).days
            
            return 0 <= days_diff <= 30
        
        except Exception as e:
            print(f"[LustAuf] Failed to check date {iso_date_str}: {e}")
            return True
    
    def _parse_html_fallback(self, html_content: str) -> List[Event]:
        """Fallback HTML parser (not used with API)."""
        print("[LustAuf] HTML fallback parser - returning empty list")
        return []
    
    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from HTML (not used with API)."""
        return {}
    
    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse event detail page for Level 2 data.
        
        Extracts full description from detail page HTML.
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract full description
        desc_elem = soup.select_one('.tribe-events-single .tribe-events-single-event-description')
        if desc_elem:
            paragraphs = desc_elem.select('p')
            descriptions = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    descriptions.append(text)
            
            if descriptions:
                detail_data['detail_description'] = '\n\n'.join(descriptions[:3])
        
        # Extract additional info
        if desc_elem:
            all_text = desc_elem.get_text(strip=True)
            if 'Adresse' in all_text:
                detail_data['detail_location'] = all_text
            elif 'Einlass' in all_text:
                # Parse admission time
                import re
                time_match = re.search(r'(\d{1,2}:\d{2})', all_text)
                if time_match:
                    detail_data['detail_time'] = f"{time_match.group(1)}:{time_match.group(2)}"
        
        return detail_data if detail_data else None
    
    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data for events.
        
        For each event, fetch detail page and extract full description.
        """
        if not events:
            return events
        
        print(f"[LustAuf Level 2] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            if not event.event_url:
                continue
            
            try:
                print(f"  Fetching: {event.name[:50]}")
                
                resp = requests.get(
                    event.event_url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                
                detail_html = resp.text
                
                # Parse detail page
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    # Update event with detail data
                    event.raw_data = detail_data
                    event.source = event.event_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
            
            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {event.event_url}: {e}")
                continue
        
        print(f"[LustAuf Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events
