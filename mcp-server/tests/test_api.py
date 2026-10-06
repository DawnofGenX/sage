"""Tests for Sage REST API."""
import os
import tempfile

import pytest


# Use a temporary database for all tests
_tmp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_file.close()
os.environ["SAGE_DB_PATH"] = _tmp_db_file.name

from fastapi.testclient import TestClient

from api.rest import app, TOOLS
from tools import extraction, crud, intelligence, sync, expansion


def reset_modules():
    """Reset global state in all tool modules."""
    extraction._db = None
    extraction._pipeline = None
    crud._db = None
    crud._provider = None
    intelligence._db = None
    intelligence._provider = None
    expansion._db = None
    expansion._provider = None


@pytest.fixture(autouse=True)
def clean_state():
    """Reset module state and DB before each test."""
    reset_modules()
    if os.path.exists(_tmp_db_file.name):
        os.unlink(_tmp_db_file.name)
    open(_tmp_db_file.name, "w").close()
    yield
    reset_modules()


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """GET /api/health returns 200 with status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["server"] == "sage"
    assert data["version"] == "1.0.0"


def test_extract_from_call(client):
    """POST /api/tools/extract_from_call with a transcript returns extraction result."""
    transcript = (
        "Hi, this is John Smith from Acme Corp. I spoke with Sarah Johnson "
        "at Globex Inc last week. She's very interested in our enterprise "
        "solution and mentioned a budget of $50,000."
    )
    response = client.post("/api/tools/extract_from_call", json={"transcript": transcript})
    assert response.status_code == 200
    data = response.json()
    assert "step1_entities" in data
    assert "step2_intent" in data
    assert "step3_record" in data
    assert "step4_derived" in data


def test_get_contact_context(client):
    """POST /api/tools/get_contact_context returns contact context."""
    # Create a contact first
    client.post("/api/tools/create_contact", json={"name": "Alice", "company": "Acme"})
    response = client.post("/api/tools/get_contact_context", json={"name": "Alice"})
    assert response.status_code == 200
    data = response.json()
    assert data["contact"] is not None
    assert data["contact"]["name"] == "Alice"


def test_get_pipeline_health(client):
    """POST /api/tools/get_pipeline_health returns pipeline health."""
    response = client.post("/api/tools/get_pipeline_health", json={})
    assert response.status_code == 200
    data = response.json()
    assert "deals_by_stage" in data
    assert "total_deals" in data
    assert "total_value" in data


def test_create_contact(client):
    """POST /api/tools/create_contact creates a contact."""
    response = client.post("/api/tools/create_contact", json={"name": "Test User", "company": "TestCo"})
    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["id"] > 0
    assert data["name"] == "Test User"


def test_create_deal(client):
    """POST /api/tools/create_deal creates a deal."""
    contact_resp = client.post("/api/tools/create_contact", json={"name": "Deal Contact"})
    contact_id = contact_resp.json()["id"]
    response = client.post("/api/tools/create_deal", json={"contact_id": contact_id, "title": "Big Deal", "value": 50000})
    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["id"] > 0
    assert data["title"] == "Big Deal"


def test_search_contacts(client):
    """POST /api/tools/search_contacts returns matching contacts."""
    client.post("/api/tools/create_contact", json={"name": "Search Alice", "company": "Acme"})
    client.post("/api/tools/create_contact", json={"name": "Search Bob", "company": "Globex"})
    response = client.post("/api/tools/search_contacts", json={"query": "Search"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    names = [c["name"] for c in data["contacts"]]
    assert "Search Alice" in names
    assert "Search Bob" in names


def test_sync_to_crm(client):
    """POST /api/tools/sync_to_crm surfaces the honest unconfigured result.

    Previously asserted status == "success" with a non-null record_id for a
    Salesforce that was never contacted. Do not restore those assertions.
    """
    response = client.post("/api/tools/sync_to_crm", json={"record": {"name": "Test"}, "target": "salesforce", "idempotency_key": "key123"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_configured"
    assert data["target"] == "salesforce"
    assert data["record_id"] is None
    assert data["provenance"] == "none"


def test_tool_not_found(client):
    """POST /api/tools/nonexistent returns 404."""
    response = client.post("/api/tools/nonexistent", json={})
    assert response.status_code == 404


def test_tool_error(client):
    """POST /api/tools/extract_from_call with invalid args returns 500."""
    response = client.post("/api/tools/extract_from_call", json={})
    assert response.status_code == 500


def test_get_company_context(client):
    """POST /api/tools/get_company_context returns company context."""
    client.post("/api/tools/create_contact", json={"name": "Alice", "company": "Acme Corp"})
    response = client.post("/api/tools/get_company_context", json={"company_name": "Acme Corp"})
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Acme Corp"
    assert len(data["contacts"]) >= 1
    assert "deals" in data
    assert "total_value" in data
    assert "health" in data


def test_get_activities(client):
    """POST /api/tools/get_activities returns activities."""
    response = client.post("/api/tools/get_activities", json={})
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert "total" in data


def test_get_deal_history(client):
    """POST /api/tools/get_deal_history returns deal history."""
    contact_resp = client.post("/api/tools/create_contact", json={"name": "History Contact"})
    contact_id = contact_resp.json()["id"]
    deal_resp = client.post("/api/tools/create_deal", json={"contact_id": contact_id, "title": "History Deal", "value": 10000})
    deal_id = deal_resp.json()["id"]
    response = client.post("/api/tools/get_deal_history", json={"deal_id": deal_id})
    assert response.status_code == 200
    data = response.json()
    assert data["deal"] is not None
    assert "stage_history" in data
    assert "interactions" in data
    assert "timeline" in data


def test_create_task(client):
    """POST /api/tools/create_task creates a task."""
    contact_resp = client.post("/api/tools/create_contact", json={"name": "Task Contact"})
    contact_id = contact_resp.json()["id"]
    response = client.post("/api/tools/create_task", json={"contact_id": contact_id, "title": "Test Task", "priority": "high"})
    assert response.status_code == 200
    data = response.json()
    assert data["created"] is True
    assert data["id"] > 0
    assert data["title"] == "Test Task"


def test_enrich_contact(client):
    """POST /api/tools/enrich_contact enriches a contact."""
    contact_resp = client.post("/api/tools/create_contact", json={"name": "Enrich Me", "company": "TechCorp"})
    contact_id = contact_resp.json()["id"]
    response = client.post("/api/tools/enrich_contact", json={"contact_id": contact_id})
    assert response.status_code == 200
    data = response.json()
    assert data["enriched"] is True
    assert data["contact"] is not None
    assert "data" in data
    assert "linkedin" in data["data"]
    assert "company_size" in data["data"]
    assert "industry" in data["data"]


def test_get_forecast(client):
    """POST /api/tools/get_forecast returns forecast."""
    response = client.post("/api/tools/get_forecast", json={})
    assert response.status_code == 200
    data = response.json()
    assert "forecast" in data
    assert "total_pipeline" in data
    assert "weighted_forecast" in data
    assert "best_case" in data
    assert "worst_case" in data
    assert "confidence" in data


def teardown_module():
    """Clean up temporary database."""
    try:
        os.unlink(_tmp_db_file.name)
    except OSError:
        pass
