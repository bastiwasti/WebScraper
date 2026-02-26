"""API-based scraper for eventim.de aggregator.

Uses the public eventim API to fetch structured event data.
No browser/Playwright needed - pure HTTP requests returning JSON.

API endpoint: https://public-api.eventim.com/websearch/search/api/exploration/v1/products
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse, parse_qs

import requests

from rules.base import BaseScraper, Event
from rules import utils


logger = logging.getLogger(__name__)


class EventimScraper(BaseScraper):
    """API-based scraper for eventim.de.

    Fetches events per city using the public eventim API.
    The city name is extracted from the URL query parameter `city_names`.
    """

    API_BASE = "https://public-api.eventim.com/websearch/search/api/exploration/v1/products"
    MAX_PER_PAGE = 50  # API hard limit

    def __init__(self, url: str):
        super().__init__(url)
        self.city_name = self._extract_city_from_url(url)

        today = datetime.now()
        self.date_from = today.strftime("%Y-%m-%d")
        self.date_to = (today + timedelta(days=180)).strftime("%Y-%m-%d")

        logger.info(f"[Eventim] City: {self.city_name}, date range: {self.date_from} to {self.date_to}")
        print(f"[Eventim] City: {self.city_name}, date range: {self.date_from} to {self.date_to}")

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return "eventim.com" in url or "eventim.de" in url

    @property
    def needs_browser(self) -> bool:
        return False

    def fetch(self) -> str:
        """Not used — fetch_events_from_api() takes over."""
        return ""

    def fetch_events_from_api(self) -> list:
        """Fetch events from the eventim public API.

        Note: The API returns max 50 products per request and pagination
        is non-functional (all pages return the same results). With
        sort=DateAsc we always get the nearest upcoming events first,
        which is exactly what we need.

        Returns:
            List of Event objects.
        """
        print(f"[Eventim] Starting API scraper for: {self.city_name}")
        logger.info(f"[Eventim] Starting API scraper for: {self.city_name}")

        params = {
            "webId": "web__eventim-de",
            "language": "de",
            "retail_partner": "EVE",
            "city_names": self.city_name,
            "sort": "DateAsc",
            "top": self.MAX_PER_PAGE,
            "date_from": self.date_from,
            "date_to": self.date_to,
        }

        try:
            resp = requests.get(
                self.API_BASE,
                params=params,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"[Eventim] API request failed: {e}")
            print(f"[Eventim] API request failed: {e}")
            return []

        products = data.get("products", [])
        total_available = data.get("totalResults", len(products))
        print(f"[Eventim] Got {len(products)} products (API reports {total_available} total for {self.city_name})")
        logger.info(f"[Eventim] Got {len(products)} products (API reports {total_available} total for {self.city_name})")

        # Convert to Event objects
        events = []
        for product in products:
            event = self._create_event_from_product(product)
            if event:
                events.append(event)

        print(f"[Eventim] Created {len(events)} Event objects for {self.city_name}")
        logger.info(f"[Eventim] Created {len(events)} Event objects for {self.city_name}")

        return events

    def _extract_city_from_url(self, url: str) -> str:
        """Extract city_names parameter from the API URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        city_names = params.get("city_names", [""])
        return city_names[0] if city_names else ""

    def _create_event_from_product(self, product: dict) -> Optional[Event]:
        """Create an Event from an eventim API product object."""
        name = product.get("name", "").strip()
        if not name:
            return None

        description = product.get("description", "") or ""
        link = product.get("link", "")

        # Extract date/time and location from typeAttributes
        type_attrs = product.get("typeAttributes", {})
        live_ent = type_attrs.get("liveEntertainment", {})

        start_date_str = live_ent.get("startDate", "")
        location_data = live_ent.get("location", {})

        # Parse date and time from ISO format
        date_normalized = ""
        time_normalized = ""
        if start_date_str:
            try:
                dt = datetime.fromisoformat(start_date_str)
                date_normalized = utils.normalize_date(dt.strftime("%Y-%m-%d"))
                time_normalized = dt.strftime("%H:%M")
            except Exception as e:
                logger.warning(f"[Eventim] Failed to parse date '{start_date_str}': {e}")

        # Extract location
        venue_name = location_data.get("name", "") if isinstance(location_data, dict) else ""
        city_raw = location_data.get("city", "") if isinstance(location_data, dict) else ""

        # Normalize city
        city = utils.map_aggregator_city(city_raw, self.city_name)

        # Build price info for description enrichment
        price = product.get("price")
        currency = product.get("currency", "EUR")
        if price and description:
            description = f"{description} (ab {price} {currency})"
        elif price:
            description = f"ab {price} {currency}"

        return Event(
            name=name,
            description=description,
            location=venue_name,
            date=date_normalized,
            time=time_normalized,
            source=link,
            city=city,
            event_url=link,
            origin=self.get_origin(),
        )
