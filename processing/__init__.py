"""
Processing package for Phase 2 of the AI Restaurant Recommendation Service.

Provides utilities for:
- Cleaning and normalizing ingested restaurant data.
- Deriving simple features useful for downstream recommendations.
- Persisting normalized data into a local SQLite store.
"""

from .phase2_processing import (  # noqa: F401
    NormalizedRestaurant,
    normalize_restaurants,
    persist_restaurants_to_sqlite,
)

