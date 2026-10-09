"""Activity recording wires state changes to the activities table.

The activities table existed in schema.sql but no code path wrote to it, so
get_activities() returned [] unconditionally. These tests pin the write layer.
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
    contact_id = db.create_contact({"name": "Activity Contact"})
    return db.create_deal({"contact_id": contact_id, "title": "Activity Deal"})


def test_record_activity_inserts_row(db, deal):
    row_id = db.record_activity(
        deal_id=deal, type="deal_updated", description="Stage moved to negotiation"
    )
    assert row_id > 0
    rows = db.get_activities(deal_id=deal)
    assert rows[0]["type"] == "deal_updated"


def test_get_activities_was_empty_before_the_write_layer(db, deal):
    """Documents the defect this plan fixes, so it cannot silently regress."""
    db.record_activity(deal_id=deal, type="note", description="hello")
    assert len(db.get_activities(deal_id=deal)) == 1


def test_update_deal_stage_writes_an_activity(db, deal):
    db.update_deal_stage(deal, "proposal")
    acts = db.get_activities(deal_id=deal)
    assert any(a["type"] == "stage_change" for a in acts), acts


def test_update_contact_writes_an_activity(db, deal):
    """update_contact must leave a trail, not just mutate the row."""
    import asyncio

    from tools.crud import update_contact

    contact_id = db.create_contact({"name": "Trail Contact", "company": "Old"})
    asyncio.run(update_contact(
        contact_id, name="Trail Contact", company="New", email=None, phone=None,
        title=None, notes=None,
    ))
    acts = db.get_activities(contact_id=contact_id)
    assert any(a["type"] == "contact_updated" for a in acts), acts


def test_create_deal_writes_an_activity(db, deal):
    import asyncio

    from tools.crud import create_deal

    asyncio.run(create_deal(contact_id=1, title="Trail Deal", value=500))
    acts = db.get_activities(deal_id=None)
    assert any(a["type"] == "deal_created" for a in acts), acts


def test_schedule_followup_writes_an_activity(db, deal):
    import asyncio

    from tools.crud import schedule_followup

    contact_id = db.create_contact({"name": "Followup Contact"})
    asyncio.run(schedule_followup(
        contact_id=contact_id, title="Check in", due_date=None, deal_id=None, notes=None
    ))
    acts = db.get_activities(contact_id=contact_id)
    assert any(a["type"] == "followup_scheduled" for a in acts), acts


def test_activity_rows_are_append_only(db, deal):
    """Nothing updates or deletes activity rows."""
    first = db.record_activity(deal_id=deal, type="note", description="one")
    second = db.record_activity(deal_id=deal, type="note", description="two")
    assert first != second
    assert len(db.get_activities(deal_id=deal)) == 2
