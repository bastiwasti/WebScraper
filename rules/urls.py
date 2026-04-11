"""Central URL definitions organized by city and aggregator type.

This file serves as the single source of truth for all event URLs.
Each URL maps to a specific subfolder in rules/ where scraper.py and regex.py are defined.
"""

from typing import List, Dict

# City-specific event URLs
# Each city can have multiple URLs (e.g., main site + cultural venues)
# Key is subfolder name in rules/cities/
CITY_URLS: Dict[str, Dict[str, str]] = {
    "monheim_am_rhein": {
        "terminkalender": "https://www.monheim.de/freizeit-tourismus/terminkalender",
        "kulturwerke": "https://www.monheimer-kulturwerke.de/de/kalender/",
        "marienburg_events": "https://marienburgmonheim.de/de/events",
    },
    "langenfeld": {
        "city_events": "https://www.langenfeld.de/Startseite/Aktuelles-und-Information/Veranstaltungen.htm",
        "schauplatz": "https://schauplatz.de/",
    },

    "leverkusen": {
        "stadt_erleben": "https://www.leverkusen.de/stadt-erleben/veranstaltungskalender/",
        "lust_auf": "https://lust-auf-leverkusen.de/",
    },
    "hilden": {
        "veranstaltungen": "https://www.hilden.de/de/veranstaltungen/",
    },
    "dormagen": {
        "feste_veranstaltungen": "https://www.dormagen.de/tourismus-freizeit/feste-veranstaltungen",
    },
    "hitdorf": {
        "kalender": "https://leben-in-hitdorf.de/kalender/",
    },
    "leichlingen": {
        "freizeit_und_tourismus": "https://www.leichlingen.de/freizeit-und-tourismus/veranstaltungen",
    },

    "burscheid": {
        "veranstaltungskalender": "https://www.burscheid.de/portal/seiten/veranstaltungskalender-900000009-40230.html",
    },
    "duesseldorf": {
        "schloss_benrath": "https://www.schloss-benrath.de/veranstaltungs-liste/angebote",
    },

}


# Aggregator event URLs
# Each aggregator can have multiple city entries
# Key is aggregator name, value is dict of {city_slug: url}
AGGREGATOR_URLS: Dict[str, Dict[str, str]] = {
    "rausgegangen": {
        "monheim_am_rhein": "https://rausgegangen.de/monheim-am-rhein/?radius=20000&lat=51.08713514258467&lng=6.884078972507269&city=monheim-am-rhein&geospatial_query_type=CENTER_AND_RADIUS",
    },
    "eventim": {
        "monheim_am_rhein": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Monheim+am+Rhein&sort=DateAsc&top=50",
        "langenfeld": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Langenfeld&sort=DateAsc&top=50",
        "leverkusen": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Leverkusen&sort=DateAsc&top=50",
        "hilden": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Hilden&sort=DateAsc&top=50",
        "dormagen": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Dormagen&sort=DateAsc&top=50",
        "hitdorf": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Hitdorf&sort=DateAsc&top=50",
        "leichlingen": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Leichlingen&sort=DateAsc&top=50",
        "burscheid": "https://public-api.eventim.com/websearch/search/api/exploration/v1/products?webId=web__eventim-de&language=de&retail_partner=EVE&city_names=Burscheid&sort=DateAsc&top=50",
    },
}


def get_all_urls() -> List[str]:
    """Return all URLs (city + aggregators)."""
    all_urls = []

    for city, url_dict in CITY_URLS.items():
        all_urls.extend(url_dict.values())

    # Add aggregator URLs
    for aggregator, url_dict in AGGREGATOR_URLS.items():
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
        city: City name (e.g., "monheim_am_rhein")
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
        - "https://www.monheim.de/freizeit-tourismus/terminkalender" -> ("city", "monheim_am_rhein/terminkalender")
    """
    url_lower = url.lower()

    for city, url_dict in CITY_URLS.items():
        for subfolder, u in url_dict.items():
            if u.lower() == url_lower:
                return ("city", f"{city}/{subfolder}")

    return None

