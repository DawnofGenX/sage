"""Tests for the LLM provider abstraction."""

import os

import pytest


from llm.provider import LLMProvider


@pytest.fixture
def provider():
    """Create a provider in mock mode (no API key)."""
    return LLMProvider(api_key="", api_url="http://localhost:9999", model="test-model")


@pytest.fixture
def sample_transcript():
    """A realistic sales call transcript."""
    return (
        "Hi, this is John Smith from Acme Corp. I spoke with Sarah Johnson "
        "at Globex Inc last week. She's very interested in our enterprise "
        "solution and mentioned a budget of $50,000. We should follow up "
        "with her on January 15th. She's excited about the demo and ready "
        "to move forward. The decision timeline is urgent."
    )


@pytest.fixture
def negative_transcript():
    """A transcript with negative sentiment."""
    return (
        "Mike Brown from TechStart Ltd is concerned about the pricing. "
        "He's worried about budget cuts and mentioned a competitor. "
        "This is a problem we need to address."
    )


# ------------------------------------------------------------------
# Mock mode detection
# ------------------------------------------------------------------


def test_mock_mode_fallback():
    """Verify mock mode is used when no API key is set."""
    provider = LLMProvider(api_key="", api_url="http://localhost:9999")
    assert provider.is_mock is True


def test_real_mode_when_api_key_set():
    """Verify real mode is used when API key is set."""
    provider = LLMProvider(api_key="sk-test-key", api_url="http://localhost:9999")
    assert provider.is_mock is False


def test_env_var_configuration():
    """Verify provider reads from environment variables."""
    os.environ["LLM_API_KEY"] = "sk-env-key"
    os.environ["LLM_API_URL"] = "https://api.example.com/v1"
    os.environ["LLM_MODEL"] = "gpt-4"
    try:
        provider = LLMProvider()
        assert provider.api_key == "sk-env-key"
        assert provider.api_url == "https://api.example.com/v1"
        assert provider.model == "gpt-4"
        assert provider.is_mock is False
    finally:
        del os.environ["LLM_API_KEY"]
        del os.environ["LLM_API_URL"]
        del os.environ["LLM_MODEL"]


# ------------------------------------------------------------------
# Entity extraction
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_entities_mock(provider, sample_transcript):
    """Test entity extraction in mock mode."""
    result = await provider.extract(sample_transcript, "entities")

    assert "people" in result
    assert "companies" in result
    assert "amounts" in result
    assert "dates" in result

    # Should find John Smith and Sarah Johnson
    assert "John Smith" in result["people"]
    assert "Sarah Johnson" in result["people"]

    # Should find Acme Corp and Globex Inc
    assert any("Acme" in c for c in result["companies"])
    assert any("Globex" in c for c in result["companies"])

    # Should find the dollar amount
    assert "$50,000" in result["amounts"]

    # Should find the date
    assert any("January" in d for d in result["dates"])


@pytest.mark.asyncio
async def test_extract_entities_empty_transcript(provider):
    """Test entity extraction with empty transcript."""
    result = await provider.extract("", "entities")
    assert result["people"] == []
    assert result["companies"] == []
    assert result["amounts"] == []
    assert result["dates"] == []


# ------------------------------------------------------------------
# Intent classification
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_intent_mock(provider, sample_transcript):
    """Test intent classification in mock mode."""
    result = await provider.extract(sample_transcript, "intent")

    assert "intent" in result
    assert "confidence" in result
    assert result["intent"] in ("new_lead", "follow_up", "deal_update", "general")
    assert 0 <= result["confidence"] <= 1


@pytest.mark.asyncio
async def test_classify_intent_new_lead(provider):
    """Test that new lead keywords are detected."""
    transcript = "I'm interested in your product and want to evaluate a demo for my team."
    result = await provider.extract(transcript, "intent")
    assert result["intent"] == "new_lead"


@pytest.mark.asyncio
async def test_classify_intent_follow_up(provider):
    """Test that follow-up keywords are detected."""
    transcript = "Just wanted to follow up on our last conversation and check in."
    result = await provider.extract(transcript, "intent")
    assert result["intent"] == "follow_up"


@pytest.mark.asyncio
async def test_classify_intent_deal_update(provider):
    """Test that deal update keywords are detected."""
    transcript = "The contract is signed and we're ready to move to the next stage."
    result = await provider.extract(transcript, "intent")
    assert result["intent"] == "deal_update"


# ------------------------------------------------------------------
# Sentiment analysis
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sentiment_positive(provider, sample_transcript):
    """Test positive sentiment detection."""
    result = await provider.extract(sample_transcript, "sentiment")
    assert result["sentiment"] == "positive"
    assert result["confidence"] > 0.5


@pytest.mark.asyncio
async def test_sentiment_negative(provider, negative_transcript):
    """Test negative sentiment detection."""
    result = await provider.extract(negative_transcript, "sentiment")
    assert result["sentiment"] == "negative"
    assert result["confidence"] > 0.5


@pytest.mark.asyncio
async def test_sentiment_neutral(provider):
    """Test neutral sentiment when no strong signals."""
    transcript = "The meeting was scheduled for Tuesday at 3pm."
    result = await provider.extract(transcript, "sentiment")
    assert result["sentiment"] == "neutral"


# ------------------------------------------------------------------
# Full extraction
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_full_mock(provider, sample_transcript):
    """Test full extraction in mock mode."""
    result = await provider.extract(sample_transcript, "full")

    assert "contacts" in result
    assert "deals" in result
    assert "followups" in result
    assert "sentiment" in result
    assert "buying_signals" in result
    assert "risks" in result

    # Should have extracted contacts
    assert len(result["contacts"]) > 0
    assert any("John Smith" in c["name"] for c in result["contacts"])

    # Should have extracted a deal with the amount
    assert len(result["deals"]) > 0
    assert result["deals"][0]["value"] == "50000"

    # Should have sentiment data (string in full extraction)
    assert result["sentiment"] == "positive"

    # Should have buying signals (budget, demo, decision, timeline)
    assert len(result["buying_signals"]) > 0


@pytest.mark.asyncio
async def test_extract_full_with_risks(provider, negative_transcript):
    """Test full extraction captures risks."""
    result = await provider.extract(negative_transcript, "full")
    assert len(result["risks"]) > 0
    assert "concern" in result["risks"] or "worried" in result["risks"]


# ------------------------------------------------------------------
# Insights
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insights_generation(provider, sample_transcript):
    """Test insight generation in mock mode."""
    result = await provider.extract(sample_transcript, "insights")

    assert "insights" in result
    assert "priority" in result
    assert isinstance(result["insights"], list)
    assert len(result["insights"]) > 0
    assert result["priority"] in ("high", "medium", "low")


@pytest.mark.asyncio
async def test_insights_high_priority(provider):
    """Test high priority when many signals present."""
    transcript = (
        "The budget is approved and we have an urgent timeline. "
        "The decision maker is ready to sign the contract. "
        "We need to schedule a demo immediately."
    )
    result = await provider.extract(transcript, "insights")
    assert result["priority"] == "high"
    assert len(result["insights"]) >= 3


@pytest.mark.asyncio
async def test_insights_low_priority(provider):
    """Test low priority when few signals present."""
    transcript = "Hello, how are you doing today?"
    result = await provider.extract(transcript, "insights")
    assert result["priority"] == "low"


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_extraction_type_defaults_to_full(provider):
    """Test that unknown extraction types fall back to full."""
    result = await provider.extract("Some transcript", "unknown_type")
    assert "contacts" in result
    assert "deals" in result


@pytest.mark.asyncio
async def test_entities_no_duplicates(provider):
    """Test that duplicate entities are not included."""
    transcript = "John Smith met with John Smith from Acme Corp."
    result = await provider.extract(transcript, "entities")
    assert result["people"].count("John Smith") == 1
