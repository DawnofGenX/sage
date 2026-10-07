"""Intelligence tools for Sage MCP server."""

from datetime import timedelta

from llm.provider import LLMProvider
from tools.common import _get_db
from tools.schemas import (
    DailyBriefing,
    DealInsights,
    FollowupsResponse,
    SearchResponse,
    WeeklyReview,
)

_provider = None


def _get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider


async def get_deal_insights(deal_id: int) -> DealInsights:
    """Get AI-powered insights for a specific deal.

    Args:
        deal_id: The deal ID to analyze.

    Returns:
        A dictionary with sentiment, risks, buying_signals, recommendation.
    """
    db = _get_db()
    provider = _get_provider()

    deal = db.get_deal(deal_id)
    if not deal:
        return {"error": "Deal not found"}

    # Get related call logs for context
    all_calls = db.get_call_logs()
    deal_calls = [c for c in all_calls if c.get("deal_id") == deal_id]

    # Build context from deal and calls
    context = f"Deal: {deal['title']}, Value: {deal.get('value')}, Stage: {deal.get('stage')}"
    if deal_calls:
        context += f". Recent call: {deal_calls[0].get('summary', 'No summary')}"

    # Use LLM to generate insights
    insights_result = await provider.extract(context, "insights")

    # Determine sentiment from deal or calls
    sentiment = deal.get("sentiment", "neutral")
    if not sentiment and deal_calls:
        sentiment = deal_calls[0].get("sentiment", "neutral")

    # Extract risks and buying signals from call logs
    risks = []
    buying_signals = []
    for call in deal_calls:
        call_risks = call.get("risks", "")
        if call_risks:
            risks.extend([r.strip() for r in call_risks.split(",") if r.strip()])
        call_signals = call.get("buying_signals", "")
        if call_signals:
            buying_signals.extend([s.strip() for s in call_signals.split(",") if s.strip()])

    # Generate recommendation
    stage = deal.get("stage", "lead")
    if stage == "won":
        recommendation = "Deal closed successfully. Focus on onboarding and upsell opportunities."
    elif stage == "lost":
        recommendation = "Deal lost. Analyze reasons and consider re-engagement in 3 months."
    elif stage == "negotiation":
        recommendation = "Final stage. Address any remaining concerns and close."
    elif stage == "proposal":
        recommendation = "Proposal sent. Follow up within 3-5 business days."
    else:
        recommendation = "Early stage. Continue qualification and build relationship."

    return {
        "deal_id": deal_id,
        "sentiment": sentiment,
        "risks": risks,
        "buying_signals": buying_signals,
        "recommendation": recommendation,
        "insights": insights_result.get("insights", []),
    }


async def get_daily_briefing() -> DailyBriefing:
    """Get a daily briefing with key metrics and action items.

    Returns:
        A dictionary with followups_due, total_deals, pipeline_value,
        stuck_deals, and insights.
    """
    db = _get_db()

    followups_due = db.get_followups_due()
    deals = db.get_all_deals()

    total_value = 0.0
    for deal in deals:
        value = deal.get("value")
        if value:
            try:
                total_value += float(value)
            except (ValueError, TypeError):
                pass

    stuck_deals = [d for d in deals if d.get("stage") in ("lead", "negotiation")]

    # Generate insights based on pipeline state
    insights = []
    if followups_due:
        insights.append(f"{len(followups_due)} follow-ups due today")
    if stuck_deals:
        insights.append(f"{len(stuck_deals)} deals may need attention")
    if not insights:
        insights.append("Pipeline is healthy. Focus on new outreach.")

    return {
        "followups_due": followups_due,
        "total_deals": len(deals),
        "pipeline_value": total_value,
        "stuck_deals": stuck_deals,
        "insights": insights,
    }


async def get_todays_followups() -> FollowupsResponse:
    """Get prioritized follow-ups for today.

    Returns:
        A dictionary with prioritized follow-ups.
    """
    db = _get_db()
    followups = db.get_followups_due()

    # Prioritize: deals with higher value get higher priority
    prioritized = []
    for followup in followups:
        priority = "medium"
        deal_id = followup.get("deal_id")
        if deal_id:
            deal = db.get_deal(deal_id)
            if deal and deal.get("value"):
                try:
                    value = float(deal["value"])
                    if value > 50000:
                        priority = "high"
                    elif value < 10000:
                        priority = "low"
                except (ValueError, TypeError):
                    pass

        prioritized.append({
            **followup,
            "priority": priority,
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    prioritized.sort(key=lambda x: priority_order.get(x.get("priority", "medium"), 1))

    return {
        "followups": prioritized,
        "total": len(prioritized),
    }


async def get_weekly_review() -> WeeklyReview:
    """Get a weekly review of sales activity.

    Returns:
        A dictionary with deals_moved, calls_made, followups_completed,
        pipeline_health, and weekly_summary.
    """
    db = _get_db()

    # Get all data
    deals = db.get_all_deals()
    calls = db.get_call_logs()
    followups = db.get_followups()

    # Calculate metrics
    deals_by_stage: dict[str, int] = {}
    for deal in deals:
        stage = deal.get("stage", "lead")
        deals_by_stage[stage] = deals_by_stage.get(stage, 0) + 1

    pipeline_value = 0.0
    for deal in deals:
        value = deal.get("value")
        if value:
            try:
                pipeline_value += float(value)
            except (ValueError, TypeError):
                pass

    completed_followups = [f for f in followups if f.get("completed")]

    # Generate summary
    summary_parts = []
    if calls:
        summary_parts.append(f"Made {len(calls)} calls")
    if completed_followups:
        summary_parts.append(f"Completed {len(completed_followups)} follow-ups")
    if deals:
        summary_parts.append(f"Managing {len(deals)} deals worth ${pipeline_value:,.0f}")

    weekly_summary = ". ".join(summary_parts) if summary_parts else "No activity recorded this week."

    return {
        "deals_moved": deals_by_stage,
        "calls_made": len(calls),
        "followups_completed": len(completed_followups),
        "pipeline_health": {
            "total_deals": len(deals),
            "pipeline_value": pipeline_value,
            "deals_by_stage": deals_by_stage,
        },
        "weekly_summary": weekly_summary,
    }


async def search_contacts(query: str) -> SearchResponse:
    """Search contacts by name, company, or email.

    Args:
        query: Search query string.

    Returns:
        A dictionary with matching contacts.
    """
    db = _get_db()
    contacts = db.search_contacts(query)

    return {
        "contacts": contacts,
        "total": len(contacts),
    }
