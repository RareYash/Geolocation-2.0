import json
from app import app

client = app.test_client()

def test_routes():
    print("Testing GET / ...")
    r = client.get("/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  OK")

    print("Testing GET /about ...")
    r = client.get("/about")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print("  OK")

    print("Testing GET /api/categories ...")
    r = client.get("/api/categories")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    cats = r.get_json()["categories"]
    assert len(cats) == 8, f"Expected 8 categories, got {len(cats)}"
    print(f"  OK ({len(cats)} categories returned)")

    print("Testing GET /api/geocode for cities:")
    for city in ["Nashik", "Pune", "Mumbai", "Thane"]:
        r = client.get(f"/api/geocode?q={city}")
        assert r.status_code == 200, f"Geocode for {city} failed: {r.status_code}"
        data = r.get_json()
        assert "lat" in data and "lng" in data, f"Missing coords for {city}"
        print(f"  {city} -> lat={data['lat']}, lng={data['lng']}")

    cities = [
        {"name": "Nashik", "lat": 19.9975, "lng": 73.7898},
        {"name": "Pune", "lat": 18.5204, "lng": 73.8567},
        {"name": "Mumbai", "lat": 19.0760, "lng": 72.8777},
        {"name": "Thane", "lat": 19.2183, "lng": 72.9781},
    ]

    print("\nTesting POST /api/recommend for each city:")
    for city in cities:
        payload = {
            "lat": city["lat"],
            "lng": city["lng"],
            "categories": ["restaurant", "grocery", "medical", "atm_bank"],
            "radius": 2000,
            "budget": 2
        }
        r = client.post("/api/recommend", json=payload)
        assert r.status_code == 200, f"Recommend for {city['name']} failed with {r.status_code}"
        data = r.get_json()
        assert "results" in data, "No results key"
        assert "summary" in data, "No summary key"
        total = data["summary"]["total_places_found"]
        print(f"  {city['name']}: {total} total places found across {len(data['results'])} categories")
        assert total > 0, f"Expected places in {city['name']}, got 0"

    print("\nALL E2E TESTS PASSED SUCCESSFULLY! :)")

if __name__ == "__main__":
    test_routes()

