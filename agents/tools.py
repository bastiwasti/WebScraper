"""Tools for the scraper agent: search and fetch web content."""

from typing import Optional

from langchain_core.tools import tool

from scrapers.registry import get_scraper

# Optional: DuckDuckGo search (install: pip install duckduckgo-search)
try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False


@tool
def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for information. Use this to find local events, event calendars, or event listings.
    Args:
        query: Search query (e.g. 'events Berlin this week', 'concerts Munich January').
        max_results: Maximum number of search results to return (default 5).
    Returns:
        A text summary of search results (title, snippet, URL) for each result.
    """
    if not HAS_DDGS:
        return (
            "DuckDuckGo search not available. Install with: pip install duckduckgo-search. "
            "Alternatively, provide event data manually or use fetch_page with known URLs."
        )
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No search results found."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. {title}\n   {body}\n   URL: {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"Search failed: {e}"


@tool
def fetch_page(url: str) -> str:
    """Fetch and extract main text from a web page. Use this to get event details from a specific URL.
    Args:
        url: Full URL of the page (must start with http:// or https://).
    Returns:
        Extracted text content from the page (cleaned, truncated if very long).
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        scraper = get_scraper(url)
        return scraper.fetch()
    except Exception as e:
        return f"Failed to fetch URL: {e}"


def fetch_page_with_browser_check(url: str) -> str:
    """Fetch a page, returning additional info about whether browser was needed."""
    try:
        scraper = get_scraper(url)
        content = scraper.fetch()
        return f"[Scraper: {scraper.__class__.__name__} | Browser: {scraper.needs_browser}]\n{content}"
    except Exception as e:
        return f"Failed to fetch URL: {e}"
