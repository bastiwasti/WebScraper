"""HTML-based parser for Langenfeld city events pages."""
from typing import List, Optional
from rules.base import BaseRule, Event
from rules import categories, utils
import requests


class CityEventsRegex(BaseRule):
    """HTML parser for Langenfeld city events.
    
    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: D.M.YYYY or DD.MM.YYYY)
    - time (required): Event time (from data-sorttime attribute)
    - location (required): Event location/venue
    - description (required): Event description (from teaser)
    - source (required): Set to self.url
    - category: Inferred from keywords
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping
    
    NO DATE FILTERING:
    - All events on the page are processed regardless of date
    - Level 2 scraping fetches detail pages for all events
    """

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Langenfeld city events.
        
        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Langenfeld city event pages."""
        return "langenfeld.de" in url and "Veranstaltungen.htm" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).
        
        Override BaseRule method to parse HTML directly since the website
        has structured event data in HTML cards.
        """
        print("[CityEvents] Using HTML parsing for event extraction")
        
        from bs4 import BeautifulSoup
        import re
        
        html_content = raw_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        for card in soup.find_all('div', class_='event_wrapper'):
            card_classes = card.get('class', [])
            if 'teaser_element' not in card_classes:
                continue
            
            try:
                title_elem = card.find('a', class_='event_teaser_title_link')
                date_elem = card.find('span', class_='event_date_to')
                location_name_elem = card.find('span', class_='event_place_bezeichnung')
                teaser_elem = card.find('span', class_='event_teaser')
                
                title = title_elem.get_text(strip=True) if title_elem else ""
                date_str = date_elem.get_text(strip=True) if date_elem else ""
                location_name = location_name_elem.get_text(strip=True) if location_name_elem else ""
                teaser = teaser_elem.get_text(strip=True) if teaser_elem else ""
                
                if not title:
                    continue

                # Infer category from card class attributes
                # Map specific keyword IDs to standard categories
                class_list = card.get('class', [])
                text = ' '.join(class_list).lower()

                category_from_class = None
                if "keyword_580" in text or "sports" in text:
                    category_from_class = "sport"
                elif any(kw in text for kw in ["keyword_582", "museum"]):
                    category_from_class = "culture"
                elif "keyword_585" in text:
                    category_from_class = "culture"
                elif "keyword_587" in text or "vhs" in text:
                    category_from_class = "education"
                elif "keyword_920" in text or "seniors" in text:
                    category_from_class = "adult"
                elif "keyword_1033" in text or "women" in text:
                    category_from_class = "adult"
                elif "keyword_5585" in text or "family" in text:
                    category_from_class = "family"
                elif "keyword_5587" in text or "school" in text:
                    category_from_class = "education"
                elif "keyword_3081" in text or "library" in text:
                    category_from_class = "education"
                elif "keyword_3574" in text or "schauplatz" in text:
                    category_from_class = "culture"
                elif "keyword_4508" in text or "market" in text:
                    category_from_class = "market"

                # Use inferred class category, or fall back to text-based inference
                if category_from_class:
                    category = category_from_class
                else:
                    category = categories.infer_category(teaser, title)

                # Normalize category
                category = categories.normalize_category(category)
                # Normalize date
                date_str = utils.normalize_date(date_str)

                event = Event(
                    name=title,
                    description=teaser,
                    location=location_name,
                    date=date_str,
                    time="",
                    source=self.url,
                    category=category,
                )
                
                events.append(event)
            
            except Exception as e:
                print(f"[CityEvents] Failed to parse event card: {e}")
                continue
        
        print(f"[CityEvents] HTML parsing returned {len(events)} events")
        return events

    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.
        
        Args:
            raw_html: Raw HTML content from calendar page.
        
        Returns:
            Dictionary mapping event name to detail URL.
        """
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        for card in soup.find_all('div', class_='event_wrapper'):
            card_classes = card.get('class', [])
            if 'teaser_element' not in card_classes:
                continue
            
            try:
                title_elem = card.find('a', class_='event_teaser_title_link')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href_attr = title_elem.get('href', '')
                    href = str(href_attr) if href_attr else ''
                    
                    if href.startswith('/'):
                        href = 'https://www.langenfeld.de' + href
                    
                    event_url_map[title] = href
            
            except Exception as e:
                print(f"[CityEvents] Failed to extract URL from card: {e}")
                continue
        
        print(f"[CityEvents] Extracted {len(event_url_map)} event detail URLs")
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
        
        desc_elem = soup.find('div', class_='dwa_event_description_text')
        if desc_elem:
            description = desc_elem.get_text(strip=True)
            if len(description) > 50:
                detail_data['detail_description'] = description
        
        loc_elem = soup.select_one('#dwa_event_location .addresse_name.name')
        if loc_elem:
            detail_data['detail_location'] = loc_elem.get_text(strip=True)
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Langenfeld city events.
        
        For each event, fetches the detail page and extracts:
        - detail_description: Full event description
        - detail_location: Enhanced location information
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[CityEvents Level 2] Fetching detail pages for {len(events)} events...")
        
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
        
        print(f"[CityEvents Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events