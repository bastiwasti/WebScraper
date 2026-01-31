"""Agent 1: Scrapes the internet for local family/children events using search and fetch tools."""

import re

from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEFAULT_LOCATION, FAMILY_FOCUS, LLM_MODEL, OLLAMA_BASE_URL
from .tools import search_web, fetch_page


# Queries tuned for Monheim 40789 and family/children events
DEFAULT_SEARCH_QUERIES = [
    "Kinder Veranstaltungen Monheim 40789",
    "Familie Events Monheim am Rhein",
    "Familienfreundlich Monheim Langenfeld Leverkusen",
    "Kinderprogramm Monheim Wochenende",
]

SYSTEM_PROMPT = """You are an event research assistant for a family in Monheim 40789, Germany.
Your task is to find local events that make sense for children and families (e.g. Kinder, Familie, Spielplatz, Museum, Theater, Kurse, Märkte, Feste).
From the raw search and web content you are given, extract every relevant event. For each event include:
- Event name
- Date and time (if available)
- Location or venue
- Short description or category
- Source: the URL or website name where you found it (required)
Keep only real events from the content; do not invent any. If the content has no suitable events, say so clearly."""

USER_PROMPT = """Summarize the following raw web content for family- and children-friendly events in: {location_query}.

Extract and list every event you find. For each event include the source (URL or site name). Output one coherent text (no JSON) for the next processing step. Base your summary only on the content below.

Raw content:
---
{raw_content}
---
"""


class ScraperAgent:
    """Finds local family/children events via web search and page fetch, then summarizes with the LLM."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.llm = ChatOllama(
            model=model or LLM_MODEL,
            base_url=base_url or OLLAMA_BASE_URL,
            temperature=0.2,
        )
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", USER_PROMPT),
        ])

    def _gather_raw_content(
        self,
        location: str,
        search_queries: list[str] | None = None,
        max_search: int = 6,
        fetch_urls: int = 3,
    ) -> str:
        """Run multiple searches (family/children in region) and optionally fetch pages."""
        queries = search_queries or (
            DEFAULT_SEARCH_QUERIES
            if (location and "monheim" in location.lower()) and FAMILY_FOCUS
            else [f"family children events {location}" if location else "family children events"]
        )
        # Cap per-query results so we don't overflow context
        per_query = max(3, max_search // len(queries))
        all_parts = []
        urls_to_fetch: list[str] = []  # preserve order (first results first)

        for q in queries[:5]:  # max 5 query variants
            search_result = search_web.invoke({"query": q, "max_results": per_query})
            all_parts.append(f"Search: {q}\n{search_result}")
            if "URL:" in search_result:
                for url in re.findall(r"URL:\s*(https?://[^\s]+)", search_result):
                    u = url.strip()
                    if u and u not in urls_to_fetch:
                        urls_to_fetch.append(u)

        for url in urls_to_fetch[:fetch_urls]:
            content = fetch_page.invoke({"url": url})
            if not content.startswith(("Error", "Failed")):
                all_parts.append(f"Page: {url}\n{content[:5000]}")

        return "\n\n---\n\n".join(all_parts)

    def run(
        self,
        location: str = "",
        search_queries: list[str] | None = None,
        max_search: int = 8,
        fetch_urls: int = 3,
    ) -> str:
        """Search for family/children events, fetch pages, and return a summarized event text."""
        location_query = location or DEFAULT_LOCATION or "the user's area"
        raw_content = self._gather_raw_content(
            location_query,
            search_queries=search_queries,
            max_search=max_search,
            fetch_urls=fetch_urls,
        )
        chain = self._prompt | self.llm | StrOutputParser()
        return chain.invoke({"location_query": location_query, "raw_content": raw_content})
