from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable, List, Optional

from ingestion import RestaurantRecord


@dataclass
class NormalizedRestaurant:
    """
    Normalized representation of a restaurant used after Phase 2 processing.
    """

    id: Optional[str]
    name: str
    location: Optional[str]
    cuisines: Optional[str]
    price_range: Optional[float]
    price_bucket: Optional[str]
    rating: Optional[float]
    votes: Optional[int]
    popularity_score: Optional[float]


def _normalize_location(location: Optional[str]) -> Optional[str]:
    if not location or not isinstance(location, str):
        return None
    # Simple trimming standardization; more complex parsing can be added later.
    return " ".join(location.split())


def _normalize_cuisines(cuisines: Optional[str]) -> Optional[str]:
    if not cuisines or not isinstance(cuisines, str):
        return None
    # Normalize casing and spacing, keep comma-separated list.
    parts = [p.strip().title() for p in cuisines.split(",") if p.strip()]
    return ", ".join(parts) if parts else None


def _price_to_bucket(price: Optional[float]) -> Optional[str]:
    if price is None:
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p <= 300:
        return "low"
    if p <= 800:
        return "medium"
    return "high"


def _compute_popularity(rating: Optional[float], votes: Optional[int]) -> Optional[float]:
    if rating is None or votes is None:
        return None
    try:
        return float(rating) * min(int(votes), 1000)
    except (TypeError, ValueError):
        return None


def normalize_restaurants(records: Iterable[RestaurantRecord]) -> List[NormalizedRestaurant]:
    """
    Apply Phase 2 cleaning and feature engineering to ingested records.

    Returns a list of NormalizedRestaurant objects ready to be stored.
    """
    normalized: List[NormalizedRestaurant] = []
    for r in records:
        if not r.name:
            continue
        location = _normalize_location(r.location)
        cuisines = _normalize_cuisines(r.cuisines)
        price_bucket = _price_to_bucket(r.price_range)
        popularity_score = _compute_popularity(r.rating, r.votes)

        normalized.append(
            NormalizedRestaurant(
                id=r.id,
                name=r.name.strip(),
                location=location,
                cuisines=cuisines,
                price_range=r.price_range,
                price_bucket=price_bucket,
                rating=r.rating,
                votes=r.votes,
                popularity_score=popularity_score,
            )
        )

    return normalized


def persist_restaurants_to_sqlite(
    restaurants: Iterable[NormalizedRestaurant],
    db_path: str = "data/restaurants.db",
) -> None:
    """
    Persist normalized restaurants into a local SQLite database.

    This function is intentionally simple and idempotent for local development:
    - Ensures the target directory exists.
    - Creates a 'restaurants' table if it does not exist.
    - Inserts all provided rows without attempting conflict resolution.
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS restaurants (
                id TEXT,
                name TEXT NOT NULL,
                location TEXT,
                cuisines TEXT,
                price_range REAL,
                price_bucket TEXT,
                rating REAL,
                votes INTEGER,
                popularity_score REAL
            )
            """
        )

        rows = [
            (
                r.id,
                r.name,
                r.location,
                r.cuisines,
                r.price_range,
                r.price_bucket,
                r.rating,
                r.votes,
                r.popularity_score,
            )
            for r in restaurants
        ]

        cursor.executemany(
            """
            INSERT INTO restaurants (
                id, name, location, cuisines,
                price_range, price_bucket, rating,
                votes, popularity_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

