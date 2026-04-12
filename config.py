import os
from dotenv import load_dotenv

load_dotenv()

# Default search settings
DEFAULT_RADIUS = 2000  # meters (2km)
MAX_RESULTS_PER_CATEGORY = 10

# Nashik center coordinates (default fallback)
NASHIK_CENTER = {"lat": 19.9975, "lng": 73.7898}

# Scoring weights for recommendation engine
SCORING_WEIGHTS = {
    "proximity": 0.35,
    "rating": 0.20,
    "budget_match": 0.25,
    "popularity": 0.20,
}

# Category definitions with OpenStreetMap tag mappings
# Each tag is an Overpass QL filter like ["amenity"="restaurant"]
CATEGORIES = {
    "restaurant": {
        "label": "Restaurant",
        "icon": "🍽️",
        "osm_tags": ['["amenity"="restaurant"]', '["amenity"="fast_food"]'],
        "keyword": None,
    },
    "grocery": {
        "label": "Grocery",
        "icon": "🛒",
        "osm_tags": ['["shop"="supermarket"]', '["shop"="convenience"]', '["shop"="grocery"]'],
        "keyword": None,
    },
    "bus_stop": {
        "label": "Bus Stop",
        "icon": "🚌",
        "osm_tags": ['["highway"="bus_stop"]', '["amenity"="bus_station"]'],
        "keyword": None,
    },
    "train_station": {
        "label": "Train Station",
        "icon": "🚂",
        "osm_tags": ['["railway"="station"]', '["railway"="halt"]'],
        "keyword": None,
    },
    "medical": {
        "label": "Medical",
        "icon": "🏥",
        "osm_tags": ['["amenity"="hospital"]', '["amenity"="pharmacy"]', '["amenity"="clinic"]'],
        "keyword": None,
    },
    "gym": {
        "label": "Gym",
        "icon": "💪",
        "osm_tags": ['["leisure"="fitness_centre"]', '["leisure"="sports_centre"]'],
        "keyword": None,
    },
    "atm_bank": {
        "label": "ATM / Bank",
        "icon": "🏧",
        "osm_tags": ['["amenity"="atm"]', '["amenity"="bank"]'],
        "keyword": None,
    },
    "study_space": {
        "label": "Study",
        "icon": "📚",
        "osm_tags": ['["amenity"="library"]', '["amenity"="cafe"]'],
        "keyword": "library study",
    },
}
