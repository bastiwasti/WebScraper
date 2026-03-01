"""Google Places API (New) source for location discovery and enrichment.

Uses the Nearby Search endpoint to discover family-friendly locations
and enrich existing OSM entries with ratings.

Requires GOOGLE_PLACES_API_KEY in .env.
"""

import requests
import time
from typing import Optional

from config import GOOGLE_PLACES_API_KEY, MONHEIM_LAT, MONHEIM_LNG
from locations.models import Location

API_URL = "https://places.googleapis.com/v1/places:searchNearby"

# --- Family-friendly filtering (target: families with kids <6yo) ---

# Layer 1: Reject places with these primaryTypes (not family destinations)
SUBCATEGORY_BLOCKLIST = {
    # Adult nightlife
    "hookah_bar", "bar", "night_club", "casino", "liquor_store",
    # Accommodation (not a day-trip destination)
    "hotel", "motel", "hostel", "lodging",
    # Shopping (not a destination)
    "shopping_mall", "department_store", "store",
    # Wellness (adults-only typically)
    "spa",
    # Religious buildings (not a family outing)
    "church", "mosque", "synagogue", "hindu_temple",
    # Services (not destinations)
    "service", "insurance_agency", "real_estate_agency",
    # Pets
    "dog_park",
    # Too generic
    "cafe",
    # Sports training (not family fun)
    "sports_school",
}

# Layer 2: Reject places whose name contains these keywords (case-insensitive)
# Catches adult entertainment with acceptable subcategories (e.g. escape rooms = amusement_center)
NAME_BLOCKLIST_KEYWORDS = [
    "escape room", "escape game", "escape am", "escapearena",
    "exit room", "exit game", "exitdoor", "exit zone", "exitzone",
    "indizio", "locked room", "team escape", "teamescape", "teamx",
    "lasertag", "laser tag", "laserzone",
    "axe ", "axt ", "axtwerfen", "axezone",
    "bdsm", "shisha", "hookah", "cocktailbar",
    "lan house", "lan party",
    "woodcutter", "kickerfabrik",
    "theke der welt",
    "virtual reality", "7th space",  # VR venues — not for toddlers
    "die drei ???",                   # mystery game — not for <6yo
    "mind arena", "spybrain", "code agency",
    "gamer d\u00fcsseldorf", "gamer k\u00f6ln",  # gameshow venues
]

# Layer 3: Museum subcategories not suitable for kids <6yo
MUSEUM_BLOCKLIST_SUBTYPES = {
    "art_museum",           # abstract art not engaging for toddlers
    "sculpture",            # not engaging for small kids
    "church",               # religious buildings
    "store",                # shops
    "association_or_organization",
}

# Pro tier field mask — rating, address, website, coordinates, types
FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,places.location,"
    "places.rating,places.userRatingCount,places.types,places.websiteUri,"
    "places.primaryType,places.googleMapsUri"
)

# Search grid: 4 points to cover ~30km radius with overlapping 15km searches
SEARCH_GRID = [
    {"name": "Monheim center", "lat": 51.0917, "lng": 6.8873},
    {"name": "Leverkusen/North", "lat": 51.03, "lng": 6.98},
    {"name": "Dormagen/South", "lat": 51.10, "lng": 6.82},
    {"name": "Langenfeld/East", "lat": 51.11, "lng": 6.95},
]
SEARCH_RADIUS_M = 15000  # 15km per grid point

# Category → Google Place Types mapping
CATEGORY_TYPES = {
    "restaurant": {
        "types": ["restaurant"],
        "min_rating": 4.0,
    },
    "playground": {
        "types": ["playground"],
        "min_rating": None,
    },
    "museum": {
        "types": ["museum"],
        "min_rating": None,
    },
    "zoo": {
        "types": ["zoo"],
        "min_rating": None,
    },
    "pool": {
        "types": ["swimming_pool"],
        "min_rating": None,
    },
    "park": {
        "types": ["park"],
        "min_rating": None,
    },
    "garden": {
        "types": ["botanical_garden"],
        "min_rating": None,
    },
    "indoor_playground": {
        "types": ["amusement_center"],
        "min_rating": None,
    },
    "sport": {
        "types": ["bowling_alley"],
        "min_rating": None,
    },
}


def _check_api_key() -> bool:
    """Check if Google Places API key is configured."""
    if not GOOGLE_PLACES_API_KEY:
        print("  ✗ GOOGLE_PLACES_API_KEY not set in .env — skipping Google Places")
        return False
    return True


def _search_nearby(
    lat: float,
    lng: float,
    radius_m: float,
    included_types: list[str],
) -> list[dict]:
    """Execute a single Nearby Search API call. Returns list of place dicts."""
    body = {
        "includedTypes": included_types,
        "maxResultCount": 20,
        "languageCode": "de",
        "rankPreference": "POPULARITY",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    try:
        resp = requests.post(API_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    ✗ Google Places API error: {e}")
        return []

    data = resp.json()
    return data.get("places", [])


def _parse_place(place: dict, category: str) -> Optional[Location]:
    """Convert a Google Places API response to a Location.

    Applies family-friendly filtering (3 layers) to reject places
    not suitable for families with children under 6.
    """
    display_name = place.get("displayName", {})
    name = display_name.get("text", "").strip()
    if not name:
        return None

    subcategory = place.get("primaryType", "")

    # Layer 1: Subcategory blocklist
    if subcategory in SUBCATEGORY_BLOCKLIST:
        return None

    # Layer 2: Name keyword blocklist
    name_lower = name.lower()
    if any(kw in name_lower for kw in NAME_BLOCKLIST_KEYWORDS):
        return None

    # Layer 3: Category-specific subcategory filter
    if category == "museum" and subcategory in MUSEUM_BLOCKLIST_SUBTYPES:
        return None

    location = place.get("location", {})
    lat = location.get("latitude")
    lng = location.get("longitude")

    address = place.get("formattedAddress", "")

    return Location(
        name=name,
        category=category,
        source="google_places",
        source_id=place.get("id", ""),
        latitude=lat,
        longitude=lng,
        address=address,
        website_url=place.get("websiteUri", ""),
        rating=place.get("rating"),
        subcategory=subcategory,
    )


def discover_all_categories() -> list[Location]:
    """Discover locations via Google Places API across all categories and grid points."""
    if not _check_api_key():
        return []

    all_locations: list[Location] = []
    api_calls = 0
    total_calls = len(CATEGORY_TYPES) * len(SEARCH_GRID)
    print(f"  Estimated API calls: {total_calls}")

    for category, spec in CATEGORY_TYPES.items():
        print(f"  Querying Google Places for: {category} ...")
        category_locations: list[Location] = []

        raw_count = 0
        for grid_point in SEARCH_GRID:
            places = _search_nearby(
                lat=grid_point["lat"],
                lng=grid_point["lng"],
                radius_m=SEARCH_RADIUS_M,
                included_types=spec["types"],
            )
            api_calls += 1
            raw_count += len(places)

            for place in places:
                loc = _parse_place(place, category)
                if loc:
                    category_locations.append(loc)

            # Small delay between calls
            time.sleep(0.2)

        filtered = raw_count - len(category_locations)
        if filtered > 0:
            print(f"    Family filter: removed {filtered} of {raw_count} (not suitable for kids <6)")

        # Apply rating filter if specified
        min_rating = spec.get("min_rating")
        if min_rating is not None:
            before = len(category_locations)
            category_locations = [
                loc for loc in category_locations
                if loc.rating is not None and loc.rating >= min_rating
            ]
            filtered = before - len(category_locations)
            if filtered > 0:
                print(f"    Rating filter ({min_rating}+): removed {filtered} locations")

        print(f"    → {len(category_locations)} locations found")
        all_locations.extend(category_locations)

    print(f"  Total API calls made: {api_calls}")
    return all_locations


def search_single_location(
    lat: float,
    lng: float,
    name: str,
    radius_m: float = 100,
) -> Optional[dict]:
    """Search for a single known location by coordinates (for enrichment).

    Returns the best matching place dict or None.
    """
    if not _check_api_key():
        return None

    # Search with a small radius around the known coordinates
    # Use no type filter to find any nearby place
    body = {
        "maxResultCount": 5,
        "languageCode": "de",
        "rankPreference": "DISTANCE",
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_m,
            }
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    try:
        resp = requests.post(API_URL, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    places = resp.json().get("places", [])
    if not places:
        return None

    # Find best name match
    name_lower = name.lower().strip()
    for place in places:
        place_name = place.get("displayName", {}).get("text", "").lower().strip()
        if place_name == name_lower or name_lower in place_name or place_name in name_lower:
            return place

    # No name match — return closest (first result since ranked by distance)
    # But only if very close (the search radius is already tight)
    return places[0] if radius_m <= 150 else None
