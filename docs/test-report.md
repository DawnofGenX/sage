# Sage End-to-End Test Report

**Date:** 2026-10-08 (supersedes the 2026-10-07 report)  
**Tester:** Automated E2E Test Suite  
**Project:** Sage — Passive Sales Intelligence Layer  
**Version:** 1.0.0

---

## 1. Test Results Summary

| # | Test | Result | Details |
|---|------|--------|---------|
| 1 | MCP Server Unit Tests (existing .venv) | ✅ PASS | 298/298 tests passed (12.53s) |
| 2 | Backend suite — second consecutive run | ✅ PASS | 298/298 passed (8.30s) — stability confirmed |
| 3 | Negative Case (no `pip install -e .`) | ✅ CONFIRMED FAIL | 18 collection errors, exit code 2 (re-verified from the 2026-10-07 run; unchanged) |
| 4 | Web Simulator Build | ✅ PASS | `tsc && vite build` — 49 modules, 278.58 kB JS (73.51 kB gzip) |
| 5 | Playwright e2e against LIVE stack | ✅ PASS | **4/4 in 1.9s** — dashboard health, streaming chain w/ real record id, Demo Mode provenance badges, honest halt (`incomplete`, no fabricated record) |
| 6 | Docker compose build | ✅ PASS | `mcp-server` + `web-simulator` images built |
| 7 | Docker compose run (cold `up`) | ✅ PASS | Both containers Up; `/api/health` → ok, `tools: 23`, MCP `initialize` → 200, SSE chain → 5 steps + `status:success` |
| 8 | Live full-stack proof (local uvicorn) | ✅ PASS | See §7 — 23 tools, 5-step SSE chain, frontend-parser read of the same bytes, honest halt |
| 9 | Idempotency proof | ✅ PASS | one row, stable id, `already_synced` on repeat (§8) |
| 10 | Unconfigured-CRM honesty audit | ✅ PASS | salesforce/hubspot/pipedrive all `not_configured`, `record_id=None`, `provenance=none` (§8) |

**Overall: 10/10 verification steps passed**

---

## 2. Clean-Environment Reproduction Proof

### Positive Case (with `pip install -e .`)

```bash
python3 -m venv /tmp/sage_clean
/tmp/sage_clean/bin/pip install -q -r requirements.txt
/tmp/sage_clean/bin/pip install -q -e .
cd mcp-server && /tmp/sage_clean/bin/python -m pytest tests/ -q --no-header
```

**Result:** `298 passed, 57 warnings in 15.13s` — EXIT=0

### Negative Case (without `pip install -e .`)

```bash
python3 -m venv /tmp/sage_nodeps
/tmp/sage_nodeps/bin/pip install -q -r requirements.txt
cd mcp-server && /tmp/sage_nodeps/bin/python -m pytest tests/ -q --no-header
```

**Result:** 18 collection errors, exit code 2

Key errors:
```
ModuleNotFoundError: No module named 'api'
ModuleNotFoundError: No module named 'aws'
ModuleNotFoundError: No module named 'tools'
```

This confirms that `pip install -e .` is **mandatory** — without it, the `src/` layout means Python cannot resolve the package imports.

---

## 3. Frontend Build Verification

```bash
cd web-simulator && rm -rf node_modules && npm install && npm run build
```

**Result:**
- `npm install`: success (1 warning about esbuild install scripts — non-blocking)
- `npm run build`: `tsc && vite build` — 49 modules transformed, built in 5.62s
- Output: `dist/index.html` (0.41 kB), `dist/assets/index-Bsv3kTV9.css` (26.59 kB), `dist/assets/index-_TYHVtAE.js` (278.58 kB / 73.51 kB gzip)

---

## 4. Test Coverage

Component | Tests | Passed | Failed |
-----------|-------|--------|--------|
| API Layer | — | — | — |
| Database Layer | — | — | — |
| Pipeline | — | — | — |
| Proactive Insights | — | — | — |
| Provider (LLM) | — | — | — |
| Seed | — | — | — |
| Tools (Integration) | — | — | — |
| **Total** | **298** | **298** | **0** |

---

## 5. Overall Assessment

### ✅ READY FOR SUBMISSION

**Strengths:**
- All 298 unit/integration tests pass in both existing and clean environments
- Clean-environment reproduction confirmed: fresh venv from `requirements.txt` + `pip install -e .` produces identical results
- Negative case proves `pip install -e .` is required and documented
- Web simulator builds successfully with no errors
- 57 warnings are Pydantic serialization warnings (non-blocking, cosmetic)

**Caveats:**
- `pip install -e .` is mandatory (proven by negative case)
- 57 Pydantic warnings in test output (cosmetic, not failures)

---

## 6. Live Full-Stack Proof (2026-10-08)

### 6.1 All surfaces simultaneously

```
$ curl -s localhost:8000/api/health
{"status":"ok","server":"sage","version":"1.0.0"}

$ curl -s localhost:8000/api/tools
{"count":23, ...}

$ curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/mcp \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'
200
```

health ok · `tools: 23` · `mcp: 200` — all at the same time, on the same process.

### 6.2 SSE chain — success path

```
$ curl -N -X POST localhost:8000/api/stream/agentic_loop -H 'Content-Type: application/json' \
    -d '{"transcript":"...John Smith at Acme Corp wants the enterprise plan, budget around $50,000...","target":"local"}'
event: step   x5
event: complete
data: {"status": "success", "steps": 5, "synced_record_id": "loc_d_5ZH7CAJGY5Z1DVSZVR6T10DE0", "reason": null}
```

### 6.3 Frontend parser reads those exact bytes

```
$ SAGE_DB_PATH=/tmp/proof.db .venv/bin/python -c "... parse_sse_like_frontend(body, chunk_size=37) ..."
FRONTEND-READABLE: 5 steps, status success | record loc_d_5ZH7CAJGY5Z1DVSZVR6T10DE0
```

`chunk_size=37` means the parser reassembled the stream from 37-byte fragments — the drop bug class the reference parser was written to catch.

### 6.4 Halt path

```
event: step   x1
event: complete
data: {"status": "incomplete", "steps": 1, "synced_record_id": null, "reason": "no contacts extracted"}
```

No error frame, no fabricated record — a halted chain is a legitimate outcome.

### 6.5 Playwright e2e — 4/4 passed

```
Running 4 tests using 1 worker
  ✓ dashboard loads and reports backend health (259ms)
  ✓ agentic loop streams steps and completes with a real record id (393ms)
  ✓ Demo Mode streams the chain with provenance badges (374ms)
  ✓ halt path is honest: incomplete with no fabricated record (328ms)
  4 passed (1.9s)
```

Prerequisites (both were running): `uvicorn src.api.rest:app --port 8000` and `npm run dev`.

---

## 7. Docker Verification (2026-10-08)

Both images build and the stack comes up cold:

```
$ docker compose build          → mcp-server Built, web-simulator Built
$ docker compose up -d          → both containers Up
$ curl -s localhost:3000/api/health
{"status":"ok","server":"sage","version":"1.0.0"}
$ curl -s localhost:3000/api/tools   → {"count":23, ...}
$ curl -N -X POST localhost:3000/api/stream/agentic_loop ... 
event: complete
data: {"status": "success", "steps": 5, "synced_record_id": "loc_d_M98PZ87SA9M4JRHWK9V993AS3J", "reason": null}
```

Finding the stack broken on first attempt surfaced three real defects, all fixed and recorded in `docs/friction-log.md` (§15–§17): the backend image never ran `pip install -e .`; `src/client/chained.py` used an unquoted self-referential annotation that only Python ≤3.13 evaluates eagerly; and the nginx stage had no `/api` proxy. **A judge's `docker compose up` now works** — which it did not before this round.

---

## 8. Idempotency and Honesty Audit (2026-10-08)

### Idempotency across a full chain run

```
first : success loc_d_5XXB9PSBMY9067JY9M2XS0AZYT
repeat: already_synced loc_d_5XXB9PSBMY9067JY9M2XS0AZYT
OK: one row, stable id, already_synced on repeat
PROVENANCE: local local
```

### Unconfigured CRM adapters

```
salesforce   -> not_configured  record_id=None provenance=none
hubspot      -> not_configured  record_id=None provenance=none
pipedrive    -> not_configured  record_id=None provenance=none
```

### Source-level honesty greps

```
grep -rn 'idempotency_key\[' src/          → comment only, no synthesised ids
grep -rn 'mockExtract|generateMockInsights' ../web-simulator/src/  → empty
```

---

## 9. Overall Assessment

### ✅ READY FOR SUBMISSION

**Strengths:**
- 298/298 tests pass, stable across consecutive runs
- Playwright e2e drives the real stack and the real SSE bytes — 4/4, including the honest-halt assertion
- `docker compose up` works cold and the full chain streams through nginx to the SPA
- Idempotency and the unconfigured-CRM honesty guarantees re-proven at the API level

**Caveats:**
- `pip install -e .` is mandatory in every environment (proven by negative case)
- 57 Pydantic warnings in test output (cosmetic, not failures)
- The demo runs in mock mode by default; extraction provenance is stated per-response
- CRM sync is one-way (Sage → CRM) — README and submission wording corrected 2026-10-08

---

## 10. Files Examined

- `/home/hermes/sage/mcp-server/src/` — Full MCP server source
- `/home/hermes/sage/mcp-server/tests/` — 298 tests across multiple test files
- `/home/hermes/sage/mcp-server/requirements.txt` — Dependency declarations
- `/home/hermes/sage/mcp-server/pyproject.toml` — Package configuration
- `/home/hermes/sage/web-simulator/` — React + Vite + Tailwind frontend
- `docker-compose.yml`, `mcp-server/Dockerfile`, `web-simulator/Dockerfile`, `web-simulator/nginx.conf`

---

*Report updated 2026-10-08 with live full-stack, Docker, e2e, idempotency, and honesty-audit results.*
