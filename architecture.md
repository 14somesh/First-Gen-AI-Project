## AI Restaurant Recommendation Service – Architecture

### Overview

A service that ingests restaurant data from the Zomato-based Hugging Face dataset, processes and stores it, enriches user requests with an LLM, and returns structured, ranked restaurant recommendations via an API.

---

## Phase 1: Data Ingestion

### Purpose
- **Purpose**: Fetch and keep restaurant data from the Hugging Face Zomato dataset synchronized and ready for processing.

### Key Components
- **Dataset Connector**: Pulls data from `ManikaSaini/zomato-restaurant-recommendation`.
- **Ingestion Orchestrator**: Schedules full and incremental loads (batch jobs).
- **Schema Mapper**: Maps raw dataset fields to internal canonical schema (e.g., `name`, `location`, `cuisine`, `price_range`, `rating`, `votes`, `coordinates`, etc.).
- **Validation Layer**: Basic checks (required fields, types, valid ranges).

### Data Flow
1. **Scheduler** triggers ingestion (e.g., daily or weekly).
2. **Dataset Connector** reads from Hugging Face dataset (API/SDK).
3. **Schema Mapper** converts raw rows into internal restaurant entities.
4. **Validation Layer** filters/flags invalid or incomplete records.
5. Valid records are handed off to **Phase 2: Data Processing & Storage**.

---

## Phase 2: Data Processing & Storage

### Purpose
- **Purpose**: Clean, normalize, enrich, and store restaurant data for efficient querying and recommendation.

### Key Components
- **Data Cleaning & Normalization Module**:
  - Normalizes location (city, area, lat/long).
  - Standardizes cuisine labels and price ranges.
  - Handles missing and inconsistent ratings.
- **Feature Engineering Module**:
  - Computes derived fields (e.g., price buckets, popularity scores, text search fields).
  - Optionally precomputes static restaurant embeddings (e.g., from description/cuisine).
- **Primary Operational Store**:
  - Relational DB (e.g., PostgreSQL) or document store (e.g., MongoDB) for restaurant entities.
- **Search/Vector Index**:
  - Text search index (e.g., PostgreSQL full text, Elasticsearch, or OpenSearch).
  - Optional vector store (e.g., pgvector extension or dedicated vector DB) for semantic similarity.
- **Metadata Store**:
  - Stores ingestion run metadata, dataset versions, and quality metrics.

### Data Flow
1. Records from **Phase 1** flow into **Data Cleaning & Normalization**.
2. Cleaned records are passed to **Feature Engineering** to generate derived attributes and embeddings (if used).
3. Processed records are written to:
   - **Primary Operational Store** for transactional reads/writes.
   - **Search/Vector Index** for search and similarity queries.
4. Run metadata (timestamps, counts, errors) is saved to **Metadata Store**.

---

## Phase 3: LLM Integration

### Purpose
- **Purpose**: Interpret natural-language user input, extract and refine preferences, and generate rich query intents to guide the recommendation engine.

### Key Components
- **LLM Client (Groq)**:
  - Abstraction over the Groq LLM API for low-latency, cost-efficient inference.
- **Prompt Builder**:
  - Constructs prompts including instructions, examples, and relevant schema descriptions.
- **Preference Extraction & Normalization Layer**:
  - Maps LLM output to structured fields: `price_range`, `location`, `cuisine`, `min_rating`, `ambience`, `special_requirements` (e.g., “vegan”, “kid-friendly”).
- **Guardrails & Validation**:
  - Validates LLM outputs, applies defaults, and handles ambiguous or missing preferences.

### Data Flow
1. API receives raw user input (text + optional explicit filters).
2. **Prompt Builder** combines:
   - User text.
   - Optional explicit filters.
   - System instructions and restaurant schema description.
3. **LLM Client** calls the LLM with the constructed prompt.
4. LLM returns a structured or semi-structured representation (e.g., JSON-like preferences and intent explanation).
5. **Preference Extraction & Normalization** parses LLM output, validates fields, and produces a normalized preference object.
6. Normalized preferences are passed to **Phase 4: Recommendation Engine**.

---

## Phase 4: Recommendation Engine

### Purpose
- **Purpose**: Use user preferences and restaurant data to compute, score, and rank a list of recommended restaurants.

### Key Components
- **Filter & Candidate Retrieval Module**:
  - Applies hard filters from preferences (location constraint, price bucket, minimum rating, cuisine subset).
  - Retrieves candidate restaurants from DB and/or search index.
- **Scoring Engine**:
  - Combines:
    - Rule-based scores (rating, distance, price match).
    - Optional similarity scores (embedding similarity to user intent or past preferences).
    - LLM-derived preference weights (e.g., “strong preference for rooftop and romantic ambience”).
- **Post-Processing & Diversification**:
  - Ensures diversity (not all from same area/cuisine).
  - Applies business rules (e.g., avoid low-review-count places).
- **Explanation Generator (Optional)**:
  - Generates brief natural-language justifications for each recommendation (can reuse LLM or template-based logic).

### Data Flow
1. Normalized preferences arrive from **Phase 3**.
2. **Filter & Candidate Retrieval** queries the:
   - **Primary Operational Store** for structured filters.
   - **Search/Vector Index** for semantic matches if used.
3. Candidate set is passed to the **Scoring Engine**.
4. Scored candidates are sorted, truncated (e.g., top N), and passed through **Post-Processing & Diversification**.
5. Final ranked list (with optional explanations) is passed to **Phase 5: API Layer**.

---

## Phase 5: API Layer

### Purpose
- **Purpose**: Expose a clean, structured interface for clients (backend consumers and UI) to request recommendations and receive consistent, machine-readable responses.

### Key Components
- **API Gateway / HTTP Service**:
  - REST (or GraphQL) endpoints for:
    - `POST /recommendations` with user input and optional constraints.
    - Optional endpoints for metadata (health, version info).
- **Request Validation & Authentication**:
  - Validates request schema.
  - Handles API keys or auth if needed.
- **Orchestration Layer**:
  - Coordinates calls across:
    - **Phase 3** (LLM Integration).
    - **Phase 4** (Recommendation Engine).
- **Response Formatter**:
  - Returns structured recommendation payloads.
 - **Web UI Client (Restaurant Discovery Page)**:
   - Single-page or multi-page web UI that allows users to:
     - Enter natural-language queries and explicit filters (price, cuisine, rating, location).
     - View recommended restaurants in a list and/or map view.
     - See key attributes (name, cuisine, rating, price range) and short LLM-generated explanations.
   - Communicates exclusively with the API layer; contains no recommendation logic itself.

### Data Flow
1. Client sends request (`user_input`, `price_range`, `location`, `cuisine`, etc.) to API.
2. **Request Validation** checks payload and auth.
3. **Orchestration Layer**:
   - Sends user input to **LLM Integration**.
   - Passes normalized preferences to **Recommendation Engine**.
4. **Recommendation Engine** returns ranked restaurants and metadata.
5. **Response Formatter** packages:
   - Restaurant details (id, name, address, coordinates, price, rating, cuisine).
   - Reasoning fields (why recommended, keywords matched).
6. API returns structured JSON response to client.

---

## High-Level System Diagram (Text)

- **External Client**
  - → calls → **API Layer (HTTP Service / Gateway)**
    - → orchestrates → **LLM Integration**
      - → calls → **LLM Provider (external)**
      - ← returns ← Interpreted Preferences (structured)
    - → calls → **Recommendation Engine**
      - → queries → **Primary Operational Store (DB)**
      - → queries → **Search/Vector Index**
      - ← returns ← Ranked Recommendations
- **Batch Flow (Offline)**
  - **Scheduler**
    - → triggers → **Data Ingestion**
      - → reads from → **Hugging Face Dataset (Zomato)**
      - → sends → **Data Processing & Storage**
        - → writes → **Primary Operational Store**
        - → updates → **Search/Vector Index**
        - → logs → **Metadata Store**

---

## Tech Stack Suggestions

- **Language / Runtime**
  - **Backend**: Python (FastAPI) or Node.js (NestJS/Express).
- **Data Ingestion**
  - Hugging Face `datasets` library (Python) for `ManikaSaini/zomato-restaurant-recommendation`.
  - Workflow scheduling: simple cron, or Airflow/Prefect if complexity grows.
- **Data Storage & Indexing**
  - Primary DB: PostgreSQL.
  - Search: PostgreSQL full text or Elasticsearch/OpenSearch.
  - Vector: pgvector extension in PostgreSQL or dedicated vector DB.
- **LLM Integration**
  - Hosted LLM API (OpenAI, Anthropic, or Hugging Face Inference Endpoint).
- **API & Infrastructure**
  - API: FastAPI/NestJS behind Nginx/API Gateway.
  - Containerization: Docker + Kubernetes (or simpler: Docker + managed container service).
  - Monitoring: Prometheus + Grafana, or managed APM (Datadog, New Relic).

---

## Basic Scalability Considerations

- **Data Ingestion & Processing**
  - Use batch jobs with incremental updates (based on dataset version or last-updated timestamps).
  - Make ingestion idempotent to support retries and re-runs.
- **Storage & Query Performance**
  - Add appropriate indexes on `location`, `cuisine`, `price_range`, `rating`.
  - Separate read/write workloads via read replicas for the primary DB.
  - Use caching (e.g., Redis) for popular queries/locations.
- **LLM Integration**
  - Introduce request-level and user-level rate limiting.
  - Cache LLM interpretation results for repeated or similar queries when possible.
  - Design prompts to enforce strict structured outputs to reduce parsing overhead and errors.
- **Recommendation Engine**
  - Keep ranking logic primarily in-application (fast, deterministic); use LLM mainly for interpreting user intent, not scoring every candidate.
  - Precompute stable features (e.g., popularity scores, embeddings) offline to minimize per-request computation.
- **API Layer & Infrastructure**
  - Stateless API service enabling horizontal scaling through load balancing.
  - Graceful degradation:
    - If LLM is unavailable, fall back to rule-based interpretation of explicit filters.
    - If vector search is down, rely on structured filters and text search only.
- **Observability**
  - Log key information: request volume, LLM latency, DB/search query latency, recommendation success metrics.
  - Track quality metrics (click-through, saves, bookings if available) to inform future model and ranking improvements.

