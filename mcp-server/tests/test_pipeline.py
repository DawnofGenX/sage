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
    """Verify all 4 stages are in the result, plus the pass accounting."""
    result = await pipeline.process(sample_transcript)

    assert "step1_entities" in result
    assert "step2_intent" in result
    assert "step3_record" in result
    assert "step4_derived" in result
    # Two logical passes; three requests, because pass 1 asks two questions.
    assert result["passes"] == 2
    assert result["llm_calls"] == 3


# ------------------------------------------------------------------
# Step 1: Entity extraction (a real pass-1 LLM call)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step1_entities_extracted(pipeline, sample_transcript):
    """Verify entities come from pass 1.

    These used to be derived from the stage-3 record, which is why stage 1
    could never disagree with stage 3. Now pass 1 asks for entities directly.
    """
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

    # Amounts and dates now come from pass 1's own extraction. The mock
    # renders the amount as the model saw it in the text ("$50,000") rather
    # than as a coerced numeric, which is the honest pass-1 shape.
    assert len(entities["amounts"]) > 0
    assert any("50,000" in str(a) or "50000" in str(a) for a in entities["amounts"])

    assert len(entities["dates"]) > 0
    assert any("January" in str(d) for d in entities["dates"])


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
# Step 4: Validation (local, not an inference)
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_step4_derived(pipeline, sample_transcript):
    """Verify the validation flag, under its honest name.

    Renamed from step4_validated: stage 4 is a local schema check, and
    "validated" read as though a fourth model call had judged the output.
    """
    result = await pipeline.process(sample_transcript)

    assert result["step4_derived"] is True
    assert result["derived_stages"] == [4]
    assert result["inferred_stages"] == [1, 2, 3]


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_transcript(pipeline):
    """Verify graceful handling of empty transcript."""
    result = await pipeline.process("")

    # All stages should still be present
    assert "step1_entities" in result
    assert "step2_intent" in result
    assert "step3_record" in result
    assert "step4_derived" in result

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
    assert result["step4_derived"] is True
