"""Seed-on-first-boot: seed only when the database is empty.

Build-time seeding cannot reach a pre-existing volume — the volume's own
/app/data masks the image's copy — so the container needs to seed at start,
against the database it actually finds.
"""
import pytest

from data.db import Database  # noqa: E402
from data.seed import ensure_seeded  # noqa: E402


@pytest.fixture
def db(tmp_path):
    """A clean, isolated database per test.

    A module-level temp file persists between tests, so whichever test runs
    first seeds it and every later test sees a populated database — the
    opposite of the "empty" state under test. tmp_path gives each test its own
    file, which is what makes the seed/skip assertions meaningful.
    """
    return Database(db_path=str(tmp_path / "seed-test.db"))


def test_ensure_seeded_populates_an_empty_database(db):
    result = ensure_seeded(db)
    assert result["seeded"] is True
    assert result["contacts_created"] > 0
    assert db.get_all_contacts(), "seed ran but no contacts exist"


def test_ensure_seeded_skips_a_populated_database(db):
    """The whole point: an existing database is not overwritten."""
    ensure_seeded(db)
    before = len(db.get_all_contacts())

    # A record the seed does not know about.
    db.create_contact({"name": "Operator Added Client", "company": "Real Co"})

    result = ensure_seeded(db)
    assert result["seeded"] is False
    assert result["reason"], "the skip path must say why it skipped"
    assert "contacts_created" not in result, (
        "skip path must not report seed counters — it did not seed"
    )
    after = db.get_all_contacts()
    assert len(after) == before + 1, "ensure_seeded must not touch existing data"
    assert any(c["name"] == "Operator Added Client" for c in after), (
        "existing rows must survive"
    )


def test_ensure_seeded_is_idempotent(db):
    first = ensure_seeded(db)
    second = ensure_seeded(db)
    assert first["seeded"] is True
    assert second["seeded"] is False
    assert "contacts_created" not in second, "second call seeds nothing"
    assert second["reason"], "must explain why nothing was seeded"


def test_ensure_seeded_creates_the_schema_when_missing(tmp_path):
    """The real first-boot case: a .gitkeep-only volume has no file at all.

    Database.__init__ runs _init_schema(), so a file that exists always has
    tables. The state that actually occurs on a fresh volume is "no file", and
    that must seed. (An earlier version of this test dropped the contacts table
    to simulate it, but that produces a state Database cannot get itself into —
    and the assertion failed for a reason that never happens in the container.)
    """
    fresh = tmp_path / "no-file-yet.db"
    assert not fresh.exists()

    db = Database(db_path=str(fresh))
    result = ensure_seeded(db)

    assert result["seeded"] is True, "a volume with no database file is empty"
    assert fresh.exists(), "the seed must create the database file"
    assert db.get_all_contacts(), "seed ran but no contacts exist"
    assert result["contacts_created"] > 0


def test_entrypoint_script_exists_and_is_executable():
    """The boot path must exist in the image, not just in a doc."""
    import stat
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "entrypoint.sh"
    assert script.exists(), "entrypoint.sh is missing"
    assert script.stat().st_mode & stat.S_IXUSR, "entrypoint.sh is not executable"


def test_dockerfile_seeds_at_runtime_not_build_time():
    """A build-time RUN ... seed cannot reach a volume that already exists."""
    from pathlib import Path

    dockerfile = (
        Path(__file__).resolve().parent.parent / "Dockerfile"
    ).read_text()
    assert "RUN python -m src.data.seed" not in dockerfile, (
        "build-time seed stays: it only works on a fresh volume"
    )
    assert "entrypoint.sh" in dockerfile, "the runtime entrypoint is not wired in"
