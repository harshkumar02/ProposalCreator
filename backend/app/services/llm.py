"""Provider-neutral JSON completion for the n8n workflow steps.

``complete_json`` sends a system prompt + user prompt to Claude or Gemini and
returns the parsed JSON object, constrained to ``schema``. The provider comes
from ``settings.LLM_PROVIDER`` unless the caller passes one, so a workflow can
be switched between providers by configuration alone.

Unlike the legacy extractors, failures raise ``LLMError`` instead of returning
an empty result: workflow runs must be marked FAILED, not silently "succeed"
with nothing extracted.
"""
import json
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

SUPPORTED_PROVIDERS = ("claude", "gemini")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(Exception):
    pass


def complete_json(
    system: str,
    prompt: str,
    schema: Dict[str, Any],
    *,
    provider: Optional[str] = None,
    max_tokens: int = 16000,
) -> Dict[str, Any]:
    provider = (provider or settings.LLM_PROVIDER).lower()
    if provider == "claude":
        text = _claude(system, prompt, schema, max_tokens)
    elif provider == "gemini":
        text = _gemini(system, prompt, schema, max_tokens)
    else:
        raise LLMError(f"Unknown LLM provider {provider!r}; expected one of {SUPPORTED_PROVIDERS}")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"{provider} returned invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError(f"{provider} returned {type(data).__name__}, expected a JSON object")
    return data


def _claude(system: str, prompt: str, schema: Dict[str, Any], max_tokens: int) -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY is not set")

    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        # Streamed so long RFP inputs/outputs don't hit the HTTP timeout.
        with client.messages.stream(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            output_config={"format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError(f"Could not reach Claude API: {e}") from e

    if message.stop_reason == "refusal":
        raise LLMError("Claude declined the request (refusal)")
    if message.stop_reason == "max_tokens":
        raise LLMError("Claude output was truncated at max_tokens")
    return next((b.text for b in message.content if b.type == "text"), "")


def _gemini(system: str, prompt: str, schema: Dict[str, Any], max_tokens: int) -> str:
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set")

    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "maxOutputTokens": max_tokens,
        },
    }
    try:
        res = httpx.post(
            GEMINI_URL.format(model=settings.GEMINI_MODEL),
            headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            json=body,
            timeout=600,
        )
    except httpx.HTTPError as e:
        raise LLMError(f"Could not reach Gemini API: {e}") from e
    if res.status_code != 200:
        raise LLMError(f"Gemini API error {res.status_code}: {res.text[:500]}")

    candidates = res.json().get("candidates") or []
    if not candidates:
        raise LLMError("Gemini returned no candidates (prompt may have been blocked)")
    candidate = candidates[0]
    if candidate.get("finishReason") == "MAX_TOKENS":
        raise LLMError("Gemini output was truncated at maxOutputTokens")
    parts = (candidate.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts)
