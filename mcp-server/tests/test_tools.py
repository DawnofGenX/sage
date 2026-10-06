"""Tests for all 16 Sage MCP tools."""

import asyncio
import os
import tempfile

import pytest


# Use a temporary database for all tests
_tmp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_file.close()
os.environ["SAGE_DB_PATH"] = _tmp_db_file.name

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
    # Reset the database file to ensure clean state
    if os.path.exists(_tmp_db_file.name):
        os.unlink(_tmp_db_file.name)
    # Create a fresh empty DB file
    open(_tmp_db_file.name, "w").close()
    yield
    reset_modules()


@pytest.fixture
def sample_transcript():
    return (
        "Hi, this is John Smith from Acme Corp. I spoke with Sarah Johnson "
        "at Globex Inc last week. She's very interested in our enterprise "
        "solution and mentioned a budget of $50,000. We should follow up "
        "with her on January 15th. She's excited about the demo and ready "
        "to move forward. The decision timeline is urgent."
    )


# ==================================================================
# Extraction tools (3)
# ==================================================================


@pytest.mark.asyncio
async def test_extract_from_call(sample_transcript):
    """Verify extraction returns all 4 steps."""
    result = await extraction.extract_from_call(sample_transcript)

    assert "step1_entities" in result
    assert "step2_intent" in result
    assert "step3_record" in result
    assert "step4_derived" in result

    # Step 1 checks
    entities = result["step1_entities"]
    assert "people" in entities
    assert "companies" in entities
    assert "amounts" in entities
    assert "dates" in entities
    assert len(entities["people"]) > 0

    # Step 2 checks
    assert result["step2_intent"] in ("new_lead", "follow_up", "deal_update", "general")

    # Step 3 checks
    record = result["step3_record"]
    assert "contacts" in record
    assert "deals" in record
    assert "followups" in record
    assert "sentiment" in record
    assert "buying_signals" in record
    assert "risks" in record

    # Step 4 checks
    assert result["step4_derived"] is True


@pytest.mark.asyncio
async def test_get_contact_context():
    """Create a contact, get context."""
    # Create a contact first
    contact_result = await crud.create_contact(
        name="Alice Johnson",
        company="Acme Corp",
        email="alice@acme.com",
    )
    contact_id = contact_result["id"]

    # Create a deal for this contact
    await crud.create_deal(
        contact_id=contact_id,
        title="Enterprise Deal",
        value=50000.0,
        stage="proposal",
    )

    # Get context
    result = await extraction.get_contact_context("Alice")

    assert result["contact"] is not None
    assert result["contact"]["name"] == "Alice Johnson"
    assert len(result["deals"]) == 1
    assert result["deals"][0]["title"] == "Enterprise Deal"


@pytest.mark.asyncio
async def test_get_pipeline_health():
    """Create deals, check health."""
    # Create contacts and deals
    c1 = await crud.create_contact(name="Bob", company="Globex")
    c2 = await crud.create_contact(name="Carol", company="Initech")

    await crud.create_deal(contact_id=c1["id"], title="Deal A", value=10000.0, stage="lead")
    await crud.create_deal(contact_id=c2["id"], title="Deal B", value=20000.0, stage="proposal")
    await crud.create_deal(contact_id=c1["id"], title="Deal C", value=30000.0, stage="negotiation")

    result = await extraction.get_pipeline_health()

    assert result["total_deals"] == 3
    assert result["total_value"] == 60000.0
    assert "lead" in result["deals_by_stage"]
    assert "proposal" in result["deals_by_stage"]
    assert "negotiation" in result["deals_by_stage"]
    assert len(result["stuck_deals"]) >= 1  # lead and negotiation are stuck


# ==================================================================
# CRUD tools (7)
# ==================================================================


@pytest.mark.asyncio
async def test_create_contact():
    """Verify contact creation."""
    result = await crud.create_contact(
        name="Test User",
        company="Test Co",
        email="test@testco.com",
        phone="555-1234",
        title="Engineer",
        notes="A test contact",
    )

    assert result["created"] is True
    assert result["id"] > 0
    assert result["name"] == "Test User"


@pytest.mark.asyncio
async def test_create_deal():
    """Verify deal creation."""
    contact = await crud.create_contact(name="Deal Contact")
    result = await crud.create_deal(
        contact_id=contact["id"],
        title="Big Deal",
        value=75000.0,
        stage="qualified",
        notes="Important deal",
    )

    assert result["created"] is True
    assert result["id"] > 0
    assert result["title"] == "Big Deal"


@pytest.mark.asyncio
async def test_update_deal_stage():
    """Create and update deal."""
    contact = await crud.create_contact(name="Stage Test")
    deal = await crud.create_deal(
        contact_id=contact["id"],
        title="Stage Deal",
        value=1000.0,
        stage="lead",
    )

    updated = await crud.update_deal_stage(deal["id"], "won")
    assert updated["stage"] == "won"

    updated = await crud.update_deal_stage(deal["id"], "lost")
    assert updated["stage"] == "lost"


@pytest.mark.asyncio
async def test_schedule_followup():
    """Create follow-up."""
    contact = await crud.create_contact(name="Followup Contact")
    deal = await crud.create_deal(
        contact_id=contact["id"],
        title="Followup Deal",
        value=5000.0,
    )

    result = await crud.schedule_followup(
        contact_id=contact["id"],
        title="Call back",
        due_date="2026-10-10",
        deal_id=deal["id"],
        notes="Discuss proposal",
    )

    assert result["created"] is True
    assert result["id"] > 0
    assert result["title"] == "Call back"


@pytest.mark.asyncio
async def test_draft_followup_email():
    """Verify email draft."""
    result = await crud.draft_followup_email(
        contact="John Smith",
        context="Discussed enterprise pricing and timeline",
        tone="formal",
    )

    assert "subject" in result
    assert "body" in result
    assert len(result["subject"]) > 0
    assert len(result["body"]) > 0
    assert "John Smith" in result["body"]


@pytest.mark.asyncio
async def test_log_call():
    """Verify call logging."""
    contact = await crud.create_contact(name="Call Contact")
    result = await crud.log_call(
        contact_id=contact["id"],
        transcript="Test call transcript",
        summary="Great call",
        duration_seconds=300,
    )

    assert result["created"] is True
    assert result["id"] > 0


# ==================================================================
# Intelligence tools (5)
# ==================================================================


@pytest.mark.asyncio
async def test_get_deal_insights():
    """Create deal, get insights."""
    contact = await crud.create_contact(name="Insights Contact")
    deal = await crud.create_deal(
        contact_id=contact["id"],
        title="Insights Deal",
        value=100000.0,
        stage="negotiation",
    )

    result = await intelligence.get_deal_insights(deal["id"])

    assert result["deal_id"] == deal["id"]
    assert "sentiment" in result
    assert "risks" in result
    assert "buying_signals" in result
    assert "recommendation" in result
    assert "insights" in result
    assert isinstance(result["insights"], list)


@pytest.mark.asyncio
async def test_get_daily_briefing():
    """Verify briefing."""
    # Create some data
    contact = await crud.create_contact(name="Briefing Contact")
    await crud.create_deal(contact_id=contact["id"], title="Brief Deal", value=5000.0)
    await crud.schedule_followup(
        contact_id=contact["id"],
        title="Brief Followup",
        due_date="2026-10-06",
    )

    result = await intelligence.get_daily_briefing()

    assert "followups_due" in result
    assert "total_deals" in result
    assert "pipeline_value" in result
    assert "stuck_deals" in result
    assert "insights" in result
    assert result["total_deals"] >= 1
    assert len(result["followups_due"]) >= 1


@pytest.mark.asyncio
async def test_get_todays_followups():
    """Verify follow-ups."""
    contact = await crud.create_contact(name="Today Contact")
    await crud.schedule_followup(
        contact_id=contact["id"],
        title="Today Followup",
        due_date="2026-10-05",
    )

    result = await intelligence.get_todays_followups()

    assert "followups" in result
    assert "total" in result
    assert result["total"] >= 1
    assert len(result["followups"]) >= 1
    # Check priority field exists
    assert "priority" in result["followups"][0]


@pytest.mark.asyncio
async def test_get_weekly_review():
    """Verify review."""
    contact = await crud.create_contact(name="Weekly Contact")
    await crud.create_deal(contact_id=contact["id"], title="Weekly Deal", value=15000.0)
    await crud.log_call(
        contact_id=contact["id"],
        transcript="Weekly call",
        summary="Good call",
        duration_seconds=600,
    )

    result = await intelligence.get_weekly_review()

    assert "deals_moved" in result
    assert "calls_made" in result
    assert "followups_completed" in result
    assert "pipeline_health" in result
    assert "weekly_summary" in result
    assert result["calls_made"] >= 1
    assert result["pipeline_health"]["total_deals"] >= 1


@pytest.mark.asyncio
async def test_search_contacts():
    """Create contacts, search."""
    await crud.create_contact(name="Search Alice", company="Acme")
    await crud.create_contact(name="Search Bob", company="Globex")
    await crud.create_contact(name="Other Charlie", company="Initech")

    result = await intelligence.search_contacts("Search")

    assert "contacts" in result
    assert "total" in result
    assert result["total"] == 2
    names = [c["name"] for c in result["contacts"]]
    assert "Search Alice" in names
    assert "Search Bob" in names


# ==================================================================
# Sync tool (1)
# ==================================================================


@pytest.mark.asyncio
async def test_sync_to_crm():
    """An unconfigured CRM reports not_configured, not a fake success.

    This test previously asserted status == "success" with a non-null
    record_id for a Salesforce that was never contacted — the fabricated-
    success defect. Do not restore those assertions.
    """
    record = {"name": "Sync Test", "email": "sync@test.com"}
    result = await sync.sync_to_crm(
        record=record,
        target="salesforce",
        idempotency_key="test-key-123",
    )

    assert result["status"] == "not_configured"
    assert result["target"] == "salesforce"
    assert result["record_id"] is None
    assert result["idempotency_key"] == "test-key-123"
    assert result["synced_at"] is None
    assert result["provenance"] == "none"
    assert result["error"]


# ==================================================================
# Cleanup
# ==================================================================


def teardown_module():
    """Clean up temporary database."""
    try:
        os.unlink(_tmp_db_file.name)
    except OSError:
        pass
