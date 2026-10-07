"""Demo flow — chained MCP tool calls with honest halting.

This module implements the five-step agentic demo chain. Each step consumes
the previous step's response; nothing is hardcoded. If extraction yields no
contacts, the chain halts immediately rather than inventing data.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from client.chained import SageMCPClient


class DemoFlowResult(BaseModel):
    """Output of run_agentic_loop — the result of the chained demo flow.

    FastMCP publishes this as a typed JSON Schema so clients get structured
    output. The model has declared fields (not just extra="allow") to avoid
    the empty-schema trap documented in tools/schemas.py.
    """

    model_config = ConfigDict(extra="allow")

    status: str = Field(
        ...,
        description="Flow status: 'success' or 'incomplete'.",
    )
    completed_steps: int = Field(
        ...,
        description="Number of steps that completed before the chain halted or finished.",
    )
    synced_record_id: str | None = Field(
        None,
        description="ID of the record in the target CRM, or None if not synced.",
    )
    steps: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recorded steps with timing and provenance metadata.",
    )
    reason: str | None = Field(
        None,
        description="Reason for halting, if the flow is incomplete.",
    )


async def run_agentic_loop(
    transcript: str,
    server: str = "http://localhost:8000/mcp",
    target: str = "local",
) -> DemoFlowResult:
    """Run the five-step agentic demo chain.

    Each step consumes the previous step's response. The chain halts honestly
    when extraction yields no contacts or when any step errors — it never
    invents data to keep moving.

    Steps:
        1. extract_from_call(transcript) → read step3_record.contacts[0]
        2. create_contact(name, company, email) → read returned id
        3. create_deal(contact_id, title, value, stage) → read returned id
        4. schedule_followup(contact_id, deal_id, title, due_date)
        5. sync_to_crm(record, target, idempotency_key=f"chain-{deal_id}")

    Args:
        transcript: The sales call transcript text.
        server: MCP server URL.
        target: Target CRM system ('local', 'salesforce', 'hubspot', 'pipedrive').

    Returns:
        DemoFlowResult with status, completed_steps, synced_record_id, steps, and reason.
    """
    steps: list[dict[str, Any]] = []

    async with SageMCPClient(server) as client:
        # ── Step 1: Extract from call ──────────────────────────────────────
        try:
            step1 = await client.call_recorded(
                "extract_from_call", {"transcript": transcript}
            )
            steps.append(step1)
        except Exception as exc:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=0,
                reason=f"extract_from_call failed: {exc}",
                steps=steps,
            )

        # Check for contacts — halt if none extracted
        contacts = (
            step1.get("result", {}).get("step3_record", {}).get("contacts", [])
        )
        if not contacts:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=1,
                reason="no contacts extracted",
                steps=steps,
            )

        contact = contacts[0]

        # ── Step 2: Create contact ─────────────────────────────────────────
        contact_args: dict[str, Any] = {
            "name": contact.get("name", ""),
            "company": contact.get("company", ""),
        }
        if contact.get("email") is not None:
            contact_args["email"] = contact["email"]

        try:
            step2 = await client.call_recorded(
                "create_contact",
                contact_args,
            )
            steps.append(step2)
        except Exception as exc:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=1,
                reason=f"create_contact failed: {exc}",
                steps=steps,
            )

        contact_id = step2.get("result", {}).get("id")
        if contact_id is None:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=2,
                reason="create_contact returned no id",
                steps=steps,
            )

        # Get deal data from extraction
        deals = step1.get("result", {}).get("step3_record", {}).get("deals", [])
        if not deals:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=2,
                reason="no deals extracted",
                steps=steps,
            )

        deal = deals[0]

        # ── Step 3: Create deal ───────────────────────────────────────────
        try:
            step3 = await client.call_recorded(
                "create_deal",
                {
                    "contact_id": contact_id,
                    "title": deal.get("title", ""),
                    "value": deal.get("value"),
                    "stage": deal.get("stage", "lead"),
                },
            )
            steps.append(step3)
        except Exception as exc:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=2,
                reason=f"create_deal failed: {exc}",
                steps=steps,
            )

        deal_id = step3.get("result", {}).get("id")
        if deal_id is None:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=3,
                reason="create_deal returned no id",
                steps=steps,
            )

        # Get followup data from extraction
        # A missing follow-up is NOT an error: plenty of calls end without one
        # being agreed. A generic follow-up is always schedulable, so fall back
        # to one rather than aborting a chain that has already created a real
        # contact and deal. Halting here previously left the chain at step 3 on
        # any transcript without an explicit follow-up, which is most of them.
        followups = (
            step1.get("result", {}).get("step3_record", {}).get("followups", [])
        )
        followup = followups[0] if followups else {}

        # ── Step 4: Schedule followup ──────────────────────────────────────
        try:
            step4 = await client.call_recorded(
                "schedule_followup",
                {
                    "contact_id": contact_id,
                    "deal_id": deal_id,
                    "title": followup.get("title", ""),
                    "due_date": followup.get("due_date"),
                },
            )
            steps.append(step4)
        except Exception as exc:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=3,
                reason=f"schedule_followup failed: {exc}",
                steps=steps,
            )

        # ── Step 5: Sync to CRM ────────────────────────────────────────────
        try:
            step5 = await client.call_recorded(
                "sync_to_crm",
                {
                    "record": {
                        "title": deal.get("title", ""),
                        "value": deal.get("value"),
                        "stage": deal.get("stage", "lead"),
                        "contact_id": contact_id,
                    },
                    "target": target,
                    "idempotency_key": f"chain-{deal_id}",
                },
            )
            steps.append(step5)
        except Exception as exc:
            return DemoFlowResult(
                status="incomplete",
                completed_steps=4,
                reason=f"sync_to_crm failed: {exc}",
                steps=steps,
            )

        synced_record_id = step5.get("result", {}).get("record_id")

        return DemoFlowResult(
            status="success",
            completed_steps=5,
            synced_record_id=synced_record_id,
            steps=steps,
        )
