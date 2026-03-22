"""
Minimal Streamlit UI for the AI Restaurant Recommendation Service.

Run from the project root so package imports resolve:
    streamlit run streamlit_app/app.py
"""
from __future__ import annotations

import sys
import textwrap
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
    st.markdown("<h2 style='font-weight: 600; margin-bottom: 0;'>AI Restaurant Recommendation</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 13px; color: #9ca3af; margin-top: 5px; margin-bottom: 20px;'>Select a place and filters to discover where to eat.</p>", unsafe_allow_html=True)

    db_path = ensure_db_populated()
    locations = list_locations().locations
    cuisines = list_cuisines().cuisines

    place_options = [""] + locations
    cuisine_options = [""] + cuisines

    # Subtle premium CSS targeting the inputs and the primary submit button
    form_css = textwrap.dedent("""
    <style>
    div[data-baseweb="select"] > div { background-color: rgba(15, 23, 42, 0.3) !important; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15) !important; }
    div[data-baseweb="input"] { background-color: rgba(15, 23, 42, 0.3) !important; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.15) !important; }
    button[data-testid="baseButton-primary"] { border-radius: 12px !important; font-weight: 600 !important; background: linear-gradient(135deg, #2563eb, #1d4ed8) !important; border: none !important; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3) !important; transition: transform 0.2s ease, box-shadow 0.2s ease !important; }
    button[data-testid="baseButton-primary"]:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 15px rgba(37, 99, 235, 0.4) !important; background: linear-gradient(135deg, #3b82f6, #2563eb) !important; }
    </style>
    """)
    st.markdown(form_css, unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<h4 style='margin-bottom: 4px; color: #f8fafc;'>Search Filters</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size: 13px; color: #94a3b8; margin-top: 0; margin-bottom: 16px;'>Configure exactly what you are looking for.</p>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            place = st.selectbox(
                "Place",
                options=place_options,
                format_func=lambda x: "Select a place" if x == "" else x,
            )
        with col2:
            cuisine = st.selectbox(
                "Cuisines",
                options=cuisine_options,
                format_func=lambda x: "Select a cuisine" if x == "" else x,
            )

        col3, col4 = st.columns(2)
        with col3:
            price_choice = st.selectbox(
                "Price Range (optional)",
                options=["Any", "low", "medium", "high"],
            )
            price_range = None if price_choice == "Any" else price_choice
        with col4:
            min_rating_raw = st.text_input("Minimum rating (optional)", placeholder="e.g. 4.0")
            min_rating: float | None = None
            if min_rating_raw.strip():
                try:
                    min_rating = float(min_rating_raw.strip())
                except ValueError:
                    st.warning("Minimum rating must be a number.")

        limit = 10  # Hardcoded to 10 to match original UI behavior

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        submitted = st.button("Get recommendations", type="primary", use_container_width=True)

    if submitted:
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

        # Premium CSS styling for results injected directly
        css = textwrap.dedent("""
        <style>
        .premium-card {
            background: linear-gradient(145deg, #1e293b, #0f172a);
            border: 1px solid rgba(148, 163, 184, 0.15);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .premium-card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.5);
        }
        .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
        .card-title { color: #f8fafc; font-size: 1.35rem; font-weight: 700; margin: 0 0 4px 0; letter-spacing: -0.025em; }
        .card-subtitle { color: #94a3b8; font-size: 0.9rem; margin: 0; }
        .rating-badge { background: linear-gradient(135deg, #22c55e, #16a34a); color: #ffffff; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; box-shadow: 0 4px 6px -1px rgba(22, 163, 74, 0.2); white-space: nowrap; }
        .chip-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
        .chip { background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(148, 163, 184, 0.2); color: #f1f5f9; padding: 4px 12px; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }
        .chip-price { background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.3); color: #7dd3fc; }
        </style>
        """)
        st.markdown(css, unsafe_allow_html=True)

        st.divider() # clean separation between form and results
        st.markdown("### Recommendations")
        st.caption("Sorted by relevance matching your preferences")

        for r in recs:
            rating_text = f"{r.rating:.1f} ★" if r.rating is not None else "No rating"
            votes_text = f"{r.votes} votes" if r.votes is not None else "New or unrated"
            cuisine_text = r.cuisines or "Various cuisines"
            price_text = r.price_bucket.title() if r.price_bucket else "N/A"
            location_text = r.location or "Location not specified"

            # Using textwrap.dedent guarantees 0 leading spaces, entirely preventing the markdown code-block bug
            card_html = textwrap.dedent(f"""
            <div class="premium-card">
                <div class="card-header">
                    <div>
                        <h3 class="card-title">{r.name}</h3>
                        <p class="card-subtitle">{location_text}</p>
                    </div>
                    <div class="rating-badge">{rating_text}</div>
                </div>
                <div class="chip-container">
                    <span class="chip">{cuisine_text}</span>
                    <span class="chip chip-price">Price: {price_text}</span>
                    <span class="chip">{votes_text}</span>
                </div>
            </div>
            """)
            st.markdown(card_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
