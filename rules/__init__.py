"""Unified rules system - scrapers + regex parsers.

This module provides a unified interface for:
- Fetching content from event URLs
- Extracting structured events via regex
- LLM fallback when regex fails

Example usage:
    from rules import fetch_events_from_url

    events = fetch_events_from_url("https://www.monheim.de/freizeit-tourismus/terminkalender")
    for event in events:
        print(f"{event.date}: {event.name}")
"""

from .registry import (
    get_rule,
    get_rule_or_raise,
    list_registered_rules,
    list_registered_urls,
    get_scraper_for_url,
    get_regex_for_url,
    create_scraper,
    create_regex,
    reinitialize_registry,
    get_origin_for_url,
)

from .urls import (
    get_all_urls,
    get_urls_for_cities,
    get_urls_for_city,
    get_url_for_key,
    get_city_for_url,
    get_rule_key_for_url,
    CITY_URLS,
)

from .base import Event, BaseRule, BaseScraper


def fetch_events_from_url(url: str, use_llm_fallback: bool = True) -> tuple[list[Event], str]:
    """Fetch and extract events from a single URL.
    
    This is the main entry point for the rules system.
    
    Args:
        url: The URL to fetch events from.
        use_llm_fallback: Whether to use LLM if regex fails (default: True).
    
    Returns:
        Tuple of (List of Event objects, extraction_method) where extraction_method is "regex", "llm", or "none".
    
    Raises:
        ValueError: If no rule found for URL.
    """
    try:
        scraper = create_scraper(url)
        regex_parser = create_regex(url)
        
        # Check if scraper supports API fetching (lust_auf)
        if hasattr(scraper, 'fetch_events_from_api'):
            # Use API for fetching all events
            all_events = scraper.fetch_events_from_api()
            return all_events, "regex"
        # Check if scraper supports pagination (stadt_erleben)
        elif hasattr(scraper, 'fetch_all_pages'):
            # Use pagination for 14-day window
            all_events = scraper.fetch_all_pages()
            return all_events, "regex"
        else:
            # Standard single-page fetching
            content = scraper.fetch()
            events, extraction_method = regex_parser.extract_events_with_method(content, use_llm_fallback)
            
            # Attempt Level 2 scraping if scraper supports it
            try:
                if hasattr(scraper, 'fetch_raw_html') and not getattr(scraper, 'DISABLE_LEVEL_2', False):
                    raw_html = scraper.fetch_raw_html()
                    events = regex_parser.fetch_level2_data(events, raw_html)
            except Exception as e:
                print(f"Warning: Level 2 scraping failed for {url}: {e}")
            
            return events, extraction_method
    except Exception as e:
        print(f"Error fetching events from {url}: {e}")
        return [], "error"


def fetch_events_from_urls(urls: list[str], use_llm_fallback: bool = True) -> list[Event]:
    """Fetch and extract events from multiple URLs.

    Args:
        urls: List of URLs to fetch events from.
        use_llm_fallback: Whether to use LLM if regex fails (default: True).

    Returns:
        List of Event objects from all URLs.
    """
    all_events = []
    for url in urls:
        events, _ = fetch_events_from_url(url, use_llm_fallback)
        all_events.extend(events)

    return all_events


__all__ = [
    "Event",
    "BaseRule",
    "CITY_URLS",
    "get_all_urls",
    "get_urls_for_cities",
    "get_urls_for_city",
    "get_url_for_key",
    "get_city_for_url",
    "get_rule_key_for_url",
    "get_rule",
    "get_rule_or_raise",
    "list_registered_rules",
    "list_registered_urls",
    "get_scraper_for_url",
    "get_regex_for_url",
    "create_scraper",
    "create_regex",
    "reinitialize_registry",
    "get_origin_for_url",
    "fetch_events_from_url",
    "fetch_events_from_urls",
]
