"""
ML-based recommendation engine.
Scores and ranks places based on proximity, budget, rating, and popularity.
"""

from config import SCORING_WEIGHTS, DEFAULT_RADIUS


def score_and_rank(places, user_budget=None, radius=None):
    """
    Score and rank a list of places using a weighted composite score.

    Scoring formula:
        score = w1 * proximity_score
              + w2 * rating_score
              + w3 * budget_match_score
              + w4 * popularity_score

    Args:
        places (list): List of place dicts from google_places module
        user_budget (int, optional): User's budget level (1=low, 2=mid, 3=high)
        radius (int, optional): Search radius used, for proximity normalization

    Returns:
        list: Same places, sorted by composite score (highest first)
    """
    if not places or isinstance(places, dict):
        return places  # pass errors through

    radius = radius or DEFAULT_RADIUS
    w = SCORING_WEIGHTS

    for place in places:
        # ── 1. Proximity Score (closer = better) ──
        dist = place.get("distance_m", radius)
        proximity_score = max(0, 1 - (dist / radius))

        # ── 2. Rating Score (normalized 0-1) ──
        rating = place.get("rating", 0)
        rating_score = rating / 5.0 if rating > 0 else 0.5  # default mid

        # ── 3. Budget Match Score ──
        budget_score = _calculate_budget_score(
            place.get("price_level", -1), user_budget
        )

        # ── 4. Popularity Score (log-scaled review count) ──
        import math
        total_ratings = place.get("total_ratings", 0)
        if total_ratings > 0:
            # Log scale: 1 review → 0, 10 → 0.5, 100 → 0.75, 1000 → 1.0
            popularity_score = min(1.0, math.log10(total_ratings + 1) / 3.0)
        else:
            popularity_score = 0.1  # small default

        # ── Composite Score ──
        composite = (
            w["proximity"] * proximity_score
            + w["rating"] * rating_score
            + w["budget_match"] * budget_score
            + w["popularity"] * popularity_score
        )

        place["scores"] = {
            "proximity": round(proximity_score, 3),
            "rating": round(rating_score, 3),
            "budget_match": round(budget_score, 3),
            "popularity": round(popularity_score, 3),
            "composite": round(composite, 3),
        }

    # Sort by composite score, descending
    places.sort(key=lambda p: p.get("scores", {}).get("composite", 0), reverse=True)
    return places


def _calculate_budget_score(price_level, user_budget):
    """
    Calculate how well a place matches the user's budget.

    Args:
        price_level (int): Place's price level (0-4, -1 if unknown)
        user_budget (int): User's budget (1=low, 2=mid, 3=high, None=any)

    Returns:
        float: Score from 0 to 1
    """
    # If we don't know the price or user doesn't care, neutral score
    if price_level == -1 or user_budget is None:
        return 0.5

    # Map user budget to expected price levels
    budget_to_price = {
        1: [0, 1],       # Low budget → prefers free/inexpensive
        2: [1, 2],       # Medium budget → inexpensive/moderate
        3: [2, 3, 4],    # High budget → moderate to expensive
    }

    preferred = budget_to_price.get(user_budget, [0, 1, 2, 3, 4])

    if price_level in preferred:
        return 1.0
    else:
        # Penalize based on distance from preferred range
        min_diff = min(abs(price_level - p) for p in preferred)
        return max(0, 1 - (min_diff * 0.3))


def filter_places(places, min_rating=None, open_only=False):
    """
    Apply additional filters to the results.

    Args:
        places (list): List of place dicts
        min_rating (float, optional): Minimum rating threshold
        open_only (bool): If True, show only currently open places

    Returns:
        list: Filtered places
    """
    if not places or isinstance(places, dict):
        return places

    filtered = places
    if min_rating is not None:
        filtered = [p for p in filtered if p.get("rating", 0) >= min_rating]
    if open_only:
        filtered = [p for p in filtered if p.get("is_open", True)]

    return filtered


def get_area_summary(all_results):
    """
    Generate a summary of the area based on search results.

    Args:
        all_results (dict): Category → places mapping

    Returns:
        dict: Summary statistics
    """
    total_places = 0
    avg_ratings = {}
    category_counts = {}

    for category, places in all_results.items():
        if isinstance(places, dict) and "error" in places:
            continue
        count = len(places) if isinstance(places, list) else 0
        total_places += count
        category_counts[category] = count

        if count > 0:
            ratings = [p["rating"] for p in places if p.get("rating", 0) > 0]
            avg_ratings[category] = (
                round(sum(ratings) / len(ratings), 1) if ratings else 0
            )

    return {
        "total_places_found": total_places,
        "category_counts": category_counts,
        "average_ratings": avg_ratings,
    }
