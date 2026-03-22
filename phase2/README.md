## Phase 2 – Data Processing & Storage

This folder is reserved for assets and documentation specific to **Phase 2: Data Processing & Storage** of the AI Restaurant Recommendation Service.

Current implementation details:
- Core processing code lives in the `processing` package:
  - `processing/phase2_processing.py` provides:
    - `normalize_restaurants` – cleaning, normalization, and basic feature engineering.
    - `persist_restaurants_to_sqlite` – writes normalized data into a local SQLite database.
  - `processing/__init__.py` re-exports key Phase 2 types and functions.
- Phase 1 ingestion outputs (`RestaurantRecord` instances) are the inputs to Phase 2.

Use this folder for any Phase 2–specific notes, schema diagrams, or auxiliary scripts you may want to add later.

