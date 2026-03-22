## Phase 5 – API Layer & UI

This folder is reserved for assets and documentation specific to **Phase 5: API Layer & UI** of the AI Restaurant Recommendation Service.

Current implementation details:
- Core API code lives in the `api` package:
  - `api/phase5_api.py` exposes a FastAPI app with:
    - `GET /` – simple web UI page for entering a natural-language request and optional filters, then viewing recommendations.
    - `POST /recommendations` – main endpoint that:
      - Ensures the SQLite DB is populated (Phases 1–2).
      - Uses Groq-backed LLM integration (Phase 3) to interpret user input.
      - Invokes the recommendation engine (Phase 4) to fetch and rank restaurants.
    - `POST /recommendations/debug` – debug endpoint that bypasses the LLM and uses only structured filters, useful for tests and local debugging.
  - `api/__init__.py` re-exports the FastAPI `app`.

Environment:
- `RESTAURANTS_DB_PATH` (optional): when set, Phase 5 will use this SQLite path instead of the default `data/restaurants.db`.

To run the API locally:

```bash
uvicorn api.phase5_api:app --reload
```

