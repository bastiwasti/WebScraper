"""Scraper for Leverkusen Lust-Auf website.

The REST calendar API (wp-json/tribe/events) was removed by the site (404).
Falls back to server-rendered "eventhub" cards on /veranstaltungen/ with
WordPress pagination (/page/N/). Page 1 shows ~Oct 17-21, page 2 ~Oct 21-25
(verified distinct), so pagination is required for the 14+-day window.
"""

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from rules.base import BaseScraper, Event
from rules.cities.leverkusen.lust_auf.regex import LustAufRegex

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
WINDOW_DAYS = 30


class LustAufScraper(BaseScraper):
    """Scraper for Leverkusen Lust-Auf website.

    Fetches paginated list pages and parses eventhub cards, then enriches
    events from detail pages (Level 2).
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Lust-Auf pages."""
        return "lust-auf-leverkusen.de" in url

    def fetch(self) -> str:
        """Fetch list page content (fallback path)."""
        return self._fetch_with_requests()

    def _fetch_with_requests(self) -> str:
        resp = requests.get(
            self.url,
            timeout=30,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        return resp.text

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL."""
        return self._fetch_with_requests()

    def _list_page_url(self, page: int) -> str:
        if page <= 1:
            return "https://lust-auf-leverkusen.de/veranstaltungen/"
        return f"https://lust-auf-leverkusen.de/veranstaltungen/page/{page}/"

    def fetch_events_from_api(self, max_pages: int = 10) -> list:
        """Fetch all events via paginated eventhub list pages.

        Pagination verified: page 2 content differs from page 1
        (AGENTS.md pattern 5 check: page 1 != page 2).

        Args:
            max_pages: Maximum number of pages to fetch.

        Returns:
            List of Event objects (Level 2 enriched).
        """
        base = LustAufRegex(self.url)
        cutoff = datetime.now() + timedelta(days=WINDOW_DAYS)

        all_events: list[Event] = []
        seen_urls: set[str] = set()
        pages_fetched = 0

        for page in range(1, max_pages + 1):
            url = self._list_page_url(page)
            print(f"[LustAuf] Fetching list page {page}: {url}")

            try:
                raw_html = base.fetch_page(url)
            except Exception as e:
                print(f"[LustAuf] Failed to fetch page {page}: {e}")
                break

            cards = base.parse_cards(raw_html)
            print(f"[LustAuf] Page {page}: {len(cards)} cards")

            new_cards = [c for c in cards if c["event_url"] not in seen_urls]
            if not new_cards:
                print(f"[LustAuf] Page {page} has no new events - stopping")
                break

            page_beyond_cutoff = False
            for card in new_cards:
                seen_urls.add(card["event_url"])
                event = base.build_event_from_card(card)
                if event:
                    all_events.append(event)
                else:
                    try:
                        dt = datetime.fromisoformat(card["datetime_iso"])
                        if dt.date() > cutoff.date():
                            page_beyond_cutoff = True
                    except ValueError:
                        pass

            pages_fetched = page

            if page_beyond_cutoff:
                print(f"[LustAuf] Page {page} reaches beyond the {WINDOW_DAYS}-day window - stopping")
                break

        print(f"[LustAuf] Fetched {len(all_events)} events from {pages_fetched} pages")
        return base.fetch_level2_data(all_events)

    @property
    def needs_browser(self) -> bool:
        """Return True if Playwright is required."""
        return False
