import os
import tempfile
from datetime import datetime, timedelta

import pytest


from data.db import Database
from llm.provider import LLMProvider
from proactive.engine import ProactiveEngine


class EmptyLLM:
    """LLM that returns no insights."""

    async def extract(self, transcript, extraction_type):
        return {"insights": [], "priority": "low"}


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = Database(db_path=db_path)
    yield database
    os.unlink(db_path)


@pytest.fixture
def llm():
    return LLMProvider()


@pytest.fixture
def engine(db, llm):
    return ProactiveEngine(db, llm)


@pytest.mark.asyncio
async def test_overdue_followup_alert(engine, db):
    """Test that overdue follow-ups generate alerts."""
    contact_id = db.create_contact({"name": "Test Contact"})
    db.create_followup({
        "contact_id": contact_id,
        "title": "Follow up with prospect",
        "due_date": (datetime.now() - timedelta(days=1)).isoformat(),
    })

    insights = await engine.generate_insights()

    assert any("Overdue follow-up" in insight for insight in insights)


@pytest.mark.asyncio
async def test_stuck_deal_alert(engine, db):
    """Test that deals with no recent activity generate alerts."""
    contact_id = db.create_contact({"name": "Test Contact"})
    deal_id = db.create_deal({
        "contact_id": contact_id,
        "title": "Stuck Deal",
        "value": 1000.0,
    })

    # Update the deal's updated_at to be 15 days ago
    conn = db._get_conn()
    old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (old_date, deal_id))
    conn.commit()
    conn.close()

    insights = await engine.generate_insights()

    assert any("Stuck deal" in insight for insight in insights)


@pytest.mark.asyncio
async def test_llm_insights(engine, db):
    """Test that LLM-based insights are generated."""
    contact_id = db.create_contact({"name": "Test Contact"})
    db.create_deal({
        "contact_id": contact_id,
        "title": "Test Deal",
        "value": 1000.0,
    })

    insights = await engine.generate_insights()

    # LLM should generate at least one insight
    assert len(insights) > 0


@pytest.mark.asyncio
async def test_insights_sorted_by_urgency(engine, db):
    """Test that insights are sorted by urgency."""
    contact_id = db.create_contact({"name": "Test Contact"})

    # Create an overdue follow-up (urgency 3)
    db.create_followup({
        "contact_id": contact_id,
        "title": "Overdue Follow-up",
        "due_date": (datetime.now() - timedelta(days=1)).isoformat(),
    })

    # Create a stuck deal (urgency 2)
    deal_id = db.create_deal({
        "contact_id": contact_id,
        "title": "Stuck Deal",
        "value": 1000.0,
    })
    conn = db._get_conn()
    old_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (old_date, deal_id))
    conn.commit()
    conn.close()

    insights = await engine.generate_insights()

    # Overdue follow-up should come before stuck deal
    overdue_idx = next((i for i, x in enumerate(insights) if "Overdue" in x), None)
    stuck_idx = next((i for i, x in enumerate(insights) if "Stuck" in x), None)

    assert overdue_idx is not None
    assert stuck_idx is not None
    assert overdue_idx < stuck_idx


@pytest.mark.asyncio
async def test_no_insights_when_all_clear(db):
    """Test that no insights are generated when everything is fine."""
    llm = EmptyLLM()
    engine = ProactiveEngine(db, llm)

    # Create a contact and deal with recent activity
    contact_id = db.create_contact({"name": "Test Contact"})
    db.create_deal({
        "contact_id": contact_id,
        "title": "Active Deal",
        "value": 1000.0,
    })

    # Create a follow-up that's not overdue
    db.create_followup({
        "contact_id": contact_id,
        "title": "Future Follow-up",
        "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
    })

    insights = await engine.generate_insights()

    assert len(insights) == 0
