from __future__ import annotations

import json
from typing import Any, Dict, Optional

from .groq_client import GroqLLMClient
from .models import ExplicitFilters, UserPreferences


SYSTEM_PROMPT = """
You are a restaurant recommendation assistant.
Your task is to read the user's free-text query and optional explicit filters,
then output a concise JSON object capturing their preferences.

JSON schema (do not include comments in the output):
{
  "price_range": string | null,          // e.g. "low", "medium", "high", "$$", "500-1000"
  "location": string | null,             // city or area
  "cuisines": string[] | [],             // list of cuisines, e.g. ["Italian", "Chinese"]
  "min_rating": number | null,           // e.g. 3.5
  "ambience": string | null,             // e.g. "romantic", "family", "rooftop"
  "special_requirements": string[] | [], // e.g. ["vegan", "kid-friendly"]
  "sort_preference": string | null       // e.g. "rating_desc", "distance_asc", "price_asc"
}

Always return a single JSON object with these keys.
"""


def _build_user_message(user_input: str, explicit_filters: Optional[ExplicitFilters]) -> str:
    payload: Dict[str, Any] = {"user_input": user_input}
    if explicit_filters is not None:
        payload["explicit_filters"] = {
            "price_range": explicit_filters.price_range,
            "location": explicit_filters.location,
            "cuisines": explicit_filters.cuisines,
            "min_rating": explicit_filters.min_rating,
        }
    return json.dumps(payload, ensure_ascii=False)


def interpret_user_input(
    user_input: str,
    explicit_filters: Optional[ExplicitFilters] = None,
    model: str = "llama-3.3-70b-versatile",
) -> UserPreferences:
    """
    High-level helper that sends user input to Groq and returns structured
    UserPreferences based on the LLM's JSON response.

    If the Groq client cannot be initialized (e.g. missing GROQ_API_KEY),
    this function falls back to building preferences purely from
    ExplicitFilters so that the rest of the pipeline can still operate.
    """
    response: Dict[str, Any] = {}

    try:
        client = GroqLLMClient(model=model)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {"role": "user", "content": _build_user_message(user_input, explicit_filters)},
        ]

        response = client.chat_completion(messages)

        # The response_format=json_object contract means the first choice content
        # should be a single JSON object.
        content = (
            response.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "{}")
        )

        try:
            parsed: Dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            parsed = {}

        price_range = parsed.get("price_range")
        location = parsed.get("location")
        cuisines_raw = parsed.get("cuisines") or []
        min_rating = parsed.get("min_rating")
        ambience = parsed.get("ambience")
        special_requirements_raw = parsed.get("special_requirements") or []
        sort_preference = parsed.get("sort_preference")

        cuisines = [
            str(c).strip() for c in cuisines_raw if isinstance(c, (str, int, float)) and str(c).strip()
        ]
        special_requirements = [
            str(s).strip()
            for s in special_requirements_raw
            if isinstance(s, (str, int, float)) and str(s).strip()
        ]

        return UserPreferences(
            price_range=str(price_range).strip() if isinstance(price_range, str) else price_range,
            location=str(location).strip() if isinstance(location, str) else location,
            cuisines=cuisines,
            min_rating=float(min_rating) if isinstance(min_rating, (int, float)) else None,
            ambience=str(ambience).strip() if isinstance(ambience, str) else ambience,
            special_requirements=special_requirements,
            sort_preference=str(sort_preference).strip() if isinstance(sort_preference, str) else sort_preference,
            raw_llm_response=response,
        )
    except RuntimeError:
        # GROQ_API_KEY missing or other initialization issue: fall back to
        # preferences derived solely from explicit filters.
        ef = explicit_filters or ExplicitFilters()

        cuisines = ef.cuisines or []
        return UserPreferences(
            price_range=ef.price_range,
            location=ef.location,
            cuisines=[str(c).strip() for c in cuisines if str(c).strip()],
            min_rating=ef.min_rating,
            ambience=None,
            special_requirements=[],
            sort_preference=None,
            raw_llm_response={"fallback": "explicit_filters_only"},
        )

