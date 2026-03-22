## Phase 4 – Recommendation Engine

This folder is reserved for assets and documentation specific to **Phase 4: Recommendation Engine** of the AI Restaurant Recommendation Service.

Current implementation details:
- Core recommendation code lives in the `recommendation` package:
  - `recommendation/models.py` defines request/response objects:
    - `RecommendationRequest`
    - `RestaurantRecommendation`
  - `recommendation/phase4_recommender.py` implements:
    - `recommend_restaurants(db_path, request, limit=10, candidate_limit=500)`
      - Reads candidates from the Phase 2 SQLite store (`restaurants` table).
      - Applies structured filtering (location/cuisine/price bucket/min rating).
      - Scores and ranks candidates with a lightweight, deterministic function.

### Testing

The test `tests/test_phase4_recommendation.py` builds a temporary SQLite DB using Phases 1–2,
then verifies Phase 4 returns valid ranked recommendations.

