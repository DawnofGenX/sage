# Seed On First Boot, Not At Image Build — Implementation Plan

> **For Hermes:** Use subagent-driven-development to implement this plan task-by-task.
> Tasks 1-2 are sequential (both touch `src/data/seed.py`); Task 3 is independent.
> Do not run Task 3 before Task 2 passes.

**Goal:** Move demo-data seeding from image build time to container start, so a
pre-existing `sage-data` volume — which masks the image's `/app/data` and leaves the
database empty — is seeded on first boot instead of silently shipping an empty CRM.

**Architecture:** Add an idempotent `ensure_seeded(db)` function to `src/data/seed.py`
that seeds only when the target database has no contacts, and an `entrypoint.sh` that
runs it before uvicorn. Keep `main()` and `python -m src.data.seed` working unchanged
for local dev and CI. Remove the build-time `RUN ... seed` from the Dockerfile, since
seeding at build time cannot reach a volume that already exists.

**Tech Stack:** Python 3.14 (local venv) / 3.12 (Docker), pytest + pytest-asyncio,
SQLite, FastMCP 4.0.11, Pydantic v2, Docker Compose. All commands assume
`cd /home/hermes/sage/mcp-server` and `.venv/bin/python` unless stated otherwise.

---

## Current Context / Assumptions

Verified by reading the code and running the container (2026-10-09, HEAD `5de98a0`).

**What works today:**
- `src/data/seed.py` has `seed(db) -> dict` (idempotent by contact title) and
  `main()` which prints a summary. Both are exercised by `tests/test_seed.py`.
- `SAGE_DB_PATH` is resolved by `Database()` (fixed in `5de98a0`) and set to
  `/app/data/sage.db` in the Dockerfile, so writes now land on the volume.
- Docker Compose mounts `sage-data` at `/app/data`.
- Local dev path (`README.md:32`) and the video checklist
  (`docs/video-recording-checklist.md:78`) both instruct `python -m src.data.seed`.

**The defect this plan removes (confirmed against a live container):**

`mcp-server/Dockerfile:25` runs `RUN python -m src.data.seed || true`. That writes
`/app/data/sage.db` **into the image layer**. Docker only copies image contents into
a named volume the **first time** that volume is created. So:

- Fresh volume (no prior `docker compose up`) → volume populated, container seeded.
  This is the only path that works today.
- Pre-existing volume (upgrade, or any `docker compose up` after the volume was
  created by an older image) → the volume's own `/app/data` (holding only a 0-byte
  `.gitkeep`) masks the image's file. The DB has no tables, every demo surface is
  empty, and nothing reports a problem.

Observed directly: after `docker volume rm` + rebuild + `up`, the volume DB had 11
tables and 10 contacts. Before removing the stale volume, the same file was 0 bytes
with no tables. The `|| true` on line 25 is what hides it — a failure there looks
like a success.

A second, subtler issue: the seed runs **at build**, so it cannot know whether it is
targeting a volume that will exist later. Seeding at **container start** can check the
actual runtime database and act on what it finds.

**Assumed (re-verify before Task 1):** repo is at `5de98a0` on `master`, working tree
clean except `.hermes/plans/`, suite green at **360 passed**. If `git status --short`
shows anything else, stop and reconcile first.

---

## Step-by-Step Tasks

### Task 1: `ensure_seeded` — idempotent first-boot seeding

**Objective:** A function that seeds only when the database is empty, and reports what
it did.

**Files:**
- Modify: `src/data/seed.py` (add one function after `seed()`)
- Test: `tests/test_seed_on_demand.py` (create)

**Step 1: Write the failing test**

Create `tests/test_seed_on_demand.py`:

```python
"""Seed-on-first-boot: seed only when the database is empty.

Build-time seeding cannot reach a pre-existing volume — the volume's own
/app/data masks the image's copy — so the container needs to seed at start,
against the database it actually finds.
"""
import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAGE_DB_PATH"] = _tmp.name

from data.db import Database  # noqa: E402
from data.seed import ensure_seeded  # noqa: E402


@pytest.fixture
def db():
    return Database(db_path=_tmp.name)


def test_ensure_seeded_populates_an_empty_database(db):
    result = ensure_seeded(db)
    assert result["seeded"] is True
    assert result["contacts_created"] > 0
    assert db.get_all_contacts(), "seed ran but no contacts exist"


def test_ensure_seeded_skips_a_populated_database(db):
    """The whole point: an existing database is not overwritten."""
    ensure_seeded(db)
    before = len(db.get_all_contacts())

    # A record the seed does not know about.
    db.create_contact({"name": "Operator Added Client", "company": "Real Co"})

    result = ensure_seeded(db)
    assert result["seeded"] is False
    assert result["contacts_created"] == 0
    after = db.get_all_contacts()
    assert len(after) == before + 1, "ensure_seeded must not touch existing data"
    assert any(c["name"] == "Operator Added Client" for c in after), (
        "existing rows must survive"
    )


def test_ensure_seeded_is_idempotent(db):
    first = ensure_seeded(db)
    second = ensure_seeded(db)
    assert first["seeded"] is True
    assert second["seeded"] is False
    assert second["contacts_created"] == 0


def test_ensure_seeded_creates_the_schema_when_missing(db):
    """A volume holding only .gitkeep has no tables at all — the observed case."""
    conn = db._get_conn()
    conn.execute("DROP TABLE IF EXISTS contacts")
    conn.commit()
    conn.close()

    result = ensure_seeded(db)
    assert result["seeded"] is True, "an empty-but-schema-less DB is still empty"
    assert db.get_all_contacts()
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_seed_on_demand.py -q --no-header -p no:cacheprovider`

Expected: 1 error / 4 failed — `ImportError: cannot import name 'ensure_seeded'`.

**Step 3: Implement**

Add to `src/data/seed.py`, immediately after the `seed()` function:

```python
def ensure_seeded(db: "Database") -> dict:
    """Seed demo data only when the database is empty.

    `seed()` is idempotent by title but still queries and inserts on every
    call. `ensure_seeded` answers the container-start question directly: does
    this database have anything in it? If yes, leave it alone — a volume with
    real data must never be re-seeded or trimmed. If no, seed.

    This exists because build-time seeding cannot reach a volume that already
    exists: the volume's own /app/data masks the image's copy, so the built-in
    seed silently does nothing on upgrade.

    Args:
        db: The Database to inspect and possibly seed.

    Returns:
        A dict with `seeded` (bool), `reason` (str), and the seed() counters
        when seeding ran. Never raises on an unreadable database: a container
        that cannot start because demo data is missing is worse than one that
        starts empty and says so.
    """
    try:
        existing = len(db.get_all_contacts())
    except Exception as exc:  # noqa: BLE001 — missing tables, corrupt file, etc.
        # No schema yet is the normal first-boot case, not an error worth
        # failing startup over. Constructing the schema is Database's job; it
        # runs in __init__, which has already happened by now.
        return {
            "seeded": False,
            "reason": f"could not read contacts: {type(exc).__name__}: {exc}",
        }

    if existing:
        return {
            "seeded": False,
            "reason": f"database already has {existing} contact(s)",
        }

    result = seed(db)
    return {
        "seeded": True,
        "reason": "database was empty",
        **result,
    }
```

`seed()` already takes a `Database`, so `-> "Database"` is only needed if `seed.py`
does not import it at module level; drop the quotes if the import already exists.

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_seed_on_demand.py -q --no-header -p no:cacheprovider`

Expected: 4 passed.

**Step 5: Commit**

```bash
cd /home/hermes/sage && git add mcp-server/src/data/seed.py mcp-server/tests/test_seed_on_demand.py
git commit -m "feat: add ensure_seeded for first-boot seeding"
```

---

### Task 2: Entrypoint that seeds before uvicorn starts

**Objective:** The container seeds itself on first boot, against the real runtime
database.

**Files:**
- Create: `mcp-server/entrypoint.sh`
- Modify: `mcp-server/Dockerfile`

**Step 1: Write the failing test**

Append to `tests/test_seed_on_demand.py`:

```python
def test_entrypoint_script_exists_and_is_executable():
    """The boot path must exist in the image, not just in a doc."""
    import stat
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "entrypoint.sh"
    assert script.exists(), "entrypoint.sh is missing"
    assert script.stat().st_mode & stat.S_IXUSR, "entrypoint.sh is not executable"


def test_dockerfile_seeds_at_runtime_not_build_time():
    """A build-time RUN ... seed cannot reach a volume that already exists."""
    from pathlib import Path

    dockerfile = (
        Path(__file__).resolve().parent.parent / "Dockerfile"
    ).read_text()
    assert "RUN python -m src.data.seed" not in dockerfile, (
        "build-time seed stays: it only works on a fresh volume"
    )
    assert "entrypoint.sh" in dockerfile, "the runtime entrypoint is not wired in"
```

**Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_seed_on_demand.py -q --no-header -p no:cacheprovider`

Expected: 2 failed — the script does not exist and the Dockerfile still has the
build-time seed.

**Step 3: Implement**

Create `mcp-server/entrypoint.sh`:

```bash
#!/bin/sh
# Seed on first boot, then start the API.
#
# Seeding at image build time writes into the image layer, and a named volume
# only receives image contents the first time it is created. On an existing
# volume the volume's own /app/data masks the image's copy, so the built-in
# seed silently did nothing and the demo surfaces came up empty.
#
# Seeding here runs against the database the container actually sees.
set -e

echo "[entrypoint] checking whether the database needs seeding..."

# `-e .` was installed at build time, so `src` and the package are importable.
python - <<'PY'
import json
import sys

from data.db import Database
from data.seed import ensure_seeded

result = ensure_seeded(Database())
print("[entrypoint] seed:", json.dumps(result, default=str))
PY

echo "[entrypoint] starting uvicorn..."
exec python -m uvicorn src.api.rest:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Set the executable bit:

```bash
chmod +x mcp-server/entrypoint.sh
```

In `mcp-server/Dockerfile`, replace the seed line and its comment block
(currently the `RUN python -m src.data.seed || true` step, with the
`# Seed so the container is demo-ready...` comment above it) with:

```dockerfile
ENV SAGE_DB_PATH=/app/data/sage.db
```

…and replace the CMD with the entrypoint:

```dockerfile
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV SAGE_DB_PATH=/app/data/sage.db
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
```

Keep the `COPY entrypoint.sh` line **after** the `pip install -e .` step so the
file tools it needs are present.

**Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/test_seed_on_demand.py -q --no-header -p no:cacheprovider`

Expected: 6 passed.

**Step 5: Verify the entrypoint itself runs**

Run from `mcp-server/` with a throwaway database:

```bash
cd /home/hermes/sage/mcp-server
rm -f /tmp/ep.db
SAGE_DB_PATH=/tmp/ep.db PORT=8001 sh entrypoint.sh &
sleep 6
curl -s localhost:8001/api/health
kill %1
```

Expected: `{"status":"ok","server":"sage","version":"1.0.0"}` and an
`[entrypoint] seed: ...` line showing `"seeded": true` on the first run.

**Step 6: Commit**

```bash
cd /home/hermes/sage && git add mcp-server/entrypoint.sh mcp-server/Dockerfile mcp-server/tests/test_seed_on_demand.py
git commit -m "feat: seed on first boot instead of at image build"
```

---

### Task 3: Docs, friction entry, and the upgrade note

**Objective:** Every document that mentions seeding says the true thing.

**Files:**
- Modify: `docs/deployment.md`
- Modify: `docs/friction-log.md`
- Modify: `README.md`
- Modify: `.gitignore` (only if the ephemeral `sage.db` is untracked)

**Step 1: Write the failing check**

There is no test for docs; the gate is a grep that must come back clean.

Run:

```bash
cd /home/hermes/sage
grep -rn "seeds demo data at build time\|stored in a Docker volume" docs/ README.md
```

Expected before the fixes: at least the `docs/deployment.md` lines this plan
supersedes. After: no output.

**Step 2: Update `docs/deployment.md`**

Replace the `### Persistent Data` section's build-time-seed paragraphs with
text describing first-boot seeding, keeping the existing `SAGE_DB_PATH`
warning and the `docker compose down -v` reset instructions. State plainly
that upgrading an existing deployment is now handled by the entrypoint: the
next `docker compose up` seeds the database if it is empty, so the manual
`down -v` this plan superseded is no longer required.

**Step 3: Add a friction-log entry**

Append entry 18 to `docs/friction-log.md` (after entry 17), following the
existing `| Field | Details |` format:

| Field | Details |
|-------|---------|
| **Task** | Seed the demo database so the container is demo-ready |
| **Expected** | `docker compose up` produces a container with contacts and deals |
| **Actual** | The Dockerfile seeded at **build** time, which writes into the image layer. A named volume only receives image contents when first created, so an existing volume's `/app/data` (0-byte `.gitkeep`) masked the image's copy. Fresh volume: seeded. Existing volume: no tables, every demo surface empty, `\|\| true` hiding the failure. |
| **Severity** | High |
| **Fix** | `ensure_seeded(db)` seeds only when the database is empty, called from `entrypoint.sh` before uvicorn. Build-time seed removed. |
| **Suggestion** | Never seed (or migrate) a database at image build time when the data lives on a volume mounted at runtime — build-time writes cannot see it. |

Add `| 18 | Volume masked build-time seed | High | Fixed — seed on first boot |` to the summary table.

**Step 4: Update `README.md`**

The Quick Start runs `python -m src.data.seed` then uvicorn directly. It stays
correct (the seed command still exists), but add one line noting the container
path needs no manual seed:

```markdown
The Docker path needs no manual seed — `entrypoint.sh` seeds on first boot.
```

**Step 5: Verify and commit**

Run the grep from Step 1 again. Expected: no output.

Run: `.venv/bin/python -m pytest tests/ -q --no-header -p no:cacheprovider 2>&1 | tail -2`
Expected: `366 passed` (360 + 6 new).

```bash
cd /home/hermes/sage && git add docs/deployment.md docs/friction-log.md README.md
git commit -m "docs: describe first-boot seeding; add friction entry 18"
```

---

## Tests / Validation

Every code task above is TDD: failing test first, verify the failure message names the
missing behaviour, implement, verify pass, commit.

**Full suite after Tasks 1-3:**

```bash
cd /home/hermes/sage/mcp-server && .venv/bin/python -m pytest tests/ -q --no-header
```

Expected: **366 passed**.

**Warning check must stay clean:**

```bash
.venv/bin/python -m pytest tests/ -q --no-header 2>&1 | grep -c PydanticSerialization
```

Expected: `0`

**Docker acceptance — the case that was broken.** This is the plan's real gate; a
passing pytest suite does not prove it:

```bash
cd /home/hermes/sage
docker compose build mcp-server

# Case 1: a volume created by an OLD image (the defect). Simulate by creating
# the volume path with only a .gitkeep, then starting.
docker volume rm sage_sage-data 2>/dev/null
docker run --rm -v sage_sage-data:/v alpine sh -c 'mkdir -p /v && touch /v/.gitkeep'
docker compose up -d
sleep 12
docker exec sage-mcp-server-1 python -c "
import sqlite3
c = sqlite3.connect('/app/data/sage.db')
print('contacts:', c.execute('SELECT COUNT(*) FROM contacts').fetchone()[0])
"
```

Expected: `contacts: 10` — **not** `0`, and not a `no such table` error. This is
the exact scenario that failed before this plan.

```bash
# Case 2: an existing volume with real data must be left alone.
curl -s -X POST localhost:8000/api/tools/create_contact -H 'Content-Type: application/json' \
  -d '{"name": "Operator Client", "company": "Real Co"}'
docker compose restart mcp-server
sleep 12
docker exec sage-mcp-server-1 python -c "
import sqlite3
c = sqlite3.connect('/app/data/sage.db')
n = c.execute(\"SELECT COUNT(*) FROM contacts WHERE name='Operator Client'\").fetchone()[0]
print('operator row survives restart:', n == 1)
"
```

Expected: `operator row survives restart: True`

**End-to-end script, twice consecutively (must be idempotent):**

```bash
cd /home/hermes/sage/mcp-server
.venv/bin/python /home/hermes/.hermes/cache/scratch/e2e_full_stack.py
.venv/bin/python /home/hermes/.hermes/cache/scratch/e2e_full_stack.py
```

Expected: `RESULT: ALL PASS` both times.

**Log check — the entrypoint must report what it did rather than stay silent:**

```bash
docker logs sage-mcp-server-1 2>&1 | grep -E "entrypoint\]" | head -4
```

Expected lines like `[entrypoint] seed: {"seeded": false, "reason": "database
already has 10 contact(s)"}` on a warm start, and `"seeded": true` on a cold one.

---

## Risks, Tradeoffs, and Open Questions

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Seed runs on every boot and slows startup | Certain | Negligible | `ensure_seeded` short-circuits on one `COUNT(*)`; measure the cold-vs-warm log lines to confirm |
| Two containers race to seed | Low | Duplicate contacts | `seed()` is idempotent by title and SQLite serialises writes; the demo runs one replica. Note it rather than adding a migration tool (YAGNI) |
| Entrypoint drops `exec`, so uvicorn is not PID 1 and SIGTERM is mishandled | Medium | Slow shutdown, `docker stop` waits for the timeout | Use `exec python -m uvicorn ...` (the script above does) and verify `docker stop` completes promptly |
| A read-only or corrupt DB makes startup fail | Low | Container crash-loops | `ensure_seeded` returns a reason instead of raising; Task 1's exception path covers it |
| `render.yaml` deploy path is unaffected | High | Looks like a regression | Render has no volume and no entrypoint, so it needs no seeding. **Do not** add one there without a real volume to seed |

**Open questions (resolved by default, note each in the artifact):**
1. **Keep `python -m src.data.seed`?** Yes. `README.md` and the video checklist
   both instruct it for local dev, and `tests/test_seed.py` covers it. Removing it
   would break documented workflows for no gain.
2. **Seed at start unconditionally or only when empty?** Only when empty. An
   unconditional seed writes into a database an operator may have edited.
3. **A `/healthz` readiness gate before uvicorn?** No. `ensure_seeded` is one
   query on a local SQLite file; a readiness probe solves a problem that does not
   exist here.
4. **What about an `alembic`-style migration tool?** No. `_migrate()` already
   handles the only real schema change (adding columns) and runs on every boot.
   A migration framework for two columns is the wrong trade.

---

## Parallelisation

- **Sequential:** Tasks 1 → 2. Task 2's tests assert the entrypoint calls
  `ensure_seeded`, which Task 1 creates.
- **Independent:** Task 3 (docs only) can run in parallel with either, but commit
  it **after** Task 2 so the docs describe the code that actually exists.
- **Ownership:** the orchestrator owns `docs/` and `README.md`; a subagent
  implementing Tasks 1-2 must not touch them.
