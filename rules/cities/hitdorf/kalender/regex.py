"""Regex parser for Hitdorf kalender website.

Event structure:
- Pagination-based calendar (WordPress/Townpress theme)
- Event cards with HTML markup
- HTML-based parsing (not regex)
"""

import re
import requests
from typing import List
from bs4 import BeautifulSoup

from rules.base import BaseRule, Event


class KalenderRegex(BaseRule):
    """HTML parser for Hitdorf kalender events.
    
    Uses BeautifulSoup to parse WordPress Townpress theme HTML.
    """

    def __init__(self, url: str):
        super().__init__(url)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hitdorf pages."""
        return "leben-in-hitdorf.de" in url and "kalender" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns (fallback only)."""
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using BeautifulSoup (primary method)."""
        events = []
        
        # Split content by page separator
        pages = raw_content.split("<!-- PAGE SEPARATOR -->")
        
        for page_num, page_html in enumerate(pages, 1):
            print(f"[Hitdorf Regex] Parsing page {page_num}")
            
            soup = BeautifulSoup(page_html, 'html.parser')
            
            # Find all event cards
            event_cards = soup.select('article.post.lsvr_event')
            
            for card in event_cards:
                try:
                    event = self._parse_event_card(card)
                    if event:
                        events.append(event)
                except Exception as e:
                    print(f"[Hitdorf Regex] Error parsing event: {e}")
                    continue
        
        print(f"[Hitdorf Regex] Total events parsed: {len(events)}")
        return events

    def _parse_event_card(self, card) -> Event | None:
        """Parse a single event card and extract data."""
        from rules import categories, utils

        # Event title
        title_elem = card.select_one('a.post__title-link')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)

        # Extract detail URL
        detail_link = title_elem.get('href', '')
        if detail_link:
            if detail_link.startswith('http'):
                pass
            else:
                detail_link = f"https://leben-in-hitdorf.de{detail_link}"

        # Date from post__info-item--date
        date_elem = card.select_one('li.post__info-item--date')
        date_str = date_elem.get_text(strip=True) if date_elem else ''

        # Normalize date (convert from German format)
        date_str = utils.normalize_date(date_str)

        # Time from post__info-item--time
        time_elem = card.select_one('li.post__info-item--time')
        time = time_elem.get_text(strip=True) if time_elem else ''

        # Normalize time
        time = utils.normalize_time(time)

        # Location from post__info-item--location
        location_elem = card.select_one('li.post__info-item--location')
        
        # Get location name (from link) and address (from text after <br>)
        location_name = ''
        address = ''
        
        if location_elem:
            loc_link = location_elem.select_one('a.post__location-link')
            if loc_link:
                location_name = loc_link.get_text(strip=True)
            
            # Get address text (everything after the <br> tag)
            br_tag = location_elem.find('br')
            if br_tag:
                address = br_tag.next_sibling
                if address and hasattr(address, 'strip'):
                    address = address.strip()
                elif address:
                    address = str(address).strip()

        # Build full location
        full_location = location_name
        if address:
            if full_location:
                full_location += f", {address}"
            else:
                full_location = address

        # Infer category using centralized system
        category = categories.infer_category(title, full_location)
        category = categories.normalize_category(category)

        return Event(
            name=title,
            description="",  # Will be filled by Level 2
            location=full_location,
            date=date_str,
            time=time,
            source=detail_link if detail_link else self.url,
            category=category,
            event_url=detail_link,
            origin=self.get_origin(),
        )

    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse detail page HTML to extract enhanced data.
        
        Args:
            detail_html: HTML content from detail page.
        
        Returns:
            Dictionary with detail_description, detail_location, etc. or None.
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract description from post__content
        desc_elem = soup.select_one('div.post__content')
        if desc_elem:
            desc_text = desc_elem.get_text(strip=True)
            if len(desc_text) > 20:
                detail_data['detail_description'] = desc_text
        
        # Extract full time info if available (from post__info)
        time_elem = soup.select_one('li.post__info-item--time')
        if time_elem:
            time_text = time_elem.get_text(strip=True)
            if time_text:
                detail_data['detail_time'] = time_text
        
        # Add html field for reference
        detail_data['html'] = detail_html[:2000]
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Hitdorf events.
        
        For each event, fetches the detail page using requests
        and extracts enhanced data: description, time, etc.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (not needed, URLs in events).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events:
            return events
        
        print(f"[Hitdorf Level 2] Fetching detail pages for {len(events)} events...")
        
        events_with_detail = 0
        
        for event in events:
            if not event.event_url:
                continue
            
            detail_url = event.event_url
            
            try:
                print(f"  Fetching: {event.name[:50]}...")
                response = requests.get(detail_url, timeout=30)
                response.raise_for_status()
                detail_html = response.text
                
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    if 'detail_description' in detail_data:
                        event.description = detail_data['detail_description']
                    events_with_detail += 1
                    print(f"    ✓ Fetched details for: {event.name[:40]}")
                else:
                    print(f"    ✗ No detail data found for: {event.name[:40]}")
            
            except Exception as e:
                print(f"    ✗ Failed to fetch detail page {detail_url}: {e}")
                continue
        
        print(f"[Hitdorf Level 2] Completed: {events_with_detail}/{len(events)} events with detail data")
        
        return events

    def extract_events_with_method(self, raw_content: str, use_llm_fallback: bool = True) -> tuple[List[Event], str]:
        """Extract events with method tracking."""
        events = self.parse_with_regex(raw_content)
        
        if not events:
            if use_llm_fallback:
                return self.parse_with_llm_fallback(raw_content), "llm"
            else:
                return [], "html_parser"
        
        return events, "html_parser"
