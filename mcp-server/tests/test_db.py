import os
import tempfile

import pytest


from data.db import Database


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = Database(db_path=db_path)
    yield database
    os.unlink(db_path)


def test_create_contact(db):
    contact_id = db.create_contact({"name": "Alice", "company": "Acme"})
    assert contact_id > 0
    contact = db.get_contact(contact_id)
    assert contact is not None
    assert contact["name"] == "Alice"
    assert contact["company"] == "Acme"


def test_create_deal(db):
    contact_id = db.create_contact({"name": "Bob", "company": "Globex"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Test Deal", "value": 1000.0})
    assert deal_id > 0
    deal = db.get_deal(deal_id)
    assert deal is not None
    assert deal["title"] == "Test Deal"
    assert deal["contact_id"] == contact_id


def test_search_contacts(db):
    db.create_contact({"name": "Charlie", "company": "Initech"})
    db.create_contact({"name": "Diana", "company": "Umbrella"})
    results = db.search_contacts("Charlie")
    assert len(results) == 1
    assert results[0]["name"] == "Charlie"


def test_get_all_deals(db):
    contact_id = db.create_contact({"name": "Eve"})
    db.create_deal({"contact_id": contact_id, "title": "Deal 1"})
    db.create_deal({"contact_id": contact_id, "title": "Deal 2"})
    deals = db.get_all_deals()
    assert len(deals) == 2


def test_update_deal_stage(db):
    contact_id = db.create_contact({"name": "Frank"})
    deal_id = db.create_deal({"contact_id": contact_id, "title": "Stage Test"})
    result = db.update_deal_stage(deal_id, "won")
    assert result is True
    deal = db.get_deal(deal_id)
    assert deal["stage"] == "won"


def test_log_call(db):
    contact_id = db.create_contact({"name": "Grace"})
    call_id = db.log_call({
        "contact_id": contact_id,
        "summary": "Great call",
        "duration_seconds": 300,
    })
    assert call_id > 0
    conn = db._get_conn()
    row = conn.execute("SELECT * FROM call_logs WHERE id = ?", (call_id,)).fetchone()
    conn.close()
    assert row is not None
    assert row["summary"] == "Great call"
