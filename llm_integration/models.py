from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ExplicitFilters:
    """
    Explicit filters provided by the user or API client alongside free text.
    """

    price_range: Optional[str] = None
    location: Optional[str] = None
    cuisines: Optional[List[str]] = None
    min_rating: Optional[float] = None


@dataclass
class UserPreferences:
    """
    Normalized representation of user preferences as interpreted by the LLM.
    """

    price_range: Optional[str] = None
    location: Optional[str] = None
    cuisines: List[str] = field(default_factory=list)
    min_rating: Optional[float] = None
    ambience: Optional[str] = None
    special_requirements: List[str] = field(default_factory=list)
    sort_preference: Optional[str] = None
    raw_llm_response: Dict = field(default_factory=dict)

