"""The pipeline board must read live data, not hardcoded samples.

App.tsx seeded `deals`, `contacts`, and `activities` from SAMPLE_* constants
and never called the API for them. The board therefore showed five invented
deals with invented sentiment while the real CRM sat behind the same server.

Root cause was an API gap: there was no tool that lists deals. get_pipeline_health
returns aggregate counts plus *stuck* deals only; get_company_context works one
company at a time. This file pins the tool that closes the gap and the mapping
that consumes it.
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAGE_DB_PATH"] = _tmp.name

from data.db import Database  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """An isolated Database, with the tool layer pointed at it.

    The tool modules resolve their DB through tools/common._get_db(), which
    caches a singleton keyed to SAGE_DB_PATH. Setting expansion._db alone is not
    enough — _get_db() returns the cached one, so the test silently reads the
    real database. Point the env var at a temp file and clear the cache instead.
    """
    target = tmp_path / "deals-tool.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(target))

    import tools.common as common
    import tools.expansion as expansion

    common._db = None
    expansion._db = None

    database = Database(db_path=str(target))
    # Hand the tool layer this exact instance, and keep the shared cache in step.
    common._db = database
    expansion._db = database
    yield database
    common._db = None
    expansion._db = None


def test_api_tools_never_drifts_from_the_registry():
    """Every registered tool must be callable over REST.

    TOOLS used to be a hand-written dict of 22 imports. The registry grew tools
    it never heard about, so /api/tools/{name} 404'd while the MCP surface
    served them fine — run_agentic_loop, get_deal_timeline_events and get_deals
    were all unreachable over REST that way, which is why the pipeline board
    fell back to hardcoded sample deals.

    The map is now derived from ALL_TOOLS. This test asserts the derivation
    holds rather than trusting it.
    """
    from api.rest import TOOLS
    from tools.registry import ALL_TOOLS

    assert TOOLS, "REST tool map is empty"
    assert len(TOOLS) == len(ALL_TOOLS), (
        f"REST exposes {len(TOOLS)} tools but the registry has {len(ALL_TOOLS)}"
    )
    missing = [fn.__name__ for fn in ALL_TOOLS if fn.__name__ not in TOOLS]
    assert not missing, f"registered but not reachable over REST: {missing}"


def test_newly_registered_tool_is_reachable_over_rest():
    """The specific regression: a tool the frontend needs must not 404.

    The pipeline board calls get_deals. If TOOLS drifts from the registry
    again, this fails before a judge sees an empty board.
    """
    from api.rest import TOOLS
    from tools.expansion import get_deals

    assert "get_deals" in TOOLS, "get_deals is not reachable over REST"
    assert TOOLS["get_deals"] is get_deals


@pytest.mark.asyncio
async def test_get_deals_returns_every_deal(db):
    from tools.expansion import get_deals

    contact_id = db.create_contact({"name": "Board Contact", "company": "Acme"})
    db.create_deal({"contact_id": contact_id, "title": "Deal A", "value": 100, "stage": "lead"})
    db.create_deal({"contact_id": contact_id, "title": "Deal B", "value": 200, "stage": "won"})

    result = await get_deals()

    assert result["total"] == 2, result
    titles = sorted(d["title"] for d in result["deals"])
    assert titles == ["Deal A", "Deal B"], titles


@pytest.mark.asyncio
async def test_get_deals_carries_contact_name(db):
    """The board renders contactName; without it every card is blank."""
    from tools.expansion import get_deals

    contact_id = db.create_contact({"name": "Sarah Chen", "company": "Acme Corp"})
    db.create_deal({"contact_id": contact_id, "title": "Acme Deal", "value": 50000, "stage": "proposal"})

    result = await get_deals()

    assert result["deals"][0]["contact_name"] == "Sarah Chen", result["deals"][0]


@pytest.mark.asyncio
async def test_get_deals_flags_stuck_deals(db):
    """The board's red 'Stuck' badge must come from the same measurement the
    proactive engine uses, not a stage-name guess."""
    from datetime import datetime, timedelta

    from tools.expansion import get_deals

    contact_id = db.create_contact({"name": "Stuck Contact", "company": "Globex"})
    deal_id = db.create_deal(
        {"contact_id": contact_id, "title": "Stuck Deal", "value": 1000, "stage": "negotiation"}
    )
    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    conn = db._get_conn()
    conn.execute("UPDATE deals SET updated_at = ? WHERE id = ?", (old, deal_id))
    conn.commit()

    result = await get_deals()

    stuck = [d for d in result["deals"] if d.get("is_stuck")]
    assert len(stuck) == 1, result
    assert stuck[0]["title"] == "Stuck Deal"


@pytest.mark.asyncio
async def test_get_deals_empty_database_returns_empty(db):
    from tools.expansion import get_deals

    result = await get_deals()

    assert result["deals"] == []
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_get_deals_is_registered_as_a_tool():
    """A tool the registry does not know about is unreachable over MCP."""
    from tools.expansion import get_deals
    from tools.registry import ALL_TOOLS

    assert get_deals in ALL_TOOLS
