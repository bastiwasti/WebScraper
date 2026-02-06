"""Central URL definitions organized by city and aggregator type.

This file serves as the single source of truth for all event URLs.
Each URL maps to a specific subfolder in rules/ where scraper.py and regex.py are defined.
"""

from typing import List, Dict

# City-specific event URLs
# Each city can have multiple URLs (e.g., main site + cultural venues)
# Key is subfolder name in rules/cities/
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
        "stadt_erleben": "https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/",
        "lust_auf": "https://lust-auf-leverkusen.de/",
        "default": "https://www.leverkusen.de",  # Fallback
    },
    "hilden": {
        "default": "https://www.hilden.de/de/veranstaltungen/",
    },
    "dormagen": {
        "default": "https://www.dormagen.de/tourismus-freizeit/feste-veranstaltungen",
    },
    "ratingen": {
        "default": "https://www.stadt-ratingen.de/kultur-und-tourismus/kulturprogramm-aktuell",
    },
}


def get_all_urls() -> List[str]:
    """Return all URLs (city + aggregators)."""
    all_urls = []

    for city, url_dict in CITY_URLS.items():
        all_urls.extend(url_dict.values())

    return all_urls


def get_urls_for_cities(cities: List[str]) -> List[str]:
    """Return URLs for specific cities."""
    urls = []

    for city in cities:
        city_lower = city.lower()
        if city_lower in CITY_URLS:
            urls.extend(CITY_URLS[city_lower].values())

    return urls


def get_urls_for_city(city: str | list[str]) -> List[str]:
    """Return all URLs for a specific city or cities.
    
    Args:
        city: Single city name (str) or list of city names (list[str]).
    
    Returns:
        List of URL strings.
    """
    urls = []
    
    # Handle single string or list of strings
    cities_to_process = [city] if isinstance(city, str) else city
    
    for c in cities_to_process:
        city_lower = c.lower()
        if city_lower in CITY_URLS:
            urls.extend(CITY_URLS[city_lower].values())
    
    return urls


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


def get_rule_key_for_url(url: str) -> tuple[str, str] | None:
    """Return (type, key) tuple for a given URL.

    Returns:
        ("city", city_key) or None.

    Examples:
        - "https://www.monheim.de/freizeit-tourismus/terminkalender" -> ("city", "monheim/terminkalender")
    """
    url_lower = url.lower()

    for city, url_dict in CITY_URLS.items():
        for subfolder, u in url_dict.items():
            if u.lower() == url_lower:
                return ("city", f"{city}/{subfolder}")

    return None

