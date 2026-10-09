"""Stage-change and activity recording — the history write layer.

stage_history and activities existed in schema.sql but no code path wrote them,
so get_deal_history / get_activities returned empty lists unconditionally.
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAGE_DB_PATH"] = _tmp.name

from data.db import Database  # noqa: E402


@pytest.fixture
def db():
    database = Database(db_path=_tmp.name)
    yield database


@pytest.fixture
def deal(db):
    contact_id = db.create_contact({"name": "History Contact"})
    return db.create_deal({"contact_id": contact_id, "title": "History Deal"})


def test_update_deal_stage_records_stage_history(db, deal):
    """The bug: the UPDATE ran, the audit row never did."""
    db.update_deal_stage(deal, "proposal")
    rows = db.get_stage_history(deal)
    assert len(rows) == 1, f"expected 1 stage_history row, got {len(rows)}"
    assert rows[0]["from_stage"] == "lead"
    assert rows[0]["to_stage"] == "proposal"


def test_stage_history_accumulates_across_changes(db, deal):
    db.update_deal_stage(deal, "proposal")
    db.update_deal_stage(deal, "negotiation")
    rows = db.get_stage_history(deal)
    assert [r["to_stage"] for r in rows] == ["proposal", "negotiation"]


def test_record_stage_change_records_source(db, deal):
    """Source distinguishes a real CRM push from a local state change."""
    db.record_stage_change(deal, "lead", "qualified", source="salesforce")
    rows = db.get_stage_history(deal)
    assert rows[0]["source"] == "salesforce"
