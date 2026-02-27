"""HTML-based parser for Marienburg Monheim events pages."""

from typing import List
from bs4 import BeautifulSoup
import re
import requests

from rules.base import BaseRule, Event
from rules import categories, utils


class MarienburgEventsRegex(BaseRule):
    """HTML parser for Marienburg Monheim events.

    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results

    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: D.M.YYYY or DD.MM.YYYY)
    - time (required): Event time (from datetime attribute)
    - location (required): Event location/venue
    - description (required): Event description (from detail page)
    - source (required): Set to self.url
    - category: Inferred from keywords
    - event_url: Extracted from detail page links
    - raw_data: Populated by Level 2 scraping

    NO DATE FILTERING:
    - All events on page are processed regardless of date
    - Level 2 scraping fetches detail pages for all events
    """

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Marienburg Monheim events.

        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Marienburg Monheim events pages."""
        return "marienburgmonheim.de" in url and "/events" in url

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).

        Override BaseRule method to parse HTML directly since website
        has structured event data in HTML cards.
        """
        print("[MarienburgEvents] Using HTML parsing for event extraction")

        html_content = raw_content

        soup = BeautifulSoup(html_content, 'html.parser')
        events = []

        for card in soup.find_all('div', class_='event-item'):
            try:
                title_elem = card.find('h2', class_='card-title')
                if not title_elem:
                    continue

                title_link = title_elem.find('a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                detail_url = title_link.get('href', '')

                if not title:
                    continue

                date_elem = card.find('time')
                datetime_attr = str(date_elem.get('datetime', '')) if date_elem else ''

                date_str = ''
                time_str = ''

                if datetime_attr:
                    datetime_match = re.match(r'(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})', datetime_attr)
                    if datetime_match:
                        iso_date = datetime_match.group(1)
                        time_str = datetime_match.group(2)
                        date_str = utils.normalize_date(iso_date)

                event_url = ''
                if detail_url:
                    detail_url_str = str(detail_url)
                    if detail_url_str.startswith('/'):
                        event_url = f"https://marienburgmonheim.de{detail_url_str}"
                    elif detail_url_str.startswith('http'):
                        event_url = detail_url_str

                location = 'Marienburg Monheim, Bleer Str. 33, 40789 Monheim am Rhein'
                description = ''

                category = categories.infer_category(description, title)
                category = categories.normalize_category(category)

                time_str = utils.normalize_time(time_str)

                event = Event(
                    name=title,
                    description=description,
                    location=location,
                    date=date_str,
                    time=time_str,
                    source=self.url,
                    category=category,
                    event_url=event_url,
                    origin=self.get_origin(),
                )

                events.append(event)

            except Exception as e:
                print(f"[MarienburgEvents] Failed to parse event card: {e}")
                continue

        print(f"[MarienburgEvents] HTML parsing returned {len(events)} events")
        return events

    def get_event_urls_from_html(self, raw_html: str) -> dict[str, str]:
        """Extract event detail URLs from calendar page raw HTML.

        Args:
            raw_html: Raw HTML content from calendar page.

        Returns:
            Dictionary mapping event name to detail URL.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_url_map = {}

        for card in soup.find_all('div', class_='event-item'):
            try:
                title_elem = card.find('h2', class_='card-title')
                if not title_elem:
                    continue

                title_link = title_elem.find('a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href_attr = title_link.get('href', '')

                if href_attr:
                    href_attr_str = str(href_attr)
                    if href_attr_str.startswith('/'):
                        href = f"https://marienburgmonheim.de{href_attr_str}"
                    elif href_attr_str.startswith('http'):
                        href = href_attr_str
                    else:
                        href = f"https://marienburgmonheim.de/{href_attr_str}"

                    event_url_map[title] = href

            except Exception as e:
                print(f"[MarienburgEvents] Failed to extract URL from card: {e}")
                continue

        print(f"[MarienburgEvents] Extracted {len(event_url_map)} event detail URLs")
        return event_url_map

    def parse_detail_page(self, detail_html: str) -> dict | None:
        """Parse event detail page to extract enhanced information.

        Args:
            detail_html: Raw HTML content from event detail page.

        Returns:
            Dictionary with detail information (detail_description, detail_location, detail_time).
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}

        h1_elem = soup.find('h1')
        if h1_elem:
            title = h1_elem.get_text(strip=True)
            detail_data['detail_title'] = title

        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc:
            desc = str(meta_desc.get('content', ''))
            if len(desc) > 20:
                detail_data['detail_description'] = desc

        main_content = soup.find('article')
        if main_content:
            paragraphs = main_content.find_all('p')
            full_desc = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

            if len(full_desc) > 50 and 'detail_description' not in detail_data:
                detail_data['detail_description'] = full_desc[:2000]

            location_patterns = [
                r'📍\s*<strong>Treffpunkt:</strong>\s*([^<]+)',
                r'Treffpunkt:\s*([^<\n]+)',
            ]

            html_content = str(main_content)
            for pattern in location_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    detail_data['detail_location'] = re.sub(r'<[^>]+>', '', location)
                    break

            time_patterns = [
                r'⏰\s*<strong[^>]*>(\d{1,2}:\d{2})\s*–\s*(\d{1,2}:\d{2})\s*Uhr</strong>',
                r'⏰\s*(\d{1,2}:\d{2})\s*–\s*(\d{1,2}:\d{2})\s*Uhr',
                r'<strong[^>]*>(\d{1,2}:\d{2})\s*–\s*(\d{1,2}:\d{2})\s*Uhr</strong>',
            ]

            for pattern in time_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    start_time = match.group(1)
                    end_time = match.group(2) if len(match.groups()) > 1 else ''
                    detail_data['detail_time'] = f"{start_time} - {end_time}" if end_time else start_time
                    break

        return detail_data if detail_data else None

    def fetch_level2_data(self, events: list[Event], raw_html: str | None = None) -> list[Event]:
        """Fetch Level 2 detail data for Marienburg Monheim events.

        For each event, fetches the detail page and extracts:
        - detail_description: Full event description
        - detail_location: Enhanced location information
        - detail_time: Event time information

        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).

        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events or not raw_html:
            return events

        event_url_map = self.get_event_urls_from_html(raw_html)

        print(f"[MarienburgEvents Level 2] Fetching detail pages for {len(events)} events...")

        for event in events:
            detail_url = event_url_map.get(event.name, event.event_url)

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

                    if 'detail_description' in detail_data:
                        event.description = detail_data['detail_description']
                    if 'detail_location' in detail_data:
                        event.location = detail_data['detail_location']
                    if 'detail_time' in detail_data:
                        event.time = utils.normalize_time(detail_data['detail_time'])

                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")

            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue

        print(f"[MarienburgEvents Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")

        return events
