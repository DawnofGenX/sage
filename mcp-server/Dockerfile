FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
COPY pyproject.toml ./
# The src/ layout means `from server import mcp`, `from tools... import ...` only
# resolve once the project itself is installed — the same constraint the test
# suite has (see the comment block in requirements.txt and the README). src/ is
# copied BEFORE the editable install because egg_info inspects it at build time.
COPY src/ ./src/
# Seed data lives at the REPO ROOT (`<repo>/data/`). The compose build context
# is `./mcp-server`, so this COPY pulls it in as `<root>/mcp-server/data/`.
# `src/data/seed.py` resolves both that and the `<repo>/data` layout; the old
# `<src/data>/../../../data` path resolved to `/data` inside the image and
# raised FileNotFoundError, leaving the container with an empty database.
COPY data/ ./data/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e . --no-deps

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# SAGE_DB_PATH is load-bearing. Database() resolves it as its default path;
# without it the path falls back to the relative "sage.db", which resolves
# against the WORKDIR (/app) — ephemeral filesystem, not the sage-data volume
# mounted at /app/data. Every write was lost on recreate while the volume held
# only a 0-byte .gitkeep, and `docker compose down -v` reset nothing.
ENV SAGE_DB_PATH=/app/data/sage.db

# Seeding is deliberately NOT a build-time step. A build-time RUN writes into
# the image layer, and a named volume only receives image contents the first
# time it is created — so an existing volume's /app/data masks the image's copy
# and the built-in seed silently does nothing. entrypoint.sh seeds at container
# start, against the database the container actually sees, and only when that
# database is empty.

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
