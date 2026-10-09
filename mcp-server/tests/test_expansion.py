"""Tests for the 6 new Sage MCP expansion tools."""
import asyncio
import os
import tempfile

import pytest


# Use a temporary database for all tests
_tmp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_file.close()
os.environ["SAGE_DB_PATH"] = _tmp_db_file.name

from tools import expansion, crud


def reset_modules():
    """Reset global state in all tool modules."""
    expansion._db = None
    expansion._provider = None
    crud._db = None
    crud._provider = None


@pytest.fixture(autouse=True)
def clean_state():
    """Reset module state and DB before each test."""
    reset_modules()
    if os.path.exists(_tmp_db_file.name):
        os.unlink(_tmp_db_file.name)
    open(_tmp_db_file.name, "w").close()
    yield
    reset_modules()


# ==================================================================
# Expansion tools (6)
# ==================================================================


@pytest.mark.asyncio
async def test_get_company_context():
    """Create contacts and deals for a company, get full context."""
    # Create contacts at the same company
    c1 = await crud.create_contact(name="Alice", company="Acme Corp", email="alice@acme.com")
    c2 = await crud.create_contact(name="Bob", company="Acme Corp", email="bob@acme.com")
    # Create a contact at a different company
    c3 = await crud.create_contact(name="Charlie", company="Globex", email="charlie@globex.com")

    # Create deals for Acme contacts
    await crud.create_deal(contact_id=c1["id"], title="Deal A", value=50000.0, stage="proposal")
    await crud.create_deal(contact_id=c2["id"], title="Deal B", value=30000.0, stage="negotiation")
    # Create a deal for Globex contact
    await crud.create_deal(contact_id=c3["id"], title="Deal C", value=10000.0, stage="lead")

    result = await expansion.get_company_context("Acme Corp")

    assert result["company"] == "Acme Corp"
    # Verify our contacts are present (there may be others from previous tests)
    contact_names = [c["name"] for c in result["contacts"]]
    assert "Alice" in contact_names
    assert "Bob" in contact_names
    # Verify our deals are present
    deal_titles = [d["title"] for d in result["deals"]]
    assert "Deal A" in deal_titles
    assert "Deal B" in deal_titles
    assert result["total_value"] >= 80000.0
    assert result["health"] in ("excellent", "good", "fair", "at_risk", "unknown")


@pytest.mark.asyncio
async def test_get_activities():
    """Create activities and verify filtering."""
    contact = await crud.create_contact(name="Activity Contact")
    deal = await crud.create_deal(
        contact_id=contact["id"],
        title="Activity Deal",
        value=10000.0,
    )

    # Insert activities directly into the DB
    db = expansion._get_db()
    conn = db._get_conn()
    conn.execute(
        "INSERT INTO activities (contact_id, deal_id, type, description) VALUES (?, ?, ?, ?)",
        (contact["id"], deal["id"], "call", "Initial discovery call"),
    )
    conn.execute(
        "INSERT INTO activities (contact_id, deal_id, type, description) VALUES (?, ?, ?, ?)",
        (contact["id"], deal["id"], "email", "Sent proposal email"),
    )
    conn.execute(
        "INSERT INTO activities (contact_id, deal_id, type, description) VALUES (?, ?, ?, ?)",
        (contact["id"], deal["id"], "meeting", "Product demo meeting"),
    )
    conn.commit()
    conn.close()

    # Reset the cached db so it picks up new data
    expansion._db = None

    # Get all activities
    result = await expansion.get_activities()
    # Not == 3: create_contact and create_deal now record activities of their
    # own (the event layer), so the total includes those rows. What this test
    # owns is the three it inserted — assert those are present rather than an
    # exact total that any future writer would break.
    kinds = {a["type"] for a in result["activities"]}
    assert {"call", "email", "meeting"} <= kinds, kinds

    # Filter by contact
    result = await expansion.get_activities(contact_id=contact["id"])
    types = [a["type"] for a in result["activities"]]
    assert types.count("call") == 1
    assert types.count("email") == 1
    assert types.count("meeting") == 1

    # Filter by deal
    result = await expansion.get_activities(deal_id=deal["id"])
    deal_types = [a["type"] for a in result["activities"]]
    assert deal_types.count("call") == 1
    assert deal_types.count("email") == 1
    assert deal_types.count("meeting") == 1

    # Filter by non-existent contact
    result = await expansion.get_activities(contact_id=9999)
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_deal_history():
    """Create a deal and verify history retrieval."""
    contact = await crud.create_contact(name="History Contact")
    deal = await crud.create_deal(
        contact_id=contact["id"],
        title="History Deal",
        value=25000.0,
        stage="lead",
    )

    # Insert stage history
    db = expansion._get_db()
    conn = db._get_conn()
    conn.execute(
        "INSERT INTO stage_history (deal_id, from_stage, to_stage) VALUES (?, ?, ?)",
        (deal["id"], None, "lead"),
    )
    conn.execute(
        "INSERT INTO stage_history (deal_id, from_stage, to_stage) VALUES (?, ?, ?)",
        (deal["id"], "lead", "qualified"),
    )
    conn.execute(
        "INSERT INTO stage_history (deal_id, from_stage, to_stage) VALUES (?, ?, ?)",
        (deal["id"], "qualified", "proposal"),
    )
    conn.commit()
    conn.close()

    # Insert an activity
    conn = db._get_conn()
    conn.execute(
        "INSERT INTO activities (contact_id, deal_id, type, description) VALUES (?, ?, ?, ?)",
        (contact["id"], deal["id"], "call", "Discovery call"),
    )
    conn.commit()
    conn.close()

    # Reset cached db
    expansion._db = None

    result = await expansion.get_deal_history(deal["id"])

    assert result["deal"] is not None
    assert result["deal"]["title"] == "History Deal"
    assert len(result["stage_history"]) == 3
    assert len(result["interactions"]) >= 1
    assert len(result["timeline"]) >= 4  # 3 stage changes + 1 activity


@pytest.mark.asyncio
async def test_create_task():
    """Create a task and verify it."""
    contact = await crud.create_contact(name="Task Contact")

    result = await expansion.create_task(
        contact_id=contact["id"],
        title="Follow up on proposal",
        due_date="2026-10-15",
        priority="high",
        notes="Check if they reviewed the proposal",
    )

    assert result["created"] is True
    assert result["id"] > 0
    assert result["title"] == "Follow up on proposal"


@pytest.mark.asyncio
async def test_enrich_contact():
    """Create a contact and enrich it."""
    contact = await crud.create_contact(
        name="Enrich Me",
        company="TechCorp",
        email="enrich@techcorp.com",
        title="CTO",
    )

    result = await expansion.enrich_contact(contact["id"])

    assert result["enriched"] is True
    assert result["contact"] is not None
    assert result["contact"]["name"] == "Enrich Me"
    assert "data" in result
    assert "linkedin" in result["data"]
    assert "company_size" in result["data"]
    assert "industry" in result["data"]


@pytest.mark.asyncio
async def test_get_forecast():
    """Create deals and verify forecast."""
    c1 = await crud.create_contact(name="Forecast Contact 1")
    c2 = await crud.create_contact(name="Forecast Contact 2")
    c3 = await crud.create_contact(name="Forecast Contact 3")

    await crud.create_deal(contact_id=c1["id"], title="Lead Deal", value=10000.0, stage="lead")
    await crud.create_deal(contact_id=c2["id"], title="Proposal Deal", value=50000.0, stage="proposal")
    await crud.create_deal(contact_id=c3["id"], title="Negotiation Deal", value=100000.0, stage="negotiation")
    # Won deal should not appear in forecast
    await crud.create_deal(contact_id=c1["id"], title="Won Deal", value=20000.0, stage="won")

    result = await expansion.get_forecast()

    assert "forecast" in result
    assert "total_pipeline" in result
    assert "weighted_forecast" in result
    assert "best_case" in result
    assert "worst_case" in result
    assert "confidence" in result

    # Verify the forecast contains our deals
    forecast_titles = [f["title"] for f in result["forecast"]]
    assert "Lead Deal" in forecast_titles
    assert "Proposal Deal" in forecast_titles
    assert "Negotiation Deal" in forecast_titles
    assert "Won Deal" not in forecast_titles

    # Verify calculations
    assert result["total_pipeline"] >= 160000.0
    assert result["weighted_forecast"] > 0
    assert result["best_case"] > result["weighted_forecast"]
    assert result["worst_case"] < result["weighted_forecast"]
    assert result["confidence"] in ("low", "medium", "high")


# ==================================================================
# Cleanup
# ==================================================================


def teardown_module():
    """Clean up temporary database."""
    try:
        os.unlink(_tmp_db_file.name)
    except OSError:
        pass
