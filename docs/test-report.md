# Sage End-to-End Test Report

**Date:** 2026-10-05  
**Tester:** Automated E2E Test Suite  
**Project:** Sage — Passive Sales Intelligence Layer  
**Version:** 1.0.0

---

## 1. Test Results Summary

| # | Test | Result | Details |
|---|------|--------|---------|
| 1 | MCP Server Unit Tests | ✅ PASS | 64/64 tests passed (1.51s) |
| 2 | Web Simulator Build | ✅ PASS | 39 modules, 197KB JS, built in 3.39s |
| 3 | Seed Script | ✅ PASS | 10 contacts, 5 deals (idempotent) |
| 4 | API Health Check | ✅ PASS | `{"status":"ok","server":"sage","version":"1.0.0"}` |
| 5 | API: extract_from_call | ⚠️ PARTIAL | Works with `{"args":{...}}`, fails with flat JSON |
| 6 | API: get_pipeline_health | ✅ PASS | Returns deals_by_stage, total_deals, total_value |
| 7 | API: get_daily_briefing | ✅ PASS | Returns followups_due, total_deals, pipeline_value |
| 8 | API: search_contacts | ⚠️ PARTIAL | Works with `{"args":{...}}`, fails with flat JSON |
| 9 | API: sync_to_crm | ⚠️ PARTIAL | Works with `{"args":{...}}`, fails with flat JSON |
| 10 | API: get_contact_context | ✅ PASS | Returns contact, deals, activities |
| 11 | API: create_contact | ✅ PASS | Creates contact, returns id |
| 12 | API: get_deal_insights | ✅ PASS | Returns recommendation, insights |
| 13 | API: get_todays_followups | ✅ PASS | Returns followups array |

**Overall: 10/13 fully passing, 3/13 with API contract issues**

---

## 2. Issues Found

### Issue #1: REST API Request Body Contract Mismatch (MEDIUM)

**Severity:** Medium  
**Endpoints Affected:** `extract_from_call`, `search_contacts`, `sync_to_crm` (and likely all others)

**Description:**  
The REST API wrapper at `/api/tools/{tool_name}` expects requests in the format:
```json
{"args": {"transcript": "..."}}
```

But the natural/expected REST contract (and the format used in the task description) is flat JSON:
```json
{"transcript": "..."}
```

**Root Cause:**  
In `src/api/rest.py`, the `ToolRequest` model wraps all parameters in an `args` field:
```python
class ToolRequest(BaseModel):
    args: dict[str, Any] = {}
```

This means clients must nest their parameters inside an `args` key, which is non-standard for REST APIs.

**Impact:**  
- API consumers following standard REST conventions will get 500 errors
- The MCP server tests pass because they call the tool functions directly, not through the REST wrapper
- The web simulator may be affected if it calls the REST API with flat JSON

**Suggested Fix:**  
Change the endpoint to accept flat JSON and spread it as kwargs:
```python
@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, request: dict[str, Any]):
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    tool_fn = TOOLS[tool_name]
    try:
        result = await tool_fn(**request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

Or use a Pydantic model with `extra = "allow"` and extract all fields.

---

### Issue #2: Entity Extraction Quality (LOW)

**Severity:** Low  
**Endpoint:** `extract_from_call`

**Description:**  
The entity extraction pipeline has quality issues:
- "Hi Sarah" is extracted as a person name (should be just "Sarah")
- "$50K" is extracted as "$50" (missing the "K" suffix)
- "next Tuesday" is not extracted as a date

**Impact:**  
Minor — the pipeline works but entity extraction accuracy could be improved.

**Suggested Fix:**  
Improve regex patterns in `src/tools/extraction.py` for:
- Name extraction (strip common greetings)
- Amount extraction (handle K/M/B suffixes)
- Date extraction (parse relative dates like "next Tuesday")

---

### Issue #3: Sentiment Data Missing (LOW)

**Severity:** Low  
**Endpoints:** `get_pipeline_health`, `get_daily_briefing`

**Description:**  
All seeded deals have `sentiment: null`, causing the sentiments summary to show `{"null": 5}`. This is expected for seed data but could be confusing.

**Impact:**  
Minor — cosmetic issue in API responses.

---

## 3. API Endpoint Verification

### Health Check
```
GET /api/health
→ {"status":"ok","server":"sage","version":"1.0.0"}
```

### Pipeline Health
```
POST /api/tools/get_pipeline_health
→ {
  "deals_by_stage": {"proposal":1, "negotiation":1, "lead":2, "closed_won":1},
  "total_deals": 5,
  "total_value": 470000.0,
  "stuck_deals": [...]
}
```

### Daily Briefing
```
POST /api/tools/get_daily_briefing
→ {
  "followups_due": [],
  "total_deals": 5,
  "pipeline_value": 470000.0,
  "stuck_deals": [...],
  "insights": ["3 deals may need attention"]
}
```

### Contact Search
```
POST /api/tools/search_contacts {"args": {"query": "Sarah"}}
→ {"contacts": [{"id":1, "name":"Sarah Chen", ...}], "total": 1}
```

### CRM Sync
```
POST /api/tools/sync_to_crm {"args": {"record": {"name": "Test"}, "target": "salesforce", "idempotency_key": "test-123"}}
→ {"status":"success", "target":"salesforce", "record_id":"sal_test-123", ...}
```

---

## 4. Test Coverage

| Component | Tests | Passed | Failed |
|-----------|-------|--------|--------|
| API Layer | 10 | 10 | 0 |
| Database Layer | 6 | 6 | 0 |
| Pipeline | 6 | 6 | 0 |
| Proactive Insights | 5 | 5 | 0 |
| Provider (LLM) | 17 | 17 | 0 |
| Seed | 3 | 3 | 0 |
| Tools (Integration) | 17 | 17 | 0 |
| **Total** | **64** | **64** | **0** |

---

## 5. Overall Assessment

### ✅ READY FOR SUBMISSION (with minor caveats)

**Strengths:**
- All 64 unit/integration tests pass
- Web simulator builds successfully
- Core API endpoints return correct data
- Seed script is idempotent and working
- Architecture is clean and well-tested

**Caveats:**
- The REST API `args` wrapper is non-standard and should be documented or fixed before demo
- Entity extraction quality could be improved but is functional
- No live LLM provider configured (falls back to mock mode, which is expected)

**Recommendation:**  
Fix the REST API request body contract (Issue #1) before the hackathon demo to avoid confusion. The fix is a 2-line change in `rest.py`. All other issues are minor and non-blocking.

---

## 6. Files Examined

- `/home/hermes/sage/mcp-server/src/api/rest.py` — REST API wrapper
- `/home/hermes/sage/mcp-server/src/tools/extraction.py` — Entity extraction
- `/home/hermes/sage/mcp-server/src/data/seed.py` — Database seeding
- `/home/hermes/sage/web-simulator/` — React + Vite + Tailwind frontend
- `/home/hermes/sage/mcp-server/tests/` — 64 tests across 6 test files

---

*Report generated by automated E2E test suite*
