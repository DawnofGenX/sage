"""Database must resolve SAGE_DB_PATH regardless of the construction site.

The defect: Database() defaulted to the literal string "sage.db" — a relative
path resolving against the process CWD. In the container that is /app (ephemeral
filesystem), not the sage-data volume mounted at /app/data, so every write was
lost on recreate while `docker compose down -v` reset nothing.

Separately, only tools/common.py read SAGE_DB_PATH. src/data/seed.py and the
server.py resource built a Database on a DIFFERENT file than every tool call, so
setting the env var changed tool behaviour and nothing else.
"""
import os

import pytest


def test_database_honors_sage_db_path(monkeypatch, tmp_path):
    from data.db import Database

    target = tmp_path / "from-env.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(target))

    db = Database()
    assert db.db_path == str(target)
    # And it writes there, not to a relative sage.db in the CWD.
    contact_id = db.create_contact({"name": "Env Contact"})
    assert target.exists()
    assert db.get_contact(contact_id)["name"] == "Env Contact"


def test_database_without_env_falls_back_to_relative(monkeypatch):
    """Local-dev behaviour is unchanged: no env var means sage.db in the CWD."""
    from data.db import Database

    monkeypatch.delenv("SAGE_DB_PATH", raising=False)
    assert Database().db_path == "sage.db"


def test_explicit_db_path_still_wins(monkeypatch, tmp_path):
    """An explicit argument must not be overridden by the env var."""
    from data.db import Database

    explicit = tmp_path / "explicit.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(tmp_path / "from-env.db"))

    assert Database(db_path=str(explicit)).db_path == str(explicit)


def test_seed_writes_to_sage_db_path(monkeypatch, tmp_path):
    """The old failure: seed.py called Database() and ignored the env var."""
    from data.db import Database
    from data.seed import seed

    target = tmp_path / "seed-target.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(target))

    result = seed(Database())
    assert target.exists(), "seed wrote to a different file than SAGE_DB_PATH"
    assert result["contacts_created"] > 0


def test_container_and_tools_agree_on_one_file(monkeypatch, tmp_path):
    """The point of all this: every construction site resolves to one file."""
    target = tmp_path / "shared.db"
    monkeypatch.setenv("SAGE_DB_PATH", str(target))

    import tools.common as common
    from data.db import Database
    from data.seed import seed

    # Simulate a fresh process: clear the cached singleton.
    common._db = None
    seed(Database())

    via_tools = common._get_db()
    assert via_tools.db_path == str(target), (
        "tools/common.py and Database() disagree on the path"
    )
    # The seeded rows are visible through the tool layer, proving they share
    # the file rather than merely agreeing on its name.
    assert via_tools.get_all_contacts(), "seed data not visible via tools"
