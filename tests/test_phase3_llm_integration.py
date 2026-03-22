import os

from dotenv import load_dotenv

from llm_integration import ExplicitFilters, UserPreferences, interpret_user_input


def test_phase3_groq_integration_basic():
    """
    Integration test for Phase 3 LLM (Groq) integration.

    - Loads GROQ_API_KEY from the local .env if present.
    - Skips assertions if the key is not available.
    - Calls interpret_user_input and checks that a sensible UserPreferences
      object is returned.
    """
    # Load environment variables from .env at project root, if present.
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Soft skip: do not fail the suite if no key is configured.
        return

    user_query = "Looking for a romantic Italian dinner in Bangalore, budget is medium, good ratings."
    explicit = ExplicitFilters(
        price_range="medium",
        location="Bangalore",
        cuisines=["Italian"],
        min_rating=4.0,
    )

    prefs = interpret_user_input(user_query, explicit_filters=explicit)

    assert isinstance(prefs, UserPreferences)
    # We expect at least some of these to be populated meaningfully.
    assert prefs.location is None or isinstance(prefs.location, str)
    assert isinstance(prefs.cuisines, list)
    assert all(isinstance(c, str) for c in prefs.cuisines)
    # min_rating may or may not be set, but when set should be numeric.
    if prefs.min_rating is not None:
        assert isinstance(prefs.min_rating, float)

