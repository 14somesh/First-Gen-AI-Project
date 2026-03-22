from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from api.phase5_api import app


def test_phase5_debug_endpoint_end_to_end(tmp_path: Path, monkeypatch):
    """
    End-to-end test for Phase 5 using the debug endpoint.

    - Points the API at a temporary SQLite DB via RESTAURANTS_DB_PATH.
    - Relies on the API's own bootstrap logic (Phases 1–2) to populate the DB.
    - Calls /recommendations/debug and verifies a non-empty, well-formed response.
    """
    db_path = tmp_path / "restaurants_phase5.db"
    monkeypatch.setenv("RESTAURANTS_DB_PATH", str(db_path))

    client = TestClient(app)

    response = client.post("/recommendations/debug", json={"limit": 3, "min_rating": 3.0})
    assert response.status_code == 200

    payload = response.json()
    assert "results" in payload
    results = payload["results"]
    assert isinstance(results, list)
    assert results, "Expected at least one recommendation from debug endpoint"

    for item in results:
        assert "name" in item and isinstance(item["name"], str) and item["name"].strip()
        assert "score" in item and isinstance(item["score"], (int, float))
        # Optional fields should exist but may be null.
        for key in ("location", "cuisines", "price_bucket", "rating", "votes"):
            assert key in item

