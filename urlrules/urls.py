"""Central URL definitions organized by city and aggregator type."""

from typing import List, Dict

# City-specific event URLs
# Note: Main city domains work best. Specific subpaths may return 404.
CITY_URLS: Dict[str, List[str]] = {
    "monheim": [
        "https://www.monheim.de/freizeit-tourismus/terminkalender",
        "https://www.monheimer-kulturwerke.de/de/kalender/",
    ],
    "solingen": [
        "https://www.solingen-live.de/",
    ],
    "haan": [
        "https://www.haan.de/Kultur-Freizeit/Veranstaltungen",
    ],
    "langenfeld": [
        "https://www.langenfeld.de",  # Main domain, has event section
    ],
    "leverkusen": [
        "https://www.leverkusen.de",  # Main domain, has event section
    ],
    "hilden": [
        "https://www.hilden.de",  # Main domain, has event section
    ],
    "dormagen": [
        "https://www.dormagen.de",  # Main domain, has event section
    ],
    "ratingen": [
        "https://www.ratingen.de",  # Main domain
    ],
}

# Regional aggregator URLs (always scraped)
AGGREGATOR_URLS: List[str] = [
    "https://rausgegangen.de/",
    "https://www.eventbrite.de/d/germany--nrw/events/",
    "https://www.meetup.com/de-DE/find/?location=de--Nordrhein-Westfalen&source=EVENTS",
]


def get_all_urls() -> List[str]:
    """Return all URLs (city + aggregators)."""
    all_urls = []

    for city, urls in CITY_URLS.items():
        all_urls.extend(urls)

    all_urls.extend(AGGREGATOR_URLS)

    return all_urls


def get_urls_for_cities(cities: List[str]) -> List[str]:
    """Return URLs for specific cities."""
    urls = []

    for city in cities:
        city_lower = city.lower()
        if city_lower in CITY_URLS:
            urls.extend(CITY_URLS[city_lower])

    return urls


def get_city_for_url(url: str) -> str | None:
    """Return city name for a given URL."""
    url_lower = url.lower()

    for city, urls in CITY_URLS.items():
        for u in urls:
            if u.lower() == url_lower:
                return city
            if u.lower() in url_lower:
                return city

    return None


def is_aggregator_url(url: str) -> bool:
    """Check if URL is a regional aggregator."""
    url_lower = url.lower()
    return any(agg_url.lower() in url_lower for agg_url in AGGREGATOR_URLS)
