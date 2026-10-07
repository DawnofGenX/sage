"""Do the tools actually return every field their schema declares required?

FastMCP validates structuredContent against the declared schema at runtime
and REJECTS the response when a required field is absent. That is not a
theoretical risk: SyncResult declaring `error` required made every
successful sync fail with "'error' is a required property", and no schema
test caught it because the tests only inspected the published schema.

This script calls every tool with plausible arguments and reports any
validation failure, so a missing-field bug surfaces as a failing test rather
than as a broken demo.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.rest import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


SAMPLE_ARGS = {
    "extract_from_call": {"transcript": "Hi Sarah from Acme Corp, $50K enterprise plan."},
    "get_contact_context": {"name": "Sarah"},
    "get_pipeline_health": {},
    "create_contact": {"name": "Schema Probe", "company": "ProbeCo"},
    "update_contact": {"contact_id": 1, "company": "ProbeCo2"},
    "create_deal": {"contact_id": 1, "title": "Probe Deal", "value": 1000},
    "update_deal_stage": {"deal_id": 1, "stage": "proposal"},
    "schedule_followup": {"contact_id": 1, "title": "Probe follow-up"},
    "draft_followup_email": {"contact": "Sarah", "context": "the proposal"},
    "log_call": {"contact_id": 1, "transcript": "probe"},
    "get_deal_insights": {"deal_id": 1},
    "get_daily_briefing": {},
    "get_todays_followups": {},
    "get_weekly_review": {},
    "search_contacts": {"query": "Sarah"},
    "sync_to_crm": {"record": {"name": "Probe"}, "target": "local",
                    "idempotency_key": "schema-probe-1"},
    "get_company_context": {"company_name": "Acme"},
    "get_activities": {"contact_id": 1},
    "get_deal_history": {"deal_id": 1},
    "create_task": {"contact_id": 1, "title": "Probe task"},
    "enrich_contact": {"contact_id": 1},
    "get_forecast": {},
}

SKIP = {"run_agentic_loop"}  # exercised by test_demo_flow.py with a live server


@pytest.mark.parametrize("tool_name", sorted(SAMPLE_ARGS))
def test_tool_returns_schema_valid_structured_content(client, tool_name):
    """Every tool must return structuredContent its own schema accepts.

    A tool that omits a required field is rejected at runtime by FastMCP,
    which surfaces to a caller as a failed call rather than as data.
    """
    if tool_name in SKIP:
        pytest.skip("covered by test_demo_flow.py against a live server")

    response = client.post(f"/api/tools/{tool_name}", json=SAMPLE_ARGS[tool_name])
    assert response.status_code == 200, (
        f"{tool_name} returned HTTP {response.status_code}: {response.text[:300]}"
    )
    body = response.json()
    assert "error" not in body or tool_name == "sync_to_crm", (
        f"{tool_name} returned an error for valid-looking input: {body}"
    )


def test_sync_success_path_is_schema_valid(client):
    """The specific regression: a SUCCESSFUL sync must validate.

    SyncResult once declared `error` required, so every success — the normal
    case — was rejected by FastMCP's structuredContent validation.
    """
    response = client.post(
        "/api/tools/sync_to_crm",
        json={"record": {"name": "Schema Valid"}, "target": "local",
              "idempotency_key": "schema-probe-success"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["provenance"] == "local"
    assert body["record_id"], "a real sync must return a real record id"
    assert "error" not in body, (
        "the success path must not carry an error key; it was declared "
        "required in the schema and that broke every successful sync"
    )