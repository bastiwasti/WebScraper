"""HTML parser for Ratingen Kulturprogramm website.

Extracts ALL events from both Kulturprogramm and Kindertheater sections.
Includes Level 3 detail page fetching for comprehensive event data.
"""

import re
import requests
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from rules.base import BaseRule, Event


class KulturprogrammRegex(BaseRule):
    """HTML parser for Ratingen Kulturprogramm events.
    
    Extracts events from both:
    - Kulturprogramm 2025/2026 section (23 events)
    - Kindertheater 2025/2026 section (5 events)
    
    Total: 28 events with Level 3 detail pages.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen Kulturprogramm pages."""
        return "ratingen.de" in url and "kulturprogramm-aktuell" in url

    def get_regex_patterns(self) -> List:
        """Return empty list - HTML parsing is used instead."""
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method)."""
        soup = BeautifulSoup(raw_content, 'html.parser')
        events = []
        
        # Parse Kulturprogramm section
        kulturprogramm_events = self._parse_kulturprogramm_section(soup)
        events.extend(kulturprogramm_events)
        
        # Parse Kindertheater section
        kindertheater_events = self._parse_kindertheater_section(soup)
        events.extend(kindertheater_events)
        
        print(f"[Ratingen Kulturprogramm] HTML parsing returned {len(events)} events")
        return events
    
    def _parse_kulturprogramm_section(self, soup: BeautifulSoup) -> List[Event]:
        """Parse Kulturprogramm section event cards.
        
        Events are in container with class like 'card-container' or 'slider'.
        """
        events = []
        
        # Try multiple selectors for event cards
        card_selectors = [
            '.card-container a',
            '.slider a',
            'a[href*="event_id"]',
            'a[href*="veranstaltung-details"]',
        ]
        
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                print(f"[Ratingen Kulturprogramm] Found {len(cards)} cards using selector: {selector}")
                break
        
        if not cards:
            print(f"[Ratingen Kulturprogramm] No event cards found with any selector")
            return []
        
        for card in cards:
            try:
                href = card.get('href', '')
                
                # Extract event_id from URL pattern (cast to str first for BeautifulSoup NavigableString)
                href_str = str(href) if href else ''
                match = re.search(r'event_id=(\d+)', href_str)
                if match:
                    event_id_str = match.group(1)
                    event_id = event_id_str if isinstance(event_id_str, str) else ''
                else:
                    event_id = ''
                
                # Extract fields from card
                day_elem = card.select_one('.event-date-day')
                month_elem = card.select_one('.event-date-month')
                time_elem = card.select_one('.time-from')
                title_elem = card.select_one('.header')
                subtitle_elem = card.select_one('.event-subtitle')
                location_elem = card.select_one('.event-location')
                
                day = day_elem.get_text(strip=True) if day_elem else ''
                month = month_elem.get_text(strip=True) if month_elem else ''
                time = time_elem.get_text(strip=True) if time_elem else ''
                title = title_elem.get_text(strip=True) if title_elem else ''
                subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ''
                location = location_elem.get_text(strip=True) if location_elem else ''
                
                # Build date string (default to 2026 if not parsed)
                date_str = f"{day}.{month}.2026" if day and month else "2026"
                
                # Build description
                description = title
                if subtitle:
                    description = f"{title}: {subtitle}"
                
                # Build detail URL
                detail_url = ''
                if event_id:
                    detail_url = f"https://www.stadt-ratingen.de/veranstaltungskalender/veranstaltung-details?tx_citkoevents3_list[action]=single&tx_citkoevents3_list[event_id]={event_id}"
                
                events.append(Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time,
                    source=self.url,
                    category="kultur",
                    event_url=detail_url,
                ))
            
            except Exception as e:
                print(f"[Ratingen Kulturprogramm] Failed to parse Kulturprogramm card: {e}")
                continue
        
        print(f"[Ratingen Kulturprogramm] Parsed {len(events)} Kulturprogramm events")
        return events
    
    def _parse_kindertheater_section(self, soup: BeautifulSoup) -> List[Event]:
        """Parse Kindertheater section event cards."""
        events = []
        
        for card in soup.select('.subject-teaser.has-overlay a'):
            try:
                href = card.get('href', '')
                
                # Extract slug from URL
                href_str = str(href) if href else ''
                slug = href_str.split('/')[-1] if href_str else ''
                
                # Extract fields
                title_elem = card.select_one('.subject-heading')
                date_text_elem = card.select_one('.subject-text')
                
                title = title_elem.get_text(strip=True) if title_elem else ''
                date_text = date_text_elem.get_text(strip=True) if date_text_elem else ''
                
                # Parse date/time from text (e.g., "Donnerstag, 25.9.25, um 16 Uhr in der Stadthalle")
                date_time_str = self._parse_date_time_from_text(date_text)
                
                # Build description
                description = date_text
                
                # Build detail URL
                href_str = str(href) if href else ''
                if href_str.startswith('/'):
                    detail_url = f"https://www.stadt-ratingen.de{href_str}"
                else:
                    detail_url = href_str
                
                events.append(Event(
                    name=title,
                    description=description,
                    location="",
                    date=date_time_str.get('date', '') if date_time_str else "",
                    time=date_time_str.get('time', '') if date_time_str else "",
                    source=self.url,
                    category="kindertheater",
                    event_url=detail_url,
                ))
            
            except Exception as e:
                print(f"[Ratingen Kulturprogramm] Failed to parse Kindertheater card: {e}")
                continue
        
        print(f"[Ratingen Kulturprogramm] Parsed {len(events)} Kindertheater events")
        return events
    
    def _parse_date_time_from_text(self, text: str) -> dict:
        """Parse date and time from German text format."""
        if not text:
            return {'date': '', 'time': ''}
        
        try:
            # Extract day and month
            # Format: "Donnerstag, 25.9.25, um 16 Uhr in der Stadthalle"
            text_str = str(text) if text else ''
            date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', text_str)
            time_match = re.search(r'(\d{1,2}:\d{2})\s+Uhr', text_str)
            
            date_str = date_match.group(0) if date_match else ''
            time_str = time_match.group(1) if time_match else ''
            
            return {'date': date_str, 'time': time_str}
        
        except Exception as e:
            print(f"[Ratingen] Failed to parse date/time from text: {e}")
            return {'date': '', 'time': ''}
    
    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs and mapping from both sections."""
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        # Parse Kulturprogramm section
        for card in soup.select('.card-container.slider a'):
            try:
                title_elem = card.select_one('.header')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                href = card.get('href', '')
                if href and title:
                    event_url_map[title] = href
            
            except Exception as e:
                continue
        
        # Parse Kindertheater section
        for card in soup.select('.subject-teaser.has-overlay a'):
            try:
                title_elem = card.select_one('.subject-heading')
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                href = card.get('href', '')
                if href and title:
                    event_url_map[title] = href
            
            except Exception as e:
                continue
        
        print(f"[Ratingen Kulturprogramm] Extracted {len(event_url_map)} event detail URLs")
        return event_url_map
    
    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse Ratingen event detail page.
        
        Extracts full description, pricing, and venue details.
        
        Args:
            detail_html: Raw HTML content from event detail page.
        
        Returns:
            Dictionary with detail information.
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract full description
        desc_elem = soup.select_one('.ce-bodytext')
        if desc_elem:
            paragraphs = desc_elem.select('p')
            descriptions = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    descriptions.append(text)
            
            if descriptions:
                detail_data['detail_description'] = '\n\n'.join(descriptions[:3])
        
        # Extract all dates (for multi-date events)
        all_p_elems = soup.select('p.ce-bodytext')
        additional_dates = [p.get_text(strip=True) for p in all_p_elems if len(p.get_text(strip=True)) > 20]
        
        if additional_dates:
            detail_data['additional_dates'] = additional_dates
        
        # Extract pricing info
        price_info = []
        for p in all_p_elems:
            text = p.get_text(strip=True)
            if text and "Eintritt:" in text:
                price_info.append(text)
        
        if price_info:
            detail_data['price_info'] = '\n\n'.join(price_info)
        
        # Extract location/contact
        loc_elem = soup.select_one('.ce-contacttext')
        if loc_elem:
            detail_data['detail_location'] = loc_elem.get_text(strip=True)
        
        return detail_data if detail_data else None
    
    def fetch_level3_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 3 detail data for events.
        
        For each event, fetches detail page and extracts comprehensive information.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 3 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[Ratingen Level 3] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            detail_url = event_url_map.get(event.name, "")
            if not detail_url:
                continue
            
            try:
                resp = requests.get(
                    detail_url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                detail_html = resp.text
                
                # Parse detail page
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
            
            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue
        
        print(f"[Ratingen Level 3] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events
