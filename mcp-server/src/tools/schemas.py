"""Pydantic output models for Sage MCP tools.

FastMCP publishes these models as JSON Schema so MCP clients get typed
output. Each model groups by the module that owns the tool. Record models
use ``model_config = ConfigDict(extra="allow")`` so an added field never
breaks a consumer.
"""

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# extraction.py
# ---------------------------------------------------------------------------


class ProvenanceMixin(BaseModel):
    """Mixin that adds a provenance field to any tool response.

    Provenance tells the consumer exactly what produced the value — a real
    external system, a mock fallback, or nothing at all. See
    ``src/provenance.py`` for the full vocabulary.
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


class ContactContext(BaseModel):
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


class PipelineHealth(BaseModel):
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


class CreatedRecord(BaseModel):
    """Output of create_contact, create_deal, create_task, log_call, schedule_followup."""

    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="ID of the newly created record.")
    created: bool = Field(..., description="Always True on success.")


class UpdatedRecord(BaseModel):
    """Output of update_contact, update_deal_stage, schedule_followup."""

    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="ID of the updated record.")
    updated: bool = Field(..., description="Always True on success.")


class EmailDraft(BaseModel):
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


class DailyBriefing(BaseModel):
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


class FollowupsResponse(BaseModel):
    """Output of ``get_todays_followups`` — prioritized follow-ups."""

    model_config = ConfigDict(extra="allow")

    followups: list[dict] = Field(..., description="Prioritized follow-up items.")
    total: int = Field(..., description="Total number of follow-ups.")


class WeeklyReview(BaseModel):
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


class SearchResponse(BaseModel):
    """Output of ``search_contacts`` — contact search results."""

    model_config = ConfigDict(extra="allow")

    contacts: list[dict] = Field(..., description="Matching contacts.")
    total: int = Field(..., description="Total number of matches.")


class DealInsights(BaseModel):
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
    """Output of ``sync_to_crm`` — result of syncing to an external CRM."""

    status: str = Field(
        ...,
        description=(
            "Sync status: 'success', 'already_synced', "
            "'not_configured', or 'error'."
        ),
    )
    target: str = Field(..., description="Target CRM system.")
    record_id: str | None = Field(
        ...,
        description="ID of the record in the target CRM, or None if not synced.",
    )
    idempotency_key: str = Field(
        ...,
        description="Idempotency key for this sync.",
    )
    synced_at: str | None = Field(
        ...,
        description="ISO timestamp of when the sync occurred, or None.",
    )
    error: str | None = Field(
        ...,
        description="Error message if sync failed, or None.",
    )


# ---------------------------------------------------------------------------
# expansion.py
# ---------------------------------------------------------------------------


class GenericRecord(BaseModel):
    """Fallback output model for expansion tools.

    Used by get_company_context, get_activities, get_deal_history,
    enrich_contact, and get_forecast. These tools return varied shapes;
    extra="allow" ensures forward compatibility.
    """

    model_config = ConfigDict(extra="allow")
