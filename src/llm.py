"""LLM provider for triage (D-026).

One place where the model is called. Everything above it (the prompt, the locked
taxonomy and scoring criteria, the validator) is model-agnostic, so swapping the
provider is a change here and nowhere else.

Provider: kie.ai, which serves models through a Gemini-compatible API:
    POST {base}/gemini/v1/models/{model}:generateContent

Configuration is environment only (secrets never in code):
    KIE_API_KEY         required
    KIE_BASE_URL        default https://api.kie.ai
    KIE_MODEL           default gemini-3-5-flash
    KIE_THINKING_LEVEL  low (default) or high

Raises LLMError on any failure. Triage catches it, leaves the item untriaged, and
a later run retries it. An item is never silently skipped and never half-written.
"""

import json
import os
import time

import requests

DEFAULT_BASE_URL = "https://api.kie.ai"
DEFAULT_MODEL = "gemini-3-5-flash"
DEFAULT_THINKING = "low"

TIMEOUT = 90
ATTEMPTS = 3

# Gemini counts thinking tokens against maxOutputTokens and spends some even at
# thinkingLevel=low. Without headroom the answer is clipped before it is finished,
# which surfaces as a JSON parse failure rather than as an obvious truncation.
THINKING_HEADROOM = 1024


class LLMError(RuntimeError):
    """The model could not be called, or returned nothing usable."""


def model_name() -> str:
    return os.getenv("KIE_MODEL", DEFAULT_MODEL)


def _api_key() -> str:
    key = os.getenv("KIE_API_KEY")
    if not key:
        raise LLMError(
            "KIE_API_KEY is not set. Copy .env.example to .env and fill it in. "
            "In GitHub Actions it is a repository secret of the same name."
        )
    return key


def complete(prompt: str, max_tokens: int, temperature: float = 0) -> tuple[str, int, int]:
    """Send one prompt, return (text, input_tokens, output_tokens).

    Retries transient faults. kie.ai signals some server errors with HTTP 200 and
    a 5xx code in the body, so the body is checked as well as the status.
    """
    model = model_name()
    base = os.getenv("KIE_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base}/gemini/v1/models/{model}:generateContent"

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens + THINKING_HEADROOM,
            "thinkingConfig": {
                "thinkingLevel": os.getenv("KIE_THINKING_LEVEL", DEFAULT_THINKING)
            },
        },
    }
    headers = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}

    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            code = data.get("code")
            if code and int(code) >= 500:
                raise LLMError(data.get("msg", "provider server error"))

            return _extract(data)

        except (requests.RequestException, LLMError, ValueError) as exc:
            last = exc
            if attempt < ATTEMPTS - 1:
                time.sleep(2 * (attempt + 1))

    raise LLMError(f"{model} failed after {ATTEMPTS} attempts: {last}")


def _extract(data: dict) -> tuple[str, int, int]:
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMError(f"no candidates in response: {json.dumps(data)[:300]}")

    parts = candidates[0].get("content", {}).get("parts", [])
    # Join every text part; skip thought and functionCall parts.
    text = "".join(p["text"] for p in parts if isinstance(p, dict) and "text" in p).strip()

    if not text:
        finish = candidates[0].get("finishReason", "unknown")
        raise LLMError(f"empty response (finishReason={finish})")

    usage = data.get("usageMetadata") or {}
    return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
