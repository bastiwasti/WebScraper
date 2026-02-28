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
                
                # Build source URL (prefer website, fallback to main calendar)
                source = website if website else self.url
                
                # Build improved description
                desc_parts = []
                desc_parts.append(title)
                if category:
                    desc_parts.append(f"Kategorie: {category}")
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
                    event_url=website,
                    origin=self.get_origin(),
                )
                events.append(event)
                
            except Exception as e:
                print(f"[Hilden] Error parsing event {event_data.get('title', 'unknown')}: {e}")
                continue
        
        print(f"[Hilden] Successfully parsed {len(events)} events")
        return events

    def parse_website_page(self, website_html: str, website_url: str) -> Optional[dict]:
        """Parse external website page for event details.
        
        Args:
            website_html: HTML content of external website.
            website_url: URL of the website.
        
        Returns:
            Dictionary with extracted details (detail_description, detail_location, etc.), or None if no details found.
        """
        detail_data = {}
        
        try:
            soup = BeautifulSoup(website_html, 'html.parser')
            
            # Remove script/style elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extract meta description
            meta_desc = soup.select_one('meta[name="description"]')
            if meta_desc and meta_desc.get('content'):
                content = str(meta_desc.get('content', ''))
                detail_data['detail_description'] = content.strip()
            
            # Extract main heading
            main_heading = soup.select_one('h1') or soup.select_one('h2')
            if main_heading:
                heading_text = main_heading.get_text(strip=True)
                if heading_text and len(heading_text) > 10:
                    if 'detail_description' not in detail_data:
                        detail_data['detail_description'] = heading_text
                    else:
                        detail_data['detail_description'] = f"{detail_data['detail_description']}\n\n{heading_text}"
            
            # Extract paragraphs for description
            paragraphs = soup.select('p')
            desc_paragraphs = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50 and len(text) < 1000:
                    # Filter out navigation/menu text
                    if not any(skip in text.lower() for skip in ['impressum', 'datenschutz', 'kontakt', 'menu', 'navigation']):
                        desc_paragraphs.append(text)
                        if len(desc_paragraphs) >= 3:
                            break
            
            if desc_paragraphs:
                if 'detail_description' in detail_data:
                    detail_data['detail_description'] = f"{detail_data['detail_description']}\n\n" + '\n\n'.join(desc_paragraphs)
                else:
                    detail_data['detail_description'] = '\n\n'.join(desc_paragraphs)
            
            # Extract location from address patterns
            address_patterns = [
                r'\d{5}\s+[A-Za-zÄÖÜäöüß]+',  # German postal code pattern
                r'[A-Za-zäöüÄÖÜß]+\s+\d{1,3}[a-z]?',  # Street address
                r'Straße|Straße|Platz|Weg|Allee',  # Street type keywords
            ]
            
            text_content = soup.get_text(separator=' ', strip=True)
            for pattern in address_patterns:
                matches = re.finditer(pattern, text_content)
                addresses = [m.group(0) for m in matches]
                if addresses:
                    detail_data['detail_location'] = ', '.join(addresses[:3])
                    break
            
            # Extract phone numbers for contact info
            phone_match = re.search(r'(\+49|0\d{3,4})\s*\d{6,}', text_content)
            if phone_match:
                detail_data['detail_phone'] = phone_match.group(0)
            
            # Store source
            detail_data['detail_source'] = website_url
            
            return detail_data if detail_data else None
            
        except Exception as e:
            print(f"[Hilden] Error parsing website page {website_url}: {e}")
            return None

    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data from external websites.
        
        For each event with an event_url, fetch the external website
        and extract additional details (full description, location, etc.).
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Optional raw HTML content from main page (not used).
        
        Returns:
            List of Event objects with Level 2 data merged in (raw_data field).
        """
        import requests
        
        if not events:
            return events
        
        events_with_urls = [e for e in events if e.event_url]
        print(f"[Hilden Level 2] Fetching details for {len(events_with_urls)} events with URLs (out of {len(events)} total)...")
        
        count_success = 0
        count_failed = 0
        
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
                
                # Parse website page
                detail_data = self.parse_website_page(resp.text, event.event_url)
                
                if detail_data:
                    # Update event with detail data
                    event.raw_data = detail_data
                    
                    # Update location from detail data if better than current
                    if 'detail_location' in detail_data and len(detail_data['detail_location']) > 20:
                        if not event.location or len(detail_data['detail_location']) > len(event.location):
                            event.location = detail_data['detail_location']
                    
                    # Update description with detail description (prefer website description over basic JSON description)
                    if 'detail_description' in detail_data and detail_data['detail_description']:
                        # Keep website description if it's meaningful (longer than title)
                        if len(detail_data['detail_description']) > len(event.name) + 10:
                            event.description = detail_data['detail_description']
                    
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
