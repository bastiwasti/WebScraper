"""HTML-based parser for Burscheid Veranstaltungskalender API."""
from typing import List, Optional
from bs4 import BeautifulSoup
import re
import requests

from rules.base import BaseRule, Event
from rules import categories, utils


class VeranstaltungskalenderRegex(BaseRule):
    """HTML parser for Burscheid event calendar via bergisch-live.de API.

    IMPORTANT: HTML parsing is PRIMARY extraction method.
    LLM (DeepSeek) will ONLY be used as fallback if:
    - HTML parsing fails to extract any events
    - HTML extraction returns empty results

    Extracts these fields:
    - name (required): Event name/title
    - date (required): Event date (format: DD.MM.YYYY)
    - time (required): Event time (from time element)
    - location (required): Event location/venue
    - description (required): Event description (from teaser + Level 2)
    - source (required): Set to API URL
    - category: Inferred from keywords
    - event_url: Extracted from bergisch-live.de links
    - raw_data: Populated by Level 2 scraping
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Burscheid Veranstaltungskalender pages."""
        return "burscheid.de" in url and "veranstaltungskalender" in url

    def get_regex_patterns(self) -> List:
        """Return regex patterns for Burscheid events.

        These patterns are fallback only. HTML parsing is primary method.
        """
        return []

    def parse_with_regex(self, raw_content: str) -> List[Event]:
        """Parse content using HTML parsing (primary method).

        Override BaseRule method to parse HTML directly since the API
        returns structured event data in HTML cards.
        """
        print("[Burscheid] Using HTML parsing for event extraction")

        soup = BeautifulSoup(raw_content, 'html.parser')
        events = []

        # Track current year from month headers
        current_year = "2026"  # Default to current year

        # Find all month headers to track year
        for monat_elem in soup.find_all('div', class_='klive-monat'):
            monat_text = monat_elem.get_text(strip=True)
            # Extract year from text like "Februar 2026"
            year_match = re.search(r'(\d{4})', monat_text)
            if year_match:
                current_year = year_match.group(1)

        # Find all event boxes
        for terminbox in soup.find_all('div', class_='klive-terminbox'):
            try:
                # Extract event ID from the anchor tag before the terminbox
                # Format: <a name="613962"></a>
                id_elem = terminbox.find_previous('a', attrs={'name': True})
                event_id = id_elem.get('name', '') if id_elem else ''

                # Extract date/time
                datum_elem = terminbox.find('div', class_='klive-datumuhrzeit')
                if not datum_elem:
                    continue

                # Parse date from klive-datum structure
                tag_elem = datum_elem.find('span', class_='klive-datum-tag')
                monat_elem = datum_elem.find('span', class_='klive-datum-monat')
                day_elem = terminbox.find('div', class_='klive-tag')

                day = tag_elem.get_text(strip=True) if tag_elem else ""
                month = monat_elem.get_text(strip=True) if monat_elem else ""

                # Normalize date (month is already in MM format from API)
                # Remove trailing dots and spaces
                day = day.rstrip('. ')
                month = month.rstrip('. ')

                date_str = f"{day}.{month}.{current_year}"
                date_str = utils.normalize_date(date_str)

                # Parse time
                zeit_elem = datum_elem.find('div', class_='klive-zeit')
                if zeit_elem:
                    time_str = zeit_elem.get_text(strip=True)
                    # Extract end time if present
                    ende_elem = zeit_elem.find('span', class_='ende')
                    if ende_elem:
                        time_str = time_str.replace('&ndash;', '-').replace('–', '-')
                    time_str = utils.normalize_time(time_str)
                else:
                    time_str = ""

                # Extract title
                titel_elem = terminbox.find('span', class_='klive-titel-artist')
                if not titel_elem:
                    continue
                title = titel_elem.get_text(strip=True)

                # Extract subtitle if available
                subtitel_elem = terminbox.find('span', class_='klive-titel-subtitel')
                subtitel = subtitel_elem.get_text(strip=True) if subtitel_elem else ""

                # Extract location from tags
                tags_elem = terminbox.find('span', class_='klive-tags')
                location = ""
                if tags_elem:
                    loc_elem = tags_elem.find('span', class_='klive-location-notdefault')
                    if loc_elem:
                        location = loc_elem.get_text(strip=True)
                        # Clean up location text
                        location = re.sub(r'Veranstaltungsort:\s*', '', location, flags=re.IGNORECASE)

                # Extract category
                rubrik_elem = terminbox.find('span', class_='klive-rubrik')
                category = "other"
                if rubrik_elem:
                    rubrik_text = rubrik_elem.get_text(strip=True)
                    category = self._map_rubrik_to_category(rubrik_text)

                # Build description from title + subtitle
                description = title
                if subtitel:
                    description += f" - {subtitel}"

                # Create event URL
                event_url = f"https://www.bergisch-live.de/{event_id}" if event_id else ""

                if not title or not date_str:
                    continue

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
                print(f"[Burscheid] Failed to parse event card: {e}")
                continue

        print(f"[Burscheid] HTML parsing returned {len(events)} events")
        return events

    def _map_rubrik_to_category(self, rubrik: str) -> str:
        """Map rubrik text to standard category.

        Args:
            rubrik: Rubrik text from the event.

        Returns:
            Standard category ID.
        """
        rubrik_lower = rubrik.lower()

        # Direct mappings
        category_map = {
            "sport": "sport",
            "kultur": "culture",
            "bildung": "education",
            "musik": "culture",
            "theater": "culture",
            "markt": "market",
            "fest": "festival",
        }

        for key, cat in category_map.items():
            if key in rubrik_lower:
                return cat

        # Fall back to inference
        return categories.infer_category(rubrik)

    def get_event_ids_from_html(self, raw_html: str) -> List[str]:
        """Extract event IDs from calendar HTML.

        Args:
            raw_html: Raw HTML content from calendar page.

        Returns:
            List of event IDs.
        """
        soup = BeautifulSoup(raw_html, 'html.parser')
        event_ids = []

        for terminbox in soup.find_all('div', class_='klive-terminbox'):
            # Find the anchor tag before the terminbox with name attribute
            id_elem = terminbox.find_previous('a', attrs={'name': True})
            if id_elem:
                event_id = id_elem.get('name', '')
                if event_id:
                    event_ids.append(event_id)

        print(f"[Burscheid] Extracted {len(event_ids)} event IDs")
        return event_ids

    def fetch_level2_data(self, events: List[Event], raw_html: str | None = None) -> List[Event]:
        """Fetch Level 2 detail data for Burscheid events.

        For each event, fetches detail page from bergisch-live.de API and extracts:
        - detail_description: Full event description
        - detail_location: Enhanced location information

        Args:
            events: List of Event objects from Level 1 parsing.
            raw_html: Raw HTML content from main page (for URL extraction).

        Returns:
            List of Event objects with Level 2 data in raw_data field.
        """
        if not events:
            return events

        client = "burscheid.de"
        print(f"[Burscheid Level 2] Fetching detail pages for {len(events)} events...")

        for event in events:
            try:
                # Extract event ID from event_url or from raw_html
                event_id = ""
                if event.event_url:
                    # Extract ID from URL like https://www.bergisch-live.de/613962
                    match = re.search(r'/(\d+)$', event.event_url)
                    if match:
                        event_id = match.group(1)

                if not event_id and raw_html:
                    # Try to find ID by searching for event name in HTML
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    for terminbox in soup.find_all('div', class_='klive-terminbox'):
                        titel_elem = terminbox.find('span', class_='klive-titel-artist')
                        if titel_elem and event.name in titel_elem.get_text(strip=True):
                            id_elem = terminbox.find_previous('a', attrs={'name': True})
                            if id_elem:
                                event_id = id_elem.get('name', '')
                                break

                if not event_id:
                    print(f"  ✗ Could not find ID for: {event.name[:50]}")
                    continue

                # Build detail API URL
                detail_url = f"https://www.bergisch-live.de/events/client={client};mode=utf8;what=detail;show={event_id}"

                # Fetch detail HTML
                resp = requests.get(
                    detail_url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"},
                )
                resp.raise_for_status()
                detail_html = resp.text

                # Parse detail HTML
                detail_data = self._parse_detail_html(detail_html)

                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")

            except Exception as e:
                print(f"  ✗ Failed to fetch detail page: {e}")
                continue

        print(f"[Burscheid Level 2] Completed: {sum(1 for e in events if e.raw_data)}/{len(events)} events with detail data")
        return events

    def _parse_detail_html(self, detail_html: str) -> dict | None:
        """Parse event detail HTML to extract enhanced information.

        Args:
            detail_html: Raw HTML content from event detail page.

        Returns:
            Dictionary with detail information (detail_description, detail_location).
        """
        soup = BeautifulSoup(detail_html, 'html.parser')
        detail_data = {}

        # Extract description from langfassung body text
        body_elem = soup.find('div', class_='klive-langfassung-inhalt')
        if body_elem:
            text_content = body_elem.get_text(separator=' ', strip=True)
            # Clean up the text
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            if len(text_content) > 50:
                detail_data['detail_description'] = text_content

        # Extract location info from langfassung
        loc_elem = soup.find('div', class_='klive-langfassung-veranstaltungsort')
        if loc_elem:
            location = loc_elem.get_text(separator=' ', strip=True)
            if location:
                # Clean up location text
                location = re.sub(r'\s+', ' ', location).strip()
                detail_data['detail_location'] = location

        return detail_data if detail_data else None
