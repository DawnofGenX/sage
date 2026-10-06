"""Tests for the local CRM target.

The "local" target exists so the demo can show a sync that genuinely succeeds
with no external credentials. These tests assert it is a real implementation —
real rows, real deterministic IDs, and idempotency enforced by a UNIQUE
constraint rather than asserted in prose.

Every test uses an isolated temp database via SAGE_DB_PATH, so nothing here
touches the developer's sage.db.
"""

import asyncio
import os
import re
import sqlite3

import pytest

# Must be set before any Sage module reads it at import time.
_TMP_DB = "/tmp/sage_local_crm_test.db"

ID_PATTERN = re.compile(r"^loc_[cd]_[0-9A-HJKMNP-TV-Z]{26}$")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Point SAGE_DB_PATH at a fresh temp DB for each test."""
    db = tmp_path / "local_crm.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(db))
    yield db


@pytest.fixture
def store():
    from sync import LocalCRMSync

    return LocalCRMSync()


# ==================================================================
# Record IDs
# ==================================================================


def test_contact_id_has_ulid_shape():
    """A local contact ID looks like a real CRM record ID, not a counter."""
    from sync.local import _derive_id

    rid = _derive_id("c", "some-key")
    assert ID_PATTERN.match(rid), f"{rid!r} is not loc_<type>_<26 crockford chars>"


def test_deal_id_prefix_differs_from_contact():
    from sync.local import _derive_id

    assert _derive_id("c", "k").startswith("loc_c_")
    assert _derive_id("d", "k").startswith("loc_d_")


def test_id_is_deterministic_across_databases(tmp_path):
    """The same key yields the same ID in a different database.

    This is what lets a recorded demo match a live one.
    """
    from sync import LocalCRMSync

    a = LocalCRMSync(str(tmp_path / "a.db"))
    b = LocalCRMSync(str(tmp_path / "b.db"))

    ra = asyncio.run(a.create_contact({"name": "Sarah Chen", "idempotency_key": "k-1"}))
    rb = asyncio.run(b.create_contact({"name": "Sarah Chen", "idempotency_key": "k-1"}))

    assert ra["id"] == rb["id"]


def test_different_keys_yield_different_ids(tmp_path):
    from sync import LocalCRMSync

    s = LocalCRMSync(str(tmp_path / "x.db"))
    a = asyncio.run(s.create_contact({"name": "A", "idempotency_key": "k-1"}))
    b = asyncio.run(s.create_contact({"name": "B", "idempotency_key": "k-2"}))
    assert a["id"] != b["id"]


# ==================================================================
# Rows are really written
# ==================================================================


def test_contact_sync_writes_a_real_row(store):
    result = asyncio.run(
        store.create_contact(
            {
                "name": "Sarah Chen",
                "company": "Acme Corp",
                "email": "sarah@acme.com",
                "title": "VP Engineering",
                "idempotency_key": "k-contact",
            }
        )
    )
    assert result["status"] == "created"

    stored = store.get_contact(result["id"])
    assert stored is not None, "row was not written"
    assert stored["first_name"] == "Sarah"
    assert stored["last_name"] == "Chen"
    assert stored["account_name"] == "Acme Corp"
    assert stored["email"] == "sarah@acme.com"


def test_deal_sync_writes_a_real_row_with_salesforce_field_names(store):
    """Field names mirror Salesforce so the two targets are comparable."""
    result = asyncio.run(
        store.create_deal(
            {
                "title": "Acme Enterprise License",
                "value": 50000,
                "stage": "negotiation",
                "idempotency_key": "k-deal",
            }
        )
    )
    assert result["status"] == "created"

    stored = store.get_deal(result["id"])
    assert stored is not None
    # Salesforce sobject vocabulary, not Sage's internal names.
    assert stored["name"] == "Acme Enterprise License"
    assert stored["stage_name"] == "Negotiation/Review"
    assert stored["amount"] == 50000
    assert stored["close_date"], "a real CRM record carries a close date"


def test_single_name_falls_back_to_last_name(store):
    """A CRM must not lose a contact whose name has no first token."""
    result = asyncio.run(
        store.create_contact({"name": "Cher", "idempotency_key": "k-oneword"})
    )
    stored = store.get_contact(result["id"])
    assert stored["last_name"] == "Cher"


def test_count_records_reflects_stored_rows(store):
    assert store.count_records() == 0
    asyncio.run(store.create_contact({"name": "A B", "idempotency_key": "k1"}))
    asyncio.run(store.create_deal({"title": "D", "idempotency_key": "k2"}))
    assert store.count_records() == 2
    assert store.count_records("contact") == 1
    assert store.count_records("deal") == 1


# ==================================================================
# Idempotency is enforced by the database, not asserted
# ==================================================================


def test_repeat_key_returns_already_synced_and_same_id(store):
    first = asyncio.run(store.create_contact({"name": "Sarah", "idempotency_key": "dup"}))
    second = asyncio.run(store.create_contact({"name": "Sarah", "idempotency_key": "dup"}))

    assert first["status"] == "created"
    assert second["status"] == "already_synced"
    assert second["id"] == first["id"]
    assert store.count_records("contact") == 1, "a repeat must not create a second row"


def test_repeat_key_on_deal_creates_no_duplicate(store):
    payload = {"title": "Deal", "value": 100, "idempotency_key": "dup-deal"}
    asyncio.run(store.create_deal(payload))
    second = asyncio.run(store.create_deal(payload))
    assert second["status"] == "already_synced"
    assert store.count_records("deal") == 1


def test_unique_constraint_is_what_enforces_it(store):
    """Prove the guard is the DB, not a code path that could be bypassed.

    Bypasses the adapter and writes a duplicate key directly. SQLite must
    refuse — this is what makes idempotency structural rather than a promise.
    """
    asyncio.run(store.create_contact({"name": "A", "idempotency_key": "uniq"}))
    conn = sqlite3.connect(store.db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO crm_local_sync_log "
                "(record_type, external_id, idempotency_key, target, payload) "
                "VALUES ('contact', 'loc_c_BYPASS', 'uniq', 'local', '{}')"
            )
    finally:
        conn.close()


def test_missing_idempotency_key_is_an_error_not_a_silent_record(store):
    result = asyncio.run(store.create_contact({"name": "No Key"}))
    assert "error" in result
    assert store.count_records() == 0


# ==================================================================
# End-to-end through the tool
# ==================================================================


def test_sync_to_crm_local_succeeds_with_real_provenance():
    from tools.sync import sync_to_crm

    result = asyncio.run(
        sync_to_crm(
            record={"name": "Sarah Chen", "company": "Acme Corp"},
            target="local",
            idempotency_key="tool-key",
        )
    )
    assert result["status"] == "success"
    assert result["provenance"] == "local"
    assert ID_PATTERN.match(result["record_id"]), result["record_id"]
    assert result["synced_at"], "a real sync is timestamped"


def test_sync_to_crm_local_deal_routes_to_the_deal_table():
    from tools.sync import sync_to_crm
    from sync import LocalCRMSync

    result = asyncio.run(
        sync_to_crm(
            record={"title": "Globex Platform", "value": 120000, "stage": "proposal"},
            target="local",
            idempotency_key="deal-key",
        )
    )
    assert result["status"] == "success"
    stored = LocalCRMSync().get_deal(result["record_id"])
    assert stored["stage_name"] == "Proposal/Price Quote"


def test_sync_to_crm_local_repeat_surfaces_already_synced():
    """The tool must distinguish a duplicate from a fresh create."""
    from tools.sync import sync_to_crm

    first = asyncio.run(
        sync_to_crm(record={"name": "Repeat"}, target="local", idempotency_key="twice")
    )
    second = asyncio.run(
        sync_to_crm(record={"name": "Repeat"}, target="local", idempotency_key="twice")
    )
    assert first["status"] == "success"
    assert second["status"] == "already_synced"
    assert second["record_id"] == first["record_id"]


def test_local_is_a_valid_target():
    from tools.sync import VALID_TARGETS

    assert "local" in VALID_TARGETS