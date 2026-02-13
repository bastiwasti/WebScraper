"""Scraper for Leverkusen Lust-Auf website.

Uses REST API to fetch all events with 30-day date filtering.
"""

import requests
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rules.base import BaseScraper


class LustAufScraper(BaseScraper):
    """Scraper for Leverkusen Lust-Auf website.
    
    Uses REST API to fetch all events with 30-day date filtering.
    Total: 588 events across 12 pages (50 events per page).
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf pages."""
        return "lust-auf-leverkusen.de" in url

    def fetch(self) -> str:
        """Fetch content from Lust-Auf URL.
        
        Uses standard requests for static content.
        """
        return self._fetch_with_requests()

    def _fetch_with_requests(self) -> str:
        """Fetch using requests."""
        import requests as req
        resp = req.get(
            self.url,
            timeout=30,
            headers={"User-Agent": "WeeklyMail/1.0"}
        )
        resp.raise_for_status()
        return resp.text

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        Returns full HTML for BeautifulSoup parsing.
        """
        return self._fetch_with_requests()

    def fetch_events_from_api(self, max_pages: int = 12) -> list:
        """Fetch all events via REST API with pagination.
        
        Args:
            max_pages: Maximum number of pages to fetch (default: 12).
        
        Returns:
            List of event dictionaries from API.
        """
        base_url = "https://lust-auf-leverkusen.de/wp-json/tribe/events/v1/events"
        all_events = []
        
        # Calculate date range (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        print(f"[LustAuf] Fetching events from {start_date_str} to {end_date_str}")
        
        for page in range(1, max_pages + 1):
            params = {
                'page': page,
                'per_page': 50,
                'start_date': start_date_str,
                'end_date': end_date_str,
            }
            
            print(f"[LustAuf] Fetching page {page}/{max_pages}...")
            
            try:
                resp = requests.get(
                    base_url,
                    params=params,
                    timeout=30,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                data = resp.json()
                
                events = data.get('events', [])
                all_events.extend(events)
                print(f"[LustAuf] Page {page}: {len(events)} events")
            
            except Exception as e:
                print(f"[LustAuf] Failed to fetch page {page}: {e}")
                continue
        
        print(f"[LustAuf] Fetched {len(all_events)} total events from {page} pages")
        return all_events

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return False
