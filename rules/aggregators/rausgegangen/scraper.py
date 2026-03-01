"""Hybrid scraper for rausgegangen.de aggregator.

Uses Level 1 + Level 2 approach:
- Level 1: Extract event URLs from city page (with 20km radius)
- Level 2: Fetch each event detail page for rich data via JSON-LD schema

This provides structured event data including:
- Name, description, dates, times
- Full location (name, address, city)
- Price information
- Source URLs
"""

import json
import logging
import re
from typing import List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright

from bs4 import BeautifulSoup
from rules.base import BaseScraper, Event
from rules import utils


logger = logging.getLogger(__name__)


class RausgegangenScraper(BaseScraper):
    """Hybrid scraper for rausgegangen.de aggregator.
    
    Focuses on Monheim with 20km radius, returns events from
    multiple cities within that radius. City mapping handles
    normalization of returned city names.
    """

    # Event detail page URL pattern (matches full and relative URLs)
    # Matches: /events/xyz/ or /en/events/xyz/ or https://rausgegangen.de/events/xyz/
    EVENT_URL_PATTERN = r'(?:https://rausgegangen\.de)?/?(?:en/)?events/([^/]+)/'

    # City code mapping for URL-based city extraction
    # Maps URL city codes (lowercase) to internal normalized city names
    CITY_CODE_MAPPING = {
        "kol": "koeln",
        "koln": "koeln",
        "dusseldorf": "dusseldorf",
        "duesseldorf": "dusseldorf",
        "solingen": "solingen",
        "neuss": "neuss",
        "leverkusen": "leverkusen",
        "monheim": "monheim_am_rhein",
        "langenfeld": "langenfeld",
        "hilden": "hilden",
        "dormagen": "dormagen",
        "burscheid": "burscheid",
        "leichlingen": "leichlingen",
        "hitdorf": "hitdorf",
        "ratingen": "ratingen",
        "haan": "haan",
        "bergisch": "bergisch_gladbach",
        "frechen": "frechen",
        "erkrath": "erkrath",
        "wuppertal": "wuppertal",
        "mettmann": "mettmann",
        "pulheim": "pulheim",
        "grevenbroich": "grevenbroich",
    }

    def __init__(self, url: str):
        super().__init__(url)
        self.base_url = "https://rausgegangen.de"
        
        today = datetime.now()
        self.date_range_start = today
        self.date_range_end = today + timedelta(days=14)
        
        logger.info(f"[Rausgegangen] Date range: {self.date_range_start.strftime('%Y-%m-%d')} to {self.date_range_end.strftime('%Y-%m-%d')} (14 days)")
        print(f"[Rausgegangen] Date range: {self.date_range_start.strftime('%Y-%m-%d')} to {self.date_range_end.strftime('%Y-%m-%d')} (14 days)")

    @property
    def needs_browser(self) -> bool:
        """Rausgegangen requires Playwright for dynamic content."""
        return True

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle rausgegangen.de pages."""
        return "rausgegangen.de" in url

    def fetch_events_from_api(self) -> list:
        """Fetch all events using hybrid approach (Level 1 + Level 2).
        
        Returns:
            List of Event objects directly (not text).
        
        Note: Method name matches pattern from lust_auf scraper
              and is detected by fetch_events_from_url() to bypass
              the standard fetch() → regex_parser flow.
        """
        print(f"[Rausgegangen] Starting hybrid scraper for: {self.url}")
        logger.info(f"[Rausgegangen] Starting hybrid scraper for: {self.url}")
        
        # Level 1: Extract event URLs from city page
        event_urls = self._extract_event_urls_from_city_page()
        print(f"[Rausgegangen] Found {len(event_urls)} event URLs")
        logger.info(f"[Rausgegangen] Found {len(event_urls)} event URLs")
        
        if not event_urls:
            logger.warning("[Rausgegangen] No event URLs found on city page")
            return []
        
        # Level 2: Fetch event details for each URL
        event_details = self._fetch_event_details(event_urls)
        print(f"[Rausgegangen] Fetched details for {len(event_details)} events")
        logger.info(f"[Rausgegangen] Fetched details for {len(event_details)} events")
        
        # Convert to Event objects and filter by date
        events = []
        events_filtered = 0
        for detail in event_details:
            event = self._create_event_from_detail(detail)
            if event:
                if self._is_within_date_range(event.date):
                    events.append(event)
                else:
                    events_filtered += 1
        
        print(f"[Rausgegangen] Created {len(events)} Event objects (filtered out {events_filtered} events outside 14-day window)")
        logger.info(f"[Rausgegangen] Created {len(events)} Event objects (filtered out {events_filtered} events outside 14-day window)")
        
        return events

    def fetch(self) -> str:
        """Fetch events using hybrid approach.
        
        This method is overridden to directly return Event objects
        instead of raw text, as the hybrid approach produces
        structured data directly.
        
        Returns:
            String representation of events for compatibility.
        """
        logger.info(f"[Rausgegangen] Starting hybrid scraper for: {self.url}")
        print(f"[Rausgegangen] Starting hybrid scraper for: {self.url}")
        
        # Level 1: Extract event URLs from city page
        event_urls = self._extract_event_urls_from_city_page()
        logger.info(f"[Rausgegangen] Found {len(event_urls)} event URLs")
        print(f"[Rausgegangen] Found {len(event_urls)} event URLs")
        
        if not event_urls:
            logger.warning("[Rausgegangen] No event URLs found on city page")
            print("[Rausgegangen] No event URLs found on city page")
            return ""
        
        # Level 2: Fetch event details for each URL
        event_details = self._fetch_event_details(event_urls)
        logger.info(f"[Rausgegangen] Fetched details for {len(event_details)} events")
        print(f"[Rausgegangen] Fetched details for {len(event_details)} events")
        
        # Convert to Event objects
        events = []
        for detail in event_details:
            event = self._create_event_from_detail(detail)
            if event:
                events.append(event)
        
        logger.info(f"[Rausgegangen] Created {len(events)} Event objects")
        print(f"[Rausgegangen] Created {len(events)} Event objects")
        
        # Return formatted text for compatibility with base class
        if events:
            return self._events_to_text(events)
        return ""

    def _extract_event_urls_from_city_page(self) -> List[str]:
        """Extract event detail page URLs from city page (Level 1).
        
        Uses Playwright to load page and extract href attributes
        from event tiles.
        
        Returns:
            List of full event detail page URLs.
        """
        event_urls = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            logger.info(f"[Rausgegangen] Loading city page: {self.url}")
            print(f"[Rausgegangen] Loading city page: {self.url}")
            page.goto(self.url, wait_until="networkidle", timeout=30000)
            
            # Get page content
            content = page.content()
            browser.close()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract all event detail page URLs
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href')
                if not href:
                    continue
                
                # Convert to string if needed
                href = str(href)
                
                # Check if this is an event detail page URL
                if '/events/' in href:
                    # Extract slug
                    match = re.match(self.EVENT_URL_PATTERN, href)
                    if match:
                        event_slug = match.group(1)
                        # Construct full URL
                        full_url = f"{self.base_url}/en/events/{event_slug}/"
                        if full_url not in event_urls:
                            event_urls.append(full_url)
            
            logger.info(f"[Rausgegangen] Extracted {len(event_urls)} unique event URLs")
            print(f"[Rausgegangen] Extracted {len(event_urls)} unique event URLs")
            
        return event_urls

    def _fetch_single_event(self, event_url: str, idx: int, total: int) -> dict | None:
        """Fetch single event detail page with timeout handling.
        
        Args:
            event_url: Event detail page URL.
            idx: Event index for logging.
            total: Total number of events for logging.
        
        Returns:
            Event detail dict or None if failed.
        """
        import requests
        import requests.exceptions
        
        REQUEST_TIMEOUT = 15  # seconds per request
        
        logger.info(f"[Rausgegangen] Fetching event {idx}/{total}: {event_url}")
        print(f"[Rausgegangen] Fetching event {idx}/{total}: {event_url}")
        
        try:
            resp = requests.get(
                event_url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "WeeklyMail/1.0"}
            )
            resp.raise_for_status()
            
            json_ld_data = self._extract_json_ld(resp.text)
            
            if json_ld_data:
                logger.info(f"[Rausgegangen] ✓ Successfully extracted data from {event_url}")
                print(f"[Rausgegangen] ✓ Successfully extracted data from {event_url}")
                return {
                    'url': event_url,
                    'json_ld': json_ld_data,
                    'html': resp.text,
                }
            else:
                logger.warning(f"[Rausgegangen] No JSON-LD found in {event_url}")
                print(f"[Rausgegangen] No JSON-LD found in {event_url}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"[Rausgegangen] ⏱ Timeout fetching {event_url} after {REQUEST_TIMEOUT}s")
            print(f"[Rausgegangen] ⏱ Timeout fetching {event_url} after {REQUEST_TIMEOUT}s")
            return None
        except Exception as e:
            logger.error(f"[Rausgegangen] ✗ Failed to fetch {event_url}: {e}")
            print(f"[Rausgegangen] ✗ Failed to fetch {event_url}: {e}")
            return None
    
    def _fetch_event_details(self, event_urls: List[str]) -> List[dict]:
        """Fetch event detail pages concurrently and extract structured data (Level 2).
        
        For each event URL:
        1. Fetch page (concurrently with ThreadPoolExecutor)
        2. Extract JSON-LD schema
        3. Parse event data (name, dates, location, price)
        
        Args:
            event_urls: List of event detail page URLs.
        
        Returns:
            List of event detail dictionaries.
        """
        import requests
        
        MAX_WORKERS = 5  # Limit concurrent requests
        event_details = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._fetch_single_event, url, idx, len(event_urls)): (idx, url)
                for idx, url in enumerate(event_urls, 1)
            }
            
            completed_count = 0
            for future in as_completed(futures):
                idx, url = futures[future]
                result = future.result()
                
                if result:
                    event_details.append(result)
                    completed_count += 1
                
                if completed_count % 10 == 0:
                    logger.info(f"[Rausgegangen] Progress: {completed_count}/{len(event_urls)} events fetched")
                    print(f"[Rausgegangen] Progress: {completed_count}/{len(event_urls)} events fetched")

        logger.info(f"[Rausgegangen] Completed: {len(event_details)}/{len(event_urls)} events fetched successfully")
        print(f"[Rausgegangen] Completed: {len(event_details)}/{len(event_urls)} events fetched successfully")
        
        return event_details

    def _is_within_date_range(self, date_str: str) -> bool:
        """Check if event date is within 14-day window.
        
        Args:
            date_str: Date string in DD.MM.YYYY format (e.g., "24.02.2026")
        
        Returns:
            True if date is within range, False otherwise.
        """
        if not date_str:
            return False
        
        try:
            event_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            today = self.date_range_start.date()
            fourteen_days = self.date_range_end.date()
            
            return today <= event_date <= fourteen_days
        except Exception as e:
            logger.warning(f"[Rausgegangen] Failed to parse date '{date_str}': {e}")
            return False

    def _extract_json_ld(self, html: str) -> Optional[dict]:
        """Extract JSON-LD schema from HTML.
        
        Looks for <script type="application/ld+json"> tags and parses
        JSON content.
        
        Args:
            html: HTML content of page.
        
        Returns:
            Parsed JSON-LD dictionary or None if not found.
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                script_content = script.string
                if not script_content:
                    continue
                json_data = json.loads(script_content)
                
                # Check if this is an Event schema
                if isinstance(json_data, dict) and json_data.get('@type') == 'Event':
                    return json_data
                
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"[Rausgegangen] Failed to parse JSON-LD: {e}")
                continue
        
        return None

    def _extract_city_from_url(self, event_url: str) -> str:
        """Extract city name from event URL slug (fallback method).

        Parses the URL slug for known city codes (e.g., "...-in-kol-..." → "koeln").

        Args:
            event_url: Full event detail page URL.

        Returns:
            Normalized city name, or empty string if not found.
        """
        match = re.match(r'.*/events/([^/]+)/', event_url)
        if not match:
            return ""

        slug = match.group(1).lower()

        for city_code, normalized_city in self.CITY_CODE_MAPPING.items():
            if f"-{city_code}-" in slug or slug.endswith(f"-{city_code}") or slug.startswith(f"{city_code}-"):
                return normalized_city

        return ""

    def _extract_city_from_name(self, name: str) -> str:
        """Extract city name from event name (fallback method).
        
        Parses event name for "in {city}" pattern (e.g., "...in Köln" → "koeln").
        
        Args:
            name: Event name/title.
        
        Returns:
            Normalized city name, or empty string if not found.
        """
        if not name:
            return ""
        
        import re
        name_lower = name.lower()
        
        for raw_city, normalized_city in utils.AGGREGATOR_CITY_MAPPING.items():
            raw_city_normalized = raw_city.lower().replace(' ', ' ').replace('_', '_')
            pattern = rf'\bin\s+{re.escape(raw_city_normalized)}\b'
            if re.search(pattern, name_lower, re.IGNORECASE):
                return normalized_city
        
        return ""

    def _create_event_from_detail(self, detail: dict) -> Optional[Event]:
        """Create Event object from event detail dictionary.
        
        Extracts data from JSON-LD schema and normalizes it:
        - Maps city name using map_aggregator_city()
        - Normalizes date and time using utils functions
        - Extracts price information
        
        Args:
            detail: Event detail dictionary with 'json_ld' and 'url' keys.
        
        Returns:
            Event object or None if required fields missing.
        """
        json_ld = detail.get('json_ld', {})
        event_url = detail.get('url', '')
        
        if not json_ld:
            return None
        
        # Extract required fields
        name = json_ld.get('name', '').strip()
        if not name:
            logger.warning("[Rausgegangen] Event missing name")
            return None
        
        # Extract dates
        start_date_str = json_ld.get('startDate', '')
        end_date_str = json_ld.get('endDate', '')
        
        # Parse and normalize dates
        date_normalized = ""
        start_time_normalized = ""
        end_time_normalized = ""
        
        if start_date_str:
            try:
                # ISO format: 2026-02-17T16:00+01:00
                start_dt = datetime.fromisoformat(start_date_str.replace('+01:00', '+01:00').replace('Z', '+00:00'))
                date_normalized = utils.normalize_date(start_dt.strftime("%Y-%m-%d"))
                start_time_normalized = start_dt.strftime("%H:%M")
            except Exception as e:
                logger.warning(f"[Rausgegangen] Failed to parse start date '{start_date_str}': {e}")
                print(f"[Rausgegangen] Failed to parse start date '{start_date_str}': {e}")
        
        if end_date_str:
            try:
                end_dt = datetime.fromisoformat(end_date_str.replace('+01:00', '+01:00').replace('Z', '+00:00'))
                end_time_normalized = end_dt.strftime("%H:%M")
            except Exception as e:
                logger.warning(f"[Rausgegangen] Failed to parse end date '{end_date_str}': {e}")
                print(f"[Rausgegangen] Failed to parse end date '{end_date_str}': {e}")
        
        # Extract location
        location_data = json_ld.get('location', {})
        location_name = location_data.get('name', '') if isinstance(location_data, dict) else ''
        address_data = location_data.get('address', {}) if isinstance(location_data, dict) else {}
        
        city_raw = address_data.get('addressLocality', '') if isinstance(address_data, dict) else ''
        postal_code = address_data.get('postalCode', '') if isinstance(address_data, dict) else ''
        street_address = address_data.get('streetAddress', '') if isinstance(address_data, dict) else ''

        city = ""

        city_from_address = utils.extract_city_from_address(city_raw, postal_code, default_city='')
        if city_from_address:
            city = utils.map_aggregator_city(city_from_address, '')

        if not city:
            city = self._extract_city_from_url(event_url)

        if not city:
            city = self._extract_city_from_name(name)

        if not city:
            city = 'monheim_am_rhein'
        
        # Build location string
        location_parts = [location_name, street_address]
        location_string = ', '.join(filter(None, location_parts))
        
        # Extract description
        description = json_ld.get('description', '') or ''
        
        # Extract price
        price_info = ""
        offers = json_ld.get('offers', {})
        if isinstance(offers, dict):
            price = offers.get('price', '0')
            currency = offers.get('priceCurrency', 'EUR')
            if price and price != '0':
                price_info = f"{price} {currency}"
            else:
                price_info = "Free admission"
        
        # Create Event object
        event = Event(
            name=name,
            description=description,
            location=location_string,
            date=date_normalized,
            time=start_time_normalized,
            end_time=end_time_normalized,
            source=event_url,
            category="other",
            city=city,
            event_url=event_url,
            raw_data=detail,  # Store full detail for reference
            origin=self.get_origin(),
        )
        
        return event

    def _events_to_text(self, events: List[Event]) -> str:
        """Convert Event objects to formatted text.
        
        This provides compatibility with the base class fetch() method
        which returns a string.
        
        Args:
            events: List of Event objects.
        
        Returns:
            Formatted text representation of events.
        """
        lines = []
        lines.append(f"Events from {self.url}\n")
        lines.append(f"Total: {len(events)} events\n")
        
        for event in events:
            lines.append(f"\nEvent: {event.name}")
            lines.append(f"  Date: {event.date}")
            lines.append(f"  Time: {event.time}{f' - {event.end_time}' if event.end_time else ''}")
            lines.append(f"  Location: {event.location}")
            lines.append(f"  City: {event.city}")
            lines.append(f"  Source: {event.source}")
            if event.description:
                lines.append(f"  Description: {event.description[:200]}...")
        
        return '\n'.join(lines)
