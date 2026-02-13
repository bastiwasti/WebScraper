"""HTML-based parser for Leverkusen Stadt_Erleben events."""

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Optional
from rules.base import BaseRule, Event
import requests


class StadtErlebenRegex(BaseRule):
    """HTML parser for Leverkusen Stadt_Erleben events.
    
    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (DD.MM.YYYY)
    - time (required): Event time (HH:MM format)
    - location (required): Event location/venue
    - description (required): Event description
    - source (required): Set to self.url
    - category (required): Inferred from event data
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping
    
    NO DATE FILTERING:
    - Fetches all events (no automatic date restriction)
    - Date filtering applied via URL parameters by scraper_agent
    
    ADVERTISING DETECTION:
    - Skips events with categories: 'Bildung', 'Veranstaltungen', 'Werbung'
    - These are promotional content, not real events
    
    PAGINATION SUPPORT:
    - Supports server-side pagination
    - URL pattern: ?sp:page[eventSearch-1.form][0]={page_num}
    """

    # Advertising categories to skip
    ADVERTISING_CATEGORIES = ['Bildung', 'Veranstaltungen', 'Werbung']
    
    # Pagination: 14-day window from today
    def __init__(self, url: str):
        super().__init__(url)
        self.today = datetime.now()
        self.date_cutoff = self.today + timedelta(days=14)
    
    def get_regex_patterns(self) -> List:
        """Return regex patterns (fallback only, HTML parsing is primary)."""
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt_erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method)."""
        soup = BeautifulSoup(raw_content, 'html.parser')
        events = []
        
        # Find all event cards
        event_cards = soup.select('li.SP-TeaserList__item div.SP-Teaser')
        
        for card in event_cards:
            try:
                # Extract detail page URL
                detail_link = card.select_one('a.SP-Teaser__link')
                if not detail_link:
                    continue
                
                href_attr = detail_link.get('href')
                detail_url = ''
                if isinstance(href_attr, str) and href_attr:
                    detail_url = href_attr
                    if detail_url.startswith('/'):
                        detail_url = f"https://www.leverkusen.de{detail_url}"
                
                # Extract event title
                title_elem = card.select_one('h2')
                title = title_elem.get_text(strip=True) if title_elem else ""
                if not title:
                    continue
                
                # Extract date and time
                date_elem = card.select_one('time.SP-Scheduling__date')
                time_elem = card.select_one('span.SP-EventInformation__time')
                
                # Parse date from datetime attribute
                date_str = ""
                time_str = ""
                event_date = None
                if date_elem:
                    date_attr = date_elem.get('datetime')
                    if date_attr and isinstance(date_attr, str):
                        date_str = self._parse_datetime(date_attr)
                        # Parse event date for filtering
                        try:
                            event_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                        except Exception:
                            pass
                
                if time_elem:
                    time_str = time_elem.get_text(strip=True)
                
                # Skip events outside 14-day window
                if event_date:
                    days_from_today = (event_date - self.today.date()).days
                    if days_from_today < 0 or days_from_today > 14:
                        continue
                
                # Extract location (not available on card, leave empty)
                location = ""
                
                # Extract category
                cat_elem = card.select_one('span.SP-Kicker__text')
                category = cat_elem.get_text(strip=True) if cat_elem else "other"
                
                # Extract description (from teaser)
                desc_elem = card.select_one('div.SP-Paragraph.SP-Teaser__paragraph')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Skip advertising
                if category in self.ADVERTISING_CATEGORIES:
                    continue
                
                events.append(Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category=category,
                    event_url=detail_url or '',
                ))
            
            except Exception as e:
                print(f"[StadtErleben] Failed to parse event card: {e}")
                continue
        
        print(f"[StadtErleben] HTML parsing returned {len(events)} events")
        return events
    
    def _parse_datetime(self, iso_datetime: str) -> str:
        """Parse ISO 8601 datetime to DD.MM.YYYY."""
        try:
            dt = datetime.fromisoformat(iso_datetime.split('+')[0])
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return ""
    
    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.
        
        Returns:
            Dictionary mapping event name to detail URL.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}
        
        # Find all event cards with detail links
        for card in soup.select('li.SP-TeaserList__item'):
            try:
                detail_link = card.select_one('a.SP-Teaser__link')
                title_elem = card.select_one('h2')
                
                if detail_link and title_elem:
                    title = title_elem.get_text(strip=True)
                    href_attr = detail_link.get('href')
                    if isinstance(href_attr, str) and href_attr:
                        href = href_attr
                        if href.startswith('/'):
                            href = f"https://www.leverkusen.de{href}"
                        event_url_map[title] = href
            
            except Exception as e:
                continue
        
        print(f"[StadtErleben] Extracted {len(event_url_map)} event detail URLs")
        return event_url_map
    
    def parse_internal_detail_page(self, detail_html: str) -> dict | None:
        """Parse internal leverkusen.de detail page.
        
        Args:
            detail_html: Raw HTML content from event detail page.
        
        Returns:
            Dictionary with detail information (detail_description, end_time).
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}
        
        # Extract full description
        desc_elem = soup.select_one('div.tribe-events-single-event-description')
        if desc_elem:
            paragraphs = desc_elem.select('p')
            descriptions = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    descriptions.append(text)
            
            if descriptions:
                detail_data['detail_description'] = '\n\n'.join(descriptions[:2])
        
        # Extract end time
        end_time_elem = soup.select_one('div.tribe-events-single-event-information time')
        if end_time_elem:
            time_str = end_time_elem.get_text(strip=True)
            # Parse "bis HH:MM Uhr" format
            import re
            match = re.search(r'bis\s+(\d{1,2}:\d{2})\s+Uhr', time_str)
            if match:
                hours = match.group(1)
                minutes = match.group(2)
                detail_data['end_time'] = f"{hours:02d}:{minutes}:00 Uhr"
        
        return detail_data if detail_data else None
    
    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse detail page (handles both internal and external pages)."""
        # Check if internal or external page
        if 'leverkusen.de' in detail_html:
            return self.parse_internal_detail_page(detail_html)
        
        # Handle external pages (lust-auf-leverkusen.de)
        # These are separate sites with their own scrapers - skip
        return None
    
    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data for events.
        
        For each event, fetches detail page and extracts:
        - detail_description: Full event description
        - end_time: End time (if available)
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        event_url_map = self.get_event_urls_from_html(raw_html)
        
        print(f"[StadtErleben Level 2] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            detail_url = event_url_map.get(event.name, "")
            if not detail_url:
                # Skip external pages
                continue
                if 'lust-auf-leverkusen.de' in detail_url:
                    continue
            
            event.event_url = detail_url
            
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
        
        print(f"[StadtErleben Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events
