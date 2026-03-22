## Phase 3 – LLM Integration (Groq)

This folder is reserved for assets and documentation specific to **Phase 3: LLM Integration** of the AI Restaurant Recommendation Service.

Current implementation details:
- Core LLM integration code lives in the `llm_integration` package:
  - `llm_integration/models.py` defines:
    - `ExplicitFilters` – structured explicit filters from the API layer.
    - `UserPreferences` – normalized preferences produced by the LLM.
  - `llm_integration/groq_client.py`:
    - `GroqLLMClient` – thin wrapper over the Groq OpenAI-compatible chat completions API (`https://api.groq.com/openai/v1/chat/completions`).
    - Requires the `GROQ_API_KEY` environment variable.
  - `llm_integration/interpreter.py`:
    - `interpret_user_input` – sends user input (and optional explicit filters) to Groq and returns a `UserPreferences` object based on a JSON response.

### Testing

Automated tests for Phase 3 are intentionally deferred until a Groq API key is configured. Once `GROQ_API_KEY` is available, you can add tests under `tests/` that:
- Call `interpret_user_input` with sample queries.
- Assert that the returned `UserPreferences` object is populated sensibly.

