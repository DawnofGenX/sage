# Sage Friction Log

Issues encountered during MCP server development for the Amazon Developer Hackathon 2026.

---

## 1. Streamable HTTP Session Management

| Field | Details |
|-------|---------|
| **Task** | Implement persistent session state across MCP tool calls over Streamable HTTP |
| **Expected** | Session ID maintained across multiple tool invocations; stateful conversations with the LLM |
| **Actual** | FastMCP's Streamable HTTP transport creates ephemeral sessions; no built-in session persistence between requests. Each HTTP request is stateless. |
| **Severity** | Medium |
| **Workaround** | Used module-level singleton pattern (`_db`, `_provider`, `_pipeline`) to maintain state across tool calls within the same server process. All state is in-memory or backed by SQLite. |
| **Suggestion** | FastMCP should provide a session middleware or context manager that persists session IDs across requests, similar to how `mcp` SDK handles it with `Session` objects. A `session_id` parameter in tool definitions would enable stateful multi-turn conversations. |

---

## 2. Tool Schema Validation

| Field | Details |
|-------|---------|
| **Task** | Define strict input schemas for MCP tools with proper type validation |
| **Expected** | Automatic request validation based on tool parameter types; clear error messages for invalid inputs |
| **Actual** | FastMCP relies on Python type hints but doesn't enforce runtime validation. Optional parameters with `None` defaults can cause `TypeError` downstream if not handled. The `update_contact` tool accepts `**kwargs` which bypasses schema validation entirely. |
| **Severity** | Medium |
| **Workaround** | Added manual validation in each tool function. Used `dict.get()` with defaults throughout. Added explicit type checking in the extraction pipeline's `_validate()` method. |
| **Suggestion** | Integrate Pydantic models for tool input/output schemas. FastMCP already depends on Pydantic — exposing it for tool definitions would enable automatic validation, OpenAPI generation, and better IDE support. A `@mcp.tool(schema=Model)` decorator would be ideal. |

---

## 3. Async Tool Execution

| Field | Details |
|-------|---------|
| **Task** | Run LLM extraction calls concurrently for improved throughput |
| **Expected** | Multiple async tool calls execute concurrently when possible; `asyncio.gather()` works across tool boundaries |
| **Actual** | FastMCP runs tools sequentially by default. The extraction pipeline's 2 passes are inherently dependent (pass 2 needs pass-1 results), but independent operations like `get_contact_context` and `get_pipeline_health` could run concurrently. No built-in batch tool execution. |
| **Severity** | Low |
| **Workaround** | Kept the pipeline sequential by design (steps are dependent). For the web simulator, used client-side `Promise.all()` for independent API calls. The mock LLM provider is synchronous, so no async bottleneck in practice. |
| **Suggestion** | Add a `Promise.all()` equivalent for MCP — either a `batch_tool_call` endpoint or automatic parallelization of independent tool calls in a single request. A `mcp.parallel([tool1, tool2])` API would be useful. |

---

## 4. CORS for Web Simulator

| Field | Details |
|-------|---------|
| **Task** | Allow the web simulator (Vite dev server on :3000) to call the MCP server (:8000) during development |
| **Expected** | Simple CORS headers on MCP server responses; `Access-Control-Allow-Origin: *` for development |
| **Actual** | FastMCP's Streamable HTTP transport doesn't include CORS headers by default. Browser blocks cross-origin requests from `:3000` to `:8000`. No configuration option in FastMCP for CORS. |
| **Severity** | High |
| **Workaround** | Used Vite's `server.proxy` configuration in `vite.config.ts` to proxy `/api` requests to the MCP server, avoiding CORS entirely in development. For production, the web simulator is served as static files and the MCP server is behind the same reverse proxy. |
| **Suggestion** | Add a `cors_origins` parameter to `FastMCP()` constructor or `mcp.run()`. Even a simple `--cors-origin *` CLI flag would solve this. Alternatively, document the Vite proxy pattern as the recommended development setup. |

---

## 5. LLM Provider Fallback Chain

| Field | Details |
|-------|---------|
| **Task** | Gracefully fall back to mock extraction when LLM API is unavailable |
| **Expected** | Automatic fallback when API key is missing or API call fails; seamless transition between real and mock modes |
| **Actual** | The `LLMProvider` class checks for `LLM_API_KEY` at init time and sets `_use_mock` permanently. If the API key is present but the API call fails (rate limit, timeout, invalid response), the exception propagates up and crashes the tool call. No retry logic or fallback. |
| **Severity** | Medium |
| **Workaround** | The mock provider uses regex/keyword-based extraction that produces realistic results for demo purposes. For production, the API key must be set. The proactive engine wraps LLM calls in try/except and returns a default insight on failure. |
| **Suggestion** | Implement a fallback chain in `LLMProvider.extract()`: try real API → on failure, log warning and fall back to mock. Add configurable retry with exponential backoff. A `fallback=True` parameter on the provider would make this explicit. |

---

## 6. Database Connection Management

| Field | Details |
|-------|---------|
| **Task** | Handle concurrent database access from multiple MCP tool calls |
| **Expected** | Thread-safe database connections; connection pooling for concurrent requests |
| **Actual** | Each `Database` method opens a new `sqlite3.connect()` and closes it immediately. SQLite's default mode allows only one writer at a time. Under concurrent load, this can cause `database is locked` errors. |
| **Severity** | Low |
| **Workaround** | SQLite's `connect()` is fast for local files. The singleton `_db` instance ensures only one `Database` object exists. For the hackathon demo scale (single user, sequential calls), this is sufficient. |
| **Suggestion** | Use `sqlite3.connect(db_path, check_same_thread=False)` with a connection pool, or switch to `aiosqlite` for async-native database access. FastMCP could provide a database middleware that handles connection lifecycle. |

---

## 7. Four-Step Extraction Claim Withdrawn

| Field | Details |
|-------|---------|
| **Task** | Documentation claims a four-step extraction pipeline |
| **Expected** | Docs describe the same architecture as the code implements |
| **Actual** | The code made one LLM call and derived four output views from it. The docs claimed four inference stages. This was a correctness defect — the submission text misstated what the software does. |
| **Severity** | High |
| **Fix** | Commit 30906d6 changed the code to two real LLM passes (entities + intent concurrent, then record generation). Stage 4 is local schema validation, not a model call. All docs updated to describe two passes / three calls, with stage 4 explicitly labelled as local validation. The retraction is stated here plainly rather than quietly edited out. |
| **Suggestion** | When code changes behaviour, grep the docs for the old claim in the same PR. A doc that says "four steps" after the code does two passes is a lie judges can catch. |

---

## 8. `sync_to_crm` Fabricated Success

| Field | Details |
|-------|---------|
| **Task** | `sync_to_crm` returns a truthful status when CRM credentials are missing |
| **Expected** | Tool returns `not_configured` with a reason when no CRM is configured |
| **Actual** | Tool returned `{"status": "success", "record_id": "sal_test-123"}` — a fabricated success with a synthesised ID. A judge who configured no CRM credentials and saw "Synced to Salesforce" had been told something untrue by the software. |
| **Severity** | High |
| **Fix** | Commit ab2f85e removed the fabricated-success path. `sync_to_crm` now returns `not_configured` when credentials are missing, `already_synced` on a repeated idempotency key, and a real record ID only when a real write occurred. A `local` sync target was added — a working CRM backed by Sage's own SQLite tables with Salesforce-shaped field names. |
| **Suggestion** | Never fabricate success responses. If a tool cannot do what it claims, it must say so explicitly. |

---

## Summary

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Streamable HTTP session management | Medium | Workaround in place |
| 2 | Tool schema validation | Medium | Workaround in place |
| 3 | Async tool execution | Low | By design |
| 4 | CORS for web simulator | High | Resolved via Vite proxy |
| 5 | LLM provider fallback chain | Medium | Partial workaround |
| 6 | Database connection management | Low | Sufficient for demo |
| 7 | Four-step extraction claim | High | Withdrawn — docs corrected |
| 8 | `sync_to_crm` fabricated success | High | Fixed — returns `not_configured` |
