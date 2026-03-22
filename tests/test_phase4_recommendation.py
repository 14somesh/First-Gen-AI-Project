from __future__ import annotations

import sqlite3
from pathlib import Path

from ingestion import ingest_restaurants
from processing import normalize_restaurants, persist_restaurants_to_sqlite
from recommendation import RecommendationRequest, recommend_restaurants


def _find_a_row_with_filters(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT location, cuisines, price_bucket, rating
            FROM restaurants
            WHERE location IS NOT NULL
              AND cuisines IS NOT NULL
              AND price_bucket IS NOT NULL
              AND rating IS NOT NULL
            LIMIT 1
            """
        )
        return cursor.fetchone()
    finally:
        conn.close()


def test_phase4_recommendations_end_to_end(tmp_path: Path):
    """
    End-to-end test for Phase 4:

    - Phase 1: ingest a sample.
    - Phase 2: normalize and persist to a temporary SQLite DB.
    - Phase 4: request recommendations and validate filtering + ranking.
    """
    ingested = ingest_restaurants(sample_size=200)
    normalized = normalize_restaurants(ingested)
    assert normalized, "Expected normalized records for Phase 4 test"

    db_path = tmp_path / "restaurants_phase4.db"
    persist_restaurants_to_sqlite(normalized, db_path=str(db_path))

    seed = _find_a_row_with_filters(db_path)
    assert seed is not None, "Expected at least one row with basic filterable fields"

    seed_location, seed_cuisines, seed_price_bucket, seed_rating = seed
    # Choose a cuisine token that is likely to match.
    cuisine_token = str(seed_cuisines).split(",")[0].strip()
    location_token = str(seed_location).split(" ")[0].strip()

    request = RecommendationRequest(
        location_query=location_token,
        cuisine_queries=[cuisine_token],
        price_bucket=seed_price_bucket,
        min_rating=float(seed_rating) - 0.1,
    )

    recs = recommend_restaurants(db_path=str(db_path), request=request, limit=10)
    assert recs, "Expected at least one recommendation"

    # Validate basic ordering by score.
    scores = [r.score for r in recs]
    assert scores == sorted(scores, reverse=True)

    # Validate filters are respected (best-effort; text matches are substring-based).
    for r in recs:
        assert r.price_bucket == seed_price_bucket
        assert r.rating is None or r.rating >= request.min_rating
        assert r.location is None or location_token.lower() in r.location.lower()
        assert r.cuisines is None or cuisine_token.lower() in r.cuisines.lower()

