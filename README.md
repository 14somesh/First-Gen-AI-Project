## AI Restaurant Recommendation Service

This project implements an AI-powered restaurant recommendation service based on a Zomato dataset hosted on Hugging Face.

At this stage, **Phase 1 (Data Ingestion)** is implemented:
- Loads the `ManikaSaini/zomato-restaurant-recommendation` dataset from Hugging Face.
- Maps raw records into a simple internal restaurant model.
- Applies lightweight validation.

### Getting Started

1. **Create and activate a virtual environment** (recommended).
2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Run tests**:

```bash
pytest
```

This will run the Phase 1 ingestion test, which loads a small sample from the dataset and validates that ingestion works end-to-end.

