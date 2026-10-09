"""get_deal_timeline_events — merged stage + activity stream.

The read tools get_deal_history and get_activities query stage_history and
activities. Those tables were write-never until the event layer landed, so both
returned empty lists. This tool merges them into one ordered stream.
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
    contact_id = db.create_contact({"name": "Timeline Contact"})
    return db.create_deal({"contact_id": contact_id, "title": "Timeline Deal"})


@pytest.mark.asyncio
async def test_get_deal_timeline_events_merges_stage_and_activity(db, deal):
    from tools.expansion import get_deal_timeline_events

    db.update_deal_stage(deal, "proposal")
    result = await get_deal_timeline_events(deal)
    kinds = [e["type"] for e in result["events"]]
    assert "stage_change" in kinds, kinds
    assert result["count"] == len(result["events"])
    assert result["count"] >= 1


@pytest.mark.asyncio
async def test_timeline_is_ordered_oldest_first(db, deal):
    from tools.expansion import get_deal_timeline_events

    db.record_stage_change(deal, "lead", "proposal", source="local")
    db.record_activity(deal_id=deal, type="call", description="spoke")
    result = await get_deal_timeline_events(deal)
    stamps = [e["timestamp"] for e in result["events"]]
    assert stamps == sorted(stamps), f"events out of order: {stamps}"


@pytest.mark.asyncio
async def test_timeline_carries_the_full_source_row(db, deal):
    """The consumer should not need a second query to see the payload."""
    from tools.expansion import get_deal_timeline_events

    db.record_stage_change(deal, "lead", "qualified", source="salesforce")
    result = await get_deal_timeline_events(deal)
    row = result["events"][0]
    assert row["data"]["to_stage"] == "qualified"
    assert row["data"]["source"] == "salesforce"


@pytest.mark.asyncio
async def test_timeline_is_empty_for_unknown_deal(db):
    """No fabricated history for a deal that does not exist."""
    from tools.expansion import get_deal_timeline_events

    result = await get_deal_timeline_events(999999)
    assert result["events"] == []
    assert result["count"] == 0


def test_timeline_tool_is_registered():
    """It must be in ALL_TOOLS or no MCP client can call it."""
    from tools.registry import ALL_TOOLS

    from tools.expansion import get_deal_timeline_events
    assert get_deal_timeline_events in ALL_TOOLS
