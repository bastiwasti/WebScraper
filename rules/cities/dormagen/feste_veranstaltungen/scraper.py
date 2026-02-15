"""Scraper for Dormagen feste-veranstaltungen website."""

import requests
from bs4 import BeautifulSoup
from rules.base import BaseScraper


class FesteVeranstaltungenScraper(BaseScraper):
    """Scraper for Dormagen feste-veranstaltungen page.
    
    Uses requests to fetch HTML from datefix.de calendar system.
    Supports pagination with configurable page count.
    """

    # Configurable pagination - change after testing
    MAX_PAGES = 10  # Number of pages to scrape (temporarily reduced for testing)
    DISABLE_LEVEL_2 = False  # Disable Level 2 to avoid timeout (10 pages × 50 events = 500 detail pages)

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Dormagen pages."""
        return "dormagen.de" in url and "feste-veranstaltungen" in url

    def fetch(self) -> str:
        """Fetch events from datefix.de calendar system.
        
        The Dormagen website uses datefix.de external event system (data-kid="6003").
        Fetches multiple pages of events.
        
        Returns raw HTML for Level 2 scraping (disabled by default for speed).
        """
        return self.fetch_raw_html()

    def fetch_raw_html_for_level2(self) -> str:
        """Fetch raw HTML content from datefix.de calendar system for Level 2 scraping.
        
        The Dormagen website uses datefix.de external event system (data-kid="6003").
        Fetches multiple pages of events.
        
        This method is used when Level 2 scraping is explicitly needed.
        Returns full HTML with all elements intact for multiple pages.
        """
        return self.fetch_raw_html()

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from datefix.de calendar system.
        
        The Dormagen website uses datefix.de external event system (data-kid="6003").
        Fetches multiple pages of events.
        
        This method is used by the regex parser for Level 2 scraping.
        
        Returns full HTML with all elements intact for multiple pages.
        """
        base_url = "https://www.datefix.de/de/kalender/6003"
        all_html = []
        
        for page in range(1, self.MAX_PAGES + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?dfxp={page}"
            
            print(f"[Dormagen] Fetching page {page}/{self.MAX_PAGES}: {url}")
            
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                all_html.append(response.text)
            except requests.RequestException as e:
                print(f"[Dormagen] Error fetching page {page}: {e}")
                continue
        
        # Combine all pages with separator
        separator = "\n<!-- PAGE SEPARATOR -->\n"
        combined_html = separator.join(all_html)
        
        print(f"[Dormagen] Fetched {len(combined_html)} chars of raw HTML")
        return combined_html
