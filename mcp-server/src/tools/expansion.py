"""Expansion tools for Sage MCP server — adds 6 new tools (17-22)."""
from datetime import datetime, timedelta

from llm.provider import LLMProvider
from tools.common import _get_db
from tools.schemas import (
    ActivitiesResponse,
    CompanyContext,
    CreatedRecord,
    DealHistory,
    EnrichmentResponse,
    ForecastResponse,
    TimelineResponse,
)

_provider = None


def _get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider


async def get_company_context(company_name: str) -> CompanyContext:
    """Get full context for a company including all contacts, deals, and interactions.

    Args:
        company_name: The company name to look up.

    Returns:
        A dictionary with company, contacts, deals, total_value, and health.
    """
    db = _get_db()

    # Find all contacts at this company
    contacts = db.search_contacts(company_name)
    company_contacts = [c for c in contacts if c.get("company") == company_name]

    # Get all deals for these contacts
    all_deals = db.get_all_deals()
    contact_ids = {c["id"] for c in company_contacts}
    deals = [d for d in all_deals if d.get("contact_id") in contact_ids]

    # Calculate total value
    total_value = 0.0
    for deal in deals:
        value = deal.get("value")
        if value:
            try:
                total_value += float(value)
            except (ValueError, TypeError):
                pass

    # Determine health based on deal stages
    health = "unknown"
    if deals:
        won = sum(1 for d in deals if d.get("stage") == "won")
        lost = sum(1 for d in deals if d.get("stage") == "lost")
        active = len(deals) - won - lost
        if won > 0 and active == 0:
            health = "excellent"
        elif active > 0 and lost == 0:
            health = "good"
        elif lost > won:
            health = "at_risk"
        else:
            health = "fair"

    return CompanyContext.model_validate(
        {
            "company": company_name,
            "contacts": company_contacts,
            "deals": deals,
            "total_value": total_value,
            "health": health,
        }
    )


async def get_activities(contact_id: int = None, deal_id: int = None) -> ActivitiesResponse:
    """Get all activities filtered by contact and/or deal.

    Args:
        contact_id: Optional contact ID to filter by.
        deal_id: Optional deal ID to filter by.

    Returns:
        A dictionary with activities list and total count.
    """
    db = _get_db()
    activities = db.get_activities(contact_id=contact_id, deal_id=deal_id)

    return ActivitiesResponse.model_validate(
        {
            "activities": activities,
            "total": len(activities),
        }
    )


async def get_deal_history(deal_id: int) -> DealHistory:
    """Get the full history of a deal including stage progression, all interactions, and timeline.

    Args:
        deal_id: The deal ID to get history for.

    Returns:
        A dictionary with deal, stage_history, interactions, and timeline.
    """
    db = _get_db()

    deal = db.get_deal(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    stage_history = db.get_stage_history(deal_id)
    interactions = db.get_deal_interactions(deal_id)
    timeline = db.get_deal_timeline(deal_id)

    return DealHistory.model_validate(
        {
            "deal": deal,
            "stage_history": stage_history,
            "interactions": interactions,
            "timeline": timeline,
        }
    )


async def get_deal_timeline_events(deal_id: int) -> TimelineResponse:
    """Get a deal's merged event stream: stage changes and activities in order.

    Read-only view over the rows written by the event layer. stage_history and
    activities are append-only, so this ordering is durable history rather than
    a reconstruction from current state.

    Distinct from get_deal_history, which returns the three views separately:
    this returns one normalised, ordered stream with the source row attached,
    which is what a client rendering a timeline actually wants.

    Args:
        deal_id: The deal ID whose events to return.

    Returns:
        A dictionary with an ordered events list and its count.
    """
    db = _get_db()

    events = []
    for row in db.get_stage_history(deal_id):
        events.append(
            {
                "type": "stage_change",
                "timestamp": row.get("changed_at"),
                "data": row,
            }
        )
    for row in db.get_activities(deal_id=deal_id):
        events.append(
            {
                "type": "activity",
                "timestamp": row.get("created_at"),
                "data": row,
            }
        )

    # Oldest first: a timeline read bottom-to-top is the wrong way round.
    # Empty timestamps sort first rather than raising.
    events.sort(key=lambda e: e.get("timestamp") or "")

    return TimelineResponse.model_validate(
        {"events": events, "count": len(events)}
    )


async def create_task(
    contact_id: int,
    title: str,
    due_date: str = None,
    priority: str = "medium",
    notes: str = None,
) -> CreatedRecord:
    """Create a general task (broader than just follow-ups).

    Args:
        contact_id: Associated contact ID.
        title: Task title.
        due_date: Optional due date (ISO format string).
        priority: Task priority ('low', 'medium', 'high').
        notes: Optional notes.

    Returns:
        A dictionary with id, title, and created flag.
    """
    db = _get_db()
    data = {
        "contact_id": contact_id,
        "title": title,
        "due_date": due_date,
        "priority": priority,
        "notes": notes,
    }
    task_id = db.create_task(data)
    # Annotated -> CreatedRecord so FastMCP publishes a typed output schema;
    # a plain dict is returned at runtime so dict-style callers keep working.
    # This mirrors create_contact/create_deal in crud.py.
    return CreatedRecord.model_validate(
        {"id": task_id, "title": title, "created": True}
    )


async def enrich_contact(contact_id: int) -> EnrichmentResponse:
    """Enrich a contact with external data (LinkedIn, ZoomInfo, etc.).

    This is a mock implementation that returns realistic enrichment data.

    Args:
        contact_id: The contact ID to enrich.

    Returns:
        A dictionary with contact, enriched flag, and enrichment data.
    """
    db = _get_db()
    contact = db.get_contact(contact_id)
    if not contact:
        return {"error": "Contact not found"}

    # Mock enrichment data based on contact info
    name = contact.get("name", "Unknown")
    company = contact.get("company", "Unknown")
    title = contact.get("title", "")

    # Generate realistic mock enrichment data
    linkedin = f"https://linkedin.com/in/{name.lower().replace(' ', '-')}"
    company_size = "50-200"  # Mock size
    industry = "Technology"  # Mock industry

    # Use LLM provider for additional enrichment context
    provider = _get_provider()
    context = f"Contact: {name}, Title: {title}, Company: {company}"
    enrichment_result = await provider.extract(context, "entities")

    # Build enrichment data
    data = {
        "linkedin": linkedin,
        "company_size": company_size,
        "industry": industry,
        "enriched_at": datetime.now().isoformat(),
    }

    # Add any companies found by the LLM
    if isinstance(enrichment_result, dict) and "companies" in enrichment_result:
        if enrichment_result["companies"]:
            data["detected_companies"] = enrichment_result["companies"]

    return EnrichmentResponse.model_validate(
        {
            "contact": contact,
            "enriched": True,
            "data": data,
        }
    )


async def get_forecast(timeframe: str = "month") -> ForecastResponse:
    """Get revenue forecast based on pipeline.

    Args:
        timeframe: Forecast timeframe ('month', 'quarter', 'year').

    Returns:
        A dictionary with forecast, total_pipeline, weighted_forecast,
        best_case, worst_case, and confidence.
    """
    db = _get_db()
    deals = db.get_all_deals()

    # Filter to open deals only
    open_deals = [d for d in deals if d.get("stage") not in ("won", "lost")]

    # Calculate pipeline metrics
    total_pipeline = 0.0
    weighted_forecast = 0.0
    best_case = 0.0
    worst_case = 0.0

    # Stage-based probability weights
    stage_weights = {
        "lead": 0.1,
        "qualified": 0.25,
        "proposal": 0.5,
        "negotiation": 0.75,
    }

    forecast_items = []
    for deal in open_deals:
        value = deal.get("value", 0)
        if not value:
            continue
        try:
            value = float(value)
        except (ValueError, TypeError):
            continue

        stage = deal.get("stage", "lead")
        weight = stage_weights.get(stage, 0.1)

        total_pipeline += value
        weighted_forecast += value * weight
        best_case += value * min(weight + 0.2, 1.0)
        worst_case += value * max(weight - 0.2, 0.0)

        forecast_items.append({
            "deal_id": deal["id"],
            "title": deal.get("title", ""),
            "value": value,
            "stage": stage,
            "probability": weight,
            "weighted_value": value * weight,
        })

    # Calculate confidence based on number of deals and data quality
    confidence = "low"
    if len(open_deals) >= 5:
        confidence = "medium"
    if len(open_deals) >= 10:
        confidence = "high"

    # Adjust for timeframe
    timeframe_multiplier = {"month": 1.0, "quarter": 3.0, "year": 12.0}
    multiplier = timeframe_multiplier.get(timeframe, 1.0)

    return ForecastResponse.model_validate(
        {
            "forecast": forecast_items,
            "total_pipeline": total_pipeline,
            "weighted_forecast": weighted_forecast * multiplier,
            "best_case": best_case * multiplier,
            "worst_case": worst_case * multiplier,
            "confidence": confidence,
        }
    )
