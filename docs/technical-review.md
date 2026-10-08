# Sage — Technical Architecture & Code Quality Review

**Reviewer:** Automated Technical Audit  
**Date:** 2026-10-05  
**Scope:** Full codebase review of MCP server, AWS adapters, LLM integration, Alexa skill, REST API, and web simulator

> **Superseded figures (2026-10-08):** This document is a dated snapshot of the
> 2026-10-05 tree. Its figures were true then and are NOT current:
> **22 MCP tools → 23** (`run_agentic_loop` added; verified live from
> `tools/registry.py` = 23) and **163 tests → 298** (verified 2026-10-08,
> `.venv/bin/python -m pytest tests/ -q` → `298 passed, 57 warnings in 8.19s`).
> The "no structured output schemas" finding below is **resolved** — all 23 tools
> return Pydantic models and publish typed `outputSchema`. Treat the rest of the
> gaps as the audit-era findings they were, not a description of HEAD.

---

## Executive Summary

Sage is a well-structured hackathon project with 22 MCP tools, 163 passing tests, and a clear separation of concerns. The architecture is sound for a demo: FastMCP server → extraction pipeline → SQLite/DynamoDB → CRM sync. However, several technical gaps would prevent this from being production-ready and would limit its impressiveness to judges evaluating technical depth.

**Overall Grade: B+ (Strong hackathon project, clear production gaps)**

---

## 1. MCP Spec Compliance

### What's Done Well
- FastMCP 4.0.11 with proper server initialization (name, version, instructions)
- 22 tools registered via decorator pattern
- Resources (`sage://pipeline/status`, `sage://contacts/{contact_id}`)
- Prompts (`analyze_call`, `generate_followup`)
- Streamable HTTP transport

### Gaps

| Issue | Severity | Details |
|-------|----------|---------|
| No structured output schemas | Medium | Tools return plain `dict` — FastMCP supports Pydantic `outputSchema` for typed, validated responses. Judges will look for this. |
| Resource handlers return `str(dict)` | Medium | `pipeline_status` returns `str(result)` and `contact_resource` returns `str(contact)` — this leaks Python dict repr over the wire instead of JSON. |
| No error handling in resources | High | If DB fails in `contact_resource`, the exception propagates as a 500 with no graceful fallback. |
| Prompts are trivial | Low | `analyze_call` just wraps transcript in a string template. No structured output, no few-shot examples. |
| No progress reporting | Medium | `extract_from_call` makes an LLM call that could take 10-30s — no `progress_notification` to keep the client alive. |
| No MCP sampling support | Low | Server doesn't expose `sampling/createMessage` for server-initiated LLM calls. |

### Recommendations
1. Add Pydantic response models for all 22 tools — this is the single biggest MCP spec improvement
2. Return proper JSON from resources, not `str(dict)`
3. Add try/catch in resource handlers with structured error responses
4. Add progress notifications to `extract_from_call` (step 1/4, 2/4, etc.)

---

## 2. Code Quality Issues

### 2.1 Duplication (DRY Violations)

**Critical: `_get_db()` and `_get_provider()` are copy-pasted across 4 files:**
- `tools/crud.py` (lines 8-25)
- `tools/extraction.py` (lines 9-27)
- `tools/intelligence.py` (lines 9-25)
- `tools/expansion.py` (lines 9-25)

Each has identical lazy-init singleton logic. This is a maintenance burden and makes testing harder.

**Critical: Mock extraction logic duplicated between `LLMProvider` and `BedrockProvider`:**
- `_mock_entities()`, `_mock_intent()`, `_mock_sentiment()`, `_mock_full()`, `_mock_insights()` are nearly identical across both classes (~200 lines of duplication)

### 2.2 Global State Anti-Pattern

Every tool module uses module-level globals:
```python
_db = None
_provider = None
_pipeline = None
_s3 = None
```

This requires tests to manually reset state via `reset_modules()`. In production, this creates:
- Thread-safety issues (no locks on lazy init)
- Hidden dependencies (tools aren't self-contained)
- Testing fragility (order-dependent test failures)

### 2.3 Dead Code / Misleading Implementation

**`draft_followup_email` (crud.py:176-225):** Calls the LLM but then **ignores the LLM output** for the email body. The body is constructed from a template. The LLM result is only used to extract a contact name. This is misleading — the tool claims to "draft using the LLM provider" but doesn't.

**`enrich_contact` (expansion.py:158-206):** Returns hardcoded mock data:
```python
company_size = "50-200"  # Mock size
industry = "Technology"  # Mock industry
```
The LinkedIn URL is generated from the name with a simple string replacement. This is not enrichment.

**`get_forecast` (expansion.py:209-283):** Uses hardcoded stage probability weights that aren't configurable or data-driven.

### 2.4 Type Safety

- `create_deal` accepts `stage: str` with no validation — any string is accepted
- `update_deal_stage` same issue — no enum validation
- `create_task` accepts `priority: str` with no validation
- `sync_to_crm` accepts `target: str` — validated only at runtime with a set membership check

---

## 3. Error Handling

### What's Done Well
- LLM provider has retry logic with exponential backoff (3 attempts)
- LLM provider validates response format before parsing
- CRM adapters return `{"error": "..."}` when not configured
- Alexa skill has try/catch in every intent handler with user-friendly error messages

### Gaps

| Issue | Severity | Details |
|-------|----------|---------|
| `sync_to_crm` fake success | **High** | When CRM is not configured, returns `{"status": "success"}` with a fabricated `record_id`. This is deceptive — callers think data was synced when it wasn't. |
| Silent exception swallowing | **High** | `proactive/engine.py:64` — `except Exception: pass` in `_schedule_proactive_alert`. No logging, no re-raise. |
| AWS adapters swallow all errors | **High** | `dynamodb.py`, `s3.py`, `eventbridge.py` — every operation catches `Exception` and returns `False`/`[]`/`{}`. No logging whatsoever. |
| REST API leaks internals | Medium | `api/rest.py:85` — `raise HTTPException(status_code=500, detail=str(e))` could leak stack traces, file paths, or credentials. |
| No input validation | Medium | `create_contact` with empty name, `create_deal` with negative value, `schedule_followup` with invalid date — all accepted. |
| LLM API errors not surfaced | Medium | When LLM fails after retries, `LLMAPIError` is raised but not caught by tool functions — propagates as raw exception to MCP client. |

### Recommendations
1. `sync_to_crm` should return `{"status": "not_configured"}` when CRM credentials are missing — not fake success
2. Add structured logging (at least `logging.warning`) to all `except Exception` blocks in AWS adapters
3. Add Pydantic validation to all tool parameters
4. Catch `LLMAPIError` in tool functions and return structured error responses
5. Sanitize REST API error messages — return generic messages, log details server-side

---

## 4. Security

| Issue | Severity | Details |
|-------|----------|---------|
| CORS misconfiguration | **High** | `api/rest.py:38-42` — `allow_origins=["*"]` with `allow_credentials=True`. Browsers reject this, but it signals security naivety. |
| No authentication | **High** | REST API and MCP server have no auth — anyone can access all endpoints. |
| No rate limiting | Medium | No protection against abuse. |
| Fake data presented as real | Medium | `enrich_contact` generates fake LinkedIn URLs, company sizes, industries. If this data flows to a CRM, it pollutes the database. |
| `sync_to_crm` record_id fabrication | Medium | `f"{target[:3]}_{idempotency_key[:8]}"` — fabricated IDs could collide with real CRM records. |
| No input sanitization | Medium | `search_contacts` uses parameterized queries (good), but `update_contact` builds SQL dynamically from dict keys (safe due to allowlist, but fragile). |

### Recommendations
1. Add API key authentication to REST API (simple `X-API-Key` header check)
2. Restrict CORS to known origins
3. Add Pydantic validators for all input parameters
4. Never fabricate success responses — return explicit "not configured" status
5. Add rate limiting (slowapi or similar)

---

## 5. Scalability

### Database
- **SQLite with file-based storage** — not suitable for production. No WAL mode, no connection pooling.
- **Every operation opens/closes a new connection** — `self._get_conn()` is called in every method, `conn.close()` at the end. No connection reuse.
- **O(n) scans in Python:**
  - `get_contact_context` loads ALL deals, filters in Python
  - `get_company_context` loads ALL deals, filters in Python
  - `get_deal_insights` loads ALL call logs, filters in Python
  - `get_daily_briefing` loads ALL deals
  - `get_weekly_review` loads ALL deals, ALL call logs, ALL followups
- **No pagination** — `get_all_deals()`, `get_all_contacts()`, `get_call_logs()` return everything.

### LLM Pipeline
- **Two-pass extraction** — pass 1 issues entities + intent concurrently; pass 2 generates the structured record grounded in pass-1 findings. Stage 4 is local schema validation, not a model call.
- **No streaming** — client waits for full response.
- **No batching** — each call is individual.
- **No caching** — same transcript processed twice makes two API calls.

### AWS Integration
- **DynamoDB is not actually used for main CRUD** — the `Database` class uses SQLite for all operations. DynamoDB is only accessible via `dynamodb_put/get/query/scan` delegation methods that are never called from the main tool flow.
- **S3 fallback uses temp directory** — data lost on restart.
- **EventBridge fallback is in-memory** — rules lost on restart.

### Recommendations
1. Add database indexes on `contact_id`, `deal_id`, `stage`, `due_date`
2. Use SQL `WHERE` clauses instead of Python filtering
3. Add pagination to all list endpoints
4. Implement connection pooling (or at least WAL mode for SQLite)
5. Add LLM response caching (hash transcript → cache result)
6. Actually wire DynamoDB into the main CRUD path (not just delegation methods)

---

## 6. AWS Integration Assessment

### Bedrock Provider
- **Not using the `LLMAPIFormat` abstraction** — has its own prompt building and response parsing, duplicating logic from `llm/formats.py`
- **No retry logic** — unlike the main LLM provider, Bedrock calls have no retries
- **Mock mode is keyword-based** — same as LLMProvider, but with different intent categories (6 vs 4)
- **No token/cost tracking** — unlike LLMProvider which tracks `total_tokens` and `total_cost`

### DynamoDB Store
- **Fallback uses a separate SQLite file** — not the main `sage.db`. Data inconsistency between main DB and DynamoDB fallback.
- **`query_items` does a full scan + client-side filter** — doesn't use DynamoDB's query API. This is O(n) and doesn't scale.
- **No batch operations** — no `batch_write_item` or `batch_get_item`
- **No TTL support** — for call log retention

### S3 Storage
- **Fallback directory is temp** — `tempfile.gettempdir()` — data lost on restart
- **No multipart upload** — large recordings will fail
- **No presigned URLs** — for secure client-side access

### EventBridge
- **Fallback is in-memory dict** — rules lost on restart
- **No error handling on `put_targets`** — if target ARN is invalid, the rule is created but has no target
- **Hardcoded account ID** — `000000000000` in fallback ARN

### Recommendations
1. Unify Bedrock provider with the `LLMAPIFormat` abstraction
2. Add retry logic to Bedrock calls
3. Use DynamoDB `query` with proper key conditions, not scan + filter
4. Wire DynamoDB into the main `Database` CRUD path
5. Use S3 persistent directory (not temp) for fallback
6. Add proper error handling to EventBridge `put_targets`

---

## 7. LLM Integration Assessment

### What's Done Well
- Clean abstraction with `LLMProvider` interface
- Auto-detection of OpenAI vs Anthropic format from URL
- Retry with exponential backoff
- Response validation before parsing
- Code fence stripping for JSON responses
- Token and cost tracking
- Mock fallback for demo mode

### Gaps

| Issue | Severity | Details |
|-------|----------|---------|
| Two-pass pipeline is 2 LLM calls | **High** | Pass 1 issues entities + intent concurrently; pass 2 generates the record. Stage 4 is local validation. |
| `draft_followup_email` ignores LLM output | **High** | The email body is template-generated, not LLM-generated. |
| No confidence thresholding | Medium | Low-confidence extractions treated same as high-confidence. |
| No prompt versioning | Medium | Prompts are hardcoded strings, not versioned. |
| No streaming | Medium | Client waits for full response. |
| No function calling | Medium | LLM can't call tools or request clarification. |
| Bedrock not using format abstraction | Medium | Duplicated prompt/response logic. |
| No token limit handling | Medium | Long transcripts may exceed context window — no chunking. |

### Recommendations
1. Pipeline now uses 2 LLM passes (entities + intent concurrent, then record generation) with local schema validation as stage 4
2. Fix `draft_followup_email` to actually use LLM-generated content
3. Add confidence thresholding — flag low-confidence extractions for review
4. Add prompt versioning (store prompts in separate files with version tags)
5. Implement transcript chunking for long calls
6. Unify Bedrock with the format abstraction

---

## 8. Architecture Gaps

### Missing Production Concerns
- **No event-driven architecture** — proactive engine is only called manually, not triggered by events
- **No webhook support** — can't receive real-time updates from CRMs
- **No audit logging** — can't track who did what
- **No metrics/observability** — token/cost tracking exists but isn't exposed via `/metrics`
- **No configuration management** — all env vars, no config file or secrets manager
- **No database migrations** — `CREATE TABLE IF NOT EXISTS` doesn't handle schema changes
- **No multi-tenancy** — all data in one database, no tenant isolation
- **No background task queue** — long-running operations block the request

### Testing Gaps
- **No integration tests with real LLM** — all real-API tests use `MockTransport`
- **No load testing** — no evidence the system handles concurrent requests
- **No contract tests** — MCP tool schemas aren't validated against a spec
- **No end-to-end tests** — web simulator has Playwright config but no E2E tests in CI

---

## 9. What Would Make This More Impressive to Judges

### High Impact (Do These First)

1. **Add Pydantic output schemas to all 22 MCP tools** — This is the single most impactful change. It shows understanding of the MCP spec, provides typed responses, and enables better client-side validation. FastMCP supports this natively.

2. **Fix `draft_followup_email` to actually use LLM output** — Currently the LLM is called but its output is discarded. Make the LLM generate the email subject and body, with fallback to template only if LLM fails.

3. **Add real-time streaming to extraction** — Use MCP progress notifications to show "Step 1/4: Extracting entities..." → "Step 2/4: Classifying intent..." etc. This makes the demo much more engaging.

4. **Add authentication to the REST API** — Even a simple API key check shows security awareness. Judges will notice the lack of auth.

5. **Wire DynamoDB into the main CRUD path** — Currently DynamoDB delegation methods exist but are never called. Make `Database` actually use DynamoDB when credentials are available, with SQLite as fallback.

6. **Add a `/metrics` endpoint** — Expose token usage, cost, extraction confidence scores, and pipeline health as Prometheus metrics. Shows production awareness.

### Medium Impact

7. **Add database indexes and SQL-level filtering** — Replace Python filtering with SQL `WHERE` clauses. Add indexes on `contact_id`, `deal_id`, `stage`.

8. **Add LLM response caching** — Hash the transcript and cache results for 24h. Reduces cost and latency for repeated calls.

9. **Add prompt versioning** — Store prompts in `prompts/v1/extraction.txt`, `prompts/v2/extraction.txt`. Shows maturity.

10. **Add structured logging** — Replace `print()` and silent `except` with proper `logging` module usage.

11. **Add input validation** — Pydantic validators on all tool parameters. Reject invalid stages, negative values, etc.

12. **Add database migrations** — Use Alembic or similar for schema versioning.

### Low Impact (Polish)

13. **Add OpenAPI schema export** — FastAPI already generates this; expose it at `/docs`.

14. **Add Docker health checks** — `HEALTHCHECK` in Dockerfile.

15. **Add CI badge and test coverage report** — Shows testing rigor.

16. **Add architecture decision records (ADRs)** — Document why SQLite over Postgres, why FastMCP over raw MCP, etc.

---

## 10. Priority Action Items

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | Add Pydantic output schemas to all 22 tools | 2-3 hours | Very High |
| 2 | Fix `draft_followup_email` to use LLM output | 30 min | High |
| 3 | Add progress notifications to extraction | 1 hour | High |
| 4 | Add API key auth to REST API | 1 hour | High |
| 5 | Fix `sync_to_crm` to not fake success | 15 min | High |
| 6 | Add structured logging to AWS adapters | 1 hour | Medium |
| 7 | Add database indexes + SQL filtering | 2 hours | Medium |
| 8 | Wire DynamoDB into main CRUD path | 3-4 hours | Medium |
| 9 | Add `/metrics` endpoint | 1 hour | Medium |
| 10 | Add input validation (Pydantic) | 2 hours | Medium |
| 11 | Unify Bedrock with format abstraction | 1 hour | Low |
| 12 | Add LLM response caching | 1 hour | Low |

---

## Summary

Sage is a solid hackathon project with good architecture and comprehensive testing. The main gaps are:

1. **MCP spec maturity** — no structured output schemas, no progress reporting
2. **Misleading implementations** — `draft_followup_email` and `enrich_contact` don't do what they claim
3. **Security** — no auth, permissive CORS, fabricated success responses
4. **Scalability** — O(n) scans, no pagination, no connection pooling
5. **AWS integration** — DynamoDB not wired into main path, silent error swallowing

The highest-impact improvements for judges are: Pydantic output schemas, real LLM-powered email drafting, progress notifications, and authentication. These four changes would significantly elevate the technical impression.
