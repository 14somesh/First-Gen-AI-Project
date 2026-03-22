from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RecommendationRequest:
    """
    Inputs used by the Phase 4 recommendation engine.

    Values are intentionally simple and map directly to fields stored in the
    Phase 2 SQLite table.
    """

    location_query: Optional[str] = None
    cuisine_queries: List[str] = field(default_factory=list)
    price_bucket: Optional[str] = None  # low | medium | high
    min_rating: Optional[float] = None


@dataclass
class RestaurantRecommendation:
    """
    Output from the Phase 4 recommendation engine.
    """

    name: str
    location: Optional[str]
    cuisines: Optional[str]
    price_bucket: Optional[str]
    rating: Optional[float]
    votes: Optional[int]
    score: float

