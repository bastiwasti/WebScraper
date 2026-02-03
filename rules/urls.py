"""Central URL definitions organized by city and aggregator type.

This file serves as the single source of truth for all event URLs.
Each URL maps to a specific subfolder in rules/ where scraper.py and regex.py are defined.
"""

from typing import List, Dict

# City-specific event URLs
# Each city can have multiple URLs (e.g., main site + cultural venues)
# Key is the subfolder name in rules/cities/
CITY_URLS: Dict[str, Dict[str, str]] = {
    "monheim": {
        "terminkalender": "https://www.monheim.de/freizeit-tourismus/terminkalender",
        "kulturwerke": "https://www.monheimer-kulturwerke.de/de/kalender/",
    },
    "langenfeld": {
        "city_events": "https://www.langenfeld.de/Startseite/Aktuelles-und-Information/Veranstaltungen.htm",
        "schauplatz": "https://schauplatz.de/",
    },
    "solingen": {
        "live": "https://www.solingen-live.de/",
    },
    "haan": {
        "kultur_freizeit": "https://www.haan.de/Kultur-Freizeit/Veranstaltungen",
    },
    "leverkusen": {
        # URLs need verification - currently broken
        "default": "https://www.leverkusen.de",
    },
    "hilden": {
        # URL needs verification - currently broken
        "default": "https://www.hilden.de",
    },
    "dormagen": {
        # URL needs verification - currently broken
        "default": "https://www.dormagen.de",
    },
    "ratingen": {
        # URL needs verification - currently broken
        "default": "https://www.ratingen.de",
    },
}

# Regional aggregator URLs (always scraped)
# Key is the subfolder name in rules/aggregators/
AGGREGATOR_URLS: Dict[str, str] = {
    "rausgegangen": "https://rausgegangen.de/",
    "meetup": "https://www.meetup.com/de-DE/find/?location=de--Nordrhein-Westfalen&source=EVENTS",
    "eventbrite": "https://www.eventbrite.de/d/germany--nrw/events/",
}


def get_all_urls() -> List[str]:
    """Return all URLs (city + aggregators)."""
    all_urls = []

    for city, url_dict in CITY_URLS.items():
        all_urls.extend(url_dict.values())

    all_urls.extend(AGGREGATOR_URLS.values())

    return all_urls


def get_urls_for_cities(cities: List[str]) -> List[str]:
    """Return URLs for specific cities."""
    urls = []

    for city in cities:
        city_lower = city.lower()
        if city_lower in CITY_URLS:
            urls.extend(CITY_URLS[city_lower].values())

    return urls


def get_urls_for_city(city: str) -> List[str]:
    """Return all URLs for a specific city."""
    city_lower = city.lower()
    return list(CITY_URLS.get(city_lower, {}).values())


def get_url_for_key(city: str, key: str) -> str | None:
    """Return specific URL for city and key.

    Args:
        city: City name (e.g., "monheim")
        key: Subfolder key (e.g., "terminkalender")

    Returns:
        URL string or None if not found.
    """
    city_lower = city.lower()
    if city_lower in CITY_URLS:
        return CITY_URLS[city_lower].get(key)
    return None


def get_city_for_url(url: str) -> str | None:
    """Return city name for a given URL."""
    url_lower = url.lower()

    for city, url_dict in CITY_URLS.items():
        for subfolder, u in url_dict.items():
            if u.lower() == url_lower or u.lower() in url_lower:
                return city

    return None


def is_aggregator_url(url: str) -> bool:
    """Check if URL is a regional aggregator."""
    url_lower = url.lower()
    return any(agg_url.lower() in url_lower for agg_url in AGGREGATOR_URLS.values())


def get_rule_key_for_url(url: str) -> tuple[str, str] | None:
    """Return (type, key) tuple for a given URL.

    Returns:
        ("city", city_key) or ("aggregator", aggregator_key) or None.

    Examples:
        - "https://www.monheim.de/freizeit-tourismus/terminkalender" -> ("city", "monheim/terminkalender")
        - "https://rausgegangen.de/" -> ("aggregator", "rausgegangen")
    """
    url_lower = url.lower()

    for city, url_dict in CITY_URLS.items():
        for subfolder, u in url_dict.items():
            if u.lower() == url_lower:
                return ("city", f"{city}/{subfolder}")

    for agg_key, agg_url in AGGREGATOR_URLS.items():
        if agg_url.lower() in url_lower:
            return ("aggregator", agg_key)

    return None
