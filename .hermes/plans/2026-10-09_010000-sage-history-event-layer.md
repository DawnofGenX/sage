# Sage History Event Layer — Implementation Plan

> **For Hermes:** Use the subagent-driven-development skill to implement this plan task-by-task.
> Two subagents may run in parallel on disjoint file sets (Tasks 1-2 write `src/`,
> Tasks 4-5 write `tests/`); see the Parallelisation note.

**Goal:** Make the history tables (`stage_history`, `activities`) actually record events so
`get_deal_history`, `get_activities`, and `get_deal_timeline` return real data — and let a
follow-up insight say "no activity for 20 days" from measured history instead of a stage-name
heuristic.

**Architecture:** Add one write primitive, `record_stage_change(deal_id, from_stage, to_stage,
source)`, in `src/data/db.py`, and call it from `update_deal_stage` (the tool and the Database
method). Add `record_activity(...)` in the same file for the call/deal/followup writes. Do **not**
add a new `events` table — the existing schema already has the right columns, the existing read
tools already query it, and `schema.sql` uses `CREATE TABLE IF NOT EXISTS` so existing databases
keep working. One new MCP tool, `get_deal_timeline_events`, is the read surface for the merged
event stream; no existing tool changes behaviour.

**Tech Stack:** Python 3.14 (local venv) / 3.12 (Docker), pytest + pytest-asyncio, SQLite,
FastMCP 4.0.11, Pydantic v2. All commands below assume `cd /home/hermes/sage/mcp-server` and
`.venv/bin/python`.

---

## Current Context / Assumptions

Verified by reading the code and querying the live database (2026-10-08, commit `abfe855`):

**What exists and works:**
- `stage_history` and `activities` tables in `src/data/schema.sql` (lines 79-86, 54-63) with
  correct columns.
- `src/data/db.py` read methods: `get_stage_history` (255), `get_activities` (219),
  `get_deal_interactions` (265), `get_deal_timeline` (285).
- Tools that read history: `get_deal_history`, `get_activities`, `get_company_context` in
  `src/tools/expansion.py`.
- `src/proactive/engine.py` computes "stuck deal" from `deals.updated_at` only.
- Test suite: 333 passing, zero warnings, 8s runtime.

**The core defect (confirmed against the live DB):**
```
stage_history rows : 0     <- never written
activities rows    : 0     <- never written
deal 1 stage       : proposal
```
`update_deal_stage` in `src/data/db.py` (121-130) runs `UPDATE deals SET stage = ?` and stops. It
does **not** insert a `stage_history` row. No code path writes `activities` either. So
`get_deal_history` and `get_activities` return empty lists unconditionally, and the
`_check_stuck_deals` insight is a stage-name heuristic wearing the costume of a measurement.

**Assumed (must be re-verified before Task 1):** the repository state is `abfe855` on `master`,
working tree clean. If `git status --short` is non-empty, stop and reconcile first.

---

## Step-by-Step Tasks

### Task 1: `record_stage_change` writes stage_history

**Objective:** A stage change leaves an audit trail row.

**Files:**
- Modify: `src/data/db.py` (add one method after `update_deal_stage`, ends line 130)
- Test: `tests/test_event_layer.py` (create)

**Step 1: Write the failing test**

Create `tests/test_event_layer.py`:

```python
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
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 2 failed, 1 passed (the direct-call test fails only because `record_stage_change` does
not exist yet).

**Step 3: Implement**

In `src/data/db.py`, replace the body of `update_deal_stage` (lines 121-130) and add the new
method immediately after it:

```python
    def update_deal_stage(self, deal_id: int, stage: str) -> bool:
        conn = self._get_conn()
        deal = conn.execute(
            "SELECT stage FROM deals WHERE id = ?", (deal_id,)
        ).fetchone()
        cursor = conn.execute(
            "UPDATE deals SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (stage, deal_id),
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()

        # The audit row is written by the caller-visible wrapper, not here: this
        # method returns a bool and is not the tool boundary.
        if updated and deal is not None:
            from_stage = deal["stage"]
            if from_stage != stage:
                self.record_stage_change(deal_id, from_stage, stage, source="local")
        return updated

    def record_stage_change(
        self, deal_id: int, from_stage: str, to_stage: str, source: str = "local"
    ) -> int:
        """Append a stage transition to stage_history.

        Append-only. Nothing updates or deletes these rows: a history that can
        be edited is not a history, and this project's whole thesis is that the
        record should be trustworthy.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO stage_history (deal_id, from_stage, to_stage, changed_at, source)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)""",
            (deal_id, from_stage, to_stage, source),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id
```

Note: this requires the `source` column below. **Do not skip Task 2.**

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 3 passed.

**Step 5: Commit**

```bash
git add src/data/db.py tests/test_event_layer.py
git commit -m "feat: record stage transitions to stage_history"
```

---

### Task 2: Add `source` and `meta` columns to stage_history

**Objective:** The schema supports provenance and a machine-readable note.

**Context:** `src/data/schema.sql` lines 79-86 define `stage_history` without `source`. Task 1's
INSERT names that column, so this must land in the same commit sequence as Task 1 — **run Task 2
immediately after Task 1, before running the full suite.**

**Files:**
- Modify: `src/data/schema.sql`

**Step 1: Write the failing test**

Append to `tests/test_event_layer.py`:

```python
def test_stage_history_has_source_and_meta_columns(db, deal):
    """Existing databases must gain the columns without a manual migration."""
    cols = {
        r[1]
        for r in db._get_conn().execute("PRAGMA table_info(stage_history)").fetchall()
    }
    assert {"source", "meta"} <= cols, f"missing columns: {cols}"


def test_existing_db_gains_columns(db):
    """CREATE TABLE IF NOT EXISTS must not silently skip an ALTER on old DBs."""
    db._get_conn().execute("DROP TABLE stage_history")
    db._init_schema()  # recreate from schema.sql
    cols = {
        r[1]
        for r in db._get_conn().execute("PRAGMA table_info(stage_history)").fetchall()
    }
    assert "source" in cols
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 1-2 failed — the `source`/`meta` columns are absent.

**Step 3: Implement**

In `src/data/schema.sql`, replace the `stage_history` table (lines 79-86) with:

```sql
CREATE TABLE IF NOT EXISTS stage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER,
    from_stage TEXT,
    to_stage TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT DEFAULT 'local',
    meta TEXT,
    FOREIGN KEY (deal_id) REFERENCES deals(id)
);
```

Because the file uses `CREATE TABLE IF NOT EXISTS`, a database created before this change keeps
the old shape. Add an idempotent migration to `_init_schema` in `src/data/db.py` so both shapes
converge. Replace `_init_schema` (lines 36-42) with:

```python
    def _init_schema(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema = f.read()
        conn = self._get_conn()
        conn.executescript(schema)
        self._migrate(conn)
        conn.close()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add columns introduced after a database was first created.

        CREATE TABLE IF NOT EXISTS never alters an existing table, so a database
        written before `source`/`meta` existed would keep the old shape forever
        and every INSERT naming them would fail. Adding each column only when it
        is missing keeps this idempotent and safe on every boot.
        """
        existing = {
            row[1] for row in conn.execute("PRAGMA table_info(stage_history)").fetchall()
        }
        for column, ddl in (
            ("source", "ALTER TABLE stage_history ADD COLUMN source TEXT DEFAULT 'local'"),
            ("meta", "ALTER TABLE stage_history ADD COLUMN meta TEXT"),
        ):
            if column not in existing:
                conn.execute(ddl)
        conn.commit()
```

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 5 passed.

**Step 5: Commit**

```bash
git add src/data/schema.sql src/data/db.py tests/test_event_layer.py
git commit -m "feat: migrate stage_history with source and meta columns"
```

---

### Task 3: Route the existing sync provenance into stage changes

**Objective:** When a sync changes a deal's stage, the history says which CRM did it.

**Context:** `src/sync/local.py` writes `crm_local_deals.stage_name`. The local adapter is the
demo's sync target. **Only touch `local.py`** — the external adapters (salesforce/hubspot/
pipedrive) are not called in the demo and would need real credentials to verify.

**Files:**
- Modify: `src/sync/local.py`
- Test: `tests/test_event_layer.py` (append)

**Step 1: Write the failing test**

```python
def test_local_sync_records_stage_source(db, deal):
    """A sync that moves a stage must attribute it, or history shows 'local'."""
    import asyncio

    from sync.local import LocalCRMSync
    from tools.sync import sync_to_crm

    db.update_deal_stage(deal, "negotiation")
    asyncio.run(sync_to_crm(
        {"title": "History Deal", "stage": "proposal", "amount": 1000, "contact_id": 1},
        target="local",
        idempotency_key="stage-source-1",
    ))
    rows = db.get_stage_history(deal)
    assert any(r["source"] == "crm_local" for r in rows), rows
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py::test_local_sync_records_stage_source -q --no-header`

Expected: FAIL — no row carries `source == "crm_local"`.

**Step 3: Implement**

Read `src/sync/local.py` first and follow its existing adapter style. Add, after the deal insert
succeeds:

```python
        # A synced stage change is attributable: name the CRM that moved it, or
        # the audit trail claims every change was local.
        if getattr(self, "_db", None) is not None and stage_changed:
            self._db.record_stage_change(
                local_deal_id, previous_stage, stage, source="crm_local"
            )
```

Only include the code shapes that exist in the file; if `LocalCRMSync` has no `_db`, use the
Database directly via `from data.db import Database` and `os.environ["SAGE_DB_PATH"]`, matching
how `src/tools/common.py` resolves the path.

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 6 passed.

**Step 5: Commit**

```bash
git add src/sync/local.py tests/test_event_layer.py
git commit -m "feat: attribute synced stage changes to the local CRM"
```

---

### Task 4: `record_activity` wires the three remaining writers

**Objective:** Contact/deal/followup changes append to `activities` so `get_activities` works.

**Files:**
- Modify: `src/data/db.py` (add method)
- Modify: `src/tools/crud.py` (call it from the three mutation tools)
- Test: `tests/test_event_layer.py` (append)

**Step 1: Write the failing tests**

```python
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
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 3 failed.

**Step 3: Implement `record_activity` in `src/data/db.py`** (after `record_stage_change`):

```python
    def record_activity(
        self,
        type: str,
        description: str,
        contact_id: int | None = None,
        deal_id: int | None = None,
        source: str = "local",
    ) -> int:
        """Append an activity row.

        Append-only, like stage_history. `activities` was read-only schema until
        now: get_activities queried a table nothing ever wrote to.
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO activities (contact_id, deal_id, type, description, source)
               VALUES (?, ?, ?, ?, ?)""",
            (contact_id, deal_id, type, description, source),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id
```

Add the `source` column to `activities` in `src/data/schema.sql` the same way Task 2 did for
`stage_history`, and extend `_migrate` to include it:

```python
        existing_activities = {
            row[1] for row in conn.execute("PRAGMA table_info(activities)").fetchall()
        }
        if "source" not in existing_activities:
            conn.execute("ALTER TABLE activities ADD COLUMN source TEXT DEFAULT 'local'")
```

Then call it from `update_deal_stage` in `src/data/db.py` — extend the block added in Task 1:

```python
        if updated and deal is not None:
            from_stage = deal["stage"]
            if from_stage != stage:
                self.record_stage_change(deal_id, from_stage, stage, source="local")
                self.record_activity(
                    deal_id=deal_id,
                    type="stage_change",
                    description=f"{from_stage} -> {stage}",
                    source="local",
                )
```

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 9 passed.

**Step 5: Commit**

```bash
git add src/data/db.py src/data/schema.sql tests/test_event_layer.py
git commit -m "feat: write activity rows on state changes"
```

---

### Task 5: Stuck-deal insight measures from history, not stage names

**Objective:** The "no activity for N days" insight becomes a measurement.

**Context:** `src/proactive/engine.py` `_check_stuck_deals` (lines 80-95) reads
`deals.updated_at`. A deal can sit at `negotiation` forever and read correctly, or be actively
worked at `lead` and be flagged. With history now written, elapsed time can be measured from the
last recorded event.

**Files:**
- Modify: `src/proactive/engine.py`
- Test: `tests/test_event_layer.py` (append)

**Step 1: Write the failing test**

```python
def test_stuck_deal_uses_history_not_stage_name(db):
    """A deal at 'lead' with 30 days of silence is stuck; 'lead' must not be magic."""
    from datetime import datetime, timedelta

    from proactive.engine import ProactiveEngine

    contact_id = db.create_contact({"name": "Stuck Contact"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Stuck Deal", "stage": "lead"})

    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    db._get_conn().execute(
        "UPDATE deals SET updated_at = ? WHERE id = ?", (old, deal_id)
    )
    db._get_conn().commit()

    engine = ProactiveEngine(db=db, llm=object())
    alerts = engine._check_stuck_deals()
    assert any("30 days" in a for a in alerts), alerts


def test_active_deal_not_flagged(db):
    """History must protect a deal that was just touched."""
    from datetime import datetime, timedelta

    from proactive.engine import ProactiveEngine

    contact_id = db.create_contact({"name": "Active Contact"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Active Deal", "stage": "lead"})
    db.record_activity(deal_id=deal_id, type="call", description="spoke today")

    engine = ProactiveEngine(db=db, llm=object())
    alerts = engine._check_stuck_deals()
    assert not any("Active Deal" in a for a in alerts), alerts
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header -k stuck`

Expected: `test_active_deal_not_flagged` FAILS (the current code flags any `lead`/`negotiation`
deal regardless of activity).

**Step 3: Implement**

Replace `_check_stuck_deals` (lines 80-95) in `src/proactive/engine.py`:

```python
    def _check_stuck_deals(self) -> list:
        """Check for deals with no recorded activity in 14+ days.

        Previously this flagged every deal whose *stage name* was 'lead' or
        'negotiation', which misreported in both directions: an actively-worked
        early-stage deal was flagged, and a stalled negotiation-stage deal could
        look fine. With stage_history and activities now written, elapsed
        silence is measured from the last recorded event.
        """
        deals = self.db.get_all_deals()
        now = datetime.now()
        alerts = []
        for d in deals:
            last_event = self._last_activity_time(d["id"])
            if last_event is None:
                # No history at all: fall back to the deal's own timestamp,
                # and say so rather than inventing an activity date.
                last_event = self._parse_date(d.get("updated_at"))
                if last_event is None:
                    continue
            days_inactive = (now - last_event).days
            if days_inactive >= 14:
                alerts.append(
                    f"Stuck deal: {d['title']} (no activity for {days_inactive} days)"
                )
        return alerts

    def _last_activity_time(self, deal_id: int) -> datetime | None:
        """Most recent recorded event for a deal, from stage_history and activities."""
        latest = None
        for row in self.db.get_stage_history(deal_id):
            stamp = self._parse_date(row.get("changed_at"))
            if stamp and (latest is None or stamp > latest):
                latest = stamp
        for row in self.db.get_activities(deal_id=deal_id):
            stamp = self._parse_date(row.get("created_at"))
            if stamp and (latest is None or stamp > latest):
                latest = stamp
        return latest
```

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 11 passed.

**Step 5: Commit**

```bash
git add src/proactive/engine.py tests/test_event_layer.py
git commit -m "fix: measure stuck deals from recorded history, not stage names"
```

---

### Task 6: New MCP tool `get_deal_timeline_events`

**Objective:** Expose the merged event stream as a first-class typed tool.

**Context:** `src/tools/expansion.py` already has `get_deal_history` (stage changes) and
`get_activities`. Adding a merged view avoids changing their contracts.

**Files:**
- Create: none (add to existing modules)
- Modify: `src/tools/expansion.py`, `src/tools/schemas.py`, `src/tools/registry.py`
- Test: `tests/test_event_layer.py` (append)

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_get_deal_timeline_events_merges_stage_and_activity(db, deal):
    from tools.expansion import get_deal_timeline_events

    db.update_deal_stage(deal, "proposal")
    result = await get_deal_timeline_events(deal)
    kinds = [e["type"] for e in result["events"]]
    assert "stage_change" in kinds, kinds
    assert result["count"] == len(result["events"])
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py::test_get_deal_timeline_events_merges_stage_and_activity -q --no-header`

Expected: FAIL — `ImportError: cannot import name 'get_deal_timeline_events'`.

**Step 3: Implement**

In `src/tools/schemas.py`, add the model (follow the `_DictAccessMixin` convention every other
model uses):

```python
class TimelineEvent(_DictAccessMixin):
    """One entry in a deal's merged event stream."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(..., description="'stage_change' or 'activity'.")
    timestamp: str = Field(..., description="When the event was recorded.")
    data: dict[str, Any] = Field(default_factory=dict, description="Full source row.")


class TimelineResponse(_DictAccessMixin):
    """Output of get_deal_timeline_events."""

    model_config = ConfigDict(extra="allow")

    events: list[TimelineEvent] = Field(default_factory=list)
    count: int = Field(0, description="Number of events returned.")
```

In `src/tools/expansion.py`, add:

```python
async def get_deal_timeline_events(deal_id: int) -> TimelineResponse:
    """Get a deal's merged event stream: stage changes and activities in order.

    Read-only view over the rows written by the event layer. stage_history and
    activities are append-only, so this ordering is durable history rather than
    a reconstruction from current state.
    """
    db = _get_db()
    events = []
    for row in db.get_stage_history(deal_id):
        events.append(
            {"type": "stage_change", "timestamp": row.get("changed_at"), "data": row}
        )
    for row in db.get_activities(deal_id=deal_id):
        events.append(
            {"type": "activity", "timestamp": row.get("created_at"), "data": row}
        )
    events.sort(key=lambda e: e.get("timestamp") or "")
    return TimelineResponse.model_validate({"events": events, "count": len(events)})
```

Add `get_deal_timeline_events` to the import block and `ALL_TOOLS` in `src/tools/registry.py`,
and import `TimelineResponse` in `expansion.py`'s `tools.schemas` import.

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_event_layer.py -q --no-header`

Expected: 12 passed.

**Step 5: Verify tool count and commit**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'src'); from tools.registry import ALL_TOOLS; print(len(ALL_TOOLS),'tools')"`

Expected: `24 tools`

```bash
git add src/tools/expansion.py src/tools/schemas.py src/tools/registry.py tests/test_event_layer.py
git commit -m "feat: add get_deal_timeline_events MCP tool"
```

---

## Tests / Validation

Every task above is TDD: failing test first, verify the failure message names the missing
behaviour, implement, verify pass, commit.

After Tasks 1-6, run the full suite:

```bash
.venv/bin/python -m pytest tests/ -q --no-header
```

Expected: `345 passed` (333 existing + 12 new). **Any regression is a stop-and-report**, not a
"fix the test later".

Then the warning check must still be clean:

```bash
.venv/bin/python -m pytest tests/ -q --no-header 2>&1 | grep -c PydanticSerialization
```

Expected: `0`

Then the end-to-end script against the running stack (must be rebuilt after the schema change):

```bash
docker compose build mcp-server && docker compose up -d
.venv/bin/python /home/hermes/.hermes/cache/scratch/e2e_full_stack.py
```

Expected: `RESULT: ALL PASS`, and `sage://pipeline/status` still returning JSON.

Finally, prove the defect is actually closed against the live database — this is the acceptance
criterion for the whole plan:

```bash
docker exec sage-mcp-server-1 python -c "
import sqlite3
c = sqlite3.connect('/app/sage.db')
print('stage_history:', c.execute('SELECT COUNT(*) FROM stage_history').fetchone()[0])
"
```

Expected: a count **greater than 0** (was 0). A still-zero count means the write layer did not
land and the plan is not done.

---

## Risks, Tradeoffs, and Open Questions

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Existing `sage.db` lacks `source`/`meta` columns | Certain | Every INSERT naming them fails | Task 2's `_migrate()`, idempotent on every boot |
| `record_stage_change` on a nonexistent deal | Low | Orphan history row | `update_deal_stage` only writes when `rowcount > 0` |
| Task 3 (sync attribution) touches an adapter with no tests | Medium | Silent breakage | Read `local.py` first; only wire the demo target; if the shape does not fit, skip Task 3 and record it in the friction log rather than guessing |
| Insight wording change breaks a doc claim | Medium | Docs contradict behaviour | `docs/submission.md` and `docs/demo-script.md` mention "stuck" — re-read both after Task 5 and correct the wording to match the measured behaviour |
| `stage_history` grows unboundedly | Medium | Slow queries at scale | Accept for the demo; note in the friction log. No pagination until there is evidence of a problem (YAGNI) |

**Open questions (resolved by default, note each in the artifact):**
1. **New `events` table vs existing `stage_history`/`activities`** — chose existing tables (no
   migration, existing read tools start working). Rejected an `events` table as leaving two dead
   tables and two query paths.
2. **Append-only vs mutable history** — chose append-only. A mutable history is not history.
3. **Should `get_deal_timeline_events` replace `get_deal_history`?** — No. Adding a tool is
   non-breaking; changing an existing contract is not. Tool count goes 23 → 24, and
   `docs/submission.md` / `submission-final-checklist.md` / `README.md` all say 23 and must be
   updated to 24 in the same commit as Task 6.

---

## Parallelisation

- **Parallelisable:** Tasks 1-2 (both `src/data/` + `tests/test_event_layer.py` — assign to one
  subagent) and Tasks 4-5 (`src/tools/crud.py`, `src/data/db.py`, `src/proactive/engine.py`,
  `tests/test_event_layer.py` — assign to a second subagent). **They share `tests/test_event_layer.py`,
  so the second subagent must append, never overwrite, and Tasks 4-5 must run after Tasks 1-2.**
- **Sequential:** Task 3 (needs the local sync path) and Task 6 (needs the models and registry
  from the earlier tasks).
- **Ownership:** the orchestrator owns `docs/*` and the acceptance run; subagents create no
  files outside their assigned paths.
