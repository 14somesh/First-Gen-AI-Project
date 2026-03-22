"""
LLM integration package for Phase 3 of the AI Restaurant Recommendation Service.

Provides a Groq-backed client and a high-level helper to interpret user input
into structured preference objects that downstream components can consume.
"""

from .models import ExplicitFilters, UserPreferences  # noqa: F401
from .interpreter import interpret_user_input  # noqa: F401

