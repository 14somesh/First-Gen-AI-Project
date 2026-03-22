from __future__ import annotations

import os
from typing import List, Optional, Union
import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingestion import ingest_restaurants
from llm_integration import ExplicitFilters, interpret_user_input
from processing import normalize_restaurants, persist_restaurants_to_sqlite
from recommendation import RecommendationRequest, RestaurantRecommendation, recommend_restaurants
import sqlite3


# Load environment variables (including GROQ_API_KEY) from .env if present.
load_dotenv()


app = FastAPI(title="AI Restaurant Recommendation Service")
logger = logging.getLogger("api")


def get_db_path() -> str:
    """
    Resolve the SQLite DB path for restaurants.

    Tests can override this via the RESTAURANTS_DB_PATH environment variable.
    """
    return os.getenv("RESTAURANTS_DB_PATH", "data/restaurants.db")


def ensure_db_populated() -> str:
    """
    Ensure the SQLite database exists and has restaurant data.

    If the DB file does not exist, this will:
    - Ingest a sample from the Hugging Face dataset (Phase 1).
    - Normalize and enrich it (Phase 2).
    - Persist it into the SQLite DB.
    """
    db_path = get_db_path()
    if not os.path.exists(db_path):
        records = ingest_restaurants(sample_size=500)
        normalized = normalize_restaurants(records)
        persist_restaurants_to_sqlite(normalized, db_path=db_path)
    return db_path


class ExplicitFiltersBody(BaseModel):
    price_range: Optional[Union[str, int, float]] = None
    location: Optional[str] = None
    cuisines: Optional[List[str]] = None
    min_rating: Optional[float] = None


class RecommendationRequestBody(BaseModel):
    user_input: Optional[str] = None
    explicit_filters: Optional[ExplicitFiltersBody] = None
    limit: int = 10


class DebugRecommendationRequestBody(BaseModel):
    """
    Simpler debug request that bypasses the LLM and uses only structured filters.
    """

    limit: int = 5
    min_rating: Optional[float] = None


class RestaurantRecommendationDTO(BaseModel):
    name: str
    location: Optional[str]
    cuisines: Optional[str]
    price_bucket: Optional[str]
    rating: Optional[float]
    votes: Optional[int]
    score: float

    @classmethod
    def from_domain(cls, rec: RestaurantRecommendation) -> "RestaurantRecommendationDTO":
        return cls(
            name=rec.name,
            location=rec.location,
            cuisines=rec.cuisines,
            price_bucket=rec.price_bucket,
            rating=rec.rating,
            votes=rec.votes,
            score=rec.score,
        )


class RecommendationResponse(BaseModel):
    results: List[RestaurantRecommendationDTO]


class LocationsResponse(BaseModel):
    locations: List[str]


class CuisinesResponse(BaseModel):
    cuisines: List[str]


def _preferences_to_request(preferences, explicit_filters: Optional[ExplicitFiltersBody]) -> RecommendationRequest:
    """
    Map Phase 3 UserPreferences (plus any explicit filters) into a Phase 4 RecommendationRequest.
    """
    # Prefer LLM-derived values; fall back to explicit ones if missing.
    location = getattr(preferences, "location", None) or (explicit_filters.location if explicit_filters else None)
    cuisines = getattr(preferences, "cuisines", None) or (explicit_filters.cuisines if explicit_filters else None)

    raw_price = getattr(preferences, "price_range", None) or (explicit_filters.price_range if explicit_filters else None)
    min_rating = getattr(preferences, "min_rating", None)
    if min_rating is None and explicit_filters is not None:
        min_rating = explicit_filters.min_rating

    cuisine_queries = cuisines or []
    if isinstance(cuisine_queries, str):
        cuisine_queries = [cuisine_queries]

    def _to_price_bucket(value):
        # "Any" / empty / None = no price filter; do not compare with restaurant prices.
        if value is None:
            return None
        if isinstance(value, str) and (not value.strip() or value.strip().lower() == "any"):
            return None
        # Accept pre-bucketed strings or numeric values.
        if isinstance(value, str) and value.lower() in {"low", "medium", "high"}:
            return value.lower()
        try:
            num = float(value)
        except (TypeError, ValueError):
            return None
        if num <= 300:
            return "low"
        if num <= 800:
            return "medium"
        return "high"

    price_bucket = _to_price_bucket(raw_price)

    return RecommendationRequest(
        location_query=location,
        cuisine_queries=cuisine_queries,
        price_bucket=price_bucket,
        min_rating=min_rating,
    )


@app.get("/locations", response_model=LocationsResponse)
def list_locations() -> LocationsResponse:
    """
    Return the list of distinct locations available in the restaurants store.
    """
    db_path = ensure_db_populated()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT location FROM restaurants WHERE location IS NOT NULL ORDER BY location"
        )
        locations = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    return LocationsResponse(locations=locations)


@app.get("/cuisines", response_model=CuisinesResponse)
def list_cuisines() -> CuisinesResponse:
    """
    Return a normalized list of distinct cuisine tokens available.
    """
    db_path = ensure_db_populated()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT cuisines FROM restaurants WHERE cuisines IS NOT NULL"
        )
        raw_rows = [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()

    # Split comma-separated cuisine strings, normalize, and deduplicate.
    tokens = set()
    for row in raw_rows:
        if not row:
            continue
        for part in row.split(","):
            token = part.strip()
            if token:
                tokens.add(token)

    cuisines = sorted(tokens)
    return CuisinesResponse(cuisines=cuisines)


@app.get("/", response_class=HTMLResponse)
def ui_page() -> str:
    """
    React-based UI page for manual testing of the recommendation flow.
    """
    return """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>AI Restaurant Recommendation</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      * { box-sizing: border-box; }
      body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #020617; color: #e5e7eb; }
      .page-root { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 32px 16px; }
      .card { width: 100%; max-width: 720px; background: #020617; border-radius: 20px; padding: 24px 22px 22px; box-shadow: 0 18px 45px rgba(15,23,42,0.75); border: 1px solid rgba(148,163,184,0.3); display: flex; flex-direction: column; gap: 20px; }
      .header { text-align: center; display: flex; flex-direction: column; gap: 4px; }
      h1 { font-size: 24px; line-height: 1.2; letter-spacing: -0.03em; margin: 0; color: #f9fafb; }
      .subtitle { font-size: 13px; color: #9ca3af; margin: 0; }
      .form { display: flex; flex-direction: column; gap: 12px; }
      .field { display: flex; flex-direction: column; gap: 4px; }
      .label { font-size: 12px; font-weight: 600; color: #e5e7eb; letter-spacing: 0.04em; text-transform: uppercase; }
      .select, .input { border-radius: 999px; border: 1px solid rgba(148,163,184,0.55); padding: 8px 12px; background: rgba(15,23,42,0.96); color: #e5e7eb; font-size: 13px; outline: none; width: 100%; }
      .select:focus, .input:focus { border-color: #38bdf8; box-shadow: 0 0 0 1px rgba(56,189,248,0.7); }
      .button { margin-top: 4px; width: 100%; padding: 10px 16px; border-radius: 999px; border: none; background: linear-gradient(135deg, #22c55e, #16a34a); color: #022c22; font-weight: 600; font-size: 14px; cursor: pointer; box-shadow: 0 12px 30px rgba(22,163,74,0.55); }
      .button[disabled] { opacity: 0.6; cursor: not-allowed; box-shadow: none; }
      .results-section { border-top: 1px solid rgba(148,163,184,0.35); padding-top: 14px; display: flex; flex-direction: column; gap: 10px; }
      .results-header { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #9ca3af; }
      .results-title { font-weight: 600; color: #e5e7eb; }
      .results-list { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; padding-right: 2px; }
      .result-card { border-radius: 14px; border: 1px solid rgba(148,163,184,0.3); background: rgba(15,23,42,0.96); padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
      .result-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
      .result-name { font-size: 14px; font-weight: 600; color: #f9fafb; }
      .result-location { font-size: 12px; color: #9ca3af; }
      .badge { font-size: 11px; padding: 3px 7px; border-radius: 999px; background: rgba(22,163,74,0.1); color: #bbf7d0; border: 1px solid rgba(34,197,94,0.7); }
      .chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
      .chip { font-size: 11px; padding: 3px 7px; border-radius: 999px; border: 1px solid rgba(148,163,184,0.5); background: rgba(17,24,39,0.95); color: #e5e7eb; }
      .cuisine-field { position: relative; }
      .cuisine-options { margin-top: 4px; border-radius: 12px; border: 1px solid rgba(148,163,184,0.5); background: rgba(15,23,42,0.98); max-height: 160px; overflow-y: auto; padding: 4px; }
      .cuisine-option { padding: 4px 8px; border-radius: 8px; font-size: 12px; cursor: pointer; color: #e5e7eb; }
      .cuisine-option:hover { background: rgba(37,99,235,0.6); }
      .empty { font-size: 12px; color: #6b7280; }
      .error { font-size: 12px; color: #fecaca; background: rgba(248,113,113,0.12); border-radius: 8px; padding: 6px 10px; border: 1px solid rgba(248,113,113,0.4); }
    </style>
    <script src="https://unpkg.com/react@18/umd/react.development.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js" crossorigin></script>
    <script src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
  </head>
  <body>
    <div id="root" class="page-root"></div>
    <script type="text/babel">
      const { useState, useEffect } = React;

      function App() {
        const [places, setPlaces] = useState([]);
        const [placesLoading, setPlacesLoading] = useState(true);
        const [placesError, setPlacesError] = useState(null);

        const [cuisineOptions, setCuisineOptions] = useState([]);
        const [cuisinesLoading, setCuisinesLoading] = useState(true);
        const [cuisinesError, setCuisinesError] = useState(null);

        const [selectedPlace, setSelectedPlace] = useState("");
        const [selectedCuisine, setSelectedCuisine] = useState("");
        const [showCuisineDropdown, setShowCuisineDropdown] = useState(false);
        const [priceRange, setPriceRange] = useState("");
        const [minRating, setMinRating] = useState("");

        const [loading, setLoading] = useState(false);
        const [error, setError] = useState(null);
        const [usingFallback, setUsingFallback] = useState(false);
        const [results, setResults] = useState([]);

        useEffect(() => {
          async function fetchPlaces() {
            try {
              const resp = await fetch("/locations");
              if (!resp.ok) throw new Error("Failed to load locations");
              const data = await resp.json();
              setPlaces(data.locations || []);
            } catch (err) {
              console.error(err);
              setPlacesError("Unable to load places. You can still search by filters.");
            } finally {
              setPlacesLoading(false);
            }
          }
          async function fetchCuisines() {
            try {
              const resp = await fetch("/cuisines");
              if (!resp.ok) throw new Error("Failed to load cuisines");
              const data = await resp.json();
              setCuisineOptions(data.cuisines || []);
            } catch (err) {
              console.error(err);
              setCuisinesError("Unable to load cuisines. You can still search by place.");
            } finally {
              setCuisinesLoading(false);
            }
          }
          fetchPlaces();
          fetchCuisines();
        }, []);

        async function fetchRecommendations() {
          // Require both place and cuisine to be selected.
          if (!selectedPlace || !selectedCuisine) {
            setError("Please select both a place and a cuisine.");
            return;
          }

          setLoading(true);
          setError(null);
          setUsingFallback(false);
          setResults([]);

          const cuisinesArray = selectedCuisine ? [selectedCuisine] : null;
          const priceBucketValue = priceRange && priceRange.trim() ? priceRange : null;
          const minRatingValue = minRating ? parseFloat(minRating) : null;

          const explicitFilters = {
            price_range: priceBucketValue,
            location: selectedPlace || null,
            cuisines: cuisinesArray,
            min_rating: minRatingValue,
          };

          const mainPayload = {
            user_input: null,
            explicit_filters: explicitFilters,
            limit: 10,
          };

          try {
            const resp = await fetch("/recommendations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(mainPayload),
            });

            if (!resp.ok) {
              throw new Error("Request failed with status " + resp.status);
            }

            const data = await resp.json();
            const items = data.data || [];
            setResults(items);
          } catch (err) {
            console.error("Recommendations request failed", err);
            setError("Unable to load recommendations right now. Please try again in a moment.");
          } finally {
            setLoading(false);
          }
        }

        return (
          <div className="card">
            <header className="header">
              <h1>AI Restaurant Recommendation</h1>
              <p className="subtitle">Select a place and filters to discover where to eat.</p>
            </header>

            {(placesError || cuisinesError) && (
              <div className="error">{placesError || cuisinesError}</div>
            )}

            <form
              className="form"
              onSubmit={(e) => {
                e.preventDefault();
                fetchRecommendations();
              }}
            >
              <div className="field">
                <label className="label">Place</label>
                <select
                  className="select"
                  value={selectedPlace}
                  onChange={(e) => setSelectedPlace(e.target.value)}
                  disabled={placesLoading || !places.length}
                >
                  <option value="">Select a place</option>
                  {placesLoading && <option disabled>Loading places…</option>}
                  {!placesLoading && !places.length && <option disabled>No places available</option>}
                  {!placesLoading &&
                    places.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                </select>
              </div>

              <div className="field cuisine-field">
                <label className="label">Cuisines</label>
                <input
                  className="input"
                  value={selectedCuisine}
                  onChange={(e) => {
                    setSelectedCuisine(e.target.value);
                    setShowCuisineDropdown(true);
                  }}
                  onFocus={() => setShowCuisineDropdown(true)}
                  placeholder="Enter cuisines"
                  disabled={cuisinesLoading || !cuisineOptions.length}
                />
                {!cuisinesLoading && cuisineOptions.length > 0 && selectedCuisine && showCuisineDropdown && (() => {
                  const filtered = cuisineOptions.filter((c) =>
                    c.toLowerCase().includes(selectedCuisine.toLowerCase())
                  );
                  return filtered.length > 0 ? (
                    <div className="cuisine-options">
                      {filtered.map((c) => (
                        <div
                          key={c}
                          className="cuisine-option"
                          onClick={() => {
                            setSelectedCuisine(c);
                            setShowCuisineDropdown(false);
                          }}
                        >
                          {c}
                        </div>
                      ))}
                    </div>
                  ) : null;
                })()}
              </div>

              <div className="field">
                <label className="label">Price Range (optional)</label>
                <select
                  className="select"
                  value={priceRange}
                  onChange={(e) => setPriceRange(e.target.value)}
                >
                  <option value="">Any</option>
                  <option value="low">low</option>
                  <option value="medium">medium</option>
                  <option value="high">high</option>
                </select>
              </div>

              <div className="field">
                <label className="label">Minimum rating (optional)</label>
                <input
                  className="input"
                  value={minRating}
                  onChange={(e) => setMinRating(e.target.value)}
                  placeholder="e.g. 4.0"
                />
              </div>

              <button
                type="submit"
                className="button"
                disabled={loading}
              >
                {loading ? "Finding recommendations…" : "Get recommendations"}
              </button>
            </form>

            <section className="results-section">
              <div className="results-header">
                <span className="results-title">Recommendations</span>
                <span>Sorted by relevance</span>
              </div>

              {error && <div className="error">{error}</div>}

              <div className="results-list">
                {results.length === 0 && !error && !loading && (
                  <div className="empty">No restaurants available for the selected filters.</div>
                )}
                {results.map((item, idx) => {
                  const rating =
                    item.rating != null ? `${item.rating.toFixed(1)} ★` : "No rating";
                  const votes =
                    item.votes != null ? `${item.votes} votes` : "New or unrated";
                  const cuisine = item.cuisines || "Various cuisines";
                  const price = item.price_bucket || "N/A";
                  const location = item.location || "Location not specified";
                  return (
                    <article key={idx} className="result-card">
                      <div className="result-header">
                        <div>
                          <div className="result-name">{item.name}</div>
                          <div className="result-location">{location}</div>
                        </div>
                        <span className="badge">{rating}</span>
                      </div>
                      <div className="chips">
                        <span className="chip">{cuisine}</span>
                        <span className="chip">Price: {price}</span>
                        <span className="chip">{votes}</span>
                      </div>
                    </article>
                  );
                })}
              </div>
            </section>
          </div>
        );
      }

      const root = ReactDOM.createRoot(document.getElementById("root"));
      root.render(<App />);
    </script>
  </body>
</html>
    """


@app.post("/recommendations")
def create_recommendations(body: RecommendationRequestBody):
    """
    Main recommendations endpoint that:
    - Uses Groq-backed LLM (Phase 3) to interpret user input.
    - Uses the recommendation engine (Phase 4) to fetch and rank results.

    Always returns JSON and never crashes on empty results.
    """
    try:
        logger.info("Incoming /recommendations request: %s", body.model_dump())

        db_path = ensure_db_populated()

        explicit_filters = None
        if body.explicit_filters is not None:
            explicit_filters = ExplicitFilters(
                price_range=body.explicit_filters.price_range,
                location=body.explicit_filters.location,
                cuisines=body.explicit_filters.cuisines,
                min_rating=body.explicit_filters.min_rating,
            )

        preferences = interpret_user_input(
            user_input=body.user_input or "",
            explicit_filters=explicit_filters,
        )

        request = _preferences_to_request(preferences, body.explicit_filters)
        recs = recommend_restaurants(db_path=db_path, request=request, limit=body.limit)

        results = [RestaurantRecommendationDTO.from_domain(r).model_dump() for r in recs]
        logger.info("Filtered recommendations count: %d", len(results))

        if not results:
            return {
                "message": "No restaurants available for the selected filters.",
                "data": [],
            }

        return {
            "message": "OK",
            "data": results,
        }
    except Exception as e:
        logger.exception("Error in /recommendations endpoint: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong",
                "details": str(e),
            },
        )


@app.post("/recommendations/debug", response_model=RecommendationResponse)
def create_recommendations_debug(body: DebugRecommendationRequestBody) -> RecommendationResponse:
    """
    Debug endpoint that bypasses the LLM and uses only structured filters.
    Useful for testing without requiring a Groq key.
    """
    db_path = ensure_db_populated()

    request = RecommendationRequest(
        location_query=None,
        cuisine_queries=[],
        price_bucket=None,
        min_rating=body.min_rating,
    )
    recs = recommend_restaurants(db_path=db_path, request=request, limit=body.limit)

    return RecommendationResponse(
        results=[RestaurantRecommendationDTO.from_domain(r) for r in recs]
    )

