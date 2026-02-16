"""HTML-based parser for Leichlingen city events pages."""
from typing import List, Optional
from rules.base import BaseRule, Event
from rules import categories, utils
import requests


class FreizeitUndTourismusRegex(BaseRule):
    """HTML parser for Leichlingen city events.
    
    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: DD.MM.YYYY)
    - time (required): Event time
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category: Inferred from keywords
    - event_url: Extracted from bergisch-live.de detail links
    - raw_data: Populated by Level 2 scraping
    
    NO DATE FILTERING:
    - All events on the page are processed regardless of date
    - Level 2 scraping fetches detail pages for all events
    """

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Leichlingen city events.
        
        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leichlingen city event pages."""
        return "leichlingen.de" in url and "freizeit-und-tourismus/veranstaltungen" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).
        
        Override BaseRule method to parse HTML directly since the website
        has structured event data in HTML cards from bergisch-live.de.
        """
        print("[FreizeitUndTourismus] Using HTML parsing for event extraction")
        
        from bs4 import BeautifulSoup
        import re
        
        html_content = raw_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        for card in soup.find_all('div', class_='klive-terminbox'):
            try:
                title_elem = card.find('span', class_='klive-titel-artist')
                pretitle_elem = card.find('span', class_='klive-titel-pretitel')
                titel_elem = card.find('span', class_='klive-titel-titel')
                date_elem = card.find('div', class_='klive-datum')
                time_elem = card.find('div', class_='klive-zeit')
                rubrik_elem = card.find('span', class_='klive-rubrik')
                location_elem = card.find('span', class_='klive-location-notdefault')
                
                title_parts = []
                if pretitle_elem:
                    title_parts.append(pretitle_elem.get_text(strip=True))
                if title_elem:
                    title_parts.append(title_elem.get_text(strip=True))
                if titel_elem:
                    title_parts.append(titel_elem.get_text(strip=True))
                
                title = ' '.join(title_parts).strip()
                
                date_str = ""
                time_str = ""
                
                if date_elem:
                    date_parts = []
                    tag_elem = date_elem.find('span', class_='klive-datum-tag')
                    monat_elem = date_elem.find('span', class_='klive-datum-monat')
                    
                    if tag_elem:
                        day_text = tag_elem.get_text(strip=True).rstrip('.')
                        if day_text and day_text != '&nbsp;' and day_text != ' ':
                            date_parts.append(day_text)
                    if monat_elem:
                        month_text = monat_elem.get_text(strip=True).rstrip('.')
                        if month_text and month_text != '&nbsp;' and month_text != ' ':
                            date_parts.append(month_text)
                    
                    date_str = '.'.join([p for p in date_parts if p])
                    
                    year_elem = card.find_previous('div', class_='klive-monat')
                    if year_elem:
                        year_text = year_elem.get_text(strip=True)
                        year_match = re.search(r'\d{4}', year_text)
                        if year_match and date_str:
                            date_str = f"{date_str}.{year_match.group()}"
                
                if time_elem:
                    time_str = time_elem.get_text(strip=True)
                    time_str = time_str.replace('&ndash;', '-').strip()
                
                location_name = ""
                if location_elem:
                    location_name = location_elem.get_text(strip=True).replace('Veranstaltungsort:', '').strip()
                
                category = ""
                if rubrik_elem:
                    category = rubrik_elem.get_text(strip=True)
                
                description = title
                
                if not title:
                    continue

                category = categories.normalize_category(categories.infer_category(description, title))
                date_str = utils.normalize_date(date_str)
                time_str = utils.normalize_time(time_str)
                
                event = Event(
                    name=title,
                    description=description,
                    location=location_name,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category=category,
                )
                
                events.append(event)
            
            except Exception as e:
                print(f"[FreizeitUndTourismus] Failed to parse event card: {e}")
                continue
        
        print(f"[FreizeitUndTourismus] HTML parsing returned {len(events)} events")
        return events

    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.
        
        For bergisch-live.de, detail pages are at: https://www.bergisch-live.de/{event_id}
        
        Args:
            raw_html: Raw HTML content from calendar page.
        
        Returns:
            Dictionary mapping event name to detail URL.
        """
        from bs4 import BeautifulSoup
        import re
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        for card in soup.find_all('div', class_='klive-terminbox'):
            try:
                title_elem = card.find('span', class_='klive-titel-artist')
                pretitle_elem = card.find('span', class_='klive-titel-pretitel')
                titel_elem = card.find('span', class_='klive-titel-titel')
                
                title_parts = []
                if pretitle_elem:
                    title_parts.append(pretitle_elem.get_text(strip=True))
                if title_elem:
                    title_parts.append(title_elem.get_text(strip=True))
                if titel_elem:
                    title_parts.append(titel_elem.get_text(strip=True))
                
                title = ' '.join(title_parts).strip()
                
                link_elem = card.find('a', class_='llink')
                if link_elem:
                    href_attr = link_elem.get('href', '')
                    href = str(href_attr) if href_attr else ''
                    if href.startswith('https://www.bergisch-live.de/'):
                        event_url_map[title] = href
            
            except Exception as e:
                print(f"[FreizeitUndTourismus] Failed to extract URL from card: {e}")
                continue
        
        print(f"[FreizeitUndTourismus] Extracted {len(event_url_map)} event detail URLs")
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
        
        desc_div = soup.find('div', class_='klive-langfassung-inhalt')
        if desc_div:
            text_parts = []
            for bText in desc_div.find_all('div', class_='bText'):
                text = bText.get_text(separator=' ', strip=True)
                if text:
                    text_parts.append(text)
            
            description = ' '.join(text_parts)
            if len(description) > 50:
                detail_data['detail_description'] = description
        
        loc_div = soup.find('div', class_='klive-langfassung-veranstaltungsort')
        if loc_div:
            location_text = loc_div.get_text(separator=' ', strip=True)
            if location_text and 'Veranstaltungsort' not in location_text:
                detail_data['detail_location'] = location_text
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Leichlingen city events.

        IMPORTANT: Level 2 is DISABLED for Leichlingen.
        The bergisch-live.de detail pages are Facebook redirect pages with no event data.
        The main page with what=All already contains all 58 available events.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (not used).
        
        Returns:
            List of Event objects unchanged (no Level 2 data).
        """
        print(f"[FreizeitUndTourismus] Level 2 disabled - bergisch-live.de detail pages are Facebook redirects with no event data")
        print(f"[FreizeitUndTourismus] Using {len(events)} events from main page (what=All parameter returns all available events)")
        return events
