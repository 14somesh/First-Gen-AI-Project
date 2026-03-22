from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional, Sequence, Tuple

from .models import RecommendationRequest, RestaurantRecommendation


def _contains_ci(haystack: Optional[str], needle: str) -> bool:
    if haystack is None:
        return False
    return needle.lower() in haystack.lower()


def _score_row(
    *,
    rating: Optional[float],
    votes: Optional[int],
    popularity_score: Optional[float],
    request: RecommendationRequest,
    location: Optional[str],
    cuisines: Optional[str],
    price_bucket: Optional[str],
) -> float:
    score = 0.0

    # Primary quality signal.
    if isinstance(rating, (int, float)):
        score += float(rating) * 10.0

    # Secondary quality signal / confidence.
    if isinstance(votes, int):
        score += min(votes, 1000) / 50.0

    # Optional precomputed popularity from Phase 2 (rating * capped votes).
    if isinstance(popularity_score, (int, float)):
        score += float(popularity_score) / 500.0

    # Preference matches.
    if request.price_bucket and price_bucket and request.price_bucket == price_bucket:
        score += 5.0

    if request.location_query and _contains_ci(location, request.location_query):
        score += 5.0

    if request.cuisine_queries and cuisines:
        matches = sum(1 for c in request.cuisine_queries if _contains_ci(cuisines, c))
        score += matches * 4.0

    return score


def _build_where_and_params(request: RecommendationRequest) -> Tuple[str, List]:
    clauses: List[str] = []
    params: List = []

    if request.min_rating is not None:
        clauses.append("rating IS NOT NULL AND rating >= ?")
        params.append(float(request.min_rating))

    # Only filter by price when a bucket is set. "Any" / None = include all restaurants.
    if request.price_bucket:
        clauses.append("price_bucket = ?")
        params.append(request.price_bucket)

    if request.location_query:
        clauses.append("location IS NOT NULL AND lower(location) LIKE ?")
        params.append(f"%{request.location_query.lower()}%")

    # Cuisine matching: OR across requested cuisines (at least one should match).
    if request.cuisine_queries:
        cuisine_clauses = []
        for c in request.cuisine_queries:
            cuisine_clauses.append("(cuisines IS NOT NULL AND lower(cuisines) LIKE ?)")
            params.append(f"%{c.lower()}%")
        clauses.append("(" + " OR ".join(cuisine_clauses) + ")")

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return where_sql, params


def recommend_restaurants(
    *,
    db_path: str,
    request: RecommendationRequest,
    limit: int = 10,
    candidate_limit: int = 500,
) -> List[RestaurantRecommendation]:
    """
    Phase 4 recommendation engine.

    - Fetches candidates from the Phase 2 SQLite store using structured filters.
    - Scores each candidate with a lightweight function.
    - Returns the top-N recommendations with scores.
    """
    where_sql, params = _build_where_and_params(request)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                name, location, cuisines, price_bucket,
                rating, votes, popularity_score
            FROM restaurants
            {where_sql}
            LIMIT ?
            """,
            [*params, int(candidate_limit)],
        )
        rows: Sequence[Tuple] = cursor.fetchall()
    finally:
        conn.close()

    scored: List[RestaurantRecommendation] = []
    for (
        name,
        location,
        cuisines,
        price_bucket,
        rating,
        votes,
        popularity_score,
    ) in rows:
        score = _score_row(
            rating=rating,
            votes=votes,
            popularity_score=popularity_score,
            request=request,
            location=location,
            cuisines=cuisines,
            price_bucket=price_bucket,
        )

        scored.append(
            RestaurantRecommendation(
                name=name,
                location=location,
                cuisines=cuisines,
                price_bucket=price_bucket,
                rating=rating,
                votes=votes,
                score=float(score),
            )
        )

    # Sort by score and remove duplicates (by name + location combination).
    scored.sort(key=lambda r: r.score, reverse=True)
    deduped: List[RestaurantRecommendation] = []
    seen_keys = set()
    for rec in scored:
        key = (rec.name.strip().lower(), (rec.location or "").strip().lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(rec)
        if len(deduped) >= int(limit):
            break

    return deduped

