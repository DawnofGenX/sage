"""Pydantic output models for Sage MCP tools.

FastMCP publishes these models as JSON Schema so MCP clients get typed
output. Each model groups by the module that owns the tool. Record models
use ``model_config = ConfigDict(extra="allow")`` so an added field never
breaks a consumer.

Every model inherits ``_DictAccessMixin``, which makes a result readable as
``result["status"]`` / ``.get("id")`` / ``"k" in result``. Tool results are
consumed that way across the codebase and in every test that asserts on
output shape, while the *declared* return type must be the model — a bare
dict returned against a model annotation is what produced the
PydanticSerializationUnexpectedValue warnings. Both constraints hold at once
only because the models carry dict access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# extraction.py
# ---------------------------------------------------------------------------


class _DictAccessMixin(BaseModel):
    """Makes a model readable the way callers already read tool results.

    Tool results are consumed as dicts throughout the codebase —``result["status"]``,
    ``.get("id")``, ``step.get("result", {})`` — and by tests that assert on
    those shapes. Returning a bare dict satisfied that but left the declared
    ``-> SyncResult`` annotation a lie, which is why every call emitted a
    PydanticSerializationUnexpectedValue warning inside FastMCP's
    ``convert_result`` (fastmcp/tools/base.py:88 dumps the return against the
    *declared* type).

    Returning the model satisfies the annotation and is warning-free — verified
    byte-identical JSON — but breaks ``result["key"]``. This mixin keeps both:
    model typing for the declared schema, dict access for the call sites.

    Read-only deliberately. Tool results are outputs; nothing in the codebase
    mutates one after the fact, and allowing ``result["k"] = v`` would create a
    second, silent way for the declared schema and the payload to disagree.
    """

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            # Pydantic puts unknown keys here when extra="allow"; raising
            # KeyError rather than AttributeError keeps dict semantics honest.
            extras = self.model_extra or {}
            if key in extras:
                return extras[key]
            raise KeyError(key) from None

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: object) -> bool:
        """Mirror ``model_dump(exclude_unset=True)``, not the declared fields.

        Reporting a declared-but-unset field as present makes
        ``"error" in successful_sync`` True while the serialized payload carries
        no such key — the exact ambiguity the SyncResult contract exists to
        avoid (friction log entry 10: `error` was once declared required and
        broke every successful sync). Membership therefore tracks what the
        serializer would emit.
        """
        if not isinstance(key, str):
            return False
        if key in type(self).model_fields:
            return key in self.model_fields_set or key in (self.model_extra or {})
        return key in (self.model_extra or {})


class ProvenanceMixin(_DictAccessMixin):
    """Mixin that adds a provenance field to any tool response.

    Provenance tells the consumer exactly what produced the value — a real
    external system, a mock fallback, or nothing at all. See
    ``src/provenance.py`` for the full vocabulary.

    Also inherits dict access from ``_DictAccessMixin`` so a tool can declare
    ``-> SomeModel`` and callers can still subscript the result.
    """

    model_config = ConfigDict(extra="allow")

    provenance: str = Field(
        ...,
        description=(
            "What produced this value: 'local', 'salesforce', 'hubspot', "
            "'pipedrive', 'bedrock', 'openai', 'anthropic', 'mock', "
            "'replay', or 'none'."
        ),
    )


class ExtractionResult(ProvenanceMixin):
    """Output of ``extract_from_call`` — the two-pass extraction pipeline.

    Two real LLM passes run (entities + intent concurrently, then the
    structured record grounded in those findings), followed by a local schema
    check reported as stage 4.
    """

    step1_entities: dict = Field(
        ...,
        description="Entities extracted in pass 1 (people, companies, etc.).",
    )
    step2_intent: str = Field(
        ...,
        description="Call intent classification from pass 2.",
    )
    step3_record: dict = Field(
        ...,
        description="Structured CRM record grounded in passes 1 and 2.",
    )
    step4_derived: bool = Field(
        ...,
        description="Whether the local schema check (stage 4) passed.",
    )
    passes: int = Field(
        ...,
        description="Number of LLM passes that ran (always 2).",
    )
    llm_calls: int = Field(
        ...,
        description="Total LLM API calls made (passes + retries).",
    )
    inferred_stages: list[int] = Field(
        ...,
        description="Pipeline stages inferred from the transcript.",
    )
    derived_stages: list[int] = Field(
        ...,
        description="Pipeline stages derived from the schema check.",
    )


class ContactContext(_DictAccessMixin):
    """Output of ``get_contact_context`` — full context for a contact."""

    model_config = ConfigDict(extra="allow")

    contact: dict | None = Field(
        ...,
        description="The contact record, or None if not found.",
    )
    deals: list[dict] = Field(
        ...,
        description="Deals associated with this contact.",
    )
    history: list[dict] = Field(
        ...,
        description="Call and activity history for this contact.",
    )


class PipelineHealth(_DictAccessMixin):
    """Output of ``get_pipeline_health`` — pipeline metrics."""

    model_config = ConfigDict(extra="allow")

    deals_by_stage: dict[str, int] = Field(
        ...,
        description="Count of deals in each stage.",
    )
    stuck_deals: list[dict] = Field(
        ...,
        description="Deals that may be stuck (lead or negotiation).",
    )
    total_deals: int = Field(
        ...,
        description="Total number of deals in the pipeline.",
    )
    total_value: float = Field(
        ...,
        description="Total value of all deals in the pipeline.",
    )


# ---------------------------------------------------------------------------
# crud.py
# ---------------------------------------------------------------------------


class CreatedRecord(_DictAccessMixin):
    """Output of create_contact, create_deal, create_task, log_call, schedule_followup."""

    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="ID of the newly created record.")
    created: bool = Field(..., description="Always True on success.")


class UpdatedRecord(_DictAccessMixin):
    """Output of update_contact, update_deal_stage, schedule_followup."""

    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="ID of the updated record.")
    updated: bool = Field(..., description="Always True on success.")


class EmailDraft(_DictAccessMixin):
    """Output of ``draft_followup_email`` — LLM-generated or templated email."""

    model_config = ConfigDict(extra="allow")

    subject: str = Field(..., description="Email subject line.")
    body: str = Field(..., description="Email body text.")
    tone_used: str = Field(
        ...,
        description="Tone that was used (formal, friendly, casual).",
    )
    templated: bool = Field(
        ...,
        description="True if a deterministic template was used instead of the LLM.",
    )


# ---------------------------------------------------------------------------
# intelligence.py
# ---------------------------------------------------------------------------


class DailyBriefing(_DictAccessMixin):
    """Output of ``get_daily_briefing`` — key metrics and action items."""

    model_config = ConfigDict(extra="allow")

    followups_due: list[dict] = Field(..., description="Follow-ups due today.")
    total_deals: int = Field(..., description="Total deals in the pipeline.")
    pipeline_value: float = Field(..., description="Total pipeline value.")
    stuck_deals: list[dict] = Field(
        ...,
        description="Deals that may need attention.",
    )
    insights: list[str] = Field(..., description="Human-readable insights.")


class FollowupsResponse(_DictAccessMixin):
    """Output of ``get_todays_followups`` — prioritized follow-ups."""

    model_config = ConfigDict(extra="allow")

    followups: list[dict] = Field(..., description="Prioritized follow-up items.")
    total: int = Field(..., description="Total number of follow-ups.")


class WeeklyReview(_DictAccessMixin):
    """Output of ``get_weekly_review`` — weekly sales activity summary."""

    model_config = ConfigDict(extra="allow")

    deals_moved: dict[str, int] = Field(..., description="Deals by stage.")
    calls_made: int = Field(..., description="Number of calls made this week.")
    followups_completed: int = Field(
        ...,
        description="Follow-ups completed this week.",
    )
    pipeline_health: dict = Field(..., description="Pipeline health snapshot.")
    weekly_summary: str = Field(
        ...,
        description="Human-readable weekly summary.",
    )


class SearchResponse(_DictAccessMixin):
    """Output of ``search_contacts`` — contact search results."""

    model_config = ConfigDict(extra="allow")

    contacts: list[dict] = Field(..., description="Matching contacts.")
    total: int = Field(..., description="Total number of matches.")


class DealInsights(_DictAccessMixin):
    """Output of ``get_deal_insights`` — AI-powered deal analysis."""

    model_config = ConfigDict(extra="allow")

    deal_id: int = Field(..., description="The deal ID that was analyzed.")
    sentiment: str = Field(
        ...,
        description="Deal sentiment (positive, neutral, negative).",
    )
    risks: list[str] = Field(..., description="Identified risks.")
    buying_signals: list[str] = Field(..., description="Identified buying signals.")
    recommendation: str = Field(..., description="Recommended next action.")


# ---------------------------------------------------------------------------
# sync.py
# ---------------------------------------------------------------------------


class SyncResult(ProvenanceMixin):
    """Output of ``sync_to_crm`` — result of syncing to an external CRM.

    Every field except `status` is optional. The success path omits `error`
    entirely, so declaring it required (even as `str | None`) made FastMCP
    reject every successful sync with "'error' is a required property" —
    found by running the chained loop, not by any schema test.
    """

    model_config = ConfigDict(extra="allow")

    status: str = Field(
        ...,
        description=(
            "Sync status: 'success', 'already_synced', "
            "'not_configured', or 'error'."
        ),
    )
    target: str | None = Field(
        default=None, description="Target CRM system."
    )
    record_id: str | None = Field(
        default=None,
        description="ID of the record in the target CRM, or None if not synced.",
    )
    idempotency_key: str | None = Field(
        default=None, description="Idempotency key for this sync."
    )
    synced_at: str | None = Field(
        default=None,
        description="ISO timestamp of when the sync occurred, or None.",
    )
    error: str | None = Field(
        default=None, description="Error message if sync failed, or None."
    )


# ---------------------------------------------------------------------------
# expansion.py
# ---------------------------------------------------------------------------


class GenericRecord(_DictAccessMixin):
    """Fallback output model for expansion tools whose shape is not yet fixed.

    NOTE: an empty model with extra="allow" generates NO `properties`, so a
    tool annotated with it still publishes a bare
    `{"type": "object", "additionalProperties": true}` — the same schema the
    untyped `-> dict` produced. That is why each expansion tool now has its
    own model below instead of sharing this one. Kept only for tools whose
    response genuinely varies per query.
    """

    model_config = ConfigDict(extra="allow")


class CompanyContext(_DictAccessMixin):
    """Output of get_company_context."""

    model_config = ConfigDict(extra="allow")
    company: str | None = None
    contacts: list[dict[str, Any]] = []
    deals: list[dict[str, Any]] = []
    total_value: float = 0.0
    health: str | None = None


class ActivitiesResponse(_DictAccessMixin):
    """Output of get_activities."""

    model_config = ConfigDict(extra="allow")
    activities: list[dict[str, Any]] = []
    total: int = 0


class DealHistory(_DictAccessMixin):
    """Output of get_deal_history."""

    model_config = ConfigDict(extra="allow")
    deal: dict[str, Any] | None = None
    stage_history: list[dict[str, Any]] = []
    interactions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []


class TimelineEvent(_DictAccessMixin):
    """One entry in a deal's merged event stream."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., description="'stage_change' or 'activity'.")
    timestamp: str = Field(..., description="When the event was recorded.")
    data: dict[str, Any] = Field(default_factory=dict, description="Full source row.")


class TimelineResponse(_DictAccessMixin):
    """Output of get_deal_timeline_events."""

    model_config = ConfigDict(extra="allow")

    events: list[TimelineEvent] = Field(default_factory=list)
    count: int = Field(0, description="Number of events returned.")


class EnrichmentResponse(_DictAccessMixin):
    """Output of enrich_contact."""

    model_config = ConfigDict(extra="allow")
    contact: dict[str, Any] | None = None
    enriched: bool = False
    data: dict[str, Any] = {}


class ForecastResponse(_DictAccessMixin):
    """Output of get_forecast."""

    model_config = ConfigDict(extra="allow")
    forecast: list[dict[str, Any]] = []
    total_pipeline: float = 0.0
    weighted_forecast: float = 0.0
    best_case: float = 0.0
    worst_case: float = 0.0
    confidence: str | float | None = None
