"""
Minimal Streamlit UI for the AI Restaurant Recommendation Service.

Run from the project root so package imports resolve:
    streamlit run streamlit_app/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Project root (parent of streamlit_app/)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from api.phase5_api import (
    ExplicitFiltersBody,
    _preferences_to_request,
    ensure_db_populated,
    list_cuisines,
    list_locations,
)
from llm_integration import ExplicitFilters, interpret_user_input
from recommendation import recommend_restaurants


def _run_recommendations(
    *,
    place: str,
    cuisine: str,
    price_range: str | None,
    min_rating: float | None,
    limit: int,
) -> list:
    db_path = ensure_db_populated()
    explicit = ExplicitFilters(
        price_range=price_range,
        location=place or None,
        cuisines=[cuisine] if cuisine else None,
        min_rating=min_rating,
    )
    preferences = interpret_user_input(user_input="", explicit_filters=explicit)
    body = ExplicitFiltersBody(
        price_range=explicit.price_range,
        location=explicit.location,
        cuisines=explicit.cuisines,
        min_rating=explicit.min_rating,
    )
    request = _preferences_to_request(preferences, body)
    return recommend_restaurants(db_path=db_path, request=request, limit=limit)


def main() -> None:
    st.set_page_config(page_title="AI Restaurant Recommendations", layout="centered")
    st.title("AI Restaurant Recommendation")

    db_path = ensure_db_populated()
    locations = list_locations().locations
    cuisines = list_cuisines().cuisines

    st.caption(f"Database: `{db_path}`")

    place_options = [""] + locations
    place = st.selectbox(
        "Place",
        options=place_options,
        format_func=lambda x: "Select a place" if x == "" else x,
    )

    cuisine_options = [""] + cuisines
    cuisine = st.selectbox(
        "Cuisines",
        options=cuisine_options,
        format_func=lambda x: "Select a cuisine" if x == "" else x,
    )

    price_choice = st.selectbox(
        "Price Range (optional)",
        options=["Any", "low", "medium", "high"],
    )
    price_range = None if price_choice == "Any" else price_choice

    min_rating_raw = st.text_input("Minimum rating (optional)", placeholder="e.g. 4.0")
    min_rating: float | None = None
    if min_rating_raw.strip():
        try:
            min_rating = float(min_rating_raw.strip())
        except ValueError:
            st.warning("Minimum rating must be a number.")

    limit = st.slider("Max results", min_value=1, max_value=25, value=10)

    if st.button("Get recommendations", type="primary"):
        if not place or not cuisine:
            st.error("Please select both a place and a cuisine.")
            return
        if min_rating_raw.strip() and min_rating is None:
            return
        with st.spinner("Finding recommendations…"):
            try:
                recs = _run_recommendations(
                    place=place,
                    cuisine=cuisine,
                    price_range=price_range,
                    min_rating=min_rating,
                    limit=limit,
                )
            except Exception as e:  # noqa: BLE001 — surface errors in UI
                st.error(f"Something went wrong: {e}")
                return

        if not recs:
            st.info("No restaurants available for the selected filters.")
            return

        rows = [
            {
                "Name": r.name,
                "Location": r.location,
                "Cuisines": r.cuisines,
                "Price": r.price_bucket,
                "Rating": r.rating,
                "Votes": r.votes,
                "Score": round(r.score, 2),
            }
            for r in recs
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
