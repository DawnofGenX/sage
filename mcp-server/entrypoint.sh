#!/bin/sh
# Seed on first boot, then start the API.
#
# Seeding at image build time writes into the image layer, and a named volume
# only receives image contents the first time it is created. On an existing
# volume the volume's own /app/data masks the image's copy, so the built-in
# seed silently did nothing and the demo surfaces came up empty.
#
# Seeding here runs against the database the container actually sees.
set -e

echo "[entrypoint] checking whether the database needs seeding..."

# The package is importable via the build-time `pip install -e .`, so plain
# `python` works in the image. Adding the package root to PYTHONPATH is what
# makes the same entrypoint work from a bare checkout too — without it the
# failure is `ModuleNotFoundError: No module named 'data.db'`.
#
# Resolved from the script's own directory (/app in the image) rather than
# hardcoded, so one entrypoint serves both the image and a local checkout.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/src/api/rest.py" ]; then PACKAGE_ROOT="$SCRIPT_DIR"; else PACKAGE_ROOT="/app"; fi
PYTHONPATH="$PACKAGE_ROOT/src:${PYTHONPATH:-}"
export PYTHONPATH

python - <<'PY'
import json

from data.db import Database
from data.seed import ensure_seeded

result = ensure_seeded(Database())
print("[entrypoint] seed:", json.dumps(result, default=str))
PY

echo "[entrypoint] starting uvicorn..."
exec python -m uvicorn src.api.rest:app --host 0.0.0.0 --port "${PORT:-8000}"
