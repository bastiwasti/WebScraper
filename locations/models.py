"""Data models for the locations/Ausflüge feature."""

from dataclasses import dataclass, field
from typing import Optional
import math


# Location categories for family-friendly Ausflugsziele
LOCATION_CATEGORIES = {
    "playground": "Spielplatz",
    "indoor_playground": "Indoor-Spielplatz",
    "park": "Park",
    "garden": "Garten",
    "museum": "Museum",
    "zoo": "Zoo / Tierpark",
    "pool": "Schwimmbad",
    "restaurant": "Familienrestaurant",
    "sport": "Sport & Freizeit",
    "other": "Sonstiges",
}


@dataclass
class Location:
    """A family-friendly location/Ausflugsziel."""

    name: str
    category: str
    source: str  # 'overpass', 'google_places', 'manual'
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = ""
    address: str = ""
    city: str = ""
    postal_code: str = ""
    subcategory: str = ""
    opening_hours: str = ""
    opening_hours_json: str = ""
    website_url: str = ""
    phone: str = ""
    rating: Optional[float] = None
    source_id: str = ""
    distance_km: Optional[float] = None

    def calculate_distance(self, ref_lat: float, ref_lng: float) -> float:
        """Calculate haversine distance in km from a reference point."""
        if self.latitude is None or self.longitude is None:
            return float("inf")

        R = 6371.0  # Earth radius in km
        lat1, lat2 = math.radians(ref_lat), math.radians(self.latitude)
        dlat = lat2 - lat1
        dlng = math.radians(self.longitude - ref_lng)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        self.distance_km = round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)
        return self.distance_km
