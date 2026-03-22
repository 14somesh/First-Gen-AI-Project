from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv


# Load environment variables from .env if present so that GROQ_API_KEY
# can be picked up when running the API server.
load_dotenv()


GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_COMPLETIONS_PATH = "/chat/completions"


class GroqLLMClient:
    """
    Thin wrapper around the Groq OpenAI-compatible chat completions API.

    This client expects the `GROQ_API_KEY` environment variable to be set.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile") -> None:
        self.model = model
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Set it before using the GroqLLMClient."
            )
        self._api_key = api_key

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def chat_completion(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Call Groq's chat completions endpoint and return the parsed JSON body.
        """
        url = f"{GROQ_BASE_URL}{GROQ_CHAT_COMPLETIONS_PATH}"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            # Encourage JSON-structured output for easier parsing.
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=self._build_headers(), content=json.dumps(payload))
            response.raise_for_status()
            return response.json()

