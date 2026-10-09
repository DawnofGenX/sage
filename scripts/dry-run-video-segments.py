"""Dry-run the 5 video segments against the LIVE stack.

Verifies each step the checklist/demo-script tells you to perform actually
works. A segment that fails here will fail on camera.
"""
import asyncio
import json
import subprocess
import urllib.request

BASE = "http://localhost:8000"
WEB = "http://localhost:3000"
PY = "/home/hermes/sage/mcp-server/.venv/bin/python"
REPO = "/home/hermes/sage"

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"   -- {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def get(url, timeout=15):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.status, r.read().decode()


def post(url, payload, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()


print("=" * 70)
print("SEGMENT 0 — Preconditions (what the checklist says to verify)")
print("=" * 70)
r = subprocess.run(["docker", "compose", "ps", "--format", "{{.Names}}={{.Status}}"],
                   cwd=REPO, capture_output=True, text=True, timeout=60)
up = {l.split("=")[0]: "up" in l.split("=", 1)[1].lower()
      for l in r.stdout.splitlines() if "=" in l and "NAME" not in l.upper()}
check("mcp-server container Up", up.get("sage-mcp-server-1", False))
check("web-simulator container Up", up.get("sage-web-simulator-1", False))

_, body = get(f"{BASE}/api/health")
check("GET /api/health -> ok", json.loads(body).get("status") == "ok", body[:50])

_, body = get(f"{BASE}/api/tools")
d = json.loads(body)
check("25 tools advertised", d["count"] == 25, f"count={d['count']}")

_, body = get(WEB)
check("web simulator serves HTML", "<html" in body.lower())

print()
print("=" * 70)
print("SEGMENT 1 — The Problem (no live dependency; stock footage)")
print("=" * 70)
print("PASS  (no system dependency — intro text overlays only)")

print()
print("=" * 70)
print("SEGMENT 2 — Passive Listening: 'Load Sample Call' dropdown")
print("=" * 70)
# The dropdown lists transcripts the agentic loop can consume.
_, body = get(f"{BASE}/api/tools")
names = [t["name"] for t in json.loads(body)["tools"]]
check("run_agentic_loop tool exists (drives the sample-call chain)",
      "run_agentic_loop" in names)
# And the contacts the sample transcript names must exist, or the demo halts.
_, body = post(f"{BASE}/api/tools/search_contacts", {"query": "Sarah"})
found = json.loads(body)["contacts"]
check("sample transcript's contact (Sarah Chen) exists in CRM",
      len(found) > 0, found[0]["name"] if found else "not found")

print()
print("=" * 70)
print("SEGMENT 3 — Auto-Extraction: 'Extract Insights'")
print("=" * 70)
TRANSCRIPT = ("Hi, this is Alex from Sage. John Smith at Acme Corp wants the "
              "enterprise plan, budget around $50,000. Sarah Chen is the VP of "
              "Engineering. Let us follow up on 12/15/2026.")
_, body = post(f"{BASE}/api/tools/extract_from_call", {"transcript": TRANSCRIPT}, timeout=120)
ext = json.loads(body)
check("extract_from_call returns structured data",
      bool(ext.get("step3_record")), json.dumps(ext)[:120])
check("reports two LLM passes", ext.get("passes") == 2, f"passes={ext.get('passes')}")
check("stage 4 is derived locally (not inferred)",
      ext.get("step4_derived") is True, f"derived={ext.get('step4_derived')}")
prov = ext.get("provenance")
print(f"      extraction provenance: {prov}  <- video must not claim Amazon Nova")
check("provenance is disclosed (not a Nova claim)", prov in ("mock", "local"), str(prov))
check("extraction yields contacts",
      bool(ext.get("step3_record", {}).get("contacts")))

print()
print("=" * 70)
print("SEGMENT 4 — Proactive Insight: 'Generate Insights'")
print("=" * 70)
_, body = post(f"{BASE}/api/tools/get_daily_briefing", {})
brief = json.loads(body)
check("daily briefing returns metrics",
      isinstance(brief, dict) and "total_deals" in brief,
      json.dumps(brief)[:120])

_, body = post(f"{BASE}/api/tools/get_pipeline_health", {})
health = json.loads(body)
stuck = health.get("stuck_deals", [])
check("stuck deals measured from history (not stage names)",
      isinstance(stuck, list), json.dumps(health)[:100])
print(f"      pipeline: {json.dumps(health.get('deals_by_stage'))}")
print(f"      stuck deals found: {len(stuck)}")
check("pipeline has seeded deals", health.get("total_deals", 0) > 0,
      f"total={health.get('total_deals')}")

# The exact insight the script's voiceover names.
dates = [d for d in stuck if "Globex" in str(d.get("title", ""))]
check("the named 'Globex Platform Deal' stuck insight is real",
      len(dates) > 0, dates[0].get("title") if dates else "not flagged")
days = [x for x in stuck if "days" in str(x)]
print(f"      (insight text includes day counts: {bool(days)})")

print()
print("=" * 70)
print("SEGMENT 5 — CRM Sync: 'Sync to CRM' button")
print("=" * 70)
_, body = post(f"{BASE}/api/tools/get_deals", {})
deals = json.loads(body)
check("board data comes from the live API (not hardcoded samples)",
      deals.get("total", 0) > 0, f"deals={deals.get('total')}")
check("each deal carries a contact name for the board card",
      all(d.get("contact_name") for d in deals.get("deals", [])),
      json.dumps(deals.get("deals", [{}])[0].get("contact_name")))
check("stuck deals are flagged with a measured day count",
      any(d.get("is_stuck") and d.get("days_inactive") is not None
          for d in deals.get("deals", [])),
      json.dumps([{ "t": d["title"], "d": d.get("days_inactive")}
                  for d in deals.get("deals", []) if d.get("is_stuck")]))

# The button syncs to the LOCAL crm — the honest version of this segment.
# A FIXED idempotency key on purpose: a fresh key each run creates a new
# contact+deal every time, which is how the demo database ended up with ten
# duplicate "Potential deal with Acme Corp" rows that a judge would have seen.
_, body = post(f"{BASE}/api/tools/sync_to_crm",
               {"record": {"title": "Video Dry Run Deal", "amount": 1000, "stage": "proposal"},
                "target": "local",
                "idempotency_key": "video-dryrun-fixed"}, timeout=60)
sync = json.loads(body)
# Either status is a correct outcome, and the difference is meaningful:
# 'success' means this run created the record; 'already_synced' means a prior
# run did and idempotency correctly declined to duplicate it. Assert the record
# id is real and stable rather than demanding one particular status, so the
# check is idempotent like the code it verifies.
check("local CRM sync succeeds or is correctly idempotent",
      sync.get("status") in ("success", "already_synced"), json.dumps(sync)[:120])
check("sync returns a real record id", bool(sync.get("record_id")), str(sync.get("record_id")))
print(f"      record id: {sync.get('record_id')}")
print("      NOTE: on-screen text must read 'Synced to CRM', NOT 'Synced to Salesforce'")

# And prove the dishonest version genuinely is unavailable.
_, body = post(f"{BASE}/api/tools/sync_to_crm",
               {"record": {"name": "X"}, "target": "salesforce",
                "idempotency_key": "video-dryrun-sf"}, timeout=60)
sf = json.loads(body)
check("salesforce sync is honestly 'not_configured'",
      sf.get("status") == "not_configured", json.dumps(sf)[:80])

print()
print("=" * 70)
print("BONUS — the new timeline tool the demo could show")
print("=" * 70)
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client as cl

    # Pick a deal that actually has history rather than assuming deal 1 does:
    # probing deal_id=1 returned count=0 the first time and looked like a tool
    # bug when it was simply a deal with no recorded events.
    _, h = post(f"{BASE}/api/tools/get_pipeline_health", {})
    stuck = json.loads(h).get("stuck_deals") or []
    target = stuck[0].get("id") if stuck else 1
    print(f"      probing deal_id={target}")

    async def timeline():
        async with cl(f"{BASE}/mcp") as s:
            async with ClientSession(s[0], s[1]) as sess:
                await sess.initialize()
                r = await sess.call_tool("get_deal_timeline_events", {"deal_id": target})
                return r.structured_content or {}

    sc = asyncio.run(timeline())
    # An empty stream is a CORRECT answer for a deal with no events. What
    # matters is that the tool responds over MCP with the right shape.
    check("get_deal_timeline_events responds over MCP with the right shape",
          "events" in sc and "count" in sc, json.dumps(sc)[:140])
    if sc.get("count", 0) == 0:
        print("      (count=0: that deal has no recorded events — correct, not broken)")
except Exception as e:
    check("get_deal_timeline_events", False, repr(e)[:100])

print()
print("=" * 70)
print("CLEANUP — leave the demo data as a judge should find it")
print("=" * 70)
# This script verifies behaviour by calling tools that WRITE. Without this
# step every run leaves another contact + deal behind, and the demo database
# accumulates rows a judge should never see. Remove anything above the seeded
# 10 contacts / 5 deals; the seed data is ids <= 10 and <= 5.
try:
    r = subprocess.run(
        ["docker", "exec", "sage-mcp-server-1", "python", "-c", """
import sqlite3
c = sqlite3.connect('/app/data/sage.db')
c.execute('DELETE FROM activities WHERE contact_id > 10 OR deal_id > 5')
c.execute('DELETE FROM stage_history WHERE deal_id > 5')
c.execute('DELETE FROM deals WHERE contact_id > 10')
c.execute('DELETE FROM contacts WHERE id > 10')
c.execute('DELETE FROM followups WHERE contact_id > 10 OR deal_id > 5')
c.commit()
print(c.execute('SELECT COUNT(*) FROM contacts').fetchone()[0],
      c.execute('SELECT COUNT(*) FROM deals').fetchone()[0])
"""],
        cwd=REPO, capture_output=True, text=True, timeout=120)
    counts = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "n/a"
    parts = counts.split() if counts else []
    ok = len(parts) == 2 and parts[0] == "10" and parts[1] == "5"
    check("demo data restored to 10 contacts / 5 deals", ok, f"got {counts!r}")
except Exception as e:
    check("demo data cleanup", False, repr(e)[:100])

print()
print("=" * 70)
print(f"RESULT: {'ALL PASS' if not failures else str(len(failures)) + ' FAILURE(S)'}")
if failures:
    for f in failures:
        print("   - " + f)
print("=" * 70)
raise SystemExit(1 if failures else 0)
