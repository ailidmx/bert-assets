import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests


class GooglePlacesService:
    """Google Places API service for fetching location data during storefront generation."""

    def __init__(self, api_key: str, cache_dir: str = "cache"):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place/details/json"
        self.photo_base_url = "https://maps.googleapis.com/maps/api/place/photo"
        self.cache_dir = cache_dir
        self.cache_ttl_hours = 24
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_key(self, place_id: str) -> str:
        return f"place_details_{place_id}.json"

    def get_cache_path(self, place_id: str) -> str:
        return os.path.join(self.cache_dir, self.get_cache_key(place_id))

    def is_cache_valid(self, cache_path: str) -> bool:
        if not os.path.exists(cache_path):
            return False
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - file_time < timedelta(hours=self.cache_ttl_hours)

    def load_from_cache(self, place_id: str) -> Optional[Dict]:
        cache_path = self.get_cache_path(place_id)
        if self.is_cache_valid(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def save_to_cache(self, place_id: str, data: Dict):
        cache_path = self.get_cache_path(place_id)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError:
            return

    def fetch_place_details(self, place_id: str, max_photos: int = 4, max_reviews: int = 6) -> Dict:
        cached_data = self.load_from_cache(place_id)
        if cached_data:
            return cached_data

        params = {
            "place_id": place_id,
            "fields": "place_id,name,formatted_address,geometry,photo,review",
            "key": self.api_key,
            "language": "es",
            "region": "mx",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "OK":
                return self.get_fallback_data(place_id)
            result = data.get("result", {})
            enriched_data = self._process_place_data(result, max_photos, max_reviews)
            self.save_to_cache(place_id, enriched_data)
            return enriched_data
        except requests.exceptions.RequestException:
            return self.get_fallback_data(place_id)
        except Exception:
            return self.get_fallback_data(place_id)

    def _process_place_data(self, place_data: Dict, max_photos: int, max_reviews: int) -> Dict:
        geometry = place_data.get("geometry", {}).get("location", {})
        location_data = {
            "name": place_data.get("name", ""),
            "address": place_data.get("formatted_address", ""),
            "placeId": place_data.get("place_id", ""),
            "location": {
                "lat": geometry.get("lat", 0),
                "lng": geometry.get("lng", 0),
            },
            "photos": [],
            "googleReviews": [],
        }

        photos = place_data.get("photos", [])
        for i, photo in enumerate(photos[:max_photos]):
            photo_ref = photo.get("photo_reference")
            if not photo_ref:
                continue
            location_data["photos"].append(
                {
                    "id": f"photo_{i + 1}",
                    "name": photo_ref,
                    "url": self._get_photo_url(photo_ref),
                    "attributions": [],
                }
            )

        reviews = place_data.get("reviews", [])
        for i, review in enumerate(reviews[:max_reviews]):
            review_text = review.get("text", "")
            if not str(review_text).strip():
                continue
            location_data["googleReviews"].append(
                {
                    "id": f"review_{i + 1}",
                    "author": review.get("author_name", "Cliente"),
                    "rating": float(review.get("rating", 0)),
                    "text": review_text,
                    "relativeTime": review.get("relative_time_description", ""),
                }
            )

        return location_data

    def _get_photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        params = {
            "photoreference": photo_reference,
            "maxwidth": max_width,
            "key": self.api_key,
        }
        return f"{self.photo_base_url}?{urlencode(params)}"

    def get_fallback_data(self, place_id: str) -> Dict:
        return {
            "name": "",
            "address": "",
            "placeId": place_id,
            "location": {"lat": 0, "lng": 0},
            "photos": [],
            "googleReviews": [],
        }


def get_google_places_api_key() -> Optional[str]:
    return os.environ.get("GOOGLE_PLACES_API_KEY") or os.environ.get("GOOGLE_PLACES_SERVER_API_KEY")


def enrich_location_data(location_data: Dict, api_key: Optional[str] = None) -> Dict:
    if not api_key:
        api_key = get_google_places_api_key()
    if not api_key:
        return location_data
    place_id = location_data.get("placeId", "")
    if not place_id:
        return location_data
    try:
        service = GooglePlacesService(api_key)
        enriched_data = service.fetch_place_details(place_id)
        result = {**location_data, **enriched_data}
        result["placeId"] = location_data.get("placeId", enriched_data.get("placeId", ""))
        result["name"] = location_data.get("name", enriched_data.get("name", ""))
        result["address"] = location_data.get("address", enriched_data.get("address", ""))
        return result
    except Exception:
        return location_data