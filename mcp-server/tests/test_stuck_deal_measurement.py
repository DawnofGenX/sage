"""Stuck-deal insight must measure inactivity, not guess from stage names.

The previous implementation flagged any deal whose stage was 'lead' or
'negotiation'. That misreported both directions: an actively-worked early-stage
deal got flagged, and a stalled negotiation-stage deal could look fine.
With stage_history and activities written, elapsed silence is measurable.
"""
import os
import tempfile
from datetime import datetime, timedelta

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAGE_DB_PATH"] = _tmp.name

from data.db import Database  # noqa: E402


@pytest.fixture
def db():
    database = Database(db_path=_tmp.name)
    yield database


def _engine(db):
    """ProactiveEngine touches an LLM only in _get_llm_insights, which the
    stuck-deal check never calls. A stand-in keeps this unit hermetic."""
    from proactive.engine import ProactiveEngine

    return ProactiveEngine(db=db, llm=object())


def test_stuck_deal_uses_history_not_stage_name(db):
    """A deal at 'lead' with 30 days of silence is stuck; 'lead' must not be magic."""
    from proactive.engine import ProactiveEngine

    contact_id = db.create_contact({"name": "Stuck Contact"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Stuck Deal", "stage": "lead"})

    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db._get_conn()
    conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (old, deal_id))
    conn.commit()

    alerts = ProactiveEngine(db=db, llm=object())._check_stuck_deals()
    assert any("30 days" in a for a in alerts), alerts


def test_active_deal_not_flagged(db):
    """History must protect a deal that was just touched."""
    contact_id = db.create_contact({"name": "Active Contact"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Active Deal", "stage": "lead"})
    db.record_activity(deal_id=deal_id, type="call", description="spoke today")

    alerts = _engine(db)._check_stuck_deals()
    assert not any("Active Deal" in a for a in alerts), alerts


def test_recent_stage_change_protects_the_deal(db):
    """A stage change is activity — it must reset the inactivity clock."""
    contact_id = db.create_contact({"name": "Recent Contact"})
    deal_id = db.create_deal(
        {"contact_id": contact_id, "title": "Recent Deal", "stage": "lead"}
    )

    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db._get_conn()
    conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (old, deal_id))
    conn.commit()

    db.record_stage_change(deal_id, "lead", "proposal", source="local")

    alerts = _engine(db)._check_stuck_deals()
    assert not any("Recent Deal" in a for a in alerts), alerts


def test_deal_with_no_history_falls_back_to_updated_at(db):
    """No event rows yet: use the deal's own timestamp and stay quiet if unknown."""
    contact_id = db.create_contact({"name": "Fallback Contact"})
    db.create_deal({"contact_id": contact_id, "title": "Fallback Deal", "stage": "negotiation"})

    # No history written at all, and updated_at is fresh (just created).
    alerts = _engine(db)._check_stuck_deals()
    assert not any("Fallback Deal" in a for a in alerts), alerts


def test_stuck_deal_reports_the_measured_days(db):
    """The number in the message must come from the recorded history, not a guess."""
    from proactive.engine import ProactiveEngine

    contact_id = db.create_contact({"name": "Measured Contact"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Measured Deal"})

    old = (datetime.now() - timedelta(days=21)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db._get_conn()
    conn.execute(
        "INSERT INTO stage_history (deal_id, from_stage, to_stage, changed_at) VALUES (?,?,?,?)",
        (deal_id, "lead", "proposal", old),
    )
    conn.commit()

    alerts = ProactiveEngine(db=db, llm=object())._check_stuck_deals()
    assert any("21 days" in a for a in alerts), alerts
