from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RestaurantRecord:
    """
    Canonical representation of a restaurant for the ingestion phase.

    This keeps a small set of normalized fields that downstream phases are
    likely to use, while also preserving the full raw record for later use.
    """

    id: Optional[str]
    name: Optional[str]
    location: Optional[str]
    cuisines: Optional[str]
    price_range: Optional[float]
    rating: Optional[float]
    votes: Optional[int]
    raw: Dict[str, Any]

