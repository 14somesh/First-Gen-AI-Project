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

        css = """
        <style>
        .results-section { border-top: 1px solid rgba(148,163,184,0.35); padding-top: 14px; display: flex; flex-direction: column; gap: 10px; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .results-header { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #9ca3af; }
        .results-title { font-weight: 600; color: #e5e7eb; }
        .results-list { display: flex; flex-direction: column; gap: 8px; max-height: 500px; overflow-y: auto; padding-right: 2px; margin-bottom: 20px; }
        .result-card { border-radius: 14px; border: 1px solid rgba(148,163,184,0.3); background: rgba(15,23,42,0.96); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
        .result-header-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
        .result-name { font-size: 14px; font-weight: 600; color: #f9fafb; margin: 0; }
        .result-location { font-size: 12px; color: #9ca3af; margin: 0; }
        .badge { font-size: 11px; padding: 3px 7px; border-radius: 999px; background: rgba(22,163,74,0.1); color: #bbf7d0; border: 1px solid rgba(34,197,94,0.7); white-space: nowrap; }
        .chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
        .chip { font-size: 11px; padding: 3px 7px; border-radius: 999px; border: 1px solid rgba(148,163,184,0.5); background: rgba(17,24,39,0.95); color: #e5e7eb; }
        </style>
        """

        html_blocks = [css, '<div class="results-section">']
        html_blocks.append('<div class="results-header"><span class="results-title">Recommendations</span><span>Sorted by relevance</span></div>')
        html_blocks.append('<div class="results-list">')

        for r in recs:
            rating_text = f"{r.rating:.1f} ★" if r.rating is not None else "No rating"
            votes_text = f"{r.votes} votes" if r.votes is not None else "New or unrated"
            cuisine_text = r.cuisines or "Various cuisines"
            price_text = r.price_bucket or "N/A"
            location_text = r.location or "Location not specified"

            card_html = f"""
            <article class="result-card">
                <div class="result-header-row">
                    <div>
                        <div class="result-name">{r.name}</div>
                        <div class="result-location">{location_text}</div>
                    </div>
                    <span class="badge">{rating_text}</span>
                </div>
                <div class="chips">
                    <span class="chip">{cuisine_text}</span>
                    <span class="chip">Price: {price_text}</span>
                    <span class="chip">{votes_text}</span>
                </div>
            </article>
            """
            html_blocks.append(card_html)
        
        html_blocks.append('</div></div>')
        
        st.markdown("".join(html_blocks), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
