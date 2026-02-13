"""Scraper for Ratingen Kulturprogramm website."""

from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from rules.base import BaseScraper


class KulturprogrammScraper(BaseScraper):
    """Scraper for Ratingen Kulturprogramm page.
    
    Uses Playwright for JavaScript rendering.
    Fetches events from both Kulturprogramm and Kindertheater sections.
    """

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """Handle Ratingen Kulturprogramm pages."""
        return "ratingen.de" in url and "kulturprogramm-aktuell" in url

    def fetch(self) -> str:
        """Fetch content from Kulturprogramm URL.
        
        Uses Playwright for JavaScript rendering.
        Returns cleaned text.
        """
        return self._fetch_with_playwright()

    def _fetch_with_playwright(self) -> str:
        """Fetch using Playwright with JavaScript rendering."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, wait_until="networkidle")
            
            # Wait for content to load
            page.wait_for_timeout(5000)
            
            # Scroll to load all content
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(2000)
            
            content = page.content()
            browser.close()
            
            # Parse and clean content
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove non-event elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()
            
            # Get clean text for analysis
            text = soup.get_text(separator="\n", strip=True)
            
            # Remove empty lines and clean up
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            cleaned_text = "\n".join(line for line in lines if len(line) > 3)
            
            return cleaned_text

    def fetch_raw_html(self) -> str:
        """Fetch raw HTML content from URL.
        
        Returns full HTML for BeautifulSoup parsing.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.url, timeout=120000)
            
            # Wait for content to load
            page.wait_for_timeout(10000)
            
            # Scroll to load all content
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(5000)
            
            content = page.content()
            browser.close()
            
            return content
