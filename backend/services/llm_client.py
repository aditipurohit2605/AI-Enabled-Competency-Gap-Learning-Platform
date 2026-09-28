import json
import logging
import os
import re
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM operations."""
    pass


class LLMConfigError(LLMError):
    """Raised when LLM configuration or API key is missing."""
    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is hit and retries are exhausted."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the allowed timeout."""
    pass


class LLMResponseParsingError(LLMError):
    """Raised when the LLM response cannot be parsed into JSON."""
    pass


def extract_json_from_text(text: str) -> dict | list:
    """
    Safely extract JSON from raw model output, stripping markdown fences if present.
    """
    text = text.strip()
    if text.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    return json.loads(text)


class BaseLLMClient:
    """Abstract interface for LLM client."""

    def generate_json(
        self,
        prompt: str,
        schema: Any = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> dict | list:
        raise NotImplementedError("Subclasses must implement generate_json")


class GeminiLLMClient(BaseLLMClient):
    """
    Thin wrapper around Google GenAI SDK (google-genai).
    Reads GEMINI_MODEL (default: gemini-2.5-flash) and GEMINI_API_KEY from environment.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            key = self.api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                raise LLMConfigError(
                    "GEMINI_API_KEY environment variable is missing. "
                    "Please configure GEMINI_API_KEY to enable AI quiz generation."
                )
            from google import genai
            self._client = genai.Client(api_key=key)
        return self._client

    def generate_json(
        self,
        prompt: str,
        schema: Any = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> dict | list:
        model_name = self.model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = self._get_client()
        from google.genai import types, errors

        config_args = {"response_mime_type": "application/json"}
        if schema is not None:
            config_args["response_schema"] = schema

        config = types.GenerateContentConfig(**config_args)

        last_error = None
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if not response.text:
                    raise LLMResponseParsingError("Model returned an empty response")
                return extract_json_from_text(response.text)

            except errors.APIError as e:
                status_code = getattr(e, "code", None)
                message = str(e)
                # Check for rate limit or quota exhaustion (429)
                if status_code == 429 or "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
                    logger.warning(f"Rate limit encountered on attempt {attempt + 1}: {e}")
                    last_error = LLMRateLimitError(f"Gemini API rate limit exceeded: {e}")
                else:
                    last_error = LLMError(f"Gemini API error: {e}")

                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    raise last_error

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse JSON on attempt {attempt + 1}: {e}")
                last_error = LLMResponseParsingError(f"Failed to parse LLM response as JSON: {e}")
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    raise last_error

            except Exception as e:
                if "timeout" in str(e).lower():
                    raise LLMTimeoutError(f"LLM request timed out: {e}")
                raise LLMError(f"Unexpected error communicating with Gemini API: {e}")

        if last_error:
            raise last_error
        raise LLMError("Exhausted retries without response")


class FakeLLMClient(BaseLLMClient):
    """
    Configurable fake LLM client for offline unit and integration tests.
    Does not make any network requests.
    """

    def __init__(self, handler: Callable[[str], dict | list] | None = None):
        self.handler = handler
        self.call_history: list[str] = []
        self._queued_responses: list[dict | list | Exception] = []

    def queue_response(self, response: dict | list | Exception):
        """Queue a specific response or exception to return on subsequent calls."""
        self._queued_responses.append(response)

    def generate_json(
        self,
        prompt: str,
        schema: Any = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> dict | list:
        self.call_history.append(prompt)

        if self._queued_responses:
            next_resp = self._queued_responses.pop(0)
            if isinstance(next_resp, Exception):
                raise next_resp
            return next_resp

        if self.handler:
            return self.handler(prompt)

        # Default fallback response if no queue or handler
        return {
            "questions": [
                {
                    "question": "Which sampling method gives every unit an equal non-zero probability?",
                    "options": [
                        "Simple Random Sampling",
                        "Convenience Sampling",
                        "Quota Sampling",
                        "Purposive Sampling"
                    ],
                    "correct_index": 0,
                    "explanation": "In Simple Random Sampling without replacement, every unit has an equal chance of selection.",
                    "source_passage": "In probability sampling, every unit in the target population has a known, non-zero probability of being selected.",
                    "difficulty": "medium"
                }
            ]
        }


# Singleton active instance
_ACTIVE_LLM_CLIENT: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    """Get the active LLM client (defaults to Gemini client)."""
    global _ACTIVE_LLM_CLIENT
    if _ACTIVE_LLM_CLIENT is None:
        _ACTIVE_LLM_CLIENT = GeminiLLMClient()
    return _ACTIVE_LLM_CLIENT


def set_llm_client(client: BaseLLMClient):
    """Set custom LLM client (e.g. FakeLLMClient for testing)."""
    global _ACTIVE_LLM_CLIENT
    _ACTIVE_LLM_CLIENT = client


def reset_llm_client():
    """Reset back to default Gemini client."""
    global _ACTIVE_LLM_CLIENT
    _ACTIVE_LLM_CLIENT = None
