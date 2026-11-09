import json

import httpx
import pytest

from app.services import llm

SCHEMA = {"type": "object", "properties": {"client_name": {"type": "string"}}, "required": ["client_name"]}


def _gemini_response(payload, finish="STOP"):
    return {"candidates": [{"finishReason": finish, "content": {"parts": [{"text": json.dumps(payload)}]}}]}


def test_gemini_returns_parsed_json(monkeypatch):
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.update(url=url, headers=headers, body=json)
        return httpx.Response(200, json=_gemini_response({"client_name": "ABC"}))

    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(llm.httpx, "post", fake_post)

    assert llm.complete_json("sys", "prompt", SCHEMA, provider="gemini") == {"client_name": "ABC"}
    assert sent["headers"]["x-goog-api-key"] == "g-key"
    assert sent["body"]["generationConfig"]["responseJsonSchema"] == SCHEMA
    assert sent["url"].endswith(f"{llm.settings.GEMINI_MODEL}:generateContent")


@pytest.mark.parametrize(
    "response, message",
    [
        (httpx.Response(429, text="quota"), "429"),
        (httpx.Response(200, json={"candidates": []}), "no candidates"),
        (httpx.Response(200, json=_gemini_response({"a": 1}, finish="MAX_TOKENS")), "truncated"),
        (httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}), "invalid JSON"),
    ],
)
def test_gemini_failures_raise(monkeypatch, response, message):
    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: response)

    with pytest.raises(llm.LLMError, match=message):
        llm.complete_json("sys", "prompt", SCHEMA, provider="gemini")


def test_missing_keys_and_unknown_provider_raise(monkeypatch):
    monkeypatch.setattr(llm.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "")

    with pytest.raises(llm.LLMError, match="ANTHROPIC_API_KEY"):
        llm.complete_json("s", "p", SCHEMA, provider="claude")
    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.complete_json("s", "p", SCHEMA, provider="gemini")
    with pytest.raises(llm.LLMError, match="Unknown LLM provider"):
        llm.complete_json("s", "p", SCHEMA, provider="mistral")


def test_default_provider_comes_from_settings(monkeypatch):
    monkeypatch.setattr(llm.settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(llm.settings, "GEMINI_API_KEY", "")

    with pytest.raises(llm.LLMError, match="GEMINI_API_KEY"):
        llm.complete_json("s", "p", SCHEMA)
