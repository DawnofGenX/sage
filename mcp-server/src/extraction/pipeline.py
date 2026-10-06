"""Two-pass extraction pipeline for sales call transcripts.

Processes a transcript in TWO real LLM passes:

  Pass 1 (concurrent)   entities + intent   — two independent requests
  Pass 2                structured record   — grounded in pass-1 output
  Stage 4               local schema validation, NOT an inference

Honesty note — why this shape:
    This module previously made ONE LLM call (extract(transcript, "full"))
    and reshaped that single response into four "stages". Its own docstring
    said so: "Makes a single LLM call and derives all steps from the result."
    Meanwhile the project docs advertised a four-step extraction pipeline.

    Rather than keep a claim the code did not support, the pipeline now does
    what it says: two genuine inference passes, with the fourth stage reported
    as `step4_derived`. The result carries `passes`, `inferred_stages`, and
    `derived_stages` so a consumer can tell which stages involved a model and
    which were local arithmetic — without reading this docstring.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol, runtime_checkable


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


@runtime_checkable
class SupportsExtraction(Protocol):
    """What the pipeline needs from a provider.

    A Protocol rather than a concrete LLMProvider so tests can supply a
    counting double, and so any future provider (Bedrock, a queue, a cache)
    can be dropped in without inheriting from LLMProvider.
    """

    last_provenance: str
    call_count: int

    async def extract(self, transcript: str, extraction_type: str) -> Any: ...


class ExtractionPipeline:
    """Two-pass extraction pipeline for sales call transcripts.

    Args:
        provider: Anything implementing SupportsExtraction.
    """

    def __init__(self, provider: SupportsExtraction):
        self.provider = provider

    async def process(self, transcript: str) -> dict[str, Any]:
        """Process a transcript through two LLM passes plus local validation.

        Returns:
            {
              'step1_entities': {'people', 'companies', 'amounts', 'dates'},
              'step2_intent': str,
              'step3_record': {'contacts', 'deals', 'followups', 'sentiment',
                               'buying_signals', 'risks'},
              'step4_derived': bool,     # local validation, not inference
              'passes': 2,               # real LLM calls made
              'inferred_stages': [1, 2, 3],
              'derived_stages': [4],
              'provenance': str,         # 'mock' | 'openai' | 'anthropic' | 'bedrock'
            }
        """
        # --- Pass 1: entities and intent are independent, so overlap them. ---
        entities_raw, intent_raw = await asyncio.gather(
            self.provider.extract(transcript, "entities"),
            self.provider.extract(transcript, "intent"),
        )

        step1_entities = self._normalize_entities(entities_raw)
        step2_intent = self._normalize_intent(intent_raw)

        # --- Pass 2: generate the record, grounded in what pass 1 found. ---
        grounding = self._build_grounding(transcript, step1_entities, step2_intent)
        full_result = await self.provider.extract(grounding, "full")
        step3_record = self._derive_record(full_result)

        # --- Stage 4: local schema validation. Not a model call. ---
        step4_derived = self._validate(step3_record)

        return {
            "step1_entities": step1_entities,
            "step2_intent": step2_intent,
            "step3_record": step3_record,
            "step4_derived": step4_derived,
            # Two logical passes: pass 1 (entities + intent, issued
            # concurrently) and pass 2 (the record). That is three HTTP
            # requests, because pass 1 asks two independent questions.
            # Both numbers are reported so no consumer has to guess which
            # one "passes" refers to — the two-pass/four-stage wording in
            # the docs has already cost one overstatement.
            "passes": 2,
            "llm_calls": 3,
            "inferred_stages": [1, 2, 3],
            "derived_stages": [4],
            "provenance": getattr(self.provider, "last_provenance", "unknown"),
        }

    # ------------------------------------------------------------------
    # Pass 1 helpers
    # ------------------------------------------------------------------

    def _normalize_entities(self, raw: Any) -> dict[str, list[str]]:
        """Coerce pass-1 entity output into the four expected list fields."""
        if not isinstance(raw, dict):
            return {field: [] for field in REQUIRED_ENTITY_FIELDS}
        result: dict[str, list[Any]] = {}
        for field in REQUIRED_ENTITY_FIELDS:
            value = raw.get(field, [])
            if not isinstance(value, list):
                value = [value] if value else []
            result[field] = value
        return result

    def _normalize_intent(self, raw: Any) -> str:
        """Pass 1 may return a bare label or a dict; accept both."""
        if isinstance(raw, dict):
            raw = raw.get("intent", "general")
        if not isinstance(raw, str) or raw not in VALID_INTENTS:
            return "general"
        return raw

    def _build_grounding(
        self, transcript: str, entities: dict[str, list[Any]], intent: str
    ) -> str:
        """Compose pass 2's input: the transcript plus pass-1 findings.

        Grounding matters: without it pass 1 is decorative, since nothing it
        found would constrain the record. The transcript is included so pass 2
        still sees the source material.
        """
        return (
            "Extract the CRM record for this sales call.\n\n"
            "Original transcript:\n"
            f"{transcript}\n\n"
            "Findings from a prior analysis pass (treat as authoritative; do "
            "not contradict them):\n"
            f"{json.dumps({'entities': entities, 'intent': intent}, indent=2)}"
        )

    # ------------------------------------------------------------------
    # Pass 2 helpers
    # ------------------------------------------------------------------

    def _derive_record(self, full_result: Any) -> dict[str, Any]:
        """Normalize pass-2 output into the canonical record shape."""
        if not isinstance(full_result, dict):
            full_result = {}
        record: dict[str, Any] = {}

        for field in ("contacts", "deals", "followups", "buying_signals", "risks"):
            value = full_result.get(field, [])
            if not isinstance(value, list):
                value = [value] if value else []
            record[field] = value

        sentiment = full_result.get("sentiment", {})
        if isinstance(sentiment, str):
            sentiment = {"sentiment": sentiment}
        if not isinstance(sentiment, dict):
            sentiment = {"sentiment": "neutral"}
        sentiment.setdefault("sentiment", "neutral")
        record["sentiment"] = sentiment

        return record

    # ------------------------------------------------------------------
    # Stage 4 — local, no LLM
    # ------------------------------------------------------------------

    def _validate(self, record: dict[str, Any]) -> bool:
        """Validate the record against the schema.

        Pure local check: this is stage 4, derived rather than inferred, and is
        reported as `step4_derived` so it is never read as a model judgement.
        """
        for field in REQUIRED_RECORD_FIELDS:
            if field not in record:
                return False

        for field in ("contacts", "deals", "followups", "buying_signals", "risks"):
            if not isinstance(record[field], list):
                return False

        sentiment = record.get("sentiment")
        if not isinstance(sentiment, dict):
            return False
        if "sentiment" not in sentiment:
            return False
        if sentiment["sentiment"] not in ("positive", "neutral", "negative"):
            return False

        return True