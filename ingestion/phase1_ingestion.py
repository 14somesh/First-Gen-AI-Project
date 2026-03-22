from __future__ import annotations

import re
from typing import Iterable, List, Optional

from datasets import Dataset, load_dataset

from .models import RestaurantRecord

DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"


class DatasetConnector:
    """Responsible for loading the raw dataset from Hugging Face."""

    def __init__(self, dataset_name: str = DATASET_NAME) -> None:
        self.dataset_name = dataset_name

    def load_raw_dataset(self, split: Optional[str] = "train") -> Dataset:
        """
        Load the underlying Hugging Face dataset.

        Many tabular datasets on Hugging Face expose a single 'train' split.
        If this ever changes, the split can be made configurable.
        """
        if split is None:
            return load_dataset(self.dataset_name)["train"]
        return load_dataset(self.dataset_name, split=split)


class SchemaMapper:
    """
    Maps raw dataset records into the internal RestaurantRecord model.

    The exact field names can vary across Zomato-style datasets, so this mapper
    uses simple heuristics and fallbacks.
    """

    @staticmethod
    def map_record(raw: dict) -> RestaurantRecord:
        # Heuristic-based extraction with common Zomato field name variants.
        name = (
            raw.get("name")
            or raw.get("Name")
            or raw.get("Restaurant Name")
            or raw.get("restaurant_name")
        )

        location = (
            raw.get("location")
            or raw.get("Location")
            or raw.get("address")
            or raw.get("Address")
            or raw.get("city")
            or raw.get("City")
        )

        cuisines = raw.get("cuisines") or raw.get("Cuisines")

        price_range = None
        for key in ("price_range", "Price Range", "approx_cost(for two people)"):
            if key in raw:
                value = raw.get(key)
                try:
                    if isinstance(value, str):
                        # Remove thousands separators and non-numeric characters.
                        numeric_str = re.sub(r"[^\d.]", "", value)
                        price_range = float(numeric_str) if numeric_str else None
                    else:
                        price_range = float(value) if value is not None else None
                except (TypeError, ValueError):
                    price_range = None
                break

        rating = None
        for key in ("rating", "Rating", "rate"):
            if key in raw:
                value = raw.get(key)
                # Some Zomato datasets use strings like "4.1/5"
                if isinstance(value, str):
                    if "/" in value:
                        value = value.split("/", 1)[0]
                    # Strip any non-numeric/non-decimal characters.
                    numeric_str = re.sub(r"[^\d.]", "", value)
                    value = numeric_str
                try:
                    rating = float(value) if value not in (None, "", ".") else None
                except (TypeError, ValueError):
                    rating = None
                break

        votes = None
        for key in ("votes", "Votes"):
            if key in raw:
                value = raw.get(key)
                try:
                    votes = int(value) if value is not None else None
                except (TypeError, ValueError):
                    votes = None
                break

        # Use any obvious id-like column if present.
        restaurant_id = None
        for key in ("id", "restaurant_id", "Restaurant ID", "url"):
            if key in raw:
                restaurant_id = str(raw.get(key))
                break

        return RestaurantRecord(
            id=restaurant_id,
            name=name,
            location=location,
            cuisines=cuisines,
            price_range=price_range,
            rating=rating,
            votes=votes,
            raw=raw,
        )


class ValidationLayer:
    """
    Lightweight validation for ingested records.

    For Phase 1 we keep validation intentionally simple: a record is considered
    valid if it has a non-empty name and a raw dictionary attached.
    """

    @staticmethod
    def is_valid(record: RestaurantRecord) -> bool:
        if not isinstance(record.raw, dict):
            return False
        if not record.name or not isinstance(record.name, str):
            return False
        return True


def ingest_restaurants(sample_size: Optional[int] = None) -> List[RestaurantRecord]:
    """
    End-to-end Phase 1 ingestion flow.

    - Loads the dataset from Hugging Face.
    - Optionally downsamples to a smaller subset for quicker experimentation.
    - Maps each raw record into a RestaurantRecord.
    - Applies basic validation and filters out invalid entries.
    """
    connector = DatasetConnector()
    raw_dataset = connector.load_raw_dataset()

    if sample_size is not None:
        # Use the first N samples deterministically for reproducibility.
        raw_dataset = raw_dataset.select(range(min(sample_size, len(raw_dataset))))

    mapper = SchemaMapper()
    validator = ValidationLayer()

    records: Iterable[RestaurantRecord] = (
        mapper.map_record(raw) for raw in raw_dataset
    )
    valid_records = [r for r in records if validator.is_valid(r)]
    return valid_records

