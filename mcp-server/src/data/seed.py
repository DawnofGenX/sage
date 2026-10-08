"""Seed the database with demo contacts and deals.

Usage:
    python -m src.data.seed
"""
import json
import os

from data.db import Database


def load_json(filename: str) -> list:
    """Load a JSON file from the data directory.

    Seed data lives at `<repo>/mcp-server/data/` — one tracked copy, inside the
    Docker image's build context (`build: ./mcp-server`), so the container and
    a checkout resolve the same bytes.

    The previous implementation resolved `<src/data>/../../../data` (the repo
    root), which worked from a checkout but resolved to `/data` inside the
    image and raised FileNotFoundError during the build-time seed — leaving the
    container with an empty database while the test suite still passed.
    """
    src_data_dir = os.path.dirname(__file__)
    # src/data/seed.py -> mcp-server/data/
    data_dir = os.path.join(src_data_dir, "..", "..", "data")

    filepath = os.path.abspath(os.path.join(data_dir, filename))
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Seed data {filename!r} not found at {filepath}. Expected the file "
            "at mcp-server/data/ (the Docker build context and the checkout both "
            "resolve this path)."
        )

    with open(filepath, "r") as f:
        return json.load(f)


def seed(db: Database) -> dict:
    """Seed the database with contacts and deals. Idempotent."""
    contacts_data = load_json("contacts.json")
    deals_data = load_json("deals.json")

    # Seed contacts (skip if name already exists)
    contact_ids = {}
    contacts_created = 0
    contacts_skipped = 0
    for c in contacts_data:
        existing = db.search_contacts(c["name"])
        if existing:
            contact_ids[c["name"]] = existing[0]["id"]
            contacts_skipped += 1
        else:
            contact_id = db.create_contact(c)
            contact_ids[c["name"]] = contact_id
            contacts_created += 1

    # Seed deals (skip if title already exists)
    deals_created = 0
    deals_skipped = 0
    for d in deals_data:
        existing_deals = db.get_all_deals()
        if any(ed["title"] == d["title"] for ed in existing_deals):
            deals_skipped += 1
        else:
            contact_id = contact_ids.get(d["contact"])
            db.create_deal({
                "contact_id": contact_id,
                "title": d["title"],
                "value": d["value"],
                "stage": d["stage"],
                "notes": d["notes"],
            })
            deals_created += 1

    return {
        "contacts_created": contacts_created,
        "contacts_skipped": contacts_skipped,
        "deals_created": deals_created,
        "deals_skipped": deals_skipped,
    }


def main():
    db = Database()
    result = seed(db)

    print("=" * 50)
    print("Sage Database Seed Summary")
    print("=" * 50)
    print(f"Contacts created: {result['contacts_created']}")
    print(f"Contacts skipped (already exist): {result['contacts_skipped']}")
    print(f"Deals created: {result['deals_created']}")
    print(f"Deals skipped (already exist): {result['deals_skipped']}")
    print("=" * 50)

    all_contacts = db.get_all_contacts()
    all_deals = db.get_all_deals()
    print(f"Total contacts in database: {len(all_contacts)}")
    print(f"Total deals in database: {len(all_deals)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
