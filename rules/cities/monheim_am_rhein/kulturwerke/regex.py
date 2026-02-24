"""Regex parser for Monheimer Kulturwerke event pages."""
import re
from typing import List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from rules.base import BaseRule, Event


class KulturwerkeRegex(BaseRule):
    """Regex parser for Monheimer Kulturwerke events.
    
    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: D.M.YYYY or DD. MonthName YYYY)
    - time (required): Event time (HH:MM Uhr format)
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category: Inferred from genre
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping
    
    DATE FILTERING (1-MONTH WINDOW):
    - Only events within 1 month from current date are processed
    - Events beyond 1 month are skipped
    - Level 2 scraping fetches detail pages for events within 1-month window
    """
    
    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Kulturwerke events.
        
        These patterns are fallback only. HTML parsing is the primary method.
        """
        patterns = [
            re.compile(
                r'(\d{1,2}\.\d{1,2}\.\d{4})\s+\d{2}:\d{2}\s*Uhr\s+(.+?)\s*$',
                re.MULTILINE
            ),
        ]
        return patterns
    
    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheimer Kulturwerke pages."""
        return "monheimer-kulturwerke.de" in url
    
    def _is_event_within_month(self, event_date: str) -> bool:
        """Check if event date is within 1 month from current date."""
        if not event_date:
            return True  # Keep events without dates
        
        try:
            event_dt = datetime.strptime(event_date, "%d.%m.%Y")
            one_month_later = datetime.now() + timedelta(days=30)
            return event_dt <= one_month_later
        except ValueError:
            return True
    
    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).
        
        Override BaseRule method to parse HTML directly since the website
        has structured event data in HTML cards.
        """
        print("[Kulturwerke] Using HTML parsing for event extraction")
        
        from bs4 import BeautifulSoup
        import re
        import requests
        
        html_content = raw_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        for card in soup.find_all('li', attrs={'data-tags': True}):
            try:
                title_elem = card.find('p', class_='title')
                subtitle_elem = card.find('p', class_='subtitle')
                genre_elem = card.find('p', class_='genre')
                date_elem = card.find(class_='date')
                location_elem = card.find('p', class_='location')
                
                title = title_elem.get_text(strip=True) if title_elem else ""
                subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""
                genre = genre_elem.get_text(strip=True) if genre_elem else ""
                
                date_str = ""
                time_str = ""
                if date_elem:
                    date_li = date_elem.find('li')
                    if date_li:
                        date_text = date_li.get_text(strip=True)
                        date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', date_text)
                        if date_match:
                            date_str = date_match.group(1)
                    
                    time_li = date_elem.find_all('li')
                    if len(time_li) > 1:
                        time_text = time_li[1].get_text(strip=True)
                        time_match = re.search(r'(\d{1,2}:\d{2})', time_text)
                        if time_match:
                            time_str = time_match.group(1) + ' Uhr'
                
                location = location_elem.get_text(strip=True) if location_elem else ""
                
                if title:
                    event_name = title
                    if subtitle:
                        event_name = f"{title} - {subtitle}"
                    
                    events.append(Event(
                        name=event_name,
                        description="",
                        location=location,
                        date=date_str,
                        time=time_str,
                        source=self.url,
                        category=genre or "other",
                        origin=self.get_origin(),
                    ))
            
            except Exception as e:
                print(f"[Kulturwerke] Failed to parse event card: {e}")
                continue
        
        print(f"[Kulturwerke] HTML parsing returned {len(events)} events")
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
        
        for card in soup.find_all('li', attrs={'data-tags': True}):
            try:
                title_elem = card.find('p', class_='title')
                subtitle_elem = card.find('p', class_='subtitle')
                link_elem = card.find('a', href=re.compile(r'^/de/kalender/'))
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ""
                    
                    event_name = title
                    if subtitle:
                        event_name = f"{title} - {subtitle}"
                    
                    href = str(link_elem.get('href', ''))
                    if href.startswith('/'):
                        href = 'https://www.monheimer-kulturwerke.de' + href
                    
                    event_url_map[event_name] = href
            
            except Exception as e:
                print(f"[Kulturwerke] Failed to extract URL from card: {e}")
                continue
        
        print(f"[Kulturwerke] Extracted {len(event_url_map)} event detail URLs")
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
        
        description_parts = []
        description_html_parts = []
        
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            html_str = str(p)
            if len(text) > 50 and not any(skip in text.lower() for skip in ['kalender', 'zurück', 'termin', 'datum', 'uhrzeit', 'ort', 'preise']):
                if text not in description_parts:
                    description_parts.append(text)
                    description_html_parts.append(html_str)
                    if len(description_parts) >= 3:
                        break
        
        if description_parts:
            detail_data['detail_description'] = ' '.join(description_parts[:3])
        if description_html_parts:
            detail_data['detail_full_description'] = '\n'.join(description_html_parts[:3])
        
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            if 'ort' in text.lower():
                detail_data['detail_location'] = text.replace('Ort:', '').replace('Ort', '').strip()
                break
        
        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Monheimer Kulturwerke events (CONCURRENT).
        
        For each event within 1-month window, fetches the detail page and extracts:
        - detail_description: Plain text description
        - detail_full_description: Full description with HTML formatting
        - detail_location: Enhanced location information
        
        Uses ThreadPoolExecutor with 5 workers for ~5x speedup.
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        import requests
        import requests.exceptions
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[Kulturwerke Level 2] Fetching detail pages for {len(events)} events (within 1-month window)...")
        
        MAX_WORKERS = 5
        REQUEST_TIMEOUT = 15
        
        def fetch_event_detail(event, detail_url):
            """Fetch single event detail page with timeout handling."""
            try:
                resp = requests.get(
                    detail_url,
                    timeout=REQUEST_TIMEOUT,
                    headers={"User-Agent": "WeeklyMail/1.0"},
                )
                resp.raise_for_status()
                detail_html = resp.text
                
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    event.event_url = detail_url
                    return event.name, True
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
                    return event.name, False
                    
            except requests.exceptions.Timeout:
                print(f"[Kulturwerke Level 2] ⏱ Timeout fetching {event.name[:50]}")
                return event.name, False
            except Exception as e:
                print(f"[Kulturwerke Level 2] ✗ Failed to fetch {event.name[:50]}: {e}")
                return event.name, False
        
        # Fetch all detail pages concurrently
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for event in events:
                detail_url = event_url_map.get(event.name, "")
                if detail_url:
                    futures.append(executor.submit(fetch_event_detail, event, detail_url))
            
            completed_count = 0
            for future in as_completed(futures):
                name, success = future.result()
                completed_count += 1
                
                if completed_count % 10 == 0:
                    print(f"[Kulturwerke Level 2] Progress: {completed_count}/{len(futures)} events fetched")
        
        success_count = sum(1 for e in events if e.raw_data)
        print(f"[Kulturwerke Level 2] Completed: {success_count}/{len(events)} events with detail data")
        
        return events
