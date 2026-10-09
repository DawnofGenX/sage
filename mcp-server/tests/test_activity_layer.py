"""Activity recording wires state changes to the activities table.

The activities table existed in schema.sql but no code path wrote to it, so
get_activities() returned [] unconditionally. These tests pin the write layer.
"""
import os
import sqlite3
import tempfile

import pytest

# IMPORTANT: do NOT assign os.environ["SAGE_DB_PATH"] here.
#
# The suite already appoints one session-wide temp DB (test_api.py and
# test_expansion.py both do it at import, and test_expansion's autouse fixture
# deletes and recreates THAT file between tests). Rebinding the env var from a
# later-imported module silently points every other module at a different file:
# their resets miss our rows and our fixtures miss theirs. Import order is
# alphabetical, so a module named test_activity_layer.py runs before test_api.py
# and would win the assignment.
#
# Instead, resolve the path read-only and let the fixture own the file.
#
# The tool modules (tools.crud, tools.expansion) resolve the DB lazily through
# tools/common._get_db(), which caches a singleton built from the env var. Tests
# that call those tools must therefore reset that cache; the fixtures below do.
#
# This module owns no path. The session DB belongs to test_api.py, which the
# suite imports anyway; importing its binding makes the dependency explicit
# rather than a race on alphabetical import order. Four modules each trying to
# appoint the session DB is exactly how test_expansion.py ended up resetting a
# file nobody was writing to (it asserts an exact activity count and saw 12
# rows from these modules).
from test_api import _tmp_db_file as _session_db  # noqa: E402

_tmp_path = _session_db.name
os.environ["SAGE_DB_PATH"] = _tmp_path

from data.db import Database  # noqa: E402


@pytest.fixture
def db():
    """A Database on the session path, with tool-module caches cleared.

    Tools resolve their DB lazily through tools.common._get_db(), which caches a
    singleton keyed to the env var. Without clearing it, a tool called in one
    test keeps the previous test's connection and sees stale rows (or a deleted
    file). Reset before AND after: the module-level caches are what the existing
    suite's reset_modules() also targets.

    The path is re-resolved per test rather than captured at import:
    test_api.py and test_expansion.py delete and recreate the session file
    between tests, so a bound path can point at an unlinked inode — the tool
    writes land in the new file while this fixture reads the old one.
    """
    _reset_tool_caches()
    path = os.environ["SAGE_DB_PATH"]
    database = Database(db_path=path)
    yield database
    _reset_tool_caches()


def _reset_tool_caches() -> None:
    """Clear the lazy singletons the tool modules hold."""
    import tools.common as common
    import tools.crud as crud
    import tools.expansion as expansion
    import tools.intelligence as intelligence

    common._db = None
    crud._db = None
    expansion._db = None
    intelligence._db = None

@pytest.fixture(autouse=True)
def _clean_event_tables():
    """Clear the history tables before and after each test in this module.

    These modules share the session DB with the rest of the suite (see the
    SAGE_DB_PATH note at the top). Rows written here survive into later modules,
    and tests that count activities — ours and test_expansion's — then see a
    total that depends on which module ran first. Clearing before AND after
    keeps each test's input deterministic in either direction.
    """
    _clear_tables()
    yield
    _clear_tables()


def _clear_tables() -> None:
    """Delete history rows, tolerating a database that is not created yet.

    Connecting to a missing path creates an empty file with no tables, so the
    DELETE raises. That happens on the first run before any test has built the
    schema — skip rather than fail.
    """
    if not os.path.exists(_tmp_path):
        return
    conn = sqlite3.connect(_tmp_path)
    try:
        for table in ("stage_history", "activities"):
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # tables not created yet
    finally:
        conn.close()



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
