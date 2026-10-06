"""Tests for the multi-step extraction pipeline."""

import os

import pytest


from extraction.pipeline import ExtractionPipeline
from llm.provider import LLMProvider


@pytest.fixture
def provider():
    """Create a provider in mock mode (no API key)."""
    return LLMProvider(api_key="", api_url="http://localhost:9999", model="test-model")


@pytest.fixture
def pipeline(provider):
    """Create an extraction pipeline with a mock provider."""
    return ExtractionPipeline(provider)


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
# Step presence tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_returns_all_steps(pipeline, sample_transcript):
    """Verify all 4 steps are in the result."""
    result = await pipeline.process(sample_transcript)

    assert "step1_entities" in result
    assert "step2_intent" in result
    assert "step3_record" in result
    assert "step4_validated" in result


# ------------------------------------------------------------------
# Step 1: Entity extraction
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_entities_extracted(pipeline, sample_transcript):
    """Verify entities are extracted."""
    result = await pipeline.process(sample_transcript)

    entities = result["step1_entities"]
    assert "people" in entities
    assert "companies" in entities
    assert "amounts" in entities
    assert "dates" in entities

    # Should find people
    assert len(entities["people"]) > 0
    assert "John Smith" in entities["people"]
    assert "Sarah Johnson" in entities["people"]

    # Should find companies
    assert len(entities["companies"]) > 0
    assert any("Acme" in c for c in entities["companies"])
    assert any("Globex" in c for c in entities["companies"])

    # Should find amounts (derived from deal values)
    assert len(entities["amounts"]) > 0
    assert "50000" in entities["amounts"]

    # Should find dates
    assert len(entities["dates"]) > 0
    assert any("January" in d for d in entities["dates"])


# ------------------------------------------------------------------
# Step 2: Intent classification
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step2_intent_classified(pipeline, sample_transcript):
    """Verify intent is classified."""
    result = await pipeline.process(sample_transcript)

    intent = result["step2_intent"]
    assert intent in ("new_lead", "follow_up", "deal_update", "general")


# ------------------------------------------------------------------
# Step 3: Record generation
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step3_record_generated(pipeline, sample_transcript):
    """Verify structured record is generated."""
    result = await pipeline.process(sample_transcript)

    record = result["step3_record"]
    assert "contacts" in record
    assert "deals" in record
    assert "followups" in record
    assert "sentiment" in record
    assert "buying_signals" in record
    assert "risks" in record

    # Should have contacts
    assert len(record["contacts"]) > 0
    assert any("John Smith" in c["name"] for c in record["contacts"])

    # Should have a deal with the amount
    assert len(record["deals"]) > 0
    assert record["deals"][0]["value"] == "50000"

    # Should have sentiment data
    assert record["sentiment"]["sentiment"] == "positive"

    # Should have buying signals
    assert len(record["buying_signals"]) > 0


# ------------------------------------------------------------------
# Step 4: Validation
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step4_validated(pipeline, sample_transcript):
    """Verify validation flag is True."""
    result = await pipeline.process(sample_transcript)

    assert result["step4_validated"] is True


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_transcript(pipeline):
    """Verify graceful handling of empty transcript."""
    result = await pipeline.process("")

    # All steps should still be present
    assert "step1_entities" in result
    assert "step2_intent" in result
    assert "step3_record" in result
    assert "step4_validated" in result

    # Entities should be empty lists
    entities = result["step1_entities"]
    assert entities["people"] == []
    assert entities["companies"] == []
    assert entities["amounts"] == []
    assert entities["dates"] == []

    # Intent should be general (no keywords matched)
    assert result["step2_intent"] == "general"

    # Record should have empty lists
    record = result["step3_record"]
    assert record["contacts"] == []
    assert record["deals"] == []
    assert record["followups"] == []
    assert record["buying_signals"] == []
    assert record["risks"] == []

    # Sentiment should be neutral
    assert record["sentiment"]["sentiment"] == "neutral"

    # Validation should still pass (all required fields present)
    assert result["step4_validated"] is True
