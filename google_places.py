"""
OpenStreetMap place search module.
Uses Overpass API for nearby search and Nominatim for geocoding.
100% free, no API key needed.
"""

import requests
import math

# ── API Endpoints ──────────────────────────────────────────────────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"

# User-Agent required by Nominatim ToS
HEADERS = {"User-Agent": "Geo-loc/2.0 (student-project)"}


def search_nearby(lat, lng, osm_tags, keyword=None, radius=2000):
    """
    Search for places near a location using Overpass API.

    Args:
        lat (float): Latitude
        lng (float): Longitude
        osm_tags (list): List of OSM tag queries, e.g. ['"amenity"="restaurant"']
        keyword (str, optional): Keyword for name filtering
        radius (int): Search radius in meters

    Returns:
        list: List of place dicts
    """
    # Build Overpass QL query
    tag_queries = []
    for tag in osm_tags:
        tag_queries.append(f'node{tag}(around:{radius},{lat},{lng});')
        tag_queries.append(f'way{tag}(around:{radius},{lat},{lng});')

    query = f"""
    [out:json][timeout:15];
    (
        {"".join(tag_queries)}
    );
    out center body;
    """

    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])

        places = _parse_elements(elements, lat, lng)

        # Filter by keyword if provided
        if keyword and places:
            keyword_lower = keyword.lower()
            filtered = [
                p for p in places
                if keyword_lower in p.get("name", "").lower()
                or keyword_lower in p.get("address", "").lower()
            ]
            # If keyword filter removes everything, return all results
            if filtered:
                places = filtered

        return places

    except requests.exceptions.RequestException as e:
        return {"error": f"Search failed: {str(e)}"}


def search_by_text(lat, lng, query_text, radius=2000):
    """
    Search for places using Nominatim text search (geocoding + search).

    Args:
        lat (float): Center latitude for bias
        lng (float): Center longitude for bias
        query_text (str): Text to search for
        radius (int): Search radius in meters

    Returns:
        list: List of place dicts
    """
    try:
        # Calculate bounding box from center + radius
        delta = radius / 111320  # rough degrees
        viewbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"

        resp = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": f"{query_text} Nashik",
                "format": "json",
                "limit": 10,
                "viewbox": viewbox,
                "bounded": 1,
                "addressdetails": 1,
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()

        places = []
        for r in results:
            plat = float(r.get("lat", 0))
            plng = float(r.get("lon", 0))
            address_parts = r.get("address", {})
            address = ", ".join(
                v for k, v in address_parts.items()
                if k not in ("country", "country_code", "state", "postcode", "state_district")
            )

            places.append({
                "place_id": r.get("osm_id", ""),
                "osm_type": r.get("osm_type", ""),
                "name": r.get("display_name", "").split(",")[0],
                "address": address or r.get("display_name", ""),
                "lat": plat,
                "lng": plng,
                "rating": 0,
                "total_ratings": 0,
                "price_level": -1,
                "is_open": True,
                "photo_url": "",
                "types": [r.get("type", "")],
                "maps_url": f"https://www.openstreetmap.org/?mlat={plat}&mlon={plng}#map=17/{plat}/{plng}",
                "distance_m": round(_haversine(lat, lng, plat, plng)),
            })

        return places

    except requests.exceptions.RequestException as e:
        return {"error": f"Text search failed: {str(e)}"}


def get_place_details(osm_id, osm_type="node"):
    """
    Get details for a specific place from Nominatim.

    Args:
        osm_id (str): OSM element ID
        osm_type (str): 'node', 'way', or 'relation'

    Returns:
        dict: Place details
    """
    try:
        # Map type letter for Nominatim
        type_letter = {"node": "N", "way": "W", "relation": "R"}.get(osm_type, "N")

        resp = requests.get(
            f"{NOMINATIM_URL}/lookup",
            params={
                "osm_ids": f"{type_letter}{osm_id}",
                "format": "json",
                "addressdetails": 1,
                "extratags": 1,
                "namedetails": 1,
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()

        if not results:
            return {"error": "Place not found"}

        r = results[0]
        plat = float(r.get("lat", 0))
        plng = float(r.get("lon", 0))

        address_parts = r.get("address", {})
        address = ", ".join(
            v for k, v in address_parts.items()
            if k not in ("country", "country_code", "state", "postcode", "state_district")
        )

        extra = r.get("extratags", {})

        # Build opening hours
        hours = []
        raw_hours = extra.get("opening_hours", "")
        if raw_hours:
            hours = [h.strip() for h in raw_hours.split(";")]

        return {
            "place_id": r.get("osm_id", ""),
            "osm_type": r.get("osm_type", ""),
            "name": r.get("namedetails", {}).get("name", r.get("display_name", "").split(",")[0]),
            "address": address or r.get("display_name", ""),
            "lat": plat,
            "lng": plng,
            "rating": 0,
            "total_ratings": 0,
            "price_level": -1,
            "phone": extra.get("phone", extra.get("contact:phone", "")),
            "website": extra.get("website", extra.get("contact:website", "")),
            "maps_url": f"https://www.openstreetmap.org/{r.get('osm_type', 'node')}/{r.get('osm_id', '')}",
            "photos": [],
            "reviews": [],
            "hours": hours,
            "is_open_now": None,
            "types": [r.get("type", "")],
            "cuisine": extra.get("cuisine", ""),
            "wheelchair": extra.get("wheelchair", ""),
            "internet_access": extra.get("internet_access", ""),
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Details lookup failed: {str(e)}"}


def geocode(address):
    """
    Geocode an address to lat/lng using Nominatim.

    Args:
        address (str): Address or place name

    Returns:
        dict or None: {"lat": float, "lng": float} or None
    """
    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": f"{address}, Nashik, Maharashtra, India",
                "format": "json",
                "limit": 1,
            },
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()

        if results:
            return {
                "lat": float(results[0]["lat"]),
                "lng": float(results[0]["lon"]),
                "display": results[0].get("display_name", address),
            }
        return None

    except requests.exceptions.RequestException:
        return None


# ── Helpers ────────────────────────────────────────────────────────

def _haversine(lat1, lng1, lat2, lng2):
    """Distance between two points in meters."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_elements(elements, user_lat, user_lng):
    """Parse Overpass API elements into clean place dicts."""
    places = []
    seen_names = set()  # deduplicate

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")

        # Skip unnamed places
        if not name:
            continue

        # Deduplicate
        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        # Get coordinates (ways use center, nodes use lat/lon)
        if el.get("type") == "way" and "center" in el:
            plat = el["center"]["lat"]
            plng = el["center"]["lon"]
        else:
            plat = el.get("lat", 0)
            plng = el.get("lon", 0)

        if not plat or not plng:
            continue

        # Build address from tags
        addr_parts = []
        for key in ["addr:street", "addr:suburb", "addr:city"]:
            if key in tags:
                addr_parts.append(tags[key])
        address = ", ".join(addr_parts) if addr_parts else f"Nashik, Maharashtra"

        # Build OSM URL
        osm_type = el.get("type", "node")
        osm_id = el.get("id", "")
        maps_url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

        places.append({
            "place_id": str(osm_id),
            "osm_type": osm_type,
            "name": name,
            "address": address,
            "lat": plat,
            "lng": plng,
            "rating": 0,  # OSM doesn't have ratings
            "total_ratings": 0,
            "price_level": -1,
            "is_open": True,
            "photo_url": "",
            "types": list(tags.keys())[:5],
            "maps_url": maps_url,
            "distance_m": round(_haversine(user_lat, user_lng, plat, plng)),
            "phone": tags.get("phone", tags.get("contact:phone", "")),
            "cuisine": tags.get("cuisine", ""),
            "opening_hours": tags.get("opening_hours", ""),
        })

    return places
