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
    st.markdown("## AI Restaurant Recommendation")
    st.markdown("<p style='font-size: 13px; color: #9ca3af; margin-top: -10px; margin-bottom: 20px;'>Select a place and filters to discover where to eat.</p>", unsafe_allow_html=True)

    db_path = ensure_db_populated()
    locations = list_locations().locations
    cuisines = list_cuisines().cuisines

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

    limit = 10  # Hardcoded to 10 to match original UI behavior

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

        st.subheader("Recommendations")
        st.caption("Sorted by relevance")

        for r in recs:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                
                location_text = r.location or "Location not specified"
                with col1:
                    st.markdown(f"**{r.name}**")
                    st.caption(location_text)
                    
                with col2:
                    rating_text = f"{r.rating:.1f} ★" if r.rating is not None else "No rating"
                    st.markdown(f"**{rating_text}**")
                
                cuisine_text = r.cuisines or "Various cuisines"
                price_text = r.price_bucket or "N/A"
                votes_text = f"{r.votes} votes" if r.votes is not None else "New or unrated"
                
                st.markdown(f"`{cuisine_text}` &nbsp; `Price: {price_text}` &nbsp; `{votes_text}`")


if __name__ == "__main__":
    main()
