# Sage — Truth, Honesty, and Agentic Chaining Design

**Date:** 2026-10-06
**Status:** Awaiting user review
**Author:** Hermes (Research Engineer profile)

---

## Why This Spec Exists

Three independent judges reviewed Sage after the first improvement round. Their verdict was consistent and uncomfortable: the project has good bones and strong documentation, but **the demo does not exercise the backend**, and **several tools report success they did not achieve**.

Two claims were verified directly against the source before this spec was written:

1. `web-simulator/src/App.tsx:427` calls `mockExtract(transcript)` — a local keyword matcher. `api.extractFromCall` exists in `src/lib/api.ts` and is never called from the demo path.
2. `mcp-server/src/tools/sync.py:58-68` catches adapter errors and returns `{"status": "success", "record_id": f"{target[:3]}_{idempotency_key[:8]}"}`. The inline comment states this is deliberate, to keep the response shape consistent.

Claim 2 is the more serious of the two. A judge who configures no CRM credentials, clicks "Sync to CRM", and sees "Synced to Salesforce ✓" has been told something untrue by our software. Everything else in this project is a matter of degree; this one is a matter of correctness.

This spec fixes the three gaps the judges ranked highest, and it does so by making the code tell the truth rather than by making the demo look busier.

---

## Design Goals

1. **No response may claim more than happened.** Every mutating tool response carries provenance. Fabricated success is removed, not relabelled.
2. **The demo must exercise the backend.** The path a judge clicks must be the path that runs `extract_from_call` on the server.
3. **The agentic loop must be inspectable, not animated.** A real MCP client performing a real chained sequence, visible in the UI and readable in the source.

---

## Non-Goals

- No new tracks, no new deployments, no change to the extraction schema shape.
- No attempt at genuine audio transcription or speaker diarization. `extract_from_call` continues to accept a transcript; the `audio_url` path remains metadata-only. Saying so in the UI is in scope; building it is not.
- No rewrite of the CRM adapters. Salesforce, HubSpot, and Pipedrive keep their current implementations; only the fallback path changes.

---

## Section 1 — Truth Discipline

### 1.1 Provenance on every mutating response

A single `Provenance` literal type is introduced and attached to every tool response that creates, updates, or syncs anything:

```python
Provenance = Literal[
    "local", "salesforce", "hubspot", "pipedrive",
    "bedrock", "openai", "anthropic",
    "mock", "replay", "none",
]
```

`mock` means "no credentials, deterministic fallback produced this." `none` means "nothing happened and here is why." `replay` is reserved for the recorded-response path described in Section 1.4 and is never produced by the CRM tools.

`LLMProvider` gains `last_provenance`, set on every `extract()` call — `bedrock` if the Bedrock branch ran, otherwise the detected wire format, otherwise `mock`. This lets the UI badge an extraction honestly without inferring anything.

### 1.2 `sync_to_crm` stops fabricating

The block at `sync.py:58-68` is deleted. On adapter error the tool returns:

```json
{
  "status": "not_configured",
  "target": "salesforce",
  "error": "Set SALESFORCE_CLIENT_ID and SALESFORCE_CLIENT_SECRET to enable.",
  "provenance": "none"
}
```

This is a breaking response-shape change. `tests/test_crm_sync.py` has a test asserting the old fake-success behaviour; that test is updated to assert `not_configured` instead, with a comment recording that the previous behaviour was the bug. The web simulator's sync handler is updated in the same change so the two never disagree.

### 1.3 A real `local` CRM target

The demo needs a sync that genuinely succeeds without requiring anyone to sign up for a Salesforce developer org. Rather than a stub, `local` is a fourth adapter backed by its own schema in the same SQLite database:

```sql
CREATE TABLE IF NOT EXISTS crm_local_contacts (
    id TEXT PRIMARY KEY,              -- loc_c_01H...
    last_name TEXT NOT NULL,
    first_name TEXT,
    email TEXT,
    title TEXT,
    account_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_local_deals (
    id TEXT PRIMARY KEY,              -- loc_d_01H...
    contact_id TEXT,
    name TEXT NOT NULL,
    amount REAL,
    stage_name TEXT,                  -- Salesforce-shaped vocabulary
    close_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES crm_local_contacts(id)
);

CREATE TABLE IF NOT EXISTS crm_local_sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type TEXT,
    external_id TEXT,
    idempotency_key TEXT UNIQUE,
    target TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Field names mirror Salesforce's `sobjects` vocabulary (`StageName`, `CloseDate`, `Account`) so that swapping the adapter underneath is a credential change, not a code change. Record IDs are ULID-style, deterministic from the idempotency key so a replayed chain produces identical IDs — which is what makes the demo repeatable.

The `UNIQUE` constraint on `idempotency_key` is the real proof that idempotency works: a second sync with the same key raises `IntegrityError`, which the adapter catches and returns as `{"status": "already_synced", "record_id": <existing>}`. The demo can show this by clicking sync twice.

`sync_to_crm` gains `local` to its target enum. Provenance is `local`.

### 1.4 Recorded replay — deferred, and explicitly optional

A `replay` mode that replays a captured real Salesforce response is **not** in this spec's scope. It was considered and deferred: it adds a labelling burden to every code path that touches it, and Section 1.3 already gives the demo a sync that is genuinely true. If a real Salesforce org becomes available before submission, `replay` can be added later behind the same provenance contract. Recorded today, it would be one more thing to keep honest.

### 1.5 `draft_followup_email` uses its LLM output

Currently `crud.py` calls `provider.extract(prompt, "full")` and discards the result, building the email from a template. A dedicated `EMAIL_PROMPT` is added to `llm/prompts.py` requesting `{subject, body, tone_used}`, and the response is used directly. The template fallback remains only when `provenance == "mock"`, and the response then carries `"provenance": "mock"` so the UI can label the email as templated.

### 1.6 Pydantic output schemas on all 22 tools

FastMCP emits `structuredContent` when a tool declares an output model, and this is the single highest-impact-per-hour item Judge 3 identified. Each of the 22 tools gains a Pydantic model describing its response, declared via FastMCP's output-model parameter. Models are grouped by module — `ExtractionResult`, `ContactResponse`, `DealResponse`, `SyncResponse`, `PipelineHealth`, and so on — in `mcp-server/src/tools/schemas.py`.

This is mechanical work with one real risk: existing tests assert on untyped dict shapes. Every test touching a tool response is updated in the same change, and the suite must return to 163 passing before this section is considered done.

---

## Section 2 — Honest Extraction Pipeline

### 2.1 Two real passes

`extraction/pipeline.py` currently issues one `extract(transcript, "full")` call and derives all four displayed stages from that single response. This changes to two genuine LLM calls:

- **Pass 1** — `extract(transcript, "entities")` and `extract(transcript, "intent")` concurrently via `asyncio.gather`. Yields entities and intent from separate requests.
- **Pass 2** — `extract(transcript, "full")`, with the pass-1 entities and intent injected into the prompt as grounding context so the record-generation call is constrained by what pass 1 actually found.

Two calls, both real, both visible to the LLM provider for token accounting.

### 2.2 Four stages on screen, honestly labelled

The UI keeps four stages. It does not claim four LLM calls.

| Stage | Label shown | Origin |
|-------|-------------|--------|
| 1 | `Entity Extraction` | pass 1 — real LLM call |
| 2 | `Intent Classification` | pass 1 — real LLM call |
| 3 | `Record Generation` | pass 2 — real LLM call |
| 4 | `Derived — schema validation` | local, no LLM |

Stages 1 and 2 share pass 1 and so resolve together; stage 3 follows pass 2; stage 4 is a pure local check and is labelled `Derived` in the UI so no one reads it as a fourth inference.

`step4_validated` is renamed `step4_derived` in the response, and the pipeline result carries `"passes": 2` so the API states the real call count.

### 2.3 Submission text correction

`docs/submission.md`, `docs/architecture.md`, `sage-hackathon-submission.md` on the Desktop, and the drafted Hackster.io "About the project" body all currently describe a four-step extraction pipeline. Each is edited to describe two LLM passes with a derived validation stage. The DemoMode narration and `docs/demo-script.md` voiceover are updated to match, since a judge comparing the video against the code is exactly the check this project should welcome.

---

## Section 3 — MCP Client Tool Chaining

### 3.1 A real MCP client

`mcp-server/src/client/chained.py` connects to the running MCP server over Streamable HTTP using the official Python SDK's client, and calls tools through the protocol — `initialize`, `tools/list`, `tools/call`. It does not import the tool functions directly and does not go through the REST wrapper.

```python
class SageMCPClient:
    async def __aenter__(self) -> "SageMCPClient": ...      # initialize
    async def list_tools(self) -> list[ToolDescriptor]: ...   # tools/list
    async def call(self, name: str, args: dict) -> dict: ...  # tools/call
    async def __aexit__(self, *exc) -> None: ...
```

Each `call` records `name`, `arguments`, `duration_ms`, `result`, and the provenance carried in the result, so the chain can be rendered step by step and asserted in tests.

### 3.2 The chain

`mcp-server/src/client/demo_flow.py` implements `run_agentic_loop(transcript: str, target: str = "local") -> dict`:

```
1. extract_from_call(transcript)
      → record.contacts[0] gives name, company
2. create_contact(name=..., company=...)
      → contact_id from step 2's response
3. create_deal(contact_id=<step 2>, title=..., value=...)
      → deal_id from step 3's response
4. schedule_followup(contact_id=<step 2>, deal_id=<step 3>, ...)
5. sync_to_crm(record=<step 3>, target=<target>, idempotency_key=...)
      → record_id, provenance
```

Every step's arguments come from a previous step's response. Nothing is hardcoded — if extraction returns no contacts, the chain stops at step 1 with `{"status": "incomplete", "completed_steps": 1, "reason": "no contacts extracted"}` rather than fabricating a contact.

The function is registered as an MCP tool itself, so `tools/list` returns 23 tools and a judge connecting with the Inspector sees the chaining capability as part of the server's surface.

### 3.3 Streaming it to the UI

`POST /api/tools/run_agentic_loop` returns Server-Sent Events, one event per completed step:

```
event: step
data: {"index":1,"tool":"extract_from_call","duration_ms":812,"provenance":"openai","summary":"1 contact, 1 deal, 1 follow-up"}

event: step
data: {"index":2,"tool":"create_contact","duration_ms":31,"provenance":"local","summary":"loc_c_01H..."}

event: complete
data: {"status":"success","steps":5,"synced_record_id":"loc_d_01H..."}
```

SSE rather than WebSocket: the traffic is one-directional, SSE reconnects on its own, and it needs no extra dependency in a FastAPI app.

### 3.4 UI: DemoFlow panel and the deletion of `mockExtract`

A new `DemoFlow.tsx` panel renders the chain as it streams: tool name, arguments, duration, provenance badge, and a one-line summary per step. It opens with a `tools/list` count so the judge sees "23 tools available" before the chain runs.

`App.tsx:427` switches from `mockExtract(transcript)` to `api.runAgenticLoop(transcript)`. `mockExtract` and `generateMockInsights` are **deleted**, not bypassed — leaving them in the file is how the next person reintroduces the problem. The extract button, the auto-demo mode, and the Call Simulator's end-of-call handler all route through the new endpoint.

If the backend is unreachable, the UI renders an explicit red `Backend unreachable — start the MCP server` state. There is no silent fallback to generated data anywhere in the demo path.

### 3.5 Extraction accuracy as a measured claim

Because the chain is real, accuracy becomes measurable rather than asserted. A small evaluation fixture — 10 transcripts with hand-labelled expected contacts, deals, amounts, and follow-ups — runs through `extract_from_call` and reports precision and recall per field into `docs/extraction-eval.md`. The Hero component's `2.5h saved / 0 manual entries` props stop being hardcoded and are computed from the tool-call log: calls processed, records created, syncs completed.

This turns Judge 1's "no real-world validation" into a number the submission can cite.

---

## Data Flow After This Change

```
Call transcript
      │
      ▼
┌─────────────────────────────────────────────┐
│ Web simulator (React)                       │
│   DemoFlow panel · Extraction stages · …    │
└────────────────────┬────────────────────────┘
                     │ POST /api/tools/run_agentic_loop
                     │ (SSE — one event per step)
                     ▼
┌─────────────────────────────────────────────┐
│ FastAPI rest.py                             │
└────────────────────┬────────────────────────┘
                     ▼
┌─────────────────────────────────────────────┐
│ SageMCPClient — real MCP over Streamable    │
│   HTTP: initialize → tools/list → tools/call│
└────────────────────┬────────────────────────┘
                     ▼
        extract_from_call  ──►  LLMProvider
        create_contact        (OpenAI | Anthropic | Bedrock | mock)
        create_deal                    │
        schedule_followup             │ 2 real passes
        sync_to_crm  ──► local | salesforce | hubspot | pipedrive
                              │
                              └─► not_configured  (never fake success)
```

---

## Acceptance Criteria

Backend:
- [ ] Every mutating tool response carries a `provenance` field from the defined set
- [ ] `sync_to_crm` returns `not_configured` with a reason when a CRM is unconfigured; no path returns `success` with a synthesised ID
- [ ] `local` target writes real rows to `crm_local_*` and returns a real record ID
- [ ] A repeated `idempotency_key` returns `already_synced` and creates no second row
- [ ] `draft_followup_email` returns LLM-generated subject and body when a real provider is configured
- [ ] All 22 tools declare a Pydantic output model; FastMCP emits `structuredContent`
- [ ] Extraction issues exactly 2 LLM calls, verifiable in the provider's call counter
- [ ] Pipeline response carries `passes: 2` and `step4_derived` instead of `step4_validated`
- [ ] `run_agentic_loop` is listed by `tools/list` and executes 5 chained steps
- [ ] Suite returns to 163 passing or better, with no test asserting the old fake-success behaviour

Frontend:
- [ ] `mockExtract` and `generateMockInsights` no longer exist in the source
- [ ] The demo path reaches `run_agentic_loop` over SSE and renders each step with a provenance badge
- [ ] The DemoMode button drives the real UI rather than a timed animation
- [ ] An unreachable backend renders an explicit error state, never generated data
- [ ] Hero statistics are computed from the tool-call log

Docs:
- [ ] `docs/submission.md`, `docs/architecture.md`, `docs/demo-script.md`, the Desktop submission file, and the Hackster.io draft describe two LLM passes with a derived validation stage
- [ ] `docs/extraction-eval.md` reports precision and recall per extracted field

---

## Risks

| Risk | Mitigation |
|------|------------|
| Output schemas break 22 tools' tests at once | One module at a time, suite green after each; schemas are mechanical |
| Response-shape change breaks the simulator | Simulator update ships in the same change as the `sync_to_crm` change |
| Two-pass extraction doubles latency | Pass 1 runs its two calls concurrently; measured and reported in the eval doc |
| SSE proxying drops events on Vercel | Demo runs against the Railway-hosted backend; frontend never proxies SSE itself |
| Judges find the retracted four-step claim and distrust the rest | The retraction is stated plainly in the submission rather than quietly edited out |

---

## What This Does Not Buy

Worth being explicit, because the judges were blunt about competitive position: Sage still has no real hardware, no real audio, and MCP servers are now common. This spec makes the project **honest and inspectable**, which is the necessary condition for a good score. It is not sufficient for first place. The remaining differentiators — actual Alexa+ device behaviour, extraction accuracy as a headline number, and a live demo URL — are submission-phase work, not architecture work, and are deliberately not in this spec.