"""JSON parser for Hilden veranstaltungen website.

Extracts events from JSON API endpoint.
Returns structured Event objects for database storage.
Implements Level 2 scraping to fetch details from external websites.
"""

import re
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from rules.base import BaseRule, Event
from rules import categories


class HildenRegex(BaseRule):
    """JSON parser for Hilden veranstaltungen events.
    
    Hilden uses a JSON API that returns structured event data.
    This parser extracts events from JSON and returns Event objects.
    Level 2 scraping fetches additional details from external websites.
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
        """Parse events from JSON API response (Level 1).
        
        Args:
            raw_content: Raw content from scraper (JSON string).
        
        Returns:
            List of Event objects.
        """
        import json
        import re
        
        try:
            events_data = json.loads(raw_content)
            print(f"[Hilden] JSON parsing {len(events_data)} events")
        except json.JSONDecodeError as e:
            print(f"[Hilden] JSON decode error: {e}")
            return []

        events = []
        events_with_detail_pages = 0
        
        for event_data in events_data:
            try:
                # Extract fields from JSON
                title = event_data.get('title', '')
                event_id = event_data.get('id', '')
                
                # Parse ISO 8601 datetime (e.g., "2025-02-20T13:00")
                start_str = event_data.get('start', '')
                end_str = event_data.get('end', '')
                
                # Extract date (YYYY-MM-DD)
                date_str = start_str.split('T')[0] if 'T' in start_str else start_str
                
                # Extract time (HH:MM)
                time_str = start_str.split('T')[1][:5] if 'T' in start_str else ''
                
                # Extract end time
                end_time_str = end_str.split('T')[1][:5] if 'T' in end_str else ''
                
                # Extract location (combine name and description)
                location_data = event_data.get('location', {})
                location_name = location_data.get('name', '') or ''
                location_desc = location_data.get('description', '') or ''
                
                if location_name and location_desc:
                    location = f"{location_name} - {location_desc}"
                elif location_name:
                    location = location_name
                elif location_desc:
                    location = location_desc
                else:
                    location = ''
                
                # Extract category
                category_data = event_data.get('category', {})
                category_raw = category_data.get('name', '')
                category = categories.infer_category(category_raw, title)
                category = categories.normalize_category(category)
                
                # Extract tags for additional info
                tags = event_data.get('tags', [])
                tag_names = [tag.get('name', '') for tag in tags]
                tags_str = ', '.join(tag_names) if tag_names else ''
                
                # Extract website URL for Level 2 scraping
                website = event_data.get('website', '') or ''
                
                # Convert relative URLs to full URLs
                if website and website.startswith('/'):
                    website = f"https://www.hilden.de{website}"
                
                # Construct detail page URL from imageSrc if available
                image_src = event_data.get('imageSrc', '')
                detail_url = ''
                if image_src and 'jahre/' in image_src:
                    # Extract base path: /de/kalender/veranstaltungen/jahre/2026/02/2026-02-28-mittelalterlicher-wintermarkt
                    base_path = re.sub(r'/[^/]+\.\w+$', '', image_src)
                    detail_url = f"https://www.hilden.de{base_path}/{event_id}"
                    events_with_detail_pages += 1
                
                # Build source URL (prefer detail page, then website, then main calendar)
                source = detail_url if detail_url else (website if website else self.url)
                
                # Build improved description
                desc_parts = []
                desc_parts.append(title)
                if category_raw:
                    desc_parts.append(f"Kategorie: {category_raw}")
                if tags_str:
                    desc_parts.append(f"Tags: {tags_str}")
                description = ' | '.join(desc_parts)
                
                # Create Event object
                event = Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    end_time=end_time_str,
                    source=source,
                    category=category,
                    event_url=detail_url,
                    city="hilden",
                    origin=self.get_origin(),
                )
                events.append(event)
                
            except Exception as e:
                print(f"[Hilden] Error parsing event {event_data.get('title', 'unknown')}: {e}")
                continue
        
        print(f"[Hilden] Successfully parsed {len(events)} events, {events_with_detail_pages} have detail pages")
        return events

    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data from Hilden detail pages.
        
        For each event with an event_url (detail page), fetch the detail page
        and extract additional details (full description, location, etc.).
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Optional raw HTML content from main page (not used).
        
        Returns:
            List of Event objects with Level 2 data merged in (raw_data field).
        """
        import requests
        from bs4 import BeautifulSoup
        import re
        
        if not events:
            return events
        
        events_with_urls = [e for e in events if e.event_url]
        print(f"[Hilden Level 2] Fetching details for {len(events_with_urls)} events with detail pages (out of {len(events)} total)...")
        
        count_success = 0
        count_failed = 0
        
        for event in events:
            if not event.event_url:
                continue
            
            try:
                print(f"  Fetching: {event.name[:50]}")
                
                resp = requests.get(
                    event.event_url,
                    timeout=20,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                
                detail_data = self.parse_hilden_detail_page(resp.text, event.event_url)
                
                if detail_data:
                    event.raw_data = detail_data
                    
                    if 'detail_description' in detail_data and detail_data['detail_description']:
                        if len(detail_data['detail_description']) > len(event.name) + 10:
                            event.description = detail_data['detail_description']
                    
                    if 'detail_location' in detail_data and detail_data['detail_location']:
                        if not event.location or len(detail_data['detail_location']) > len(event.location):
                            event.location = detail_data['detail_location']
                    
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                    count_success += 1
                else:
                    print(f"  ✗ No details found for: {event.name[:50]}")
                    count_failed += 1
            
            except requests.exceptions.Timeout:
                print(f"  ✗ Timeout fetching: {event.event_url}")
                count_failed += 1
            except requests.exceptions.RequestException as e:
                print(f"  ✗ Failed to fetch {event.event_url}: {e}")
                count_failed += 1
            except Exception as e:
                print(f"  ✗ Error processing {event.name[:50]}: {e}")
                count_failed += 1
                continue
        
        print(f"[Hilden Level 2] Completed: {count_success} successes, {count_failed} failures")
        
        return events

    def parse_hilden_detail_page(self, html: str, url: str) -> dict:
        """Parse Hilden detail page for event information.
        
        Args:
            html: HTML content of the detail page.
            url: URL of the detail page.
        
        Returns:
            Dictionary with extracted details (detail_description, detail_location, etc.).
        """
        import json
        
        detail_data = {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract meta description (contains full event description)
            meta_desc = soup.select_one('meta[name="description"]')
            if meta_desc and meta_desc.get('content'):
                content = str(meta_desc.get('content', '')).strip()
                if content and len(content) > 50:
                    detail_data['detail_description'] = content
            
            # Extract from schema.org JSON-LD as fallback
            json_ld_script = soup.select_one('script[type="application/ld+json"]')
            if json_ld_script and json_ld_script.string and 'detail_description' not in detail_data:
                try:
                    schema_data = json.loads(json_ld_script.string)
                    if isinstance(schema_data, list):
                        for item in schema_data:
                            if item.get('@type') == 'Event':
                                desc = item.get('description', '')
                                if desc and len(desc) > 50:
                                    detail_data['detail_description'] = desc
                                break
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # Extract location from schema.org data
            if json_ld_script and json_ld_script.string:
                try:
                    schema_data = json.loads(json_ld_script.string)
                    if isinstance(schema_data, list):
                        for item in schema_data:
                            if item.get('@type') == 'Event':
                                location = item.get('location', {})
                                if isinstance(location, dict):
                                    loc_name = location.get('name', '')
                                    address = location.get('address', {})
                                    if isinstance(address, dict):
                                        street = address.get('streetAddress', '')
                                        postal = address.get('postalCode', '')
                                        city = address.get('addressLocality', '')
                                        parts = [loc_name, street, postal, city]
                                        location_str = ', '.join(p for p in parts if p)
                                        if location_str:
                                            detail_data['detail_location'] = location_str
                                break
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            detail_data['detail_source'] = url
            
            if not detail_data:
                return {}
            
            return detail_data
            
        except Exception as e:
            print(f"[Hilden] Error parsing detail page {url}: {e}")
            return {}

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
