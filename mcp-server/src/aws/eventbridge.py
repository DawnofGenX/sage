"""EventBridge-backed proactive trigger scheduling with in-process fallback.

Wraps Amazon EventBridge for scheduling proactive insight triggers.
Falls back to in-process scheduling when AWS credentials are not available.

EventBridge Rule Patterns:
    Rule: sage-daily-insights
        Schedule: cron(0 9 * * ? *) — Every day at 9 AM UTC
        Target: Lambda function generating daily sales insights

    Rule: sage-overdue-followups
        Schedule: cron(0 */4 * * ? *) — Every 4 hours
        Target: Lambda function checking for overdue follow-ups

    Rule: sage-stale-deal-alert
        Schedule: cron(0 12 ? * MON *) — Every Monday at noon
        Target: Lambda function identifying stale deals

    Rule: sage-call-summary
        Event Pattern: Triggered after each call recording is processed
        Target: Lambda function generating call summaries

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-1)
    EVENTBRIDGE_BUS: EventBridge bus name (default: default)
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any


class EventBridgeTriggers:
    """EventBridge-backed trigger scheduling with in-process fallback.

    Schedules proactive insight generation using EventBridge rules
    when AWS credentials are available, otherwise uses in-process tracking.
    """

    def __init__(
        self,
        region: str | None = None,
        bus_name: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
    ):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.bus_name = bus_name or os.environ.get("EVENTBRIDGE_BUS", "default")
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self._use_fallback = not (self.aws_access_key and self.aws_secret_key)
        self._client = None
        self._fallback_rules: dict[str, dict] = {}

    @property
    def is_fallback(self) -> bool:
        """Return True if using in-process fallback (no AWS credentials)."""
        return self._use_fallback

    def _get_client(self):
        """Lazy-initialize the EventBridge client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "events",
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                )
            except ImportError:
                raise RuntimeError(
                    "boto3 is required for EventBridge integration. "
                    "Install with: pip install boto3"
                )
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def schedule_insight(self, name: str, schedule: str, payload: dict) -> str:
        """Schedule a proactive insight trigger.

        Args:
            name: Rule name (e.g., "sage-daily-insights").
            schedule: Schedule expression (e.g., "cron(0 9 * * ? *)" or "rate(1 day)").
            payload: Event payload to pass to the target.

        Returns:
            The rule ARN (or rule ID in fallback mode).
        """
        if self._use_fallback:
            return self._fallback_schedule(name, schedule, payload)

        try:
            client = self._get_client()
            response = client.put_rule(
                Name=name,
                ScheduleExpression=schedule,
                State="ENABLED",
                Description=f"Sage proactive insight trigger: {name}",
                EventBusName=self.bus_name,
            )
            rule_arn = response["RuleArn"]

            # Put target (Lambda function)
            client.put_targets(
                Rule=name,
                Targets=[
                    {
                        "Id": f"{name}-target",
                        "Arn": payload.get("target_arn", ""),
                        "Input": json.dumps(payload),
                    }
                ],
            )
            return rule_arn
        except Exception:
            return self._fallback_schedule(name, schedule, payload)

    def list_rules(self) -> list:
        """List all EventBridge rules on the Sage bus.

        Returns:
            List of rule dictionaries with name, schedule, state, and ARN.
        """
        if self._use_fallback:
            return self._fallback_list()

        try:
            client = self._get_client()
            response = client.list_rules(
                EventBusName=self.bus_name,
            )
            rules = []
            for rule in response.get("Rules", []):
                rules.append({
                    "name": rule.get("Name", ""),
                    "schedule": rule.get("ScheduleExpression", ""),
                    "state": rule.get("State", ""),
                    "arn": rule.get("Arn", ""),
                    "description": rule.get("Description", ""),
                })
            return rules
        except Exception:
            return []

    def delete_rule(self, name: str) -> bool:
        """Delete an EventBridge rule.

        Args:
            name: The rule name to delete.

        Returns:
            True if the rule was deleted successfully.
        """
        if self._use_fallback:
            return self._fallback_delete(name)

        try:
            client = self._get_client()
            # First remove targets
            try:
                targets = client.list_targets_by_rule(
                    Rule=name,
                    EventBusName=self.bus_name,
                )
                target_ids = [t["Id"] for t in targets.get("Targets", [])]
                if target_ids:
                    client.remove_targets(
                        Rule=name,
                        Ids=target_ids,
                        EventBusName=self.bus_name,
                    )
            except Exception:
                pass

            client.delete_rule(
                Name=name,
                EventBusName=self.bus_name,
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # In-Process Fallback
    # ------------------------------------------------------------------

    def _fallback_schedule(self, name: str, schedule: str, payload: dict) -> str:
        """Store rule in in-process fallback."""
        rule_id = str(uuid.uuid4())
        self._fallback_rules[name] = {
            "id": rule_id,
            "name": name,
            "schedule": schedule,
            "payload": payload,
            "state": "ENABLED",
            "created_at": datetime.now().isoformat(),
            "arn": f"arn:aws:events:{self.region}:000000000000:rule/{self.bus_name}/{name}",
        }
        return rule_id

    def _fallback_list(self) -> list:
        """List rules from in-process fallback."""
        return list(self._fallback_rules.values())

    def _fallback_delete(self, name: str) -> bool:
        """Delete rule from in-process fallback."""
        if name in self._fallback_rules:
            del self._fallback_rules[name]
            return True
        return False

