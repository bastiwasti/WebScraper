"""HTML-based parser for Schloss Benrath event pages."""
from typing import List, Optional
from rules.base import BaseRule, Event
from rules import categories, utils
import requests


class SchlossBenrathRegex(BaseRule):
    """HTML parser for Schloss Benrath events.

    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results

    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: DD.MM.YYYY)
    - time (required): Event time (format: HH:MM Uhr)
    - location (required): Event location/venue
    - description (required): Event description (from detail page)
    - source (required): Set to self.url
    - category: Inferred from category data attribute
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping

    NO DATE FILTERING:
    - All events on page are processed regardless of date
    - Level 2 scraping fetches detail pages for all events
    """

    MAX_PAGES = 1

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Schloss Benrath events.

        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Schloss Benrath pages."""
        return "schloss-benrath.de" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).

        Override BaseRule method to parse HTML directly since website
        has structured event data in HTML cards.
        """
        print("[SchlossBenrath] Using HTML parsing for event extraction")

        from bs4 import BeautifulSoup
        import re

        html_content = raw_content

        soup = BeautifulSoup(html_content, 'html.parser')
        events = []

        cards = soup.select('div.event-teaser')
        print(f"[SchlossBenrath] Found {len(cards)} event-teaser cards")

        for card in cards:
            try:
                link = card.select_one('a.event-teaser__link')
                if not link:
                    continue

                href = link.get('href', '')
                if not href:
                    continue

                if href.startswith('/'):
                    href = 'https://www.schloss-benrath.de' + href

                date_time_elem = card.select_one('.event-teaser__dateAndTime span')
                title_elem = card.select_one('h3')

                date_time_str = date_time_elem.get_text(strip=True) if date_time_elem else ""
                title = title_elem.get_text(strip=True) if title_elem else ""

                if not title:
                    print(f"[SchlossBenrath] Skipping card: no title")
                    continue

                date_str, time_str = self._parse_date_time(date_time_str)

                location = ""
                description = ""

                category = categories.infer_category(description, title)
                category = categories.normalize_category(category)

                events.append(Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category=category,
                    event_url=href,
                    origin=self.get_origin(),
                ))

            except Exception as e:
                print(f"[SchlossBenrath] Failed to parse event card: {e}")
                continue

        print(f"[SchlossBenrath] HTML parsing returned {len(events)} events")
        return events

    def _parse_date_time(self, date_time_str: str) -> tuple[str, str]:
        """Parse date and time from German format.

        Args:
            date_time_str: String like "Sa., 7. März 2026 | 07:00 Uhr"

        Returns:
            Tuple of (date, time) where date is DD.MM.YYYY and time is HH:MM
        """
        import re

        date_str = ""
        time_str = ""

        match = re.search(r'(\d{1,2})\.\s+(\w+)\s+(\d{4})\s*\|\s*(\d{2}):(\d{2})', date_time_str)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2)
            year = match.group(3)
            hour = match.group(4)
            minute = match.group(5)

            month_map = {
                'Januar': '01', 'januar': '01',
                'Februar': '02', 'februar': '02',
                'März': '03', 'märz': '03',
                'April': '04', 'april': '04',
                'Mai': '05', 'mai': '05',
                'Juni': '06', 'juni': '06',
                'Juli': '07', 'juli': '07',
                'August': '08', 'august': '08',
                'September': '09', 'september': '09',
                'Oktober': '10', 'oktober': '10',
                'November': '11', 'november': '11',
                'Dezember': '12', 'dezember': '12',
            }

            month_num = month_map.get(month, month)
            date_str = f"{day}.{month_num}.{year}"
            time_str = f"{hour}:{minute}"

        return date_str, time_str

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

        for card in soup.select('div.event-teaser'):
            try:
                title_elem = card.select_one('h3')
                link = card.select_one('a.event-teaser__link')

                if title_elem and link:
                    title = title_elem.get_text(strip=True)
                    href_attr = link.get('href', '')
                    href = str(href_attr) if href_attr else ''

                    if href.startswith('/'):
                        href = 'https://www.schloss-benrath.de' + href

                    event_url_map[title] = href

            except Exception as e:
                print(f"[SchlossBenrath] Failed to extract URL from card: {e}")
                continue

        print(f"[SchlossBenrath] Extracted {len(event_url_map)} event detail URLs")
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

        try:
            location_elem = soup.select_one('.event-detail__header--location')
            if location_elem:
                detail_data['detail_location'] = location_elem.get_text(strip=True)

            description_text = ""
            for div in soup.find_all('div'):
                classes = div.get('class', [])
                if 'event-detail' in str(classes):
                    paragraphs = div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 50 and 'karten' not in text.lower():
                            description_text = text
                            break
                    if description_text:
                        break

            if description_text:
                detail_data['detail_description'] = description_text

            detail_data['html'] = detail_html[:2000]

        except Exception as e:
            print(f"[SchlossBenrath] Failed to parse detail page: {e}")

        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Schloss Benrath events.

        For each event, fetches detail page and extracts:
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

        print(f"[SchlossBenrath Level 2] Fetching detail pages for {len(events)} events...")

        for event in events:
            detail_url = event_url_map.get(event.name, event.event_url)

            if not detail_url:
                continue

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
                    if 'detail_description' in detail_data:
                        event.description = detail_data['detail_description']
                    if 'detail_location' in detail_data:
                        event.location = detail_data['detail_location']
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")

            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue

        print(f"[SchlossBenrath Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")

        return events
