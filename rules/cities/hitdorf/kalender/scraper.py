"""Scraper for Hitdorf kalender website."""

import requests
from bs4 import BeautifulSoup
from rules.base import BaseScraper


class KalenderScraper(BaseScraper):
    """Scraper for Hitdorf kalender page.
    
    Uses requests to fetch HTML from WordPress Townpress theme.
    Supports pagination with configurable page count.
    """

    # Configurable pagination - change after testing
    MAX_PAGES = 1  # Number of pages to scrape (all events on page 1)
    DISABLE_LEVEL_2 = False  # Enable Level 2 for descriptions

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Hitdorf pages."""
        return "leben-in-hitdorf.de" in url and "kalender" in url

    def fetch(self) -> str:
        """Fetch events from Hitdorf WordPress site.
        
        The Hitdorf website uses WordPress with Townpress theme.
        Fetches multiple pages of events.
        
        Returns raw HTML for Level 2 scraping.
        """
        return self.fetch_raw_html()

    def fetch_raw_html_for_level2(self) -> str:
        """Fetch raw HTML content from Hitdorf kalender for Level 2 scraping.
        
        The Hitdorf website uses WordPress with Townpress theme.
        Fetches multiple pages of events.
        
        This method is used when Level 2 scraping is explicitly needed.
        Returns full HTML with all elements intact for multiple pages.
        """
        return self.fetch_raw_html()

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from Hitdorf kalender.
        
        The Hitdorf website uses WordPress with Townpress theme.
        Fetches multiple pages of events.
        
        This method is used by the regex parser for Level 2 scraping.
        
        Returns full HTML with all elements intact for multiple pages.
        """
        base_url = self.url
        all_html = []
        
        for page in range(1, self.MAX_PAGES + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url.rstrip('/')}/page/{page}/"
            
            print(f"[Hitdorf] Fetching page {page}/{self.MAX_PAGES}: {url}")
            
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                all_html.append(response.text)
            except requests.RequestException as e:
                print(f"[Hitdorf] Error fetching page {page}: {e}")
                continue
        
        # Combine all pages with separator
        separator = "\n<!-- PAGE SEPARATOR -->\n"
        combined_html = separator.join(all_html)
        
        print(f"[Hitdorf] Fetched {len(combined_html)} chars of raw HTML")
        return combined_html
