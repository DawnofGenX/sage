"""Sync tool for Sage MCP server with real CRM adapters."""

from datetime import datetime, timezone

from sync import SalesforceSync, HubSpotSync, PipedriveSync, LocalCRMSync

from tools.schemas import SyncResult

# "local" is Sage's own CRM tables. It is always available — there are no
# credentials to configure — so it is the target the demo uses when no external
# CRM is set up. It is a real implementation with real stored rows, not a stub.
VALID_TARGETS = {"salesforce", "hubspot", "pipedrive", "local"}


async def sync_to_crm(record: dict, target: str, idempotency_key: str) -> SyncResult:
    """Sync a record to an external CRM system.

    Uses real CRM adapters for Salesforce, HubSpot, and Pipedrive, plus Sage's
    own "local" CRM. Returns not_configured when the target CRM has no
    credentials — it never reports success for a record it did not create.

    Args:
        record: The record data to sync.
        target: Target CRM system ('salesforce', 'hubspot', 'pipedrive', 'local').
        idempotency_key: Unique key to prevent duplicate syncs.

    Returns:
        A dictionary with status, target, record_id, idempotency_key,
        synced_at, and provenance.
    """
    if target not in VALID_TARGETS:
        return {
            "status": "error",
            "target": target,
            "record_id": None,
            "idempotency_key": idempotency_key,
            "synced_at": None,
            "provenance": "none",
            "error": f"Invalid target. Must be one of: {', '.join(sorted(VALID_TARGETS))}",
        }

    # Select the appropriate adapter
    if target == "salesforce":
        adapter = SalesforceSync()
    elif target == "hubspot":
        adapter = HubSpotSync()
    elif target == "pipedrive":
        adapter = PipedriveSync()
    elif target == "local":
        adapter = LocalCRMSync()
    else:  # pragma: no cover - unreachable given VALID_TARGETS
        return {
            "status": "error",
            "target": target,
            "record_id": None,
            "idempotency_key": idempotency_key,
            "synced_at": None,
            "provenance": "none",
            "error": f"Unknown target: {target}",
        }

    # The local adapter derives its record ID from the idempotency key, so it
    # must receive that key in the payload. External CRMs ignore it.
    payload = dict(record)
    payload["idempotency_key"] = idempotency_key

    # Determine if this is a contact or deal sync
    if "title" in record or "amount" in record or "stage" in record:
        result = await adapter.create_deal(payload)
    else:
        result = await adapter.create_contact(payload)

    if "error" in result:
        # Do NOT fabricate success here.
        #
        # This branch previously returned status="success" with a synthesised
        # record_id (f"{target[:3]}_{idempotency_key[:8]}") so callers would see
        # a consistent response shape. That was a lie: the CRM was never
        # contacted, and anyone running without credentials saw "Synced to
        # Salesforce" for a record that did not exist. See
        # docs/superpowers/specs/2026-10-06-truth-and-agentic-chaining-design.md
        # section 1.2.
        return {
            "status": "not_configured",
            "target": target,
            "record_id": None,
            "idempotency_key": idempotency_key,
            "synced_at": None,
            "error": result["error"],
            "provenance": "none",
        }

    # A repeated idempotency key is a real, successful no-op: the first sync
    # created the record, and this one correctly declined to duplicate it.
    # Reported distinctly from "created" so a caller can tell them apart.
    if result.get("status") == "already_synced":
        return {
            "status": "already_synced",
            "target": target,
            "record_id": result.get("id"),
            "idempotency_key": idempotency_key,
            "synced_at": None,
            "provenance": target,
        }

    return {
        "status": "success",
        "target": target,
        "record_id": result["id"],
        "idempotency_key": idempotency_key,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "provenance": target,
    }
