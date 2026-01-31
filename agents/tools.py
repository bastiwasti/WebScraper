"""Tools for the scraper agent: search and fetch web content."""

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool

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


def _clean_text(text: str, max_chars: Optional[int] = 8000) -> str:
    """Normalize whitespace and truncate to avoid token overflow."""
    text = re.sub(r"\s+", " ", text).strip()
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


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
        resp = requests.get(url, timeout=15, headers={"User-Agent": "WeeklyMail/1.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return _clean_text(text)
    except requests.RequestException as e:
        return f"Failed to fetch URL: {e}"
    except Exception as e:
        return f"Error extracting content: {e}"
