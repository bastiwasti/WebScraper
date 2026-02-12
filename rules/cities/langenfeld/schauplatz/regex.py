"""HTML-based parser for Schauplatz event pages."""
from typing import List, Optional
from rules.base import BaseRule, Event
import requests


class SchauplatzRegex(BaseRule):
    """HTML parser for Schauplatz events.
    
    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: DD.MM.YYYY)
    - time (required): Event time (format: HH:MM Uhr)
    - location (required): Event location/venue
    - description (required): Event description (from excerpt)
    - source (required): Set to self.url
    - category: Inferred from category links
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping
    
    NO DATE FILTERING:
    - All events on page are processed regardless of date
    - Level 2 scraping fetches detail pages for all events
    """

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Schauplatz events.
        
        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Schauplatz pages."""
        return "schauplatz.de" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).
        
        Override BaseRule method to parse HTML directly since the website
        has structured Ztix event data in HTML cards.
        """
        print("[Schauplatz] Using HTML parsing for event extraction")
        
        from bs4 import BeautifulSoup
        import re
        
        html_content = raw_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        cards = soup.select('div.ztix_box')
        print(f"[Schauplatz] Found {len(cards)} ztix_box cards")
        
        for card in cards:
            card_classes = card.get('class', [])
            if 'gray' in card_classes:
                continue
            
            try:
                date_elem = card.select_one('.ztix_box_header .ztix_date')
                time_elem = card.select_one('.ztix_box_header .ztix_time')
                venue_elem = card.select_one('.ztix_box_main .ztix_venue')
                title_elem = card.select_one('.ztix_box_main .ztix_title a')
                excerpt_elem = card.select_one('.ztix_grid_excerpt p')
                price_alert_elem = card.select_one('.ztix_box_main .kontakt_box.alert')
                
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                time_str = time_elem.get_text(strip=True) if time_elem else ""
                venue = venue_elem.get_text(strip=True) if venue_elem else ""
                title = title_elem.get_text(strip=True) if title_elem else ""
                excerpt = excerpt_elem.get_text(strip=True) if excerpt_elem else ""
                price_alert = price_alert_elem.get_text(strip=True) if price_alert_elem else ""
                
                if not title:
                    print(f"[Schauplatz] Skipping card: no title")
                    continue
                
                events.append(Event(
                    name=title,
                    description=f"{excerpt} {price_alert}" if price_alert else excerpt,
                    location=venue,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category="other",
                ))
            
            except Exception as e:
                print(f"[Schauplatz] Failed to parse event card: {e}")
                continue
        
        print(f"[Schauplatz] HTML parsing returned {len(events)} events")
        return events

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date format from DD.MM.YYYY to DD.MM.YYYY."""
        date_str = date_str.strip()
        
        if '.' in date_str and date_str.count('.') >= 2:
            parts = date_str.split('.')
            if len(parts) == 3:
                day = parts[0].zfill(2, '0')
                month = parts[1].zfill(2, '0')
                year = parts[2]
                return f"{day}.{month}.{year}"
        
        return date_str

    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.
        
        Args:
            raw_html: Raw HTML content from calendar page.
        
        Returns:
            Dictionary mapping event name to detail URL.
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        for card in soup.select('div.ztix_box'):
            card_classes = card.get('class', [])
            if 'gray' in card_classes:
                continue
            
            try:
                title_elem = card.select_one('.ztix_box_main .ztix_title a')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href_attr = title_elem.get('href', '')
                    href = str(href_attr) if href_attr else ''
                    
                    if href.startswith('/'):
                        href = 'https://schauplatz.de' + href
                    
                    event_url_map[title] = href
            
            except Exception as e:
                print(f"[Schauplatz] Failed to extract URL from card: {e}")
                continue
        
        print(f"[Schauplatz] Extracted {len(event_url_map)} event detail URLs")
        return event_url_map

    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse event detail page to extract enhanced information.
        
        Args:
            detail_html: Raw HTML content from event detail page.
        
        Returns:
            Dictionary with detail information (detail_description, detail_location).
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        title_elem = soup.select_one('#ztix_single h1')
        subtitle_elem = soup.select_one('#ztix_single h2')
        
        if title_elem:
            title = title_elem.get_text(strip=True)
            if subtitle_elem:
                title = f"{title} - {subtitle_elem.get_text(strip=True)}"
        
        description = ""
        for p in soup.select('#ztix_single .col-md-8 .main_info p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                description = text
                break
        
        if description:
            detail_data['detail_description'] = description
        
        date_elem = soup.select_one('.date-time-row .date')
        time_elem = soup.select_one('.date-time-row .time')
        
        if date_elem and time_elem:
            date_str = date_elem.get_text(strip=True)
            time_str = time_elem.get_text(strip=True)
            detail_data['detail_date'] = date_str
            detail_data['detail_time'] = time_str
        
        venue_elem = soup.select_one('.venue .name')
        location_elem = soup.select_one('.location .address')
        
        if venue_elem:
            venue = venue_elem.get_text(strip=True)
            if location_elem:
                location = f"{venue} {location_elem.get_text(strip=True)}"
                detail_data['detail_location'] = location
            else:
                detail_data['detail_location'] = venue
        
        price_elem = soup.select_one('.price-row .price')
        if price_elem:
            price = price_elem.get_text(strip=True)
            detail_data['detail_price'] = price
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Schauplatz events.
        
        For each event, fetches the detail page and extracts:
        - detail_description: Full event description
        - detail_location: Enhanced location information
        - detail_date: Full date information
        - detail_time: Full time information
        - detail_price: Pricing information
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[Schauplatz Level 2] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            detail_url = event_url_map.get(event.name, "")
            
            if not detail_url:
                continue
            
            event.event_url = detail_url
            
            try:
                resp = requests.get(
                    detail_url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"},
                )
                resp.raise_for_status()
                detail_html = resp.text
                
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
        
        print(f"[Schauplatz Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events