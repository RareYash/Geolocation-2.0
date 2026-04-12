"""
Geo-loc 2.0 — Nashik City Newcomer Assistant
Flask backend — uses free OpenStreetMap APIs (no billing needed).
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from config import CATEGORIES, DEFAULT_RADIUS, NASHIK_CENTER
from google_places import search_nearby, search_by_text, get_place_details, geocode
from recommender import score_and_rank, filter_places, get_area_summary


app = Flask(__name__)
CORS(app)


# ── Page Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ── API Routes ──────────────────────────────────────────────────────

@app.route("/api/categories", methods=["GET"])
def get_categories():
    """Return all available service categories."""
    cats = [
        {"id": key, "label": info["label"], "icon": info["icon"]}
        for key, info in CATEGORIES.items()
    ]
    return jsonify({"categories": cats})


@app.route("/api/geocode", methods=["GET"])
def geocode_address():
    """Geocode an address to lat/lng."""
    address = request.args.get("q", "")
    if not address:
        return jsonify({"error": "Address required"}), 400

    result = geocode(address)
    if result:
        return jsonify(result)
    return jsonify({"error": "Location not found"}), 404


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """
    Main recommendation endpoint.

    JSON body: { "lat", "lng", "categories": [], "budget": int, "radius": int }
    Returns: { "results": { category: [places] }, "summary": {} }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    lat = data.get("lat")
    lng = data.get("lng")
    categories = data.get("categories", [])
    budget = data.get("budget")
    radius = data.get("radius", DEFAULT_RADIUS)

    if not lat or not lng:
        return jsonify({"error": "lat and lng are required"}), 400
    if not categories:
        return jsonify({"error": "At least one category is required"}), 400

    valid_cats = [c for c in categories if c in CATEGORIES]
    if not valid_cats:
        return jsonify({"error": "No valid categories provided"}), 400

    all_results = {}

    for cat_key in valid_cats:
        cat_info = CATEGORIES[cat_key]
        osm_tags = cat_info["osm_tags"]
        keyword = cat_info.get("keyword")

        # Search via Overpass API
        places = search_nearby(lat, lng, osm_tags, keyword=keyword, radius=radius)

        # Fallback to text search if empty
        if isinstance(places, list) and len(places) == 0:
            fallback_query = keyword or cat_info["label"]
            places = search_by_text(lat, lng, fallback_query, radius=radius)

        # Score and rank
        if isinstance(places, list):
            places = score_and_rank(places, user_budget=budget, radius=radius)

        all_results[cat_key] = places

    summary = get_area_summary(all_results)

    return jsonify({"results": all_results, "summary": summary})


@app.route("/api/place-details/<osm_type>/<place_id>", methods=["GET"])
def place_details(osm_type, place_id):
    """Get detailed info for a specific place."""
    details = get_place_details(place_id, osm_type=osm_type)
    if isinstance(details, dict) and "error" in details:
        return jsonify(details), 500
    return jsonify(details)


@app.route("/api/config", methods=["GET"])
def get_config():
    """Return public configuration."""
    return jsonify({
        "default_center": NASHIK_CENTER,
        "default_radius": DEFAULT_RADIUS,
    })


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🗺️  City locator — Using free OpenStreetMap APIs")
    print("   No API key needed! Just run and go.\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
