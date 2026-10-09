"""Shared pytest fixtures and path setup for Sage MCP server tests.

Every test file previously duplicated the same boilerplate:
    - Create a temp database file
    - Set SAGE_DB_PATH
    - Add src/ to sys.path

This module centralizes that so individual test files can focus on
testing behavior, not environment setup.
"""
import os
import sys
import tempfile

# Ensure src/ is on the path so `from tools.x import ...` works.
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Isolated database so tests never touch a real one.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SAGE_DB_PATH"] = _tmp_db.name
