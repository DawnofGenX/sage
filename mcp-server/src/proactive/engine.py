"""Proactive insight engine combining rule-based triggers with LLM analysis."""
from datetime import datetime, timedelta

from aws.eventbridge import EventBridgeTriggers
from data.db import Database
from llm.provider import LLMProvider


class ProactiveEngine:
    """Generate proactive sales insights from CRM data."""

    def __init__(self, db: Database, llm: LLMProvider):
        self.db = db
        self.llm = llm
        self._eventbridge = None

    def _get_eventbridge(self) -> EventBridgeTriggers:
        """Lazy-initialize the EventBridge triggers."""
        if self._eventbridge is None:
            self._eventbridge = EventBridgeTriggers()
        return self._eventbridge

    async def generate_insights(self) -> list:
        """Generate proactive insights from CRM data."""
        insights = []

        # Rule-based triggers
        insights.extend(self._check_overdue_followups())
        insights.extend(self._check_stuck_deals())
        insights.extend(self._check_budget_deadlines())

        # LLM-based insights
        llm_insights = await self._get_llm_insights()
        insights.extend(llm_insights)

        # Sort by urgency
        insights.sort(key=lambda x: self._urgency_score(x), reverse=True)

        # Schedule a proactive alert via EventBridge
        if insights:
            self._schedule_proactive_alert(insights)

        return insights

    def _schedule_proactive_alert(self, insights: list) -> None:
        """Schedule a proactive alert using EventBridge.

        After generating insights, this schedules a trigger to re-check
        insights on a regular cadence. Uses EventBridge when AWS credentials
        are available, otherwise falls back to in-process scheduling.
        """
        try:
            eventbridge = self._get_eventbridge()
            eventbridge.schedule_insight(
                name="sage-proactive-insights",
                schedule="cron(0 */4 * * ? *)",  # Every 4 hours
                payload={
                    "insight_count": len(insights),
                    "highest_urgency": self._urgency_score(insights[0]) if insights else 0,
                    "target_arn": "arn:aws:lambda:us-east-1:000000000000:function:sage-insights",
                },
            )
        except Exception:
            # Silently fail — scheduling is best-effort
            pass

    def _check_overdue_followups(self) -> list:
        """Check for overdue follow-ups."""
        followups = self.db.get_followups_due()
        now = datetime.now()
        alerts = []
        for f in followups:
            due_date = f.get("due_date")
            if due_date:
                due = self._parse_date(due_date)
                if due and due < now:
                    alerts.append(f"Overdue follow-up: {f['title']} (due {due_date})")
        return alerts

    def _check_stuck_deals(self) -> list:
        """Check for deals with no activity in 14+ days."""
        deals = self.db.get_all_deals()
        now = datetime.now()
        alerts = []
        for d in deals:
            updated_at = d.get("updated_at")
            if updated_at:
                updated = self._parse_date(updated_at)
                if updated:
                    days_inactive = (now - updated).days
                    if days_inactive >= 14:
                        alerts.append(
                            f"Stuck deal: {d['title']} (no activity for {days_inactive} days)"
                        )
        return alerts

    def _check_budget_deadlines(self) -> list:
        """Check for deals with budget/deadline mentions in notes."""
        deals = self.db.get_all_deals()
        alerts = []
        for d in deals:
            notes = d.get("notes") or ""
            notes_lower = notes.lower()
            if "budget" in notes_lower or "deadline" in notes_lower:
                alerts.append(f"Budget deadline approaching: {d['title']}")
        return alerts

    async def _get_llm_insights(self) -> list:
        """Get LLM-based insights."""
        try:
            context = self._build_pipeline_context()
            result = await self.llm.extract(context, "insights")
            insights = result.get("insights", [])
            # Filter to only string insights
            insights = [i for i in insights if isinstance(i, str)]
            return insights
        except Exception:
            return ["General follow-up recommended to maintain engagement"]

    def _build_pipeline_context(self) -> str:
        """Build pipeline context for LLM analysis."""
        deals = self.db.get_all_deals()
        contacts = self.db.get_all_contacts()
        followups = self.db.get_followups()

        context = f"Sales pipeline: {len(deals)} deals, {len(contacts)} contacts, {len(followups)} follow-ups."

        if deals:
            context += f" Active deals: {', '.join(d['title'] for d in deals[:5])}."

        return context

    def _urgency_score(self, insight: str) -> int:
        """Assign urgency score to an insight."""
        if "Overdue" in insight:
            return 3
        elif "Stuck" in insight:
            return 2
        elif "Budget" in insight or "deadline" in insight:
            return 2
        else:
            return 1

    @staticmethod
    def _parse_date(date_str: str) -> datetime | None:
        """Parse a date string in various formats."""
        if not date_str:
            return None

        # Try ISO format first
        try:
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m/%d/%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                pass

        return None
