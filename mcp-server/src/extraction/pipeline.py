"""Multi-step extraction pipeline for sales call transcripts.

Processes transcripts through four stages:
  1. Entity extraction (people, companies, amounts, dates)
  2. Intent classification (new_lead, follow_up, deal_update, general)
  3. Structured record generation (contacts, deals, followups, sentiment, buying_signals, risks)
  4. Schema validation (ensure required fields exist, normalize data)
"""

from __future__ import annotations

from typing import Any

from llm.provider import LLMProvider


# Valid intent values
VALID_INTENTS = {"new_lead", "follow_up", "deal_update", "general"}

# Required fields for a structured record
REQUIRED_RECORD_FIELDS = {
    "contacts",
    "deals",
    "followups",
    "sentiment",
    "buying_signals",
    "risks",
}

# Required fields for entity extraction
REQUIRED_ENTITY_FIELDS = {"people", "companies", "amounts", "dates"}


class ExtractionPipeline:
    """Multi-step extraction pipeline that processes sales call transcripts.

    Takes an LLMProvider instance and runs four extraction steps:
    entity extraction, intent classification, record generation,
    and schema validation.
    """

    def __init__(self, provider: LLMProvider):
        """Initialize the pipeline with an LLM provider.

        Args:
            provider: An LLMProvider instance for making extraction calls.
        """
        self.provider = provider

    async def process(self, transcript: str) -> dict[str, Any]:
        """Process a transcript through all four extraction steps.

        Makes a single LLM call and derives all steps from the result.

        Args:
            transcript: The sales call transcript text.

        Returns:
            A dictionary with all four steps visible:
            {
                'step1_entities': {'people': [...], 'companies': [...], 'amounts': [...], 'dates': [...]},
                'step2_intent': 'new_lead',
                'step3_record': {'contacts': [...], 'deals': [...], 'followups': [...],
                                 'sentiment': '...', 'buying_signals': [...], 'risks': [...]},
                'step4_validated': True
            }
        """
        # Single LLM call for all extraction
        full_result = await self.provider.extract(transcript, "full")

        # Step 1: Derive entities from the full result
        step1_entities = self._derive_entities(full_result)

        # Step 2: Derive intent from the full result
        step2_intent = self._derive_intent(full_result)

        # Step 3: Derive record from the full result
        step3_record = self._derive_record(full_result)

        # Step 4: Schema validation
        step4_validated = self._validate(step3_record)

        return {
            "step1_entities": step1_entities,
            "step2_intent": step2_intent,
            "step3_record": step3_record,
            "step4_validated": step4_validated,
        }

    def _derive_entities(self, full_result: dict[str, Any]) -> dict[str, list[str]]:
        """Step 1: Derive entities (people, companies, amounts, dates) from full result.

        Args:
            full_result: The full extraction result from the LLM.

        Returns:
            A dictionary with keys 'people', 'companies', 'amounts', 'dates'.
        """
        contacts = full_result.get("contacts", [])
        deals = full_result.get("deals", [])
        followups = full_result.get("followups", [])

        people = [c.get("name", "") for c in contacts if c.get("name")]
        companies = [c.get("company", "") for c in contacts if c.get("company")]
        amounts = [str(d.get("value", "")) for d in deals if d.get("value") is not None]
        dates = [f.get("due_date") for f in followups if f.get("due_date")]

        return {"people": people, "companies": companies, "amounts": amounts, "dates": dates}

    def _derive_intent(self, full_result: dict[str, Any]) -> str:
        """Step 2: Derive intent from full result.

        Args:
            full_result: The full extraction result from the LLM.

        Returns:
            One of 'new_lead', 'follow_up', 'deal_update', or 'general'.
        """
        intent = full_result.get("intent", "general")
        if intent not in VALID_INTENTS:
            intent = "general"
        return intent

    def _derive_record(self, full_result: dict[str, Any]) -> dict[str, Any]:
        """Step 3: Derive structured CRM record from full result.

        Args:
            full_result: The full extraction result from the LLM.

        Returns:
            A dictionary with keys 'contacts', 'deals', 'followups',
            'sentiment', 'buying_signals', 'risks'.
        """
        record: dict[str, Any] = {}

        for field in ("contacts", "deals", "followups", "buying_signals", "risks"):
            value = full_result.get(field, [])
            if not isinstance(value, list):
                value = [value] if value else []
            record[field] = value

        sentiment = full_result.get("sentiment", {})
        if not isinstance(sentiment, dict):
            sentiment = {"sentiment": str(sentiment)}
        if "sentiment" not in sentiment:
            sentiment["sentiment"] = "neutral"
        record["sentiment"] = sentiment

        return record

    def _validate(self, record: dict[str, Any]) -> bool:
        """Step 4: Validate the structured record against the schema.

        Ensures all required fields exist and have the correct types.
        Normalizes data where possible.

        Args:
            record: The structured record to validate.

        Returns:
            True if the record is valid, False otherwise.
        """
        # Check all required fields are present
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record:
                return False

        # Validate list fields
        for field in ("contacts", "deals", "followups", "buying_signals", "risks"):
            if not isinstance(record[field], list):
                return False

        # Validate sentiment is a dict with required keys
        sentiment = record.get("sentiment")
        if not isinstance(sentiment, dict):
            return False
        if "sentiment" not in sentiment:
            return False
        if sentiment["sentiment"] not in ("positive", "neutral", "negative"):
            return False

        return True
