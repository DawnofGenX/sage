"""Tests for real LLM integration: extraction, token/cost tracking,
single-call pipeline, and mock fallback.

All real-API tests use ``httpx.MockTransport`` so no network access is
required.
"""

import json

import httpx
import pytest

from extraction.pipeline import ExtractionPipeline
from llm.provider import LLMProvider


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
# Real LLM extraction
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_llm_extraction(sample_transcript):
    """Verify real LLM extraction works with mock transport."""
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "contacts": [{"name": "John Smith", "company": "Acme Corp"}],
                                "deals": [{"title": "Enterprise deal", "value": 50000, "stage": "lead"}],
                                "followups": [{"title": "Follow up", "due_date": "2025-01-15"}],
                                "sentiment": "positive",
                                "buying_signals": ["budget"],
                                "risks": [],
                                "intent": "new_lead",
                            })
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    provider = make_provider(handler)
    result = await provider.extract(sample_transcript, "full")

    assert result["contacts"][0]["name"] == "John Smith"
    assert result["deals"][0]["value"] == 50000
    assert result["sentiment"] == "positive"
    assert result["intent"] == "new_lead"


# ------------------------------------------------------------------
# Token tracking
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_tracking():
    """Verify tokens are tracked across API calls."""
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"intent": "new_lead"}'}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 100},
            },
        )

    provider = make_provider(handler)
    assert provider.total_tokens == 0

    await provider.extract("transcript", "full")
    assert provider.total_tokens == 300

    await provider.extract("another transcript", "full")
    assert provider.total_tokens == 600


# ------------------------------------------------------------------
# Cost tracking
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_tracking():
    """Verify cost is calculated based on model and token count."""
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"intent": "new_lead"}'}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 1000},
            },
        )

    provider = make_provider(handler, model="gpt-4o-mini")
    assert provider.total_cost == 0.0

    await provider.extract("transcript", "full")
    # gpt-4o-mini: $0.0006 per 1K tokens, 2000 tokens = $0.0012
    assert provider.total_cost == pytest.approx(0.0012)


def test_calculate_cost_unknown_model():
    """Verify cost calculation uses default rate for unknown models."""
    provider = LLMProvider(api_key="sk-test", model="unknown-model")
    cost = provider._calculate_cost(5000)
    # Default: $0.001 per 1K tokens, 5000 tokens = $0.005
    assert cost == pytest.approx(0.005)


# ------------------------------------------------------------------
# Single-call pipeline
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_call_pipeline(sample_transcript):
    """Verify pipeline makes only 1 LLM call."""
    call_count = {"count": 0}

    def handler(request):
        call_count["count"] += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({
                                "contacts": [{"name": "John Smith", "company": "Acme Corp"}],
                                "deals": [{"title": "Deal", "value": 50000, "stage": "lead"}],
                                "followups": [{"title": "Follow up", "due_date": "2025-01-15"}],
                                "sentiment": "positive",
                                "buying_signals": ["budget"],
                                "risks": [],
                                "intent": "new_lead",
                            })
                        }
                    }
                ],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    provider = make_provider(handler)
    pipeline = ExtractionPipeline(provider)
    result = await pipeline.process(sample_transcript)

    assert call_count["count"] == 1
    assert result["step4_validated"] is True
    assert result["step2_intent"] == "new_lead"
    assert result["step1_entities"]["people"] == ["John Smith"]


# ------------------------------------------------------------------
# Mock fallback
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_fallback(sample_transcript):
    """Verify mock mode still works without API key."""
    provider = LLMProvider(api_key="", api_url="http://localhost:9999")
    assert provider.is_mock is True

    result = await provider.extract(sample_transcript, "full")
    assert "contacts" in result
    assert "deals" in result
    assert "sentiment" in result
    assert "intent" in result
