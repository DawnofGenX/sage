"""Tests for the LLM provider integration: format detection, retries,
timeouts, response validation, and mock fallback.

All real-API tests use ``httpx.MockTransport`` so no network access is
required.
"""

import json
import os

import httpx
import pytest


from llm.formats import AnthropicFormat, OpenAIFormat, detect_format, parse_json_response
from llm.provider import LLMAPIError, LLMProvider


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure LLM env vars don't leak into provider construction."""
    for var in ("LLM_API_KEY", "LLM_API_URL", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def sample_transcript():
    """A realistic sales call transcript."""
    return (
        "Hi, this is John Smith from Acme Corp. I spoke with Sarah Johnson "
        "at Globex Inc last week. She's very excited about our enterprise "
        "solution and mentioned a budget of $50,000."
    )


def make_provider(handler, **kwargs):
    """Build a real-mode provider backed by a MockTransport."""
    transport = httpx.MockTransport(handler)
    kwargs.setdefault("api_key", "sk-test")
    kwargs.setdefault("retry_base_delay", 0)
    return LLMProvider(transport=transport, **kwargs)


# ------------------------------------------------------------------
# Format detection
# ------------------------------------------------------------------


def test_openai_format_detection():
    """OpenAI chat/completions URLs use the OpenAI format."""
    provider = LLMProvider(api_key="sk-test", api_url="https://api.openai.com/v1/chat/completions")
    assert provider.api_format == "openai"
    assert isinstance(provider._format, OpenAIFormat)


def test_anthropic_format_detection():
    """Anthropic messages URLs use the Anthropic format."""
    provider = LLMProvider(
        api_key="sk-test",
        api_url="https://api.anthropic.com/v1/messages",
        model="claude-sonnet-4-20250514",
    )
    assert provider.api_format == "anthropic"
    assert isinstance(provider._format, AnthropicFormat)


def test_detect_format_openai_compatible():
    """OpenRouter-style URLs default to the OpenAI-compatible format."""
    fmt = detect_format("https://openrouter.ai/api/v1/chat/completions")
    assert isinstance(fmt, OpenAIFormat)


def test_detect_format_anthropic():
    """Anthropic URLs are detected from the URL string."""
    fmt = detect_format("https://api.anthropic.com/v1/messages")
    assert isinstance(fmt, AnthropicFormat)


def test_openai_payload_shape():
    """OpenAI payload uses messages + Bearer auth."""
    fmt = OpenAIFormat()
    payload = fmt.build_payload("gpt-4o-mini", "PROMPT")
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"] == [{"role": "user", "content": "PROMPT"}]
    headers = fmt.build_headers("sk-test")
    assert headers["Authorization"] == "Bearer sk-test"


def test_anthropic_payload_shape():
    """Anthropic payload uses max_tokens + x-api-key auth."""
    fmt = AnthropicFormat()
    payload = fmt.build_payload("claude-sonnet-4-20250514", "PROMPT")
    assert payload["model"] == "claude-sonnet-4-20250514"
    assert payload["max_tokens"] == 4096
    headers = fmt.build_headers("sk-test")
    assert headers["x-api-key"] == "sk-test"
    assert "anthropic-version" in headers


# ------------------------------------------------------------------
# Retry logic
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Transient 500s are retried; a later success is returned."""
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(500, text="server error")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"intent": "new_lead", "confidence": 0.9}'}}]},
        )

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    result = await provider.extract("some transcript", "intent")

    assert calls["count"] == 3
    assert result == {"intent": "new_lead", "confidence": 0.9}


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    """After max_retries failures, LLMAPIError is raised."""
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(503, text="unavailable")

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    with pytest.raises(LLMAPIError):
        await provider.extract("some transcript", "intent")

    assert calls["count"] == 3  # initial attempt + 2 retries


@pytest.mark.asyncio
async def test_retry_on_429():
    """HTTP 429 (rate limit) is retryable."""
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"sentiment": "neutral", "confidence": 0.6}'}}]},
        )

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    result = await provider.extract("transcript", "sentiment")

    assert calls["count"] == 2
    assert result["sentiment"] == "neutral"


# ------------------------------------------------------------------
# Timeout handling
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_handling():
    """A timeout is retried, then raised as LLMAPIError.

    MockTransport bypasses the network stack so it cannot enforce real
    timeouts; raising httpx.ReadTimeout from the handler exercises the
    same timeout-exception code path deterministically.
    """
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        raise httpx.ReadTimeout("simulated timeout", request=request)

    provider = make_provider(
        handler,
        api_url="https://api.openai.com/v1/chat/completions",
        timeout=0.05,
        max_retries=2,
    )
    with pytest.raises(LLMAPIError):
        await provider.extract("transcript", "intent")

    assert calls["count"] == 2


# ------------------------------------------------------------------
# Response validation
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_validation():
    """Non-JSON LLM content fails validation and raises after retries."""
    def handler(request):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "this is not json"}}]},
        )

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    with pytest.raises(LLMAPIError):
        await provider.extract("transcript", "intent")


@pytest.mark.asyncio
async def test_response_validation_malformed_payload():
    """A response missing required keys fails format validation."""
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    with pytest.raises(LLMAPIError):
        await provider.extract("transcript", "intent")


@pytest.mark.asyncio
async def test_code_fenced_json_parsed():
    """Markdown code fences around JSON are stripped before parsing."""
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "```json\n{\"intent\": \"follow_up\", \"confidence\": 0.7}\n```"}}
                ]
            },
        )

    provider = make_provider(handler, api_url="https://api.openai.com/v1/chat/completions")
    result = await provider.extract("transcript", "intent")

    assert result == {"intent": "follow_up", "confidence": 0.7}


@pytest.mark.asyncio
async def test_anthropic_response_parsed():
    """Anthropic content blocks are extracted and parsed."""
    def handler(request):
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": '{"intent": "deal_update", "confidence": 0.8}'}]},
        )

    provider = make_provider(
        handler,
        api_url="https://api.anthropic.com/v1/messages",
        model="claude-sonnet-4-20250514",
    )
    result = await provider.extract("transcript", "intent")

    assert result == {"intent": "deal_update", "confidence": 0.8}


def test_parse_json_response_rejects_non_object():
    """JSON arrays are rejected — extraction must return an object."""
    with pytest.raises(ValueError):
        parse_json_response("[1, 2, 3]")


# ------------------------------------------------------------------
# Mock fallback
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_fallback(sample_transcript):
    """Without an API key, mock mode returns structured data."""
    provider = LLMProvider(api_key="", api_url="http://localhost:9999")
    assert provider.is_mock is True

    result = await provider.extract(sample_transcript, "entities")
    assert "John Smith" in result["people"]
    assert "$50,000" in result["amounts"]


@pytest.mark.asyncio
async def test_mock_fallback_no_network():
    """Mock mode must never touch the network, even with a bogus URL."""
    provider = LLMProvider(api_key="", api_url="http://127.0.0.1:1/unreachable")
    result = await provider.extract("Hello world", "sentiment")
    assert result["sentiment"] in ("positive", "neutral", "negative")


def test_real_mode_when_api_key_set():
    """With an API key the provider uses the real API path."""
    provider = LLMProvider(api_key="sk-test", api_url="https://api.openai.com/v1/chat/completions")
    assert provider.is_mock is False
