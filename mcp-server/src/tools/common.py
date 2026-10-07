"""Shared utilities for Sage MCP tools."""
import os

from data.db import Database
from llm.provider import LLMProvider

_db = None


def _get_db() -> Database:
    global _db
    if _db is None:
        db_path = os.environ.get("SAGE_DB_PATH", "sage.db")
        _db = Database(db_path=db_path)
    return _db


def _get_provider() -> LLMProvider:
    """Get an LLMProvider instance with default configuration."""
    return LLMProvider()
