"""Regex parser for Dormagen feste-veranstaltungen website.

Event structure:
- Pagination-based calendar (datefix.de system)
- Event cards with schema.org markup
- HTML-based parsing (not regex)
"""

import re
from typing import List
from bs4 import BeautifulSoup

from rules.base import BaseRule, Event


class FesteVeranstaltungenRegex(BaseRule):
    """HTML parser for Dormagen feste-veranstaltungen events.
    
    Uses BeautifulSoup to parse datefix.de calendar HTML.
    """

    def __init__(self, url: str):
        super().__init__(url)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns (fallback only)."""
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using BeautifulSoup (primary method)."""
        events = []
        
        # Split content by page separator
        pages = raw_content.split("<!-- PAGE SEPARATOR -->")
        
        for page_num, page_html in enumerate(pages,1):
            print(f"[Dormagen Regex] Parsing page {page_num}")
            
            soup = BeautifulSoup(page_html, 'html.parser')
            
            # Find all event cards
            event_cards = soup.select('div.terminitem')
            
            for card in event_cards:
                try:
                    event = self._parse_event_card(card)
                    if event:
                        events.append(event)
                except Exception as e:
                    print(f"[Dormagen Regex] Error parsing event: {e}")
                    continue
        
        print(f"[Dormagen Regex] Total events parsed: {len(events)}")
        return events

    def _parse_event_card(self, card) -> Event | None:
        """Parse a single event card and extract data."""
        from rules import categories, utils

        # Event title
        title_elem = card.select_one('h5.dfx-titel-liste-dreizeilig a')
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)

        # Extract detail URL
        detail_link = title_elem.get('href', '')
        if detail_link:
            # Convert to full URL if needed
            if detail_link.startswith('/'):
                detail_link = f"https://www.datefix.de{detail_link}"
            elif detail_link.startswith('http'):
                pass
            else:
                detail_link = f"https://www.datefix.de/{detail_link}"

        # Start date (ISO format from meta tag)
        start_date_elem = card.select_one('meta[itemprop="startDate"]')
        start_date = start_date_elem.get('content', '') if start_date_elem else ''

        # Normalize date
        start_date = utils.normalize_date(start_date)

        # Time from dfx-zeit-liste-dreizeilig
        time_elem = card.select_one('span.dfx-zeit-liste-dreizeilig')
        time = time_elem.get_text(strip=True) if time_elem else ''

        # Location name
        location_elem = card.select_one('span.dfx-lokal-liste-dreizeilig')
        location = location_elem.get_text(strip=True) if location_elem else ''

        # Address components
        postal_code_elem = card.select_one('span[itemprop="postalCode"]')
        postal_code = postal_code_elem.get_text(strip=True) if postal_code_elem else ''

        city_elem = card.select_one('span[itemprop="addressLocality"]')
        city = city_elem.get_text(strip=True) if city_elem else ''

        street_elem = card.select_one('span[itemprop="streetAddress"]')
        street = street_elem.get_text(strip=True) if street_elem else ''

        # Build full address
        address_parts = [street, f"{postal_code} {city}".strip()]
        address = ', '.join([p for p in address_parts if p])

        # Combine location and address
        full_location = location
        if address:
            if full_location:
                full_location += f", {address}"
            else:
                full_location = address

        # Infer category using centralized system
        category = categories.infer_category(title, full_location)
        category = categories.normalize_category(category)

        # Clean time format (e.g., "11:00 Uhr bis 17:00 Uhr" -> "11:00 - 17:00")
        time = utils.normalize_time(time)

        return Event(
            name=title,
            description="",  # Will be filled by Level 2
            location=full_location,
            date=start_date,
            time=time,
            source=detail_link if detail_link else self.url,
            category=category,
            event_url=detail_link,
            origin=self.get_origin(),
        )

    def _clean_time(self, time_str: str) -> str:
        """Clean and normalize time string."""
        if not time_str:
            return ""
        
        # Remove "Uhr" and clean up
        time_str = re.sub(r'\s+Uhr\b', '', time_str, flags=re.IGNORECASE)
        time_str = re.sub(r'bis\s*', ' - ', time_str, flags=re.IGNORECASE)
        time_str = time_str.strip()
        
        return time_str

    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse detail page HTML to extract enhanced data.
        
        Args:
            detail_html: HTML content from detail page.
        
        Returns:
            Dictionary with detail_description, detail_location, etc. or None.
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract description from detail page
        # Try multiple selectors for description
        desc_selectors = [
            'div.dfx-beschreibung',
            'div[itemprop="description"]',
            'p.dfx-beschreibung',
            '.description',
            'div.dfx-detail-beschreibung',
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                if len(desc_text) > 50:  # Only use if substantial
                    detail_data['detail_description'] = desc_text
                    break
        
        # Extract location from detail page if available
        loc_selectors = [
            'div[itemprop="location"]',
            'span[itemprop="name"]',
            '.dfx-ort',
            '.dfx-location',
        ]
        
        for selector in loc_selectors:
            loc_elem = soup.select_one(selector)
            if loc_elem:
                loc_text = loc_elem.get_text(strip=True)
                if loc_text and len(loc_text) > 5:
                    detail_data['detail_location'] = loc_text
                    break
        
        # Extract full address if available
        address_elem = soup.select_one('[itemprop="address"]')
        if address_elem:
            street = address_elem.select_one('[itemprop="streetAddress"]')
            postal_code = address_elem.select_one('[itemprop="postalCode"]')
            city = address_elem.select_one('[itemprop="addressLocality"]')
            
            address_parts = []
            if street:
                address_parts.append(street.get_text(strip=True))
            if postal_code and city:
                address_parts.append(f"{postal_code.get_text(strip=True)} {city.get_text(strip=True)}")
            
            if address_parts:
                detail_data['detail_address'] = ', '.join(address_parts)
        
        # Extract end time if available
        end_date_elem = soup.select_one('meta[itemprop="endDate"]')
        if end_date_elem:
            end_date = end_date_elem.get('content', '')
            if end_date:
                detail_data['detail_end_time'] = end_date
        
        # Add html field for reference
        detail_data['html'] = detail_html[:2000]
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Dormagen events.
        
        For each event, fetches the detail page using Playwright (JavaScript required)
        and extracts enhanced data: description, location, end time, etc.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (not needed, URLs in events).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events:
            return events
        
        print(f"[Dormagen Level 2] Fetching detail pages for {len(events)} events...")
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[Dormagen Level 2] Playwright not available, skipping Level 2")
            return events
        
        events_with_detail = 0
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            for event in events:
                # Use event_url if available, otherwise skip
                if not event.event_url:
                    continue
                
                detail_url = event.event_url
                
                try:
                    # Fetch detail page with Playwright (JavaScript required)
                    print(f"  Fetching: {event.name[:50]}...")
                    page.goto(detail_url, timeout=30000, wait_until="networkidle")
                    
                    # Get the rendered HTML
                    detail_html = page.content()
                    
                    # Parse detail page
                    detail_data = self.parse_detail_page(detail_html)
                    
                    if detail_data:
                        event.raw_data = detail_data
                        event.source = detail_url
                        events_with_detail += 1
                        print(f"    ✓ Fetched details for: {event.name[:40]}")
                    else:
                        print(f"    ✗ No detail data found for: {event.name[:40]}")
                
                except Exception as e:
                    print(f"    ✗ Failed to fetch detail page {detail_url}: {e}")
                    continue
            
            browser.close()
        
        print(f"[Dormagen Level 2] Completed: {events_with_detail}/{len(events)} events with detail data")
        
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
