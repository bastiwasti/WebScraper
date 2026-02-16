"""Regex parser for Monheim terminkalender event pages."""

import re
from typing import List, Optional

from rules.base import BaseRule, Event


class TerminkalenderRegex(BaseRule):
    """Regex parser for Monheim terminkalender events."""

    def get_regex_patterns(self) -> List[re.Pattern]:
        """Return regex patterns for Monheim events.

        Matches cleaned text format: HH.MM Uhr Event Name (no space after Uhr)
        """
        patterns = [
            re.compile(
                r'(\d{1,2}\.\d{2})\s*Uhr\s*([A-ZÄÖÜ][^K\d]+?)(?=\s*\d{1,2}\.\d{2}\s*Uhr|Kategorie:|\s*$)',
                re.DOTALL | re.MULTILINE
            ),
        ]
        return patterns

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Monheim terminkalender pages."""
        return "monheim.de" in url and "terminkalender" in url.lower()

    def _create_event_from_match(self, match: tuple) -> Optional[Event]:
        """Create Event from Monheim regex match.

        Format: HH.MM Uhr<br>Event Name
        Group 1: Time (HH.MM)
        Group 2: Event name
        """
        if len(match) < 2:
            return None

        time = match[0].strip() if len(match) > 0 else ""
        name = match[1].strip() if len(match) > 1 else ""

        # Format time as HH.MM Uhr
        if time and not time.endswith(' Uhr'):
            time = time + ' Uhr'

        source = self.url

        if not name:
            return None

        category = self._infer_category("", name)

        return Event(
            name=name,
            description="",
            location="",
            date="",  # Date will be filled from H1
            time=time,
            source=source,
            category=category,
        )

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (not regex).
        
        Override BaseRule method to parse HTML directly since the website
        has structured event data in HTML that's better than regex on cleaned text.
        """
        print("[Terminkalender] Using custom HTML parsing")
        
        from bs4 import BeautifulSoup
        import re
        import requests
        
        # Fetch raw HTML for parsing
        try:
            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()
            html_content = resp.text
        except Exception as e:
            print(f"[Terminkalender] Failed to fetch HTML: {e}, falling back to cleaned text")
            html_content = raw_content
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        events = []
        
        # Parse H1 date ranges and track current date
        current_h1_date = None
        
        # Iterate through all elements to track H1 dates in order
        for element in soup.find_all(True):
            if element.name == 'h1':
                h1_text = element.get_text(strip=True)
                # Extracts START date of range: "Mittwoch, 11. Februar 2026 - Mittwoch, 11. März 2026"
                date_match = re.search(r'(\d{1,2}\.\s+\w+\s+\d{4})', h1_text)
                if date_match:
                    current_h1_date = date_match.group(1)
        
        for div in soup.find_all('div', class_='info'):
            title_span = div.find('span', class_='title')
            if not title_span:
                continue
            
            title_text = title_span.get_text(strip=True)
            match = re.search(r'(\d{1,2}\.\d{2})\s*Uhr\s*(.+)', title_text)
            if match:
                time = match.group(1) + ' Uhr'
                name = match.group(2).strip()

                # Use H1 date as default
                date = current_h1_date or ""

                if name:
                    from rules import categories, utils
                    # Infer and normalize category
                    category = categories.infer_category("", name)
                    category = categories.normalize_category(category)
                    # Normalize time format
                    time = utils.normalize_time(time)
                    # Normalize date format
                    date = utils.normalize_date(date)

                    events.append(Event(
                        name=name,
                        description="",
                        location="",
                        date=date,
                        time=time,
                        source=self.url,
                        category=category,
                    ))
        
        print(f"[Terminkalender] HTML parsing returned {len(events)} events")
        return events

    def get_event_urls_from_html(self, raw_html: str) -> list[str]:
        """Extract event detail URLs from calendar page raw HTML.

        Args:
            raw_html: Raw HTML content from calendar page.

        Returns:
            List of unique event detail URLs (e.g., "/freizeit-tourismus/terminkalender/termin/slug-id").
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, 'html.parser')
        urls = []

        for link in soup.find_all('a', class_='url date'):
            href = link.get('href', '')
            title = str(link.get('title', '')) if link.get('title') else ''
            if href and '/freizeit-tourismus/terminkalender/termin/' in href and title:
                urls.append(href)

        return urls

    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse event detail page to extract enhanced information.

        Args:
            detail_html: Raw HTML content from event detail page.

        Returns:
            Dictionary with detail information (detail_title, detail_date, detail_time,
            detail_end_time, detail_location, detail_description, detail_category).
        """
        from bs4 import BeautifulSoup
        import re

        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}

        dt_tags = soup.find_all('dt')
        for dt in dt_tags:
            label = dt.get_text(strip=True)
            dd = dt.find_next_sibling('dd')
            if not dd:
                continue

            value = dd.get_text(strip=True)

            if label in ['Termin:', 'Termine:']:
                detail_data['detail_date'] = value.replace('*', '').strip()
            elif label == 'Beginn:':
                time_match = re.search(r'(\d{1,2}:\d{2})', value)
                if time_match:
                    detail_data['detail_time'] = time_match.group(1) + ' Uhr'
            elif label == 'Ende:':
                end_time_match = re.search(r'(\d{1,2}:\d{2})', value)
                if end_time_match:
                    detail_data['detail_end_time'] = end_time_match.group(1) + ' Uhr'

        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            if text.startswith('Ort:'):
                detail_data['detail_location'] = text.replace('Ort:', '').strip()
                break

        for elem in soup.find_all('p'):
            text = elem.get_text(strip=True)
            if 'Kategorie:' in text:
                match = re.search(r'Kategorie:\s*(\w+)', text)
                if match:
                    detail_data['detail_category'] = match.group(1).strip()
                break

        description_parts = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if (len(text) > 30 and
                not any(x in text for x in ['Terminkalender', 'zurück', 'Häufig gesucht', 'Kategorie:', 'Ort:'])):
                description_parts.append(text)
                if len(description_parts) >= 2:
                    break

        if description_parts:
            detail_data['detail_description'] = ' '.join(description_parts)

        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Monheim terminkalender events.
        
        For each event, fetches the detail page and extracts:
        - detail_date: More accurate date
        - detail_time: Start time
        - detail_end_time: End time
        - detail_location: Event venue/location
        - detail_description: Event description
        - detail_category: Event category
        
        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).
        
        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events
        
        from bs4 import BeautifulSoup
        import re
        import requests
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # Build mapping of event name -> detail URL
        event_url_map = {}
        
        for div in soup.find_all('div', class_='info'):
            link = div.find('a', class_='url date')
            if not link:
                continue
            
            href = link.get('href')
            title = str(link.get('title')) if link.get('title') else ''
            
            if href and title and '/freizeit-tourismus/terminkalender/termin/' in str(href):
                # Convert to full URL if relative
                href_str = str(href)
                if href_str.startswith('/'):
                    href_str = 'https://www.monheim.de' + href_str
                event_url_map[title] = href_str
        
        # Fetch detail pages and merge data
        print(f"[Terminkalender Level 2] Fetching detail pages for {len(events)} events...")
        
        for event in events:
            detail_url = event_url_map.get(event.name, "")
            
            if not detail_url:
                # No detail URL found for this event, skip Level 2 scraping
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
                
                # Parse detail page
                detail_data = self.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url  # Use detail URL as source when Level 2 succeeds
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
            
            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue
        
        print(f"[Terminkalender Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        
        return events
    
