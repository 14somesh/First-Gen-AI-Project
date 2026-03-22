## AI Restaurant Recommendation Service

An AI-powered service utilizing Hugging Face datasets and Groq LLMs to provide intelligent, ranked restaurant recommendations based on natural language preferences.

**Core Stack:**
- **Backend:** FastAPI, SQLite, Recommendation Engine
- **Frontend:** Streamlit (`streamlit_app/app.py`)

### Getting Started

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure Variables**: Add required API keys (e.g., `GROQ_API_KEY`) to an `.env` file.
3. **Run tests**: `pytest`
4. **Launch Application**: Execute `.\run_local.bat` to concurrently start the Streamlit UI (port 8501) and FastAPI server (port 8000).
