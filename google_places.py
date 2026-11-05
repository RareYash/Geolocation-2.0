"""
OpenStreetMap place search module.
Uses Nominatim, Photon, and Overpass API with multi-tiered resilience.
100% free, no API key needed.
"""

import requests
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── API Endpoints ──────────────────────────────────────────────────
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
PHOTON_URL = "https://photon.komoot.io/api"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_TIMEOUT = 3  # short timeout to prevent blocking when mirrors are unreachable
NOMINATIM_TIMEOUT = 8

# User-Agent required by Nominatim ToS (must be a valid identifying string, not generic/example.com)
HEADERS = {
    "User-Agent": "CityLocatorApp/2.0 (student-project; contact: mytestgeo2026@gmail.com)",
    "Accept": "application/json",
}


def _haversine(lat1, lng1, lat2, lng2):
    """Distance between two points in meters."""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _overpass_post(url, query):
    resp = requests.post(
        url, data={"data": query}, headers=HEADERS, timeout=OVERPASS_TIMEOUT
    )
    resp.raise_for_status()
    return resp.json()


def _overpass_race(query):
    """Send query to Overpass mirrors with short timeout; return first success."""
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS_URLS))
    futures = [pool.submit(_overpass_post, u, query) for u in OVERPASS_URLS]
    try:
        for fut in as_completed(futures):
            try:
                return fut.result()
            except Exception:
                continue
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return None


def search_nearby(lat, lng, osm_tags, keyword=None, radius=2000):
    """
    Search for places near a location using Overpass API, with automatic fallback
    to Nominatim bounded search and Photon API when Overpass is slow or unreachable.

    Args:
        lat (float): Latitude
        lng (float): Longitude
        osm_tags (list): List of OSM tag queries, e.g. ['["amenity"="restaurant"]']
        keyword (str, optional): Keyword for name filtering or text fallback
        radius (int): Search radius in meters

    Returns:
        list: List of place dicts
    """
    places = []

    # 1. Try Overpass first
    tag_queries = []
    for tag in osm_tags:
        tag_queries.append(f'node{tag}(around:{radius},{lat},{lng});')
        tag_queries.append(f'way{tag}(around:{radius},{lat},{lng});')

    query = f"""
    [out:json][timeout:5];
    (
        {"".join(tag_queries)}
    );
    out center body 20;
    """

    try:
        data = _overpass_race(query)
        if data and "elements" in data and len(data["elements"]) > 0:
            places = _parse_elements(data["elements"], lat, lng)
            if keyword and places:
                keyword_lower = keyword.lower()
                filtered = [
                    p for p in places
                    if keyword_lower in p.get("name", "").lower()
                    or keyword_lower in p.get("address", "").lower()
                ]
                if filtered:
                    places = filtered
    except Exception:
        places = []

    # 2. If Overpass failed or found nothing, fall back to Nominatim bounded search
    if not places:
        search_terms = []
        if keyword:
            search_terms.append(keyword)
        # Extract tag values (e.g. restaurant from ["amenity"="restaurant"])
        for tag in osm_tags:
            if "=" in tag:
                val = tag.split("=")[-1].strip('[]"\'')
                val = val.replace("_", " ")
                if val not in search_terms:
                    search_terms.append(val)

        for term in search_terms[:2]:
            nom_places = _search_nominatim_bounded(lat, lng, term, radius=radius)
            if nom_places:
                places.extend(nom_places)
                if len(places) >= 10:
                    break

    # 3. If still no places, try Photon as fast global OSM fallback
    if not places and keyword:
        photon_places = _search_photon(lat, lng, keyword, radius=radius)
        if photon_places:
            places.extend(photon_places)

    # Deduplicate places by name and place_id
    unique_places = []
    seen = set()
    for p in places:
        key = (p.get("name", "").strip().lower(), round(p.get("lat", 0), 3), round(p.get("lng", 0), 3))
        if key not in seen:
            seen.add(key)
            unique_places.append(p)

    # Sort by distance
    unique_places.sort(key=lambda p: p.get("distance_m", 999999))
    return unique_places[:15]


def _search_nominatim_bounded(lat, lng, query_text, radius=2000):
    """Search for places inside a bounding box around center coordinates using Nominatim."""
    try:
        delta = (radius * 1.5) / 111320.0  # rough degrees
        viewbox = f"{lng - delta},{lat - delta},{lng + delta},{lat + delta}"

        resp = requests.get(
            f"{NOMINATIM_URL}/search",
            params={
                "q": query_text,
                "format": "json",
                "limit": 15,
                "viewbox": viewbox,
                "bounded": 1,
                "addressdetails": 1,
                "extratags": 1,
            },
            headers=HEADERS,
            timeout=NOMINATIM_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        results = resp.json()

        places = []
        for r in results:
            plat = float(r.get("lat", 0))
            plng = float(r.get("lon", 0))
            dist = round(_haversine(lat, lng, plat, plng))
            if dist > radius * 2.0:
                continue

            address_parts = r.get("address", {})
            address = ", ".join(
                v for k, v in address_parts.items()
                if k not in ("country", "country_code", "postcode")
            )
            name = (
                r.get("namedetails", {}).get("name")
                or r.get("name")
                or r.get("display_name", "").split(",")[0]
            )

            extra = r.get("extratags", {})
            osm_type = r.get("osm_type", "node")
            osm_id = str(r.get("osm_id", ""))

            places.append({
                "place_id": osm_id,
                "osm_type": osm_type,
                "name": name,
                "address": address or r.get("display_name", ""),
                "lat": plat,
                "lng": plng,
                "rating": 0,
                "total_ratings": 0,
                "price_level": -1,
                "is_open": True,
                "photo_url": "",
                "types": [r.get("type", "")] if r.get("type") else [],
                "maps_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                "distance_m": dist,
                "phone": extra.get("phone", extra.get("contact:phone", "")),
                "cuisine": extra.get("cuisine", ""),
                "opening_hours": extra.get("opening_hours", ""),
            })

        return places
    except Exception:
        return []


def _search_photon(lat, lng, query_text, radius=2000):
    """Search for places using Photon API (Komoot OSM search)."""
    try:
        resp = requests.get(
            PHOTON_URL,
            params={
                "q": query_text,
                "lat": lat,
                "lon": lng,
                "limit": 15,
            },
            headers=HEADERS,
            timeout=NOMINATIM_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        features = data.get("features", [])

        places = []
        for f in features:
            coords = f.get("geometry", {}).get("coordinates", [0, 0])
            plng, plat = float(coords[0]), float(coords[1])
            dist = round(_haversine(lat, lng, plat, plng))
            if dist > radius * 2.5:
                continue

            props = f.get("properties", {})
            name = props.get("name") or props.get("street")
            if not name:
                continue

            addr_parts = [props.get("street"), props.get("city"), props.get("state")]
            address = ", ".join(p for p in addr_parts if p)

            osm_id = str(props.get("osm_id", ""))
            osm_type = props.get("osm_type", "N").lower()
            if osm_type == "n":
                osm_type = "node"
            elif osm_type == "w":
                osm_type = "way"
            elif osm_type == "r":
                osm_type = "relation"

            places.append({
                "place_id": osm_id,
                "osm_type": osm_type,
                "name": name,
                "address": address or "Local Area",
                "lat": plat,
                "lng": plng,
                "rating": 0,
                "total_ratings": 0,
                "price_level": -1,
                "is_open": True,
                "photo_url": "",
                "types": [props.get("osm_value", "")],
                "maps_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}" if osm_id else f"https://www.openstreetmap.org/?mlat={plat}&mlon={plng}#map=17/{plat}/{plng}",
                "distance_m": dist,
                "phone": "",
                "cuisine": "",
                "opening_hours": "",
            })
        return places
    except Exception:
        return []


def search_by_text(lat, lng, query_text, radius=2000):
    """
    Search for places using Nominatim text search.

    Args:
        lat (float): Center latitude for bias
        lng (float): Center longitude for bias
        query_text (str): Text to search for
        radius (int): Search radius in meters

    Returns:
        list: List of place dicts
    """
    places = _search_nominatim_bounded(lat, lng, query_text, radius=radius)
    if not places:
        places = _search_photon(lat, lng, query_text, radius=radius)
    return places


def get_place_details(osm_id, osm_type="node"):
    """
    Get details for a specific place from Nominatim lookup.

    Args:
        osm_id (str): OSM element ID
        osm_type (str): 'node', 'way', or 'relation'

    Returns:
        dict: Place details
    """
    try:
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
            timeout=NOMINATIM_TIMEOUT,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results:
                r = results[0]
                plat = float(r.get("lat", 0))
                plng = float(r.get("lon", 0))

                address_parts = r.get("address", {})
                address = ", ".join(
                    v for k, v in address_parts.items()
                    if k not in ("country", "country_code", "postcode")
                )

                extra = r.get("extratags", {})
                hours = []
                raw_hours = extra.get("opening_hours", "")
                if raw_hours:
                    hours = [h.strip() for h in raw_hours.split(";")]

                name = (
                    r.get("namedetails", {}).get("name")
                    or r.get("name")
                    or r.get("display_name", "").split(",")[0]
                )

                return {
                    "place_id": str(r.get("osm_id", osm_id)),
                    "osm_type": r.get("osm_type", osm_type),
                    "name": name,
                    "address": address or r.get("display_name", ""),
                    "lat": plat,
                    "lng": plng,
                    "rating": 0,
                    "total_ratings": 0,
                    "price_level": -1,
                    "phone": extra.get("phone", extra.get("contact:phone", "")),
                    "website": extra.get("website", extra.get("contact:website", "")),
                    "maps_url": f"https://www.openstreetmap.org/{r.get('osm_type', osm_type)}/{r.get('osm_id', osm_id)}",
                    "photos": [],
                    "reviews": [],
                    "hours": hours,
                    "is_open_now": None,
                    "types": [r.get("type", "")],
                    "cuisine": extra.get("cuisine", ""),
                    "wheelchair": extra.get("wheelchair", ""),
                    "internet_access": extra.get("internet_access", ""),
                }
    except Exception:
        pass

    # Graceful fallback details
    return {
        "place_id": str(osm_id),
        "osm_type": osm_type,
        "name": f"Place #{osm_id}",
        "address": "OpenStreetMap location",
        "lat": 0,
        "lng": 0,
        "rating": 0,
        "total_ratings": 0,
        "price_level": -1,
        "phone": "",
        "website": "",
        "maps_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
        "photos": [],
        "reviews": [],
        "hours": [],
        "is_open_now": None,
        "types": [],
        "cuisine": "",
        "wheelchair": "",
        "internet_access": "",
    }


def geocode(address):
    """
    Geocode an address to lat/lng using Nominatim and Photon.

    Args:
        address (str): Address or place name

    Returns:
        dict or None: {"lat": float, "lng": float, "display": str} or None
    """
    if not address or not address.strip():
        return None

    address_clean = address.strip()

    # If comma-separated coords: "19.9975, 73.7898"
    parts = address_clean.split(",")
    if len(parts) == 2:
        try:
            return {"lat": float(parts[0].strip()), "lng": float(parts[1].strip()), "display": address_clean}
        except ValueError:
            pass

    queries_to_try = [address_clean]
    if "india" not in address_clean.lower():
        queries_to_try.append(f"{address_clean}, Maharashtra, India")

    for q in queries_to_try:
        try:
            resp = requests.get(
                f"{NOMINATIM_URL}/search",
                params={
                    "q": q,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers=HEADERS,
                timeout=NOMINATIM_TIMEOUT,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    return {
                        "lat": float(results[0]["lat"]),
                        "lng": float(results[0]["lon"]),
                        "display": results[0].get("display_name", address_clean),
                    }
        except Exception:
            pass

    # Fallback to Photon geocoding
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": address_clean, "limit": 1},
            headers=HEADERS,
            timeout=NOMINATIM_TIMEOUT,
        )
        if resp.status_code == 200:
            features = resp.json().get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                props = features[0].get("properties", {})
                display_parts = [props.get("name"), props.get("city"), props.get("state"), props.get("country")]
                display = ", ".join(p for p in display_parts if p) or address_clean
                return {
                    "lat": float(coords[1]),
                    "lng": float(coords[0]),
                    "display": display,
                }
    except Exception:
        pass

    return None


def _parse_elements(elements, user_lat, user_lng):
    """Parse Overpass API elements into clean place dicts."""
    places = []
    seen_names = set()

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")

        if not name:
            continue

        if name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        if el.get("type") == "way" and "center" in el:
            plat = el["center"]["lat"]
            plng = el["center"]["lon"]
        else:
            plat = el.get("lat", 0)
            plng = el.get("lon", 0)

        if not plat or not plng:
            continue

        addr_parts = []
        for key in ["addr:street", "addr:suburb", "addr:city"]:
            if key in tags:
                addr_parts.append(tags[key])
        address = ", ".join(addr_parts) if addr_parts else "Local Area"

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
            "rating": 0,
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
