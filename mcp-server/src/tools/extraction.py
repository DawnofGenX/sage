"""Extraction tools for Sage MCP server."""
from aws.s3 import S3Storage
from extraction.pipeline import ExtractionPipeline
from llm.provider import LLMProvider
from tools.common import _get_db
from tools.schemas import ContactContext, ExtractionResult, PipelineHealth

_pipeline = None
_s3 = None


def _get_pipeline() -> ExtractionPipeline:
    global _pipeline
    if _pipeline is None:
        provider = LLMProvider()
        _pipeline = ExtractionPipeline(provider)
    return _pipeline


def _get_s3() -> S3Storage:
    global _s3
    if _s3 is None:
        _s3 = S3Storage()
    return _s3


async def extract_from_call(transcript: str, audio_url: str | None = None) -> ExtractionResult:
    """Process a call transcript through the two-pass extraction pipeline.

    Two real LLM passes run (entities + intent concurrently, then the
    structured record grounded in those findings), followed by a local schema
    check reported as stage 4. See extraction/pipeline.py for why stage 4 is
    named `step4_derived`.

    Args:
        transcript: The sales call transcript text.
        audio_url: Optional S3 URL of the call recording. If provided, the
            recording is fetched from S3 and can be used for additional
            processing (e.g., duration estimation).

    Returns:
        A dictionary with the four stages plus the pass accounting:
        step1_entities, step2_intent, step3_record, step4_derived,
        passes (2), llm_calls (3), inferred_stages, derived_stages, provenance.
    """
    pipeline = _get_pipeline()

    # If audio_url is provided, fetch the recording from S3
    if audio_url:
        s3 = _get_s3()
        # Extract the S3 key from the URL
        key = _extract_s3_key(audio_url)
        if key:
            audio_data = s3.get_recording(key)
            if audio_data:
                # Estimate duration from audio size (rough heuristic)
                # In production, this would use proper audio analysis
                estimated_duration = len(audio_data) // 16000  # ~16KB per second for MP3
                if estimated_duration > 0:
                    transcript = f"[Duration: ~{estimated_duration}s] {transcript}"

    return ExtractionResult.model_validate(await pipeline.process(transcript))


def _extract_s3_key(audio_url: str) -> str | None:
    """Extract the S3 object key from an S3 URL.

    Supports both virtual-hosted-style and path-style S3 URLs.
    """
    if not audio_url:
        return None

    # Virtual-hosted-style: https://bucket.s3.region.amazonaws.com/key
    if ".s3." in audio_url:
        parts = audio_url.split(".s3.", 1)
        if len(parts) == 2:
            remainder = parts[1]
            # Remove region prefix if present
            if ".amazonaws.com/" in remainder:
                key = remainder.split(".amazonaws.com/", 1)[1]
            else:
                key = remainder
            return key

    # Path-style: https://s3.region.amazonaws.com/bucket/key
    if "s3." in audio_url and ".amazonaws.com/" in audio_url:
        parts = audio_url.split(".amazonaws.com/", 1)
        if len(parts) == 2:
            # Remove bucket name (first path segment)
            path = parts[1]
            segments = path.split("/", 1)
            if len(segments) == 2:
                return segments[1]

    # File URL fallback (local storage)
    if audio_url.startswith("file://"):
        return audio_url.replace("file://", "")

    return None


async def get_contact_context(
    name: str,
    include_history: bool = True,
    include_deals: bool = True,
) -> ContactContext:
    """Search for a contact by name and return full context.

    Args:
        name: The contact name to search for.
        include_history: Whether to include call history.
        include_deals: Whether to include associated deals.

    Returns:
        A dictionary with contact, deals, history, and activities.

        `history` and `activities` carry the same call/activity records. The
        schema declares both because that is what a consumer of this tool has
        always read (the field was required while the tool returned only
        `activities`, so every call failed validation once the return stopped
        being a bare dict). Both are emitted so neither reader breaks.
    """
    db = _get_db()
    contacts = db.search_contacts(name)

    if not contacts:
        return ContactContext.model_validate(
            {"contact": None, "deals": [], "history": [], "activities": []}
        )

    contact = contacts[0]
    contact_id = contact["id"]

    deals = []
    if include_deals:
        all_deals = db.get_all_deals()
        deals = [d for d in all_deals if d.get("contact_id") == contact_id]

    activities = []
    if include_history:
        activities = db.get_contact_activities(contact_id)

    return ContactContext.model_validate(
        {
            "contact": contact,
            "deals": deals,
            "history": activities,
            "activities": activities,
        }
    )


async def get_pipeline_health(
    timeframe: str = "week",
    include_sentiment: bool = True,
) -> PipelineHealth:
    """Get pipeline health metrics.

    Args:
        timeframe: Time window for metrics ('week', 'month', 'quarter').
        include_sentiment: Whether to include sentiment analysis.

    Returns:
        A dictionary with deals_by_stage, stuck_deals, total_deals, total_value.
    """
    db = _get_db()
    deals = db.get_all_deals()

    deals_by_stage: dict[str, int] = {}
    total_value = 0.0
    stuck_deals = []

    for deal in deals:
        stage = deal.get("stage", "lead")
        deals_by_stage[stage] = deals_by_stage.get(stage, 0) + 1

        value = deal.get("value")
        if value:
            try:
                total_value += float(value)
            except (ValueError, TypeError):
                pass

        # A deal is "stuck" if it's been in the same stage for a while
        # For mock purposes, consider deals in 'lead' or 'negotiation' as potentially stuck
        if stage in ("lead", "negotiation"):
            stuck_deals.append(deal)

    result = {
        "deals_by_stage": deals_by_stage,
        "stuck_deals": stuck_deals,
        "total_deals": len(deals),
        "total_value": total_value,
    }

    if include_sentiment:
        sentiments = {}
        for deal in deals:
            s = deal.get("sentiment", "unknown")
            sentiments[s] = sentiments.get(s, 0) + 1
        result["sentiments"] = sentiments

    return PipelineHealth.model_validate(result)
