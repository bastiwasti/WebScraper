"""Scraper registry - maps URLs to appropriate scrapers."""

from typing import List, Type

from .base import BaseScraper
from .monheim import MonheimScraper
from .static import StaticScraper

_SCRAPER_CLASSES: List[Type[BaseScraper]] = [
    MonheimScraper,
    StaticScraper,
]


def get_scraper(url: str) -> BaseScraper:
    """Return the appropriate scraper instance for the given URL.

    Args:
        url: The URL to scrape.

    Returns:
        A scraper instance that can handle the URL.
    """
    for scraper_class in _SCRAPER_CLASSES:
        if scraper_class.can_handle(url):
            return scraper_class(url)

    raise ValueError(f"No scraper found for URL: {url}")


def register_scraper(scraper_class: Type[BaseScraper]) -> None:
    """Register a new scraper class.

    Newer scrapers take priority over older ones, so insert at the beginning.

    Args:
        scraper_class: A BaseScraper subclass.
    """
    _SCRAPER_CLASSES.insert(0, scraper_class)


def list_scrapers() -> List[str]:
    """Return list of registered scraper class names."""
    return [cls.__name__ for cls in _SCRAPER_CLASSES]
