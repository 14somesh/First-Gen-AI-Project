"""
Ingestion package for Phase 1 of the AI Restaurant Recommendation Service.

Currently provides utilities to load the Zomato-based dataset from Hugging Face
and map it into a simple internal model that downstream phases can consume.
"""

from .models import RestaurantRecord  # noqa: F401
from .phase1_ingestion import ingest_restaurants  # noqa: F401

