from ingestion import ingest_restaurants, RestaurantRecord


def test_phase1_ingestion_returns_non_empty_sample():
    """
    Basic end-to-end test for Phase 1 ingestion.

    - Loads a small sample from the Hugging Face dataset.
    - Ensures we get at least one valid RestaurantRecord back.
    - Performs light sanity checks on a few key fields.
    """
    records = ingest_restaurants(sample_size=50)

    assert isinstance(records, list)
    assert records, "Expected at least one ingested restaurant record"

    for record in records:
        assert isinstance(record, RestaurantRecord)
        # Name should be a non-empty string based on our validation rules.
        assert isinstance(record.name, str)
        assert record.name.strip() != ""
        # Raw record must always be present.
        assert isinstance(record.raw, dict)
