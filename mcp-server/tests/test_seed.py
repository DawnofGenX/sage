import os
import tempfile

import pytest


from data.db import Database
from data.seed import seed


@pytest.fixture
def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    database = Database(db_path=db_path)
    yield database
    os.unlink(db_path)


def test_seed_contacts(db):
    """Verify all 10 contacts are seeded."""
    result = seed(db)
    assert result["contacts_created"] == 10

    contacts = db.get_all_contacts()
    assert len(contacts) == 10

    names = {c["name"] for c in contacts}
    expected = {
        "Sarah Chen",
        "Mike Johnson",
        "Jennifer Williams",
        "David Stark",
        "Lisa Wayne",
        "Tom Oscorp",
        "Amy Hooli",
        "James Cyberdyne",
        "Nina Tyrell",
        "Alex Weyland",
    }
    assert names == expected


def test_seed_deals(db):
    """Verify all 5 deals are seeded."""
    result = seed(db)
    assert result["deals_created"] == 5

    deals = db.get_all_deals()
    assert len(deals) == 5

    titles = {d["title"] for d in deals}
    expected = {
        "Acme Enterprise License",
        "Globex Platform Deal",
        "Initech Team Plan",
        "Stark Custom Deployment",
        "Wayne Enterprise Rollout",
    }
    assert titles == expected


def test_seed_idempotent(db):
    """Verify running seed twice doesn't create duplicates."""
    # First run
    result1 = seed(db)
    assert result1["contacts_created"] == 10
    assert result1["deals_created"] == 5

    contacts_after_first = len(db.get_all_contacts())
    deals_after_first = len(db.get_all_deals())
    assert contacts_after_first == 10
    assert deals_after_first == 5

    # Second run — should skip everything
    result2 = seed(db)
    assert result2["contacts_created"] == 0
    assert result2["contacts_skipped"] == 10
    assert result2["deals_created"] == 0
    assert result2["deals_skipped"] == 5

    contacts_after_second = len(db.get_all_contacts())
    deals_after_second = len(db.get_all_deals())
    assert contacts_after_second == 10
    assert deals_after_second == 5
