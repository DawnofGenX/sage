"""Shared utilities for tool implementations."""
import os
from data.db import Database

_db = None


def _get_db() -> Database:
    """Get a Database instance with the configured path."""
    global _db
    if _db is None:
        _db = Database(os.environ.get("SAGE_DB_PATH", "sage.db"))
    return _db
