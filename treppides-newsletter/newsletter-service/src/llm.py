"""The ONLY model-aware code. Swap providers/models here; nothing else knows the model.

kie.ai Gemini-compatible proxy: POST {base}/gemini/v1/models/{model}:generateContent
Auth: Bearer {KIE_API_KEY}.
"""
from __future__ import annotations

import json
import time

import requests

from . import config

# (connect timeout, read timeout). Triage calls can be slow when the model thinks.
_TIMEOUT = (10, 150)
_RETRIES = 3


class LLMError(RuntimeError):
    pass


def generate_json(prompt: str, max_output_tokens: int = 2048) -> dict:
    """Send one prompt, expect a single JSON object back. Returns:
    {data: dict, input_tokens: int, output_tokens: int, credits: float}.
    Retries transient network errors and 5xx with backoff."""
    url = f"{config.KIE_BASE_URL}/gemini/v1/models/{config.KIE_MODEL}:generateContent"
    headers = {
        "Authorization": f"Bearer {config.KIE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }

    last_err = None
    for attempt in range(1, _RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_err = f"network {type(e).__name__}"
            time.sleep(2 * attempt)
            continue
        if resp.status_code >= 500:
            last_err = f"kie.ai {resp.status_code}"
            time.sleep(2 * attempt)
            continue
        if resp.status_code != 200:
            raise LLMError(f"kie.ai {resp.status_code}: {resp.text[:300]}")
        break
    else:
        raise LLMError(f"exhausted {_RETRIES} retries: {last_err}")

    body = resp.json()

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise LLMError(f"unexpected response shape: {json.dumps(body)[:300]}") from e

    usage = body.get("usageMetadata", {})
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"model did not return valid JSON: {text[:300]}") from e

    return {
        "data": data,
        "input_tokens": usage.get("promptTokenCount", 0),
        "output_tokens": usage.get("candidatesTokenCount", 0)
        + usage.get("thinkingTokenCount", 0),
        "credits": body.get("credits_consumed", 0.0),
    }
