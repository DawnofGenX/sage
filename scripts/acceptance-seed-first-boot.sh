#!/bin/sh
# Acceptance test for seed-on-first-boot.
#
# The defect this proves fixed: the Dockerfile seeded at IMAGE BUILD time, which
# writes into the image layer. A named volume only receives image contents the
# first time it is created, so a pre-existing volume's /app/data masked the
# image's copy and the container came up with NO TABLES.
#
# Case 1 reproduces that broken state: a volume containing only a .gitkeep.
# Case 2 proves an operator's rows survive a restart.
#
# Run from /home/hermes/sage. Requires docker compose. Idempotent.
set -e

# scripts/ sits directly under the repo root, so one level up — not two.
# (`../..` landed in /home, where `docker compose build mcp-server` reports
# "no such service" and the whole run is meaningless.)
cd "$(dirname "$0")/.."   # -> /home/hermes/sage
REPO="$PWD"
[ -f "$REPO/docker-compose.yml" ] || { echo "not at repo root: $REPO"; exit 1; }

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; exit 1; }

# One run at a time. Two concurrent runs share the volume and the container
# name, so the second sees the first's database and passes or fails arbitrarily.
# A lock is the difference between "verified" and "undefined".
if ! mkdir /tmp/.sage-acceptance.lock.d 2>/dev/null; then
    fail "another acceptance run is in progress (/tmp/.sage-acceptance.lock.d) — wait for it"
fi
trap 'rm -rf /tmp/.sage-acceptance.lock.d' EXIT

count_sql() {
    docker exec sage-mcp-server-1 python -c "
import sqlite3, sys
c = sqlite3.connect('/app/data/sage.db')
try:
    print(c.execute('$1').fetchone()[0])
except Exception as e:
    print('ERR', e)
"
}

echo "=== building ==="
docker compose build mcp-server 2>&1 | tail -2

echo
echo "=== CASE 1: volume created by an OLD image (the defect) ==="

# Stop first. A running container holds the volume open, `docker volume rm`
# then fails with "volume is in use", and with `|| true` that failure is
# invisible — which is exactly the class of silent-success bug this test exists
# to catch. Refuse to continue rather than pass against the wrong volume.
if ! docker compose down >/dev/null 2>&1; then
    fail "docker compose down failed — cannot get a clean volume"
fi

if docker volume inspect sage_sage-data >/dev/null 2>&1; then
    if ! docker volume rm sage_sage-data >/dev/null 2>&1; then
        fail "could not remove sage_sage-data (still in use?)"
    fi
fi
docker volume inspect sage_sage-data >/dev/null 2>&1 \
  && fail "sage_sage-data still exists after removal"

# Recreate the broken state: the volume holds only a .gitkeep, no tables.
docker run --rm -v sage_sage-data:/v alpine sh -c 'mkdir -p /v && touch /v/.gitkeep'

# Prove the setup really is the broken state before the fix is judged on it.
ENTRIES=$(docker run --rm -v sage_sage-data:/v alpine sh -c 'ls -A /v')
echo "volume contents before boot: [$ENTRIES]"
[ "$ENTRIES" = ".gitkeep" ] \
  || fail "volume is not the broken state (expected only .gitkeep)"

docker compose up -d >/dev/null 2>&1
sleep 12

CONTACTS=$(count_sql "SELECT COUNT(*) FROM contacts")
echo "contacts after boot: $CONTACTS"
case "$CONTACTS" in
  ERR*) fail "container booted with no tables: $CONTACTS" ;;
  0)    fail "container booted but seeded nothing" ;;
  *)    pass "cold boot seeds the database ($CONTACTS contacts)" ;;
esac

DEALS=$(count_sql "SELECT COUNT(*) FROM deals")
[ "$DEALS" -gt 0 ] && pass "deals seeded ($DEALS)" || fail "no deals seeded"

echo
echo "=== entrypoint reported what it did ==="
docker logs sage-mcp-server-1 2>&1 | grep -E "\[entrypoint\]" | tail -3 || fail "no entrypoint log lines"

echo
echo "=== CASE 2: an operator's row survives a restart ==="
curl -s -X POST localhost:8000/api/tools/create_contact \
  -H 'Content-Type: application/json' \
  -d '{"name": "Acceptance Probe Operator", "company": "Real Co"}' >/dev/null

BEFORE=$(count_sql "SELECT COUNT(*) FROM contacts WHERE name='Acceptance Probe Operator'")
docker compose restart mcp-server >/dev/null 2>&1
sleep 12

AFTER=$(count_sql "SELECT COUNT(*) FROM contacts WHERE name='Acceptance Probe Operator'")
echo "operator row before=$BEFORE after=$AFTER"
[ "$BEFORE" = "1" ] && [ "$AFTER" = "1" ] \
  && pass "operator row survived restart" \
  || fail "operator row lost (before=$BEFORE after=$AFTER)"

TOTAL=$(count_sql "SELECT COUNT(*) FROM contacts")
[ "$TOTAL" -gt "$CONTACTS" ] \
  && pass "seed did not overwrite existing data (total $TOTAL > seeded $CONTACTS)" \
  || fail "existing data was replaced (total $TOTAL, seeded $CONTACTS)"

echo
echo "=== health ==="
curl -s localhost:8000/api/health || fail "health endpoint unreachable"
echo
pass "health endpoint reachable"

echo
echo "RESULT: ALL PASS"
