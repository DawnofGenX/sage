# Sage — Submission Readiness Plan (15 days to deadline)

> **For Hermes:** Execute task-by-task. Tasks 0–5 are the deadline path; 6–8 are quality gates that must not slip past day 11. Verify each task yourself — a number you did not run is not a result.

**Goal:** Make Sage submittable: correct stale tests, prove the whole stack works end-to-end from a clean environment, and produce the submission artifacts a judge actually reads.

**Deadline:** 2026-10-23 12:00 PT — **15 days** from 2026-10-07.

**Architecture:** No new features. This plan is repair-and-proof: fix what is stale, verify what is claimed, and produce the artifacts. Every task ends in a verified state and a commit.

**Tech stack:** Python 3.14.7 / FastMCP 4.0.11 / mcp 2.3.0 / React 18 + Vite 5 / Node 20 / SQLite

---

## Verified Current State

Read-only investigation, 2026-10-07:

```
23 MCP tools registered, 23 in ALL_TOOLS, 0 untyped schemas
298 tests passing (mcp-server), EXIT=0, stable across 3 consecutive runs
npm run build + npx tsc --noEmit: clean
17 commits
```

### Uncommitted work in the tree

Two test files carry uncommitted edits left by a subagent that registered tool 23 and did not update the counts. **The edits are correct** (22 → 23) and pass; they simply were never committed.

### Known-stale artifacts (verified, not assumed)

| Artifact | Defect | Consequence |
|---|---|---|
| `web-simulator/tests/e2e.spec.ts` | References `Start Demo` and `Demo complete!` — both **removed** when DemoMode became stream-driven. `@playwright/test` is **not installed** (`grep playwright package.json` → 0). | Test suite is dead code. Any judge or CI running it fails. |
| `docs/test-report.md` | Claims "64/64 tests passed" | Understates by 234 and predates every fix since |
| `/mnt/c/Users/pkans/OneDrive/Desktop/sage-hackathon-submission.md` | **Does not exist** | A separate copy of the submission text was lost; `docs/submission.md` is now the single source of truth |

### What is genuinely proven

- All 23 tools publish typed output schemas; verified at the protocol level.
- `POST /mcp`, `GET /api/health`, `POST /api/tools/{n}`, `GET /api/tools` all 200 simultaneously.
- Real MCP client over Streamable HTTP; `tools/list` returns 23.
- Five-tool chained loop; each step consumes the prior response; halts honestly with no contacts.
- SSE frames parse correctly at chunk sizes 4096 → 7 bytes.
- `mockExtract` deleted; `step4_validated` → `step4_derived` everywhere; frontend reads the real backend.

### What is NOT yet proven

- Clean-environment reproducibility (Task 2).
- Chain end-to-end through SSE to a browser (Task 3).
- Idempotency in a full run (Task 4).
- No remaining fabricated-success path (Task 5).
- Docker build (Task 6).

---

## Task 0 — Commit the pending count fixes (day 1, 15 min)

**Objective:** Clear the uncommitted tree so later verification runs against committed code.

**Step 1: Confirm the diff is only the count update**

```bash
cd /home/hermes/sage
git diff --stat
git diff mcp-server/tests/ | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)'
```

Expected: `test_mcp_client.py` and `test_output_schemas.py`, each changing `22` → `23` in assertions and docstrings. **If anything else appears, stop and report it** — an unexpected diff in a repo this size is a signal, not noise.

**Step 2: Verify, then commit**

```bash
cd mcp-server && .venv/bin/python -m pytest tests/test_mcp_client.py tests/test_output_schemas.py -q --no-header
```
Expected: 12 passed.

```bash
cd /home/hermes/sage
git add mcp-server/tests/test_mcp_client.py mcp-server/tests/test_output_schemas.py
git diff --cached --name-only    # must be exactly those two
git commit -m "test: update tool-count assertions to 23 after registering run_agentic_loop"
```

---

## Task 1 — Repair or remove the dead e2e spec (day 1, 45 min)

**Objective:** A test suite that cannot run is worse than none. Decide honestly, then act.

**Step 1: Confirm it is genuinely broken**

```bash
cd /home/hermes/sage/web-simulator
grep -rn "Start Demo\|Demo complete!" src/ || echo "referenced UI does not exist"
```

Expected: both absent. The spec's second test would fail at its first click.

**Step 2: Choose — do not do both**

**Option A (recommended): make it real.** Playwright can drive the actual demo end-to-end, which is the single most convincing artifact for a judge — proof the whole stack works, not just the backend.

```bash
cd /home/hermes/sage/web-simulator
npm install -D @playwright/test
npx playwright install chromium
```

Rewrite `tests/e2e.spec.ts` against the current UI:

```typescript
import { test, expect } from '@playwright/test';

// Requires the backend running on :8000 (see Step 3).
test('dashboard loads and reports backend health', async ({ page }) => {
  const errors: string[] = []
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
  await page.goto('/')
  await expect(page.locator('text=Sage')).toBeVisible()
  // The hero must not claim the backend is unreachable.
  await expect(page.locator('text=Backend unreachable')).toHaveCount(0)
})

test('agentic loop streams steps to the UI', async ({ page }) => {
  await page.goto('/')
  await page.click('text=Extract Insights')
  // Each step renders with a provenance badge as it arrives.
  await expect(page.locator('text=extract_from_call').first()).toBeVisible({ timeout: 30000 })
  await expect(page.locator('text=sync_to_crm').first()).toBeVisible({ timeout: 30000 })
  // The run completes with a real record id.
  await expect(page.locator('text=loc_d_').first()).toBeVisible({ timeout: 30000 })
})
```

**Step 3: Run against a real backend**

```bash
cd /home/hermes/sage/mcp-server && .venv/bin/python -m src.data.seed
cd /home/hermes/sage/mcp-server && .venv/bin/python -m uvicorn src.api.rest:app --port 8000 &
cd /home/hermes/sage/web-simulator && npm run dev
npx playwright test
```

Expected: both tests pass. If Playwright cannot run in this environment (no browser deps), record that honestly rather than deleting the tests — see Step 4.

**Step 4: If it cannot run, say so in the file**

Replace the spec body with a header explaining it requires a running backend and `npx playwright install chromium`, and note in `docs/test-report.md` that it was authored but not executed. **Do not delete it** — a written e2e test is a claim about intended coverage; deleting it hides that. Do not leave it looking runnable when it isn't.

**Step 5: Commit**

```bash
git add web-simulator/tests/e2e.spec.ts web-simulator/package.json
git commit -m "test(e2e): drive the real streaming demo end-to-end against a running backend"
```

---

## Task 2 — Clean-environment reproduction (day 1-2, 45 min)

**Objective:** Prove a judge can clone and run this. The single most damaging submission risk.

**Step 1: Fresh venv from declared dependencies only**

```bash
cd /home/hermes/sage/mcp-server
rm -rf /tmp/sage_clean && python3 -m venv /tmp/sage_clean
/tmp/sage_clean/bin/pip install -q -r requirements.txt
/tmp/sage_clean/bin/pip install -q -e .
/tmp/sage_clean/bin/python -m pytest tests/ -q --no-header
```

Expected: **298 passed**, EXIT=0.

The `-e .` step is mandatory. Without it the suite cannot import `tools`/`data` and fails with 13 collection errors — this was the exact defect fixed in `acaf94b`.

**Step 2: Prove the negative case too**

```bash
rm -rf /tmp/sage_nodeps && python3 -m venv /tmp/sage_nodeps
/tmp/sage_nodeps/bin/pip install -q -r requirements.txt
/tmp/sage_nodeps/bin/python -m pytest tests/ -q --no-header 2>&1 | tail -3
```

Expected: collection errors mentioning `No module named 'tools'`. **This confirms the README's warning is accurate** rather than cargo-culted.

**Step 3: Verify the frontend the same way**

```bash
cd /home/hermes/sage/web-simulator
rm -rf node_modules && npm install && npm run build
```

Expected: build succeeds.

**Step 4: Record the real numbers in `docs/test-report.md`**

Replace the stale "64/64" line with the verified figures: backend count from Step 1, frontend build status, and the date. **Only numbers you just ran.** If a figure differs from an earlier claim, state which it supersedes.

**Step 5: Commit**

---

## Task 3 — Full-stack live proof (day 2-3, 1 hour)

**Objective:** One run that exercises every layer together, producing evidence for the demo video.

**Step 1: Start the backend and confirm all surfaces**

```bash
cd /home/hermes/sage/mcp-server && .venv/bin/python -m src.data.seed
cd /home/hermes/sage/mcp-server && .venv/bin/python -m uvicorn src.api.rest:app --port 8000 &
sleep 4
curl -s localhost:8000/api/health
curl -s localhost:8000/api/tools | .venv/bin/python -c "import sys,json; d=json.load(sys.stdin); print('tools:', d['count'])"
curl -s -o /dev/null -w "mcp:%{http_code}\n" -X POST localhost:8000/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"c","version":"1"}}}'
```

Expected: health ok, `tools: 23`, `mcp:200`.

**Step 2: Run the chain over real SSE and capture the frames**

```bash
curl -N -X POST localhost:8000/api/stream/agentic_loop \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"Hi, this is Alex from Sage. John Smith at Acme Corp wants the enterprise plan, budget around $50,000. Sarah Chen is the VP of Engineering. Let us follow up on 12/15/2026.","target":"local"}' \
  | tee /tmp/sage_stream.txt
```

Expected: five `event: step` frames then one `event: complete` with `status:success` and a `loc_d_...` record id.

**Step 3: Prove the frontend parser reads those exact bytes**

```bash
cd /home/hermes/sage/mcp-server
SAGE_DB_PATH=/tmp/proof.db .venv/bin/python -c "
import sys; sys.path.insert(0,'tests')
from sse_reference_parser import parse_sse_like_frontend
body = open('/tmp/sage_stream.txt').read()
r = parse_sse_like_frontend(body, chunk_size=37)
assert not r['dropped'], r['dropped']
assert len(r['steps']) == 5, len(r['steps'])
assert r['complete']['status'] == 'success'
print('FRONTEND-READABLE: 5 steps, status', r['complete']['status'],
      '| record', r['complete']['synced_record_id'])
"
```

This is the artifact that proves the demo works end-to-end. **Save the output** — it belongs in the submission.

**Step 4: Confirm the halt path in the same run**

```bash
curl -N -X POST localhost:8000/api/stream/agentic_loop \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"mm hm, sure, let us circle back","target":"local"}'
```

Expected: one `event: step`, then `event: complete` with `status:incomplete` and a reason naming no contacts. **No error frame** — a halted chain is a legitimate outcome.

**Step 5: Screenshot the running UI**

With the backend up and `npm run dev` running, capture per `docs/screenshot-checklist.md`. Save to `docs/screenshots/`. These are submission artifacts — capture them now while the system is known-good, not on submission day.

**Step 6: Commit** the screenshots and the captured stream proof.

---

## Task 4 — Idempotency and honesty audit (day 3, 45 min)

**Objective:** Re-prove the two guarantees this project was rebuilt around.

**Step 1: Idempotency across a full chain run**

```bash
cd /home/hermes/sage/mcp-server
rm -f /tmp/idem.db
SAGE_DB_PATH=/tmp/idem.db .venv/bin/python - <<'PY'
import asyncio, os
from src.api.rest import app  # noqa: F401  (ensures schema exists)
from data.db import Database
from tools.sync import sync_to_crm

async def main():
    rec = {"title": "Proof Deal", "amount": 5000, "stage": "proposal"}
    key = "idempotency-proof-001"
    a = await sync_to_crm(rec, target="local", idempotency_key=key)
    b = await sync_to_crm(rec, target="local", idempotency_key=key)
    print("first :", a["status"], a["record_id"])
    print("repeat:", b["status"], b["record_id"])
    assert a["status"] == "success", a
    assert b["status"] == "already_synced", b
    assert a["record_id"] == b["record_id"], "repeat must return the original id"
    db = Database(os.environ["SAGE_DB_PATH"])
    n = db._get_conn().execute("SELECT COUNT(*) FROM crm_local_deals").fetchone()[0]
    assert n == 1, f"expected exactly 1 row, found {n}"
    print("OK: one row, stable id, already_synced on repeat")

asyncio.run(main())
PY
```

Expected: `OK: one row, stable id, already_synced on repeat`.

**Step 2: Honest-unconfigured audit**

```bash
cd /home/hermes/sage/mcp-server
.venv/bin/python -c "
import asyncio
from tools.sync import sync_to_crm
async def m():
    for t in ('salesforce','hubspot','pipedrive'):
        r = await sync_to_crm({'name':'X'}, target=t, idempotency_key='audit')
        assert r['status'] == 'not_configured', (t, r)
        assert r['record_id'] is None and r['provenance'] == 'none', (t, r)
        print(f'{t:12s} -> {r[\"status\"]:15s} record_id={r[\"record_id\"]} provenance={r[\"provenance\"]}')
asyncio.run(m())
"
```

Expected: all three `not_configured`, null record id, `provenance: none`.

**Step 3: Source-level honesty grep**

```bash
cd /home/hermes/sage/mcp-server
grep -rn 'status.*success' src/ | grep -v provenance   # only the genuine success path
grep -rn 'idempotency_key\[' src/                       # must be empty — no synthesised ids
grep -rn 'mockExtract\|generateMockInsights' ../web-simulator/src/   # must be empty
```

Expected: the first shows only the real success path and explanatory comments; the second and third return nothing.

**Step 4: Re-run the full suite twice** to confirm stability.

**Step 5: Commit** any fix these audits surface.

---

## Task 5 — Honesty and accuracy claims audit (day 4, 1 hour)

**Objective:** Nothing in the submission overstates what the code does. This is the project's defining standard.

**Step 1: Every numeric claim in the docs must be traceable**

```bash
cd /home/hermes/sage
grep -rnoE "[0-9]+ (passed|tests|tools|MCP tools)" docs/*.md | sort -u
```

For each hit, confirm it matches a number you ran today. **Correct any that do not.** A stale "16 tools" in a document a judge reads is the exact failure mode this project exists to eliminate.

**Step 2: Re-read `docs/submission.md` as a hostile judge**

Ask of each claim: *what evidence in this repo supports this?* Anything without evidence either gets evidence or gets softened.

Known soft spots to check specifically:
- "Amazon Nova via AWS Bedrock" — the demo runs in mock mode by default. State the provenance honestly.
- Extraction accuracy figures — `docs/extraction-eval.md` measures the deterministic fallback, **not** a frontier LLM. Ensure `submission.md` does not blur that.
- "Bidirectional sync" — sync is currently one-way (Sage → CRM). Either implement the reverse or correct the wording. **Correcting the wording is the honest option and takes five minutes.**

**Step 3: Add the friction entries for defects found during this plan**

`docs/friction-log.md` gains entries for: the missing MCP mount, the required-but-absent `SyncResult.error`, the `GenericRecord` empty-schema trap, the `list_tools` 404, and the SSE parser contract bugs. All were real; all are worth recording for a reader deciding how much to trust the rest.

**Step 4: Commit**

---

## Task 6 — Docker build verification (day 5, 45 min)

**Objective:** `docker compose up` is the first thing a judge tries. It must work.

**Step 1: Build both images**

```bash
cd /home/hermes/sage
docker compose build
docker compose config > /dev/null && echo "compose config valid"
```

Expected: both images build.

**Step 2: Run the stack and verify live**

```bash
docker compose up -d
sleep 8
curl -s localhost:8000/api/health
curl -s localhost:3000 | head -5
docker compose down
```

Expected: health ok, frontend serves HTML.

**Step 3: If Docker is unavailable or fails**, record the exact failure in `docs/friction-log.md` and ensure `docs/deployment.md` leads with the manual path. **Do not claim Docker works unverified.**

**Step 4: Commit** any Dockerfile/compose changes needed.

---

## Task 7 — Submission text and artifacts (day 6-8, 2 hours)

**Objective:** Produce what a judge reads, from the verified state.

**Step 1: Update `docs/submission.md` to the verified facts**

Tool count 23. Typed schemas on all. Real MCP endpoint. Chained loop with honest halting. Include the Task 3 stream proof and the Task 4 idempotency result as evidence.

**Step 2: Reconcile the Desktop copy — it is gone**

`/mnt/c/Users/pkans/OneDrive/Desktop/sage-hackathon-submission.md` no longer exists. Decide once:

- **Recommended:** delete the duplicate concept. `docs/submission.md` is the single source of truth; copy it to Desktop **at submission time** so there is exactly one authored copy and no drift.
- If a Desktop copy is wanted, generate it from `docs/submission.md` rather than editing two files.

**Step 3: Final grep sweep**

```bash
cd /home/hermes/sage
grep -rniE "four[- ]step extraction|4-step pipeline" docs/ ; echo "exit=$? (1 = clean)"
grep -rniE "step4_validated" docs/ web-simulator/src/ ; echo "exit=$? (1 = clean)"
grep -rn "mockExtract" web-simulator/src/ ; echo "exit=$? (1 = clean)"
```

All three must report no matches.

**Step 4: Regenerate `docs/test-report.md`** from Task 2's run, with the date and the exact commands.

**Step 5: Commit**

---

## Task 8 — Demo video (day 9-11, 2 hours)

**Objective:** The video is the first thing a judge sees. Record it while the system is verified.

**Step 1: Follow `docs/video-recording-checklist.md` exactly**

It already specifies the five segments, the voiceover, and the export settings. The narration was corrected in `a53cc84` to say "two passes" — keep it that way.

**Step 2: Record against the live stack** (backend on :8000, frontend on :3000)

Capture in this order, all from the real system:
1. `GET /api/tools` showing 23 tools
2. The streaming chain — 5 steps arriving with provenance badges
3. The completion card with a real `loc_d_` id
4. The halt path — `incomplete`, no contacts
5. The pipeline board

**Step 3: Upload to YouTube as unlisted**, with `docs/youtube-description.md`.

**Step 4: Verify before submitting**: watch it end-to-end; confirm every claim in the voiceover matches what the screen shows. **A video claiming something the footage contradicts is the worst artifact in the submission.**

**Step 5: Commit** the description and the checklist-as-used.

---

## Submission Checklist (day 12-14)

Run through before submitting. Anything unchecked blocks submission.

**Code**
- [ ] Clean-environment suite green (Task 2), numbers recorded
- [ ] Full-stack live proof captured (Task 3)
- [ ] Idempotency proven (Task 4)
- [ ] Honesty greps clean (Task 4)
- [ ] Docker verified or failure documented (Task 6)
- [ ] `npm run build` + `npx tsc --noEmit` clean
- [ ] E2E spec runs or its non-runnable status is documented (Task 1)

**Artifacts**
- [ ] Demo video uploaded, watched end-to-end, claims match footage (Task 8)
- [ ] Screenshots captured from the running system (Task 3)
- [ ] `docs/submission.md` reflects only verified claims (Task 5, 7)
- [ ] `docs/test-report.md` has today's real numbers (Task 2)
- [ ] `docs/friction-log.md` records this round's defects (Task 5)
- [ ] Screenshots referenced from the submission

**Submission form (Hackster.io)**
- [ ] Project name and elevator pitch (<200 chars)
- [ ] "About the project" — matches `docs/submission.md`
- [ ] Built-with tags
- [ ] Repository URL live and public, MIT licence present
- [ ] Live demo URL reachable **from a cold load** — test in a private window
- [ ] Video URL
- [ ] Image gallery (≥3 screenshots)

**Final honesty gate — the one that matters most**

- [ ] Read the submission as if you were the judge who will check the code.
- [ ] Every factual claim traces to something in the repo.
- [ ] No number is inherited from a previous session without re-verification.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Clean-env install fails on a judge's machine | Medium | Fatal to credibility | Task 2, both directions; fix `requirements.txt` before anything else |
| Demo video claims something the footage contradicts | Medium | Severe | Record from the live system; watch before submitting |
| Deployment is unreachable at judging time | Medium | Fatal for a "try it" link | Deploy and verify from a cold, private browser session |
| E2E remains non-runnable | Medium | Moderate | Task 1 Step 4 — document honestly rather than leave it looking runnable |
| Overclaiming slips back into the docs | **High** | Severe | Task 5 trace-every-claim audit; it has already happened three times this project |
| Time runs short | Medium | Missed polish | Tasks 0–5 are the deadline path; 6–8 are gates that must not slip past day 11 |

---

## Execution Order

```
Day 1   Task 0  commit pending count fixes
        Task 1  repair or document the e2e spec
        Task 2  clean-environment reproduction      <-- highest risk, do early
Day 2-3 Task 3  full-stack live proof + screenshots
        Task 4  idempotency + honesty audit
Day 4   Task 5  claims audit + friction entries
Day 5   Task 6  docker verification
Day 6-8 Task 7  submission text and artifacts
Day 9-11 Task 8  demo video
Day 12-14      submission checklist
```

Tasks 0, 1, 2 are independent and can run in parallel — different files, no shared state. Tasks 3→4→5 are sequential: each verifies the state the next one audits. Tasks 6, 7, 8 can overlap once 5 is done.

**Ownership rule for parallel dispatch:** the orchestrator owns `docs/test-report.md`, `docs/submission.md`, and `web-simulator/package.json`. Subagents create new files only.