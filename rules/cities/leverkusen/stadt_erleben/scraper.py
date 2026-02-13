"""Scraper for Leverkusen Stadt_Erleben URL."""

from typing import Optional
import requests

from rules.base import BaseScraper


class StadtErlebenScraper(BaseScraper):
    """Scraper for Leverkusen stadt_erleben event pages."""

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Leverkusen stadt_erleben pages."""
        return "leverkusen.de" in url and "stadt-erleben/veranstaltungskalender/" in url

    def fetch(self) -> str:
        """Fetch content from StadtErleben URL.

        Returns raw HTML for BeautifulSoup parsing.
        """
        return self.fetch_raw_html()

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.

        This is used by regex parser for Level 2 scraping.
        Returns full HTML with all elements intact.
        """
        try:
            resp = requests.get(
                self.url,
                timeout=15,
                headers={"User-Agent": "WeeklyMail/1.0"}
            )
            resp.raise_for_status()
            print(f"[StadtErleben] Fetched {len(resp.text)} chars of raw HTML")
            return resp.text
        except Exception as e:
            print(f"[StadtErleben] failed to fetch raw HTML: {e}")
            raise

    def fetch_all_pages(self, max_pages: int = 45) -> list:
        """Fetch multiple pages with pagination for 14-day window.
        
        Continues fetching pages until:
        1. All events in 14-day window are collected
        2. A page returns no events in date range
        3. Max pages reached
        
        Args:
            max_pages: Maximum number of pages to fetch (default: 45 total pages).
        
        Returns:
            List of all events from all pages within 14-day window, with Level 2 data.
        """
        all_events = []
        page = 1
        consecutive_empty_pages = 0
        
        # Get parser for the base URL
        parser = self._create_parser(self)
        
        # Store raw HTML for Level 2 scraping
        raw_html_by_event_name = {}
        
        print(f"[StadtErleben] Fetching pages (14-day window, max {max_pages} pages)...")
        
        while page <= max_pages and consecutive_empty_pages < 2:
            if page == 1:
                url = self.url
            else:
                url = f"{self.url}?sp:page[eventSearch-1.form][0]={page}"
            
            print(f"[StadtErleben] Fetching page {page}: {url}")
            
            try:
                # Fetch HTML directly for this page
                resp = requests.get(
                    url,
                    timeout=15,
                    headers={"User-Agent": "WeeklyMail/1.0"}
                )
                resp.raise_for_status()
                print(f"[StadtErleben] Fetched {len(resp.text)} chars of raw HTML")
                
                # Extract event URLs for Level 2
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                for card in soup.select('li.SP-TeaserList__item'):
                    title_elem = card.select_one('h2')
                    detail_link = card.select_one('a.SP-Teaser__link')
                    if title_elem and detail_link:
                        title = title_elem.get_text(strip=True)
                        href = detail_link.get('href', '')
                        if href.startswith('/'):
                            href = f"https://www.leverkusen.de{href}"
                        raw_html_by_event_name[title] = href
                
                # Parse events
                events = parser.parse_with_regex(resp.text)
                
                if events:
                    print(f"[StadtErleben] Page {page}: {len(events)} events")
                    all_events.extend(events)
                    consecutive_empty_pages = 0
                else:
                    print(f"[StadtErleben] Page {page}: No events in date range (stopping soon)")
                    consecutive_empty_pages += 1
                
                page += 1
            
            except Exception as e:
                print(f"[StadtErleben] Failed to fetch page {page}: {e}")
                consecutive_empty_pages += 1
        
        print(f"[StadtErleben] Fetched {len(all_events)} events from {page - 1} pages (14-day window)")
        
        # Apply Level 2 scraping to all events
        print(f"[StadtErleben Level 2] Fetching detail pages for {len(all_events)} events...")
        
        for event in all_events:
            detail_url = raw_html_by_event_name.get(event.name, "")
            if not detail_url:
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
                detail_data = parser.parse_detail_page(detail_html)
                
                if detail_data:
                    event.raw_data = detail_data
                    event.source = detail_url
                    print(f"  ✓ Fetched details for: {event.name[:50]}")
                else:
                    print(f"  ✗ Failed to parse details for: {event.name[:50]}")
            
            except Exception as e:
                print(f"  ✗ Failed to fetch detail page {detail_url}: {e}")
                continue
        
        print(f"[StadtErleben Level 2] Completed: {sum(1 for e in all_events if e.raw_data)}/{len(all_events)} events with detail data")
        
        return all_events

    def _create_parser(self, scraper):
        """Create parser for this scraper."""
        from rules import create_regex
        return create_regex(scraper.url)