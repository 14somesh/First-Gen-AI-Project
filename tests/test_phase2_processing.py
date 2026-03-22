from pathlib import Path
import sqlite3

from ingestion import ingest_restaurants
from processing import NormalizedRestaurant, normalize_restaurants, persist_restaurants_to_sqlite


def test_phase2_normalization_and_persistence(tmp_path: Path):
    """
    End-to-end test for Phase 2:

    - Uses Phase 1 to ingest a small sample from the Hugging Face dataset.
    - Normalizes and enriches the data (Phase 2 processing).
    - Persists normalized rows into a temporary SQLite database.
    - Reads back from SQLite to verify structure and basic content.
    """
    # Phase 1: ingest a small sample.
    ingested = ingest_restaurants(sample_size=50)
    assert ingested, "Expected non-empty ingestion result for Phase 2 test"

    # Phase 2: normalize and enrich.
    normalized = normalize_restaurants(ingested)
    assert normalized, "Expected at least one normalized restaurant"
    assert all(isinstance(r, NormalizedRestaurant) for r in normalized)

    # Persist into a temporary SQLite database.
    db_path = tmp_path / "restaurants_phase2.db"
    persist_restaurants_to_sqlite(normalized, db_path=str(db_path))

    # Verify database contents.
    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, location, cuisines, price_bucket FROM restaurants")
        rows = cursor.fetchall()
        assert rows, "Expected at least one row in restaurants table"

        # Basic sanity checks on a sample row.
        sample_name, sample_location, sample_cuisines, sample_bucket = rows[0]
        assert isinstance(sample_name, str) and sample_name.strip() != ""
        # Location/cuisines/bucket may be nullable, but when present should be strings.
        if sample_location is not None:
            assert isinstance(sample_location, str)
        if sample_cuisines is not None:
            assert isinstance(sample_cuisines, str)
        if sample_bucket is not None:
            assert sample_bucket in {"low", "medium", "high"}
    finally:
        conn.close()

