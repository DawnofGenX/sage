"""Stuck-deal insight must measure inactivity, not guess from stage names.

The previous implementation flagged any deal whose stage was 'lead' or
'negotiation'. That misreported both directions: an actively-worked early-stage
deal got flagged, and a stalled negotiation-stage deal could look fine.
With stage_history and activities written, elapsed silence is measurable.
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

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
