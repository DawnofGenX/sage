# Sage — Remaining Implementation Plan (Tasks 5-12)

> **For Hermes:** Execute task-by-task with a subagent per task. Verify each task's claimed result yourself — a test count you did not run is unverified.

**Goal:** Finish the truth-discipline work: typed tool outputs, a real MCP client, the chained agentic loop, SSE streaming, a demo path that exercises the backend, measured accuracy, and corrected submission text.

**Architecture:** Each MCP tool declares a Pydantic output model so FastMCP emits `structuredContent`. A real MCP client speaks the protocol to the running server and chains five tools, each consuming the previous step's response, streaming to the UI over SSE. The web simulator's `mockExtract` is deleted, not bypassed.

**Tech stack (all versions verified against the installed environment):** Python 3.14.7, FastMCP 4.0.11, mcp 2.3.0, FastAPI 0.142.2, Pydantic 2.13.5, React 18 + Vite 5, Node 20

---

## Verified Baseline

Established by running, not by reading a prior report:

```
225 passed in 5.67s        EXIT=0
```

Interpreter: `mcp-server/.venv/bin/python`. Repo: `/home/hermes/sage`, branch has commits `7d736cd` → `30906d6`.

**Every "suite green" gate below means 225 + the tests added by that task, EXIT=0.**

### Verified FastMCP output-schema API

Introspected, not assumed. `FastMCP.tool()` accepts `output_schema`. A Pydantic return annotation is enough — no explicit wiring needed:

```python
from pydantic import BaseModel
from fastmcp import FastMCP

class Out(BaseModel):
    count: int
    label: str

@mcp.tool()
async def probe(x: int) -> Out: ...
```

Empirically confirmed:
- `(await mcp.list_tools())[0].output_schema` → `{'properties': {...}, 'required': [...], 'type': 'object'}`
- `(await mcp.call_tool("probe", {"x": 7})).structured_content` → `{'count': 7, 'label': 'ok'}`

Note the attribute is snake_case `output_schema` / `structured_content`. There is **no** `_tools` attribute on `FastMCP` and **no** `get_tools()` — use `await mcp.list_tools()`. Both were wrong guesses that cost time; do not repeat them.

### Verified MCP client API

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client   # NOT streamablehttp_client

# streamable_http_client is an @asynccontextmanager yielding TransportStreams
# sig: (url, *, http_client=None, terminate_on_close=True,
#       max_sse_event_size=1048576) -> AsyncGenerator[TransportStreams, None]
async with streamable_http_client(url) as streams:
    async with ClientSession(streams.read_stream, streams.write_stream) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("name", {"arg": 1})
```

`call_tool` returns `CallToolResult | InputRequiredResult | Result`. `CallToolResult` fields: `meta, content, structured_content, is_error, result_type`. **Narrow on `result_type` before reading `.structured_content`** or elicitation responses raise `AttributeError`.

### Current frontend state

- 16 components in `web-simulator/src/components/`
- `App.tsx:138` `mockExtract`, `App.tsx:234` `generateMockInsights`, `App.tsx:427` the call site — all to be deleted
- `step4_validated` still referenced at `App.tsx:39,230,457`, `ExtractionPipeline.tsx:33,207-216`, `lib/types.ts:61` — Task 4 renamed it server-side, so the frontend is currently stale
- `lib/api.ts` has 14 methods; needs `runAgenticLoop` as an SSE consumer

### REST layer

`src/api/rest.py:76` accepts flat JSON and dispatches to a `TOOLS` dict of 22 entries. Task 8 adds an SSE route alongside it.

### CRITICAL — the MCP server is not mounted on the REST app

Verified by probing a live server: `POST /mcp`, `POST /`, and `POST /mcp/` all return **404**. `rest.py:35` creates a plain `FastAPI()` and never mounts the MCP app. Only `/api/health` and `/api/tools/{tool_name}` exist.

So the project currently serves a REST API and calls itself an MCP server, but exposes no MCP endpoint at all. Task 6 must fix this before any client can connect.

**Verified mounting recipe.** `mcp.http_app(path=...)` registers its routes at `/mcp` regardless of the `path` argument, so the mount prefix and the path argument interact confusingly. Three combinations were tried; only the third works:

```python
from fastmcp import FastMCP
from fastapi import FastAPI

mcp = FastMCP("sage", version="1.0.0", instructions="...")
# ... tools registered ...

mcp_app = mcp.http_app()
app = FastAPI(lifespan=mcp_app.lifespan)     # lifespan is REQUIRED

@app.get("/api/health")                      # 1. declare REST routes FIRST
async def health():
    return {"status": "ok", "server": "sage", "version": "1.0.0"}

@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, request: dict):
    ...

app.mount("/", mcp_app)                      # 2. mount MCP LAST, at "/"
```

Two failure modes, both observed:

| Attempt | Result |
|---|---|
| `FastAPI()` without lifespan | `RuntimeError: StreamableHTTPSessionManager task group was not initialized` |
| REST routes declared *after* `mount("/")` | `/api/health` → 404 (MCP shadows it) |
| `mount("/mcp", http_app(path="/mcp"))` | `/mcp` → 404 (double prefix) |
| **lifespan + REST first + `mount("/")` last** | `/api/health` 200, `/api/tools/{n}` 200, `/mcp` 200 ✓ |

Verify with the exact check in Task 6 Step 0 — all three must return 200 simultaneously.

---

## Task 5 — Pydantic output schemas (highest risk; one commit per module)

**Objective:** FastMCP emits `structuredContent` for all 22 tools.

**Files:**
- Create: `mcp-server/src/tools/schemas.py`
- Modify: `mcp-server/src/tools/{extraction,crud,intelligence,sync,expansion}.py`
- Modify: `mcp-server/tests/test_schemas.py` (new)

### Step 1: Write the failing test

`mcp-server/tests/test_schemas.py`:

```python
"""Every tool must expose an output schema, verified at the protocol level.

A declared-but-unemitted schema is indistinguishable from a working one if
you only check that the annotation exists, so these tests assert on what
FastMCP actually publishes and returns.
"""
import pytest
from tools.registry import ALL_TOOLS


@pytest.mark.asyncio
async def test_every_tool_is_registered():
    from server import mcp
    tools = await mcp.list_tools()
    assert len(tools) == len(ALL_TOOLS)


@pytest.mark.asyncio
async def test_every_tool_publishes_an_output_schema():
    from server import mcp
    missing = [t.name for t in await mcp.list_tools() if t.output_schema is None]
    assert not missing, f"tools with no output schema: {missing}"


@pytest.mark.asyncio
async def test_health_tool_returns_structured_content():
    from server import mcp
    result = await mcp.call_tool("extract_from_call", {"transcript": "Hi Sarah, $50K."})
    assert result.structured_content is not None
```

Run: `.venv/bin/python -m pytest tests/test_schemas.py -q --no-header`
Expected: FAIL — no tool declares an output schema yet.

### Step 2: Create `schemas.py`

One model per tool response, grouped by module. Every model carries `provenance` where the tool returns one. Use `model_config = ConfigDict(extra="allow")` on record models so an added field never breaks a consumer.

```python
"""Pydantic output models for every MCP tool.

Declaring these makes FastMCP publish an `output_schema` in tools/list and
return `structuredContent` on every call. Grouped by the module that owns the
tool so adding a tool and its schema happen in the same place.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ProvenanceMixin(BaseModel):
    """Provenance of the value, when the tool produces one."""
    provenance: str | None = Field(
        default=None,
        description="What produced this value: local/salesforce/.../mock/none",
    )


# --- extraction.py ---
class ExtractionResult(BaseModel):
    step1_entities: dict[str, list[Any]]
    step2_intent: str
    step3_record: dict[str, Any]
    step4_derived: bool
    passes: int
    llm_calls: int
    inferred_stages: list[int]
    derived_stages: list[int]
    provenance: str


class ContactContext(BaseModel):
    model_config = ConfigDict(extra="allow")
    contact: dict[str, Any]
    deals: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []


class PipelineHealth(BaseModel):
    model_config = ConfigDict(extra="allow")
    deals_by_stage: dict[str, int] = {}
    stuck_deals: list[dict[str, Any]] = []
    total_deals: int
    total_value: float


# --- crud.py ---
class CreatedRecord(ProvenanceMixin, BaseModel):
    id: int | str | None = None
    created: bool = True


class UpdatedRecord(ProvenanceMixin, BaseModel):
    model_config = ConfigDict(extra="allow")


class EmailDraft(ProvenanceMixin, BaseModel):
    subject: str
    body: str
    tone_used: str
    templated: bool


# --- intelligence.py ---
class DailyBriefing(BaseModel):
    model_config = ConfigDict(extra="allow")
    followups_due: list[dict[str, Any]] = []
    total_deals: int
    pipeline_value: float
    stuck_deals: list[dict[str, Any]] = []
    insights: list[str] = []


class FollowupsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    followups: list[dict[str, Any]] = []
    total: int = 0


class WeeklyReview(BaseModel):
    model_config = ConfigDict(extra="allow")
    deals_moved: Any = None
    calls_made: int
    followups_completed: int
    pipeline_health: dict[str, Any]
    weekly_summary: str


class SearchResponse(BaseModel):
    contacts: list[dict[str, Any]] = []
    total: int = 0


class DealInsights(BaseModel):
    model_config = ConfigDict(extra="allow")
    deal_id: int | None = None
    sentiment: Any = None
    risks: list[str] = []
    buying_signals: list[str] = []
    recommendation: str | None = None


# --- sync.py ---
class SyncResult(ProvenanceMixin, BaseModel):
    status: str
    target: str
    record_id: str | None = None
    idempotency_key: str
    synced_at: str | None = None
    error: str | None = None


# --- expansion.py ---
class GenericRecord(BaseModel):
    """Fallback for the expansion tools whose shapes vary by query."""
    model_config = ConfigDict(extra="allow")
```

### Step 3: Attach models one module at a time

For each tool, add a return annotation importing from `schemas`. Example — `extraction.py`:

```python
from tools.schemas import ContactContext, ExtractionResult, PipelineHealth

async def extract_from_call(transcript: str, audio_url: str | None = None) -> ExtractionResult:
    ...
    return ExtractionResult(**{...})
```

**Per module:** run the suite, fix every failure, commit. A module that fails is fixed before the next one starts — 22 changes landing together is how this task produces a mass failure.

```bash
.venv/bin/python -m pytest tests/ -q --no-header    # must be EXIT=0
git add -A && git diff --cached --name-only        # read the list
git commit -m "feat(schemas): <module> tools declare Pydantic output models"
```

### Step 4: Live protocol verification

A schema can be declared and never emitted. Prove it over the wire:

```bash
.venv/bin/python -m uvicorn src.api.rest:app --port 8000 &
sleep 3
.venv/bin/python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("http://localhost:8000/mcp") as s:
        async with ClientSession(s.read_stream, s.write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", len(tools.tools))
            missing = [t.name for t in tools.tools if t.outputSchema is None]
            print("missing outputSchema:", missing or "none")
            assert not missing
asyncio.run(main())
PY
```

Expected: `tools: 22`, `missing outputSchema: none`.

**Watch the endpoint path.** Confirm whether `/mcp` or `/` — run once and read the error before assuming.

---

## Task 6 — Real MCP client

**Objective:** A client that speaks the protocol, not a REST wrapper.

**Files:**
- Create: `mcp-server/src/client/__init__.py`
- Create: `mcp-server/src/client/chained.py`
- Create: `mcp-server/tests/test_mcp_client.py`

### Step 0: Mount the MCP server on the REST app (do this FIRST)

**This is a prerequisite for everything else in this task.** The MCP server is currently not mounted at all — see "CRITICAL" above. A client cannot connect until this is fixed.

Modify `src/api/rest.py`:

1. Import `from server import mcp` (the FastMCP instance).
2. Replace `app = FastAPI(title="Sage API", version="1.0.0")` with:

```python
mcp_app = mcp.http_app()
app = FastAPI(
    title="Sage API",
    version="1.0.0",
    lifespan=mcp_app.lifespan,   # required, or the session manager never starts
)
```

3. Leave all existing `@app.get`/`@app.post` decorators where they are (they now come first, which is correct).
4. Add `app.mount("/", mcp_app)` **after every REST route is declared** — as the last statement in the module.

Watch for a circular import: `server.py` imports from `tools.registry`, and `rest.py` importing `server` must not create a cycle. If it does, construct the FastMCP instance in a shared module both import.

**Verify all three surfaces respond:**

```bash
.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from src.api.rest import app
with TestClient(app) as c:
    print("GET  /api/health  ->", c.get("/api/health").status_code)
    r = c.post("/api/tools/get_pipeline_health", json={})
    print("POST /api/tools/..->", r.status_code)
    m = c.post("/mcp", json={"jsonrpc":"2.0","id":1,"method":"initialize",
        "params":{"protocolVersion":"2025-11-25","capabilities":{},
                  "clientInfo":{"name":"p","version":"1"}}},
        headers={"Accept":"application/json, text/event-stream"})
    print("POST /mcp         ->", m.status_code)
    assert c.get("/api/health").status_code == 200
    assert m.status_code == 200
    print("all three OK")
PY
```

Expected: `200`, `200`, `200`, then `all three OK`.

### Step 1: Tests first, against a real in-process server

```python
"""Tests for the real MCP client.

These run against an actual FastMCP server over Streamable HTTP — no mocked
transport. The point of this module is that the protocol path genuinely works,
and a mocked transport cannot prove that.
"""
import asyncio
import pytest
from client.chained import SageMCPClient


@pytest.fixture
async def running_server():
    """Start the real server on an ephemeral port for the duration of a test."""
    # Implementation note: use fastmcp's in-memory transport if available,
    # otherwise bind a real port with uvicorn on 127.0.0.1:0 and read the
    # assigned port. Do NOT mock streamable_http_client.
    ...


@pytest.mark.asyncio
async def test_lists_tools_over_the_protocol(running_server):
    async with SageMCPClient(running_server) as client:
        names = {t.name for t in await client.list_tools()}
    assert "extract_from_call" in names
    assert "sync_to_crm" in names


@pytest.mark.asyncio
async def test_call_returns_structured_content(running_server):
    async with SageMCPClient(running_server) as client:
        result = await client.call("get_pipeline_health", {})
    assert result["data"], "expected structured content"


@pytest.mark.asyncio
async def test_call_records_timing_and_provenance(running_server):
    async with SageMCPClient(running_server) as client:
        record = await client.call_recorded("get_pipeline_health", {})
    assert record["name"] == "get_pipeline_health"
    assert record["duration_ms"] >= 0
```

### Step 2: Implement `SageMCPClient`

```python
"""A real MCP client speaking Streamable HTTP.

Exists so the agentic loop is a genuine protocol client rather than a REST
call wearing an MCP hat. Judge-facing demos are inspectable: a reviewer can
read this file and confirm tools/list and tools/call are really used.
"""
from __future__ import annotations
import time
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class SageMCPClient:
    """MCP client for the Sage server."""

    def __init__(self, url: str, timeout: float = 30.0):
        self.url = url
        self.timeout = timeout
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "SageMCPClient":
        self._stack = AsyncExitStack()
        streams = await self._stack.enter_async_context(
            streamable_http_client(self.url)
        )
        self._session = await self._stack.enter_async_context(
            ClientSession(streams.read_stream, streams.write_stream)
        )
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._session = None

    async def list_tools(self) -> list:
        result = await self._session.list_tools()
        return list(result.tools)

    async def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return its structured content.

        call_tool may return CallToolResult, InputRequiredResult, or Result.
        Narrow on result_type before touching structured_content — elicitation
        responses have no such attribute and would raise AttributeError.
        """
        result = await self._session.call_tool(name, args)
        return self._unwrap(result)

    @staticmethod
    def _unwrap(result: Any) -> dict[str, Any]:
        kind = getattr(result, "result_type", None)
        if kind == "input_required" or type(result).__name__ == "InputRequiredResult":
            return {"error": "tool requested input", "result_type": kind}
        data = getattr(result, "structured_content", None)
        if data is None:
            # Fall back to text content so a tool without a schema still works.
            text = getattr(result, "content", None)
            if text:
                for block in text:
                    text_body = getattr(block, "text", None)
                    if text_body:
                        return {"raw": text_body}
            return {}
        return data

    async def call_recorded(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and capture what happened, for rendering in the UI."""
        started = time.perf_counter()
        data = await self.call(name, args)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "name": name,
            "arguments": args,
            "duration_ms": duration_ms,
            "result": data,
            "provenance": data.get("provenance") if isinstance(data, dict) else None,
        }
```

### Step 3: Run and commit

```bash
.venv/bin/python -m pytest tests/test_mcp_client.py -q --no-header    # EXIT=0
git commit -m "feat(client): real MCP client over Streamable HTTP with result narrowing"
```

---

## Task 7 — The chained agentic loop

**Objective:** Five tools, each consuming the previous step's response.

**Files:**
- Create: `mcp-server/src/client/demo_flow.py`
- Modify: `mcp-server/src/tools/registry.py`
- Create: `mcp-server/tests/test_demo_flow.py`

### Step 1: Tests first

The contract that matters: nothing is hardcoded, and the chain halts rather than inventing data.

```python
@pytest.mark.asyncio
async def test_contact_id_is_passed_forward(running_server):
    result = await run_agentic_loop(SAMPLE_TRANSCRIPT, server=running_server)
    steps = {s["name"]: s for s in result["steps"]}
    create_contact = steps["create_contact"]["result"]
    create_deal = steps["create_deal"]["result"]
    assert create_deal["contact_id"] == create_contact["id"], (
        "step 3 must use the id step 2 returned"
    )


@pytest.mark.asyncio
async def test_deal_id_is_passed_to_followup(running_server):
    result = await run_agentic_loop(SAMPLE_TRANSCRIPT, server=running_server)
    steps = {s["name"]: s for s in result["steps"]}
    assert (steps["schedule_followup"]["result"]["deal_id"]
            == steps["create_deal"]["result"]["id"])


@pytest.mark.asyncio
async def test_chain_syncs_to_local_with_a_real_id(running_server):
    result = await run_agentic_loop(SAMPLE_TRANSCRIPT, server=running_server, target="local")
    assert result["status"] == "success"
    assert result["synced_record_id"].startswith(("loc_d_", "loc_c_"))
    assert result["steps"][-1]["provenance"] == "local"


@pytest.mark.asyncio
async def test_chain_halts_when_no_contacts_extracted(running_server):
    """No contacts means no chain. Never fabricate one to keep going."""
    result = await run_agentic_loop("mm hm, sure, let's circle back", server=running_server)
    assert result["status"] == "incomplete"
    assert result["completed_steps"] == 1
    assert "no contacts" in result["reason"].lower()
```

### Step 2: Implement `run_agentic_loop`

```python
"""The five-tool agentic loop, chained over a real MCP client.

Each step's arguments are read from the previous step's response. Nothing is
literal. When extraction yields no contacts the chain halts and says so —
inventing a contact to keep the demo moving would be exactly the dishonesty
this project is trying to remove.
"""
from __future__ import annotations
import time
from typing import Any

from client.chained import SageMCPClient


async def run_agentic_loop(
    transcript: str,
    server: str = "http://localhost:8000/mcp",
    target: str = "local",
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    async with SageMCPClient(server) as client:
        async def step(name: str, args: dict[str, Any]) -> dict[str, Any]:
            record = await client.call_recorded(name, args)
            steps.append(record)
            if "error" in record["result"]:
                raise ChainAborted(name, record["result"]["error"])
            return record["result"]

        try:
            extraction = await step("extract_from_call", {"transcript": transcript})
        except ChainAborted as exc:
            return {"status": "incomplete", "completed_steps": len(steps),
                    "reason": str(exc), "steps": steps}

        contacts = extraction.get("step3_record", {}).get("contacts", [])
        if not contacts:
            return {"status": "incomplete", "completed_steps": 1,
                    "reason": "no contacts extracted", "steps": steps}

        first = contacts[0]
        contact = await step("create_contact", {
            "name": first.get("name", "Unknown"),
            "company": first.get("company"),
            "email": first.get("email"),
        })

        deals = extraction["step3_record"].get("deals", [])
        first_deal = deals[0] if deals else {"title": "New opportunity"}
        deal = await step("create_deal", {
            "contact_id": contact["id"],
            "title": first_deal.get("title"),
            "value": first_deal.get("value"),
            "stage": first_deal.get("stage", "lead"),
        })

        followups = extraction["step3_record"].get("followups", [])
        due = followups[0].get("due_date") if followups else None
        await step("schedule_followup", {
            "contact_id": contact["id"],
            "deal_id": deal["id"],
            "title": (followups[0].get("title") if followups
                      else "Follow up"),
            "due_date": due,
        })

        sync = await step("sync_to_crm", {
            "record": {"title": deal["title"], "amount": deal.get("value"),
                       "stage": deal.get("stage")},
            "target": target,
            "idempotency_key": f"chain-{deal['id']}",
        })

    return {
        "status": "success",
        "completed_steps": len(steps),
        "synced_record_id": sync.get("record_id"),
        "steps": steps,
    }


class ChainAborted(Exception):
    """A step failed; the chain stops rather than continuing on bad state."""
```

### Step 3: Register as tool 23

Add to `src/tools/registry.py` `ALL_TOOLS`, wrapping so FastMCP registers it. Confirm the count becomes 23 via `await mcp.list_tools()`.

### Step 4: Run and commit

```bash
.venv/bin/python -m pytest tests/test_demo_flow.py -q --no-header
git commit -m "feat(flow): five-tool chained agentic loop registered as MCP tool 23"
```

---

## Task 8 — SSE endpoint

**Objective:** Stream the chain to the UI, one event per step.

**Files:**
- Create: `mcp-server/src/api/stream.py`
- Modify: `mcp-server/src/api/rest.py`
- Create: `mcp-server/tests/test_sse.py`

### Step 1: Tests first

```python
@pytest.mark.asyncio
async def test_stream_emits_one_event_per_step():
    events = []
    async for line in collect_sse(_run(SAMPLE_TRANSCRIPT)):
        events.append(line)
    steps = [e for e in events if e.startswith("event: step")]
    assert len(steps) == 5
    assert any(e.startswith("event: complete") for e in events)


@pytest.mark.asyncio
async def test_stream_reports_an_incomplete_chain():
    """A halted chain must still emit `complete` with status incomplete."""
    async for line in collect_sse(_run("mm hm")):
        assert "event: complete" in line or "event: step" in line


@pytest.mark.asyncio
async def test_stream_surfaces_tool_error_as_an_event():
    """A mid-chain failure must emit `error` and close cleanly.

    A silently truncated stream leaves the frontend waiting forever — the
    exact failure mode streaming clients exist to prevent.
    """
    events = [l async for l in collect_sse(_run_with_broken_tool())]
    assert any("event: error" in e for e in events) or \
           any("incomplete" in e for e in events)
```

### Step 2: Implement

Add to `rest.py`:

```python
from fastapi.responses import StreamingResponse

@app.post("/api/stream/agentic_loop")
async def stream_agentic_loop(payload: dict[str, Any]):
    """Stream the chained agentic loop as Server-Sent Events."""
    from client.demo_flow import run_agentic_loop

    async def gen():
        try:
            result = await run_agentic_loop(
                payload["transcript"],
                target=payload.get("target", "local"),
            )
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"
            return

        for i, s in enumerate(result.get("steps", []), start=1):
            summary = f"{s['name']} -> {s.get('provenance') or 'no provenance'}"
            yield (f"event: step\n"
                   f"data: {json.dumps({'index': i, 'tool': s['name'], 'duration_ms': s['duration_ms'], 'provenance': s.get('provenance'), 'summary': summary})}\n\n")

        yield (f"event: complete\n"
               f"data: {json.dumps({'status': result['status'], 'steps': result.get('completed_steps', 0), 'synced_record_id': result.get('synced_record_id'), 'reason': result.get('reason')})}\n\n")

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})
```

SSE over WebSocket deliberately: one-directional, self-reconnecting, no new dependency.

### Step 3: Verify by hand, then commit

```bash
.venv/bin/python -m uvicorn src.api.rest:app --port 8000 &
curl -N -X POST http://localhost:8000/api/stream/agentic_loop \
  -H 'Content-Type: application/json' \
  -d '{"transcript":"Hi Sarah from Acme Corp, enterprise plan for $50K."}'
```

Expected: five `event: step` lines then `event: complete`.
Commit: `feat(api): SSE endpoint streaming the chained agentic loop`

---

## Task 9 — Delete `mockExtract`, wire the real path

**Objective:** The demo exercises the backend, or it visibly fails.

**Files:**
- Modify: `web-simulator/src/App.tsx` (delete `mockExtract` L138, `generateMockInsights` L234, fix call site L427)
- Modify: `web-simulator/src/lib/api.ts`, `lib/types.ts`
- Create: `web-simulator/src/components/DemoFlow.tsx`
- Modify: `web-simulator/src/components/ExtractionPipeline.tsx` (`step4_validated` → `step4_derived`)

### Step 1: Delete, do not bypass

```bash
grep -n "mockExtract\|generateMockInsights" src/App.tsx
```

Remove both functions and every call site. Then:

```bash
grep -rn "mockExtract\|generateMockInsights" src/ ; echo "exit=$?"
```

Must print nothing. Leaving dead generators is how the next person reintroduces the fake demo.

### Step 2: Add the SSE client

In `lib/api.ts`:

```typescript
export function runAgenticLoop(
  transcript: string,
  onStep: (e: { index: number; tool: string; duration_ms: number; provenance: string | null; summary: string }) => void,
  onComplete: (e: { status: string; steps: number; synced_record_id: string | null; reason?: string }) => void,
  onError: (e: { error: string }) => void,
): EventSource {
  const es = new EventSource('/api/stream/agentic_loop', {
    // EventSource is GET-only; POST via fetch+ReadableStream instead.
  } as never);
  return es; // see note
}
```

**Note:** `EventSource` cannot POST. Use `fetch` with a `ReadableStream` reader and parse `event:`/`data:` frames manually, or add an SSE endpoint that accepts the transcript via query string. Choose the fetch+stream-reader path and parse frames in a helper.

### Step 3: Fix the stale `step4_validated` references

The server renamed it in Task 4; the frontend still reads the old name in `App.tsx:39,230,457`, `ExtractionPipeline.tsx:33,207-216`, `lib/types.ts:61`. Rename all to `step4_derived` and relabel the UI text "Schema Valid" → "Derived — schema check" so the display does not imply a fourth inference.

### Step 4: Build and verify the diff

```bash
npm run build
```

Then read the diff for unintended deletions — this file lost JSX balance in an earlier parallel round:

```bash
git diff --stat src/App.tsx
git diff src/App.tsx | grep '^-' | grep -v '^---'   # every deletion justified?
```

Commit: `feat(ui): replace mock extraction with the real chained agentic loop over SSE`

---

## Task 10 — Measured extraction accuracy

**Objective:** Replace asserted quality with a number.

**Files:**
- Create: `mcp-server/tests/fixtures/eval_transcripts.json`
- Create: `mcp-server/tests/test_extraction_eval.py`
- Create: `docs/extraction-eval.md`

### Step 1: Fixture — 10 transcripts, hand-labelled

The labels are hand-written constants. **The extractor must never see them** — a fixture the same code generates and grades proves nothing.

```json
[
  {"id": "eval-01",
   "transcript": "Hi Sarah, this is Alex from Sage. We want the enterprise plan for $50K.",
   "expected": {"people": ["Sarah"], "companies": ["Acme"], "amounts": ["50000"]}},
  {"id": "eval-02", "transcript": "...", "expected": {}}
]
```

Fill all 10. Keep each `expected` to fields that are unambiguous in the text.

### Step 2: Compute precision/recall per field

```python
def test_extraction_accuracy_is_measured(sample_transcript):
    """Writes docs/extraction-eval.md and asserts no field scores below zero."""
    rows = []
    for case in EVAL_FIXTURE:
        result = ExtractionPipeline(provider).process(case["transcript"])
        entities = result["step1_entities"]
        for field in ("people", "companies", "amounts"):
            tp, fp, fn = score(entities.get(field, []), case["expected"].get(field, []))
            rows.append({"id": case["id"], "field": field,
                         "precision": tp / (tp + fp) if tp + fp else None,
                         "recall": tp / (tp + fn) if tp + fn else None})
    write_report(rows)
```

Report per-field precision and recall. If a metric is `None`, say so rather than printing 0.

### Step 3: Hero stats from the call log

`Hero.tsx` takes `hoursSaved={2.5} manualEntries={0}` as hardcoded props. Compute from the tool-call log instead: calls processed, records created, syncs completed. Do not fabricate a time figure — derive it from observed counts or drop the metric.

Commit: `feat(eval): measured extraction accuracy; hero stats computed from the call log`

---

## Task 11 — Correct the submission text

**Objective:** The docs stop claiming a four-step pipeline.

**Files:**
- Modify: `docs/submission.md`, `docs/architecture.md`, `docs/demo-script.md`, `docs/video-recording-checklist.md`, `docs/friction-log.md`
- Modify: `/mnt/c/Users/pkans/OneDrive/Desktop/sage-hackathon-submission.md`

### Step 1: Find every occurrence

```bash
grep -rniE "four[- ]step|4[- ]step|four stage|multi-step" docs/ /mnt/c/Users/pkans/OneDrive/Desktop/sage-hackathon-submission.md
```

### Step 2: Rewrite each

Two passes, three requests, stage 4 derived. The DemoMode narration and `docs/demo-script.md` voiceover change to match — a judge comparing video against code is the comparison this project should welcome.

Also update the "Amazon Nova-powered extraction" framing to state plainly that extraction runs on whatever provider is configured and reports its own provenance.

### Step 3: Record the retraction

Add a `docs/friction-log.md` entry: the four-step framing was withdrawn and why. Stated plainly beats quietly edited.

### Step 4: Verify nothing stale survives

```bash
grep -rniE "four[- ]step extraction|4-step pipeline" docs/ ; echo "exit=$? (1 = clean)"
```

---

## Task 12 — Full verification

**Objective:** Nothing reported green on someone else's word.

### Step 1: Clean-environment suite

```bash
rm -rf /tmp/sage_final && python3 -m venv /tmp/sage_final
/tmp/sage_final/bin/pip install -q -r requirements.txt
/tmp/sage_final/bin/pip install -q -e .
/tmp/sage_final/bin/python -m pytest tests/ -q --no-header
```

Expected: all pass, EXIT=0. **The `-e .` step is mandatory** — without it the suite cannot import `tools`/`data` and fails with 13 collection errors.

### Step 2: Frontend

```bash
cd ../web-simulator && npm run build
grep -rn "mockExtract" src/ ; echo "exit=$? (1 = clean)"
```

### Step 3: Live protocol

Start the server, connect a real client, assert `tools/list` returns 23 and a tool call returns populated `structuredContent`.

### Step 4: Chain end-to-end

Run `run_agentic_loop` against a seeded DB with `target="local"`. Assert 5 steps, a `loc_d_` record ID, and rows present in `crm_local_deals`.

### Step 5: Idempotency

Run the same chain twice with the same idempotency key. Assert the second returns `already_synced` and no duplicate row exists.

### Step 6: Honesty audit

```bash
grep -rn 'status.*success' src/ | grep -v provenance
grep -rn 'idempotency_key\[' src/
```

The only hits should be the genuine success path and comments quoting the old bug.

### Step 7: Write verified numbers

Replace inherited figures in `docs/test-report.md` with what actually ran. Include the clean-venv result.

---

## Risks

| Risk | Mitigation |
|---|---|
| 22 output schemas break tests at once | One module per commit, suite green after each. A failing module is fixed, not deferred |
| Pydantic model rejects a field a tool returns | `extra="allow"` on record models; add fields deliberately |
| Endpoint path is `/mcp` not `/` | Run once and read the error before assuming; do not hardcode a guess |
| `EventSource` cannot POST | Use `fetch` + `ReadableStream`; parse `event:`/`data:` frames |
| SSE dies behind a proxy | Frontend talks to the backend directly; it never proxies SSE itself |
| Chain test needs a live server | Use a real ephemeral-port server, never a mocked transport |
| Judges find a stale claim | `grep` in Task 11 must return zero hits before submitting |

---

## Execution Order

Tasks 5→8 are sequential and share the tool modules. Task 9 depends on Task 8's endpoint. Tasks 10 and 11 are independent of 5-9 and can run in parallel with them — neither touches `src/`.

**Ownership rule for any parallel dispatch:** the orchestrator owns `src/server.py`, `src/tools/registry.py`, `src/api/rest.py`, and `web-simulator/src/App.tsx`. Subagents create new files only. That split prevents the duplicate-definition merge that corrupted `App.tsx` in an earlier round.