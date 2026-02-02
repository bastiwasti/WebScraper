"""Agent 1: Scrapes the internet for local events using search and fetch tools."""

import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from config import DEFAULT_LOCATION, LLM_MODEL, OLLAMA_BASE_URL, XAI_API_KEY, XAI_BASE_URL, XAI_MODEL, ZAI_API_KEY, ZAI_BASE_URL, ZAI_MODEL, GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from .tools import search_web, fetch_page


# City-specific official event URLs
CITY_EVENT_URLS = {
    "monheim": [
        "https://www.monheim.de/freizeit-tourismus/veranstaltungen",
        "https://www.monheimer-kulturwerke.de/de/kalender/",
    ],
    "langenfeld": [
        "https://www.langenfeld.de/freizeit-kultur/veranstaltungen",
        "https://www.kultur-langenfeld.de/",
    ],
    "leverkusen": [
        "https://www.leverkusen.de/leben-in-lev/veranstaltungen.php",
        "https://www.kulturstadtlev.de/veranstaltungen",
    ],
    "hilden": [
        "https://www.hilden.de/kultur-freizeit/veranstaltungen",
    ],
    "dormagen": [
        "https://www.dormagen.de/leben-in-dormagen/veranstaltungen",
    ],
    "ratingen": [
        "https://www.ratingen.de/freizeit-kultur/veranstaltungen",
    ],
    "solingen": [
        "https://www.solingen-live.de/",
    ],
    "haan": [
        "https://www.haan.de/Kultur-Freizeit/Veranstaltungen",
    ],
}

# Regional aggregators (always scraped)
REGIONAL_AGGREGATORS = [
    "https://rausgegangen.de/",
    "https://www.eventbrite.de/d/germany--nrw/events/",
    "https://www.meetup.com/de-DE/find/?location=de--Nordrhein-Westfalen&source=EVENTS",
]

SYSTEM_PROMPT = """You are an event research assistant. Your task is to find and extract local events from web content.

From the raw search and web content you are given, extract every relevant event. For each event include:
- Event name
- Date and time (if available)
- Location or venue
- Short description or category
- Source: the URL or website name where you found it (required)

Keep only real events from the content; do not invent any. If the content has no suitable events, say so clearly."""

USER_PROMPT = """Summarize the following raw web content for events in: {location_query}.

Extract and list every event you find. For each event include the source (URL or site name). Output one coherent text (no JSON) for the next processing step. Base your summary only on the content below.

Raw content:
---
{raw_content}
---
"""


class ScraperAgent:
    """Finds local events via web search and page fetch, then summarizes with the LLM."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        from config import LLM_PROVIDER

        if LLM_PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.2,
            )
        elif LLM_PROVIDER == "groq" and GROQ_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or GROQ_MODEL,
                api_key=GROQ_API_KEY,
                base_url=GROQ_BASE_URL,
                temperature=0.2,
            )
        elif LLM_PROVIDER == "xai" and XAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or XAI_MODEL,
                api_key=XAI_API_KEY,
                base_url=XAI_BASE_URL,
                temperature=0.2,
            )
        elif LLM_PROVIDER == "zai" and ZAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=model or ZAI_MODEL,
                api_key=ZAI_API_KEY,
                base_url=ZAI_BASE_URL,
                temperature=0.2,
            )
        else:
            from langchain_ollama import ChatOllama
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
        cities: list[str] | None = None,
    ) -> str:
        """Run multiple searches and scrape fixed URLs for events."""
        all_parts = []
        urls_to_fetch: list[str] = []

        # 1. Add city-specific URLs (all cities if not specified)
        cities_to_scrape = cities if cities else list(CITY_EVENT_URLS.keys())
        for city in cities_to_scrape:
            city_lower = city.lower()
            if city_lower in CITY_EVENT_URLS:
                for url in CITY_EVENT_URLS[city_lower]:
                    if url not in urls_to_fetch:
                        urls_to_fetch.append(url)

        # 2. Always include regional aggregators
        for url in REGIONAL_AGGREGATORS:
            if url not in urls_to_fetch:
                urls_to_fetch.append(url)

        # 3. Add custom search queries if provided
        if search_queries:
            per_query = max(3, max_search // len(search_queries))
            for q in search_queries[:5]:
                search_result = search_web.invoke({"query": q, "max_results": per_query})
                all_parts.append(f"Search: {q}\n{search_result}")
                if "URL:" in search_result:
                    for url in re.findall(r"URL:\s*(https?://[^\s]+)", search_result):
                        u = url.strip()
                        if u and u not in urls_to_fetch:
                            urls_to_fetch.append(u)

        # 4. Fetch URLs (respect fetch_urls limit)
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
        cities: list[str] | None = None,
    ) -> str:
        """Search for events, fetch pages from fixed URLs, and return a summarized event text."""
        location_query = location or DEFAULT_LOCATION or "the user's area"
        raw_content = self._gather_raw_content(
            location_query,
            search_queries=search_queries,
            max_search=max_search,
            fetch_urls=fetch_urls,
            cities=cities,
        )
        chain = self._prompt | self.llm | StrOutputParser()
        return chain.invoke({"location_query": location_query, "raw_content": raw_content})
