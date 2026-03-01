"""OpenStreetMap Overpass API source for discovering family-friendly locations."""

import time
import requests
from typing import Optional

from config import MONHEIM_LAT, MONHEIM_LNG, LOCATIONS_RADIUS_KM
from locations.models import Location

OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"
RADIUS_M = LOCATIONS_RADIUS_KM * 1000

# Overpass queries per category.
# Each query searches for nodes AND ways within the radius.
# We use "out center;" for ways so we get a single lat/lon point.
CATEGORY_QUERIES = {
    "playground": {
        "query": '(node["leisure"="playground"](around:{r},{lat},{lng});way["leisure"="playground"](around:{r},{lat},{lng}););',
        "subcategory_tag": None,
    },
    "indoor_playground": {
        "query": (
            '(node["leisure"="indoor_play"](around:{r},{lat},{lng});'
            'way["leisure"="indoor_play"](around:{r},{lat},{lng});'
            'node["sport"="trampoline"](around:{r},{lat},{lng});'
            'node["leisure"="amusement_arcade"]["kids"="yes"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": None,
    },
    "park": {
        "query": '(way["leisure"="park"](around:{r},{lat},{lng});relation["leisure"="park"](around:{r},{lat},{lng}););',
        "subcategory_tag": None,
    },
    "garden": {
        "query": (
            '(way["leisure"="garden"](around:{r},{lat},{lng});'
            'node["leisure"="garden"](around:{r},{lat},{lng});'
            'way["tourism"="garden"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": None,
    },
    "museum": {
        "query": (
            '(node["tourism"="museum"](around:{r},{lat},{lng});'
            'way["tourism"="museum"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": "museum",
    },
    "zoo": {
        "query": (
            '(node["tourism"="zoo"](around:{r},{lat},{lng});'
            'way["tourism"="zoo"](around:{r},{lat},{lng});'
            'node["zoo"="petting_zoo"](around:{r},{lat},{lng});'
            'way["zoo"="petting_zoo"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": "zoo",
    },
    "pool": {
        "query": (
            '(node["amenity"="swimming_pool"](around:{r},{lat},{lng});'
            'way["amenity"="swimming_pool"](around:{r},{lat},{lng});'
            'node["leisure"="swimming_pool"](around:{r},{lat},{lng});'
            'way["leisure"="swimming_pool"](around:{r},{lat},{lng});'
            'node["leisure"="water_park"](around:{r},{lat},{lng});'
            'way["leisure"="water_park"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": None,
    },
    "sport": {
        "query": (
            '(node["leisure"="miniature_golf"](around:{r},{lat},{lng});'
            'way["leisure"="miniature_golf"](around:{r},{lat},{lng});'
            'node["sport"="climbing"]["leisure"="sports_centre"](around:{r},{lat},{lng});'
            'way["sport"="climbing"]["leisure"="sports_centre"](around:{r},{lat},{lng});'
            'node["leisure"="ice_rink"](around:{r},{lat},{lng});'
            'way["leisure"="ice_rink"](around:{r},{lat},{lng}););'
        ),
        "subcategory_tag": "sport",
    },
}


def _build_query(category: str) -> str:
    """Build a full Overpass QL query for a category."""
    spec = CATEGORY_QUERIES[category]
    body = spec["query"].format(r=RADIUS_M, lat=MONHEIM_LAT, lng=MONHEIM_LNG)
    return f"[out:json][timeout:30];{body}out center tags;"


def _parse_element(element: dict, category: str) -> Optional[Location]:
    """Parse a single Overpass API element into a Location."""
    tags = element.get("tags", {})
    name = tags.get("name", "").strip()

    # Skip unnamed entries (many small playgrounds have no name)
    if not name:
        return None

    # Get coordinates — nodes have lat/lon directly, ways have center
    lat = element.get("lat") or element.get("center", {}).get("lat")
    lng = element.get("lon") or element.get("center", {}).get("lon")

    # Build address from addr:* tags
    street = tags.get("addr:street", "")
    housenumber = tags.get("addr:housenumber", "")
    address = f"{street} {housenumber}".strip()

    # Detect subcategory from tags
    subcategory = ""
    spec = CATEGORY_QUERIES[category]
    if spec["subcategory_tag"] and spec["subcategory_tag"] in tags:
        subcategory = tags[spec["subcategory_tag"]]

    return Location(
        name=name,
        category=category,
        source="overpass",
        source_id=f"{element['type']}/{element['id']}",
        latitude=lat,
        longitude=lng,
        description=tags.get("description", ""),
        address=address,
        city=tags.get("addr:city", ""),
        postal_code=tags.get("addr:postcode", ""),
        subcategory=subcategory,
        opening_hours=tags.get("opening_hours", ""),
        website_url=tags.get("website", "") or tags.get("contact:website", "") or tags.get("url", ""),
        phone=tags.get("phone", "") or tags.get("contact:phone", ""),
    )


def query_overpass(category: str, max_retries: int = 2) -> list[Location]:
    """Query the Overpass API for a single category. Returns parsed Location list."""
    query = _build_query(category)

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(OVERPASS_ENDPOINT, data={"data": query}, timeout=60)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            if attempt < max_retries and "429" in str(e):
                wait = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s before retry ...")
                time.sleep(wait)
            else:
                print(f"  ✗ Overpass query failed for {category}: {e}")
                return []

    data = resp.json()
    elements = data.get("elements", [])

    locations = []
    for el in elements:
        loc = _parse_element(el, category)
        if loc:
            locations.append(loc)

    return locations


def discover_all_categories() -> list[Location]:
    """Query Overpass for all categories. Returns combined Location list."""
    all_locations = []

    for category in CATEGORY_QUERIES:
        print(f"  Querying Overpass for: {category} ...")
        locs = query_overpass(category)
        print(f"    → {len(locs)} named locations found")
        all_locations.extend(locs)
        # Be polite to the free Overpass API
        time.sleep(3)

    return all_locations
