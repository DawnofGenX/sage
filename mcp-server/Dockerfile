FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
COPY pyproject.toml ./
# The src/ layout means `from server import mcp`, `from tools... import ...` only
# resolve once the project itself is installed — the same constraint the test
# suite has (see the comment block in requirements.txt and the README). src/ is
# copied BEFORE the editable install because egg_info inspects it at build time.
COPY src/ ./src/
# Seed data is copied to /app/seed-data, NOT /app/data.
#
# /app/data is where the sage-data volume mounts, and a named volume replaces
# the image's directory at runtime — the JSON baked into the image is masked by
# the volume's contents. That is invisible at build time (the build-time seed
# used to work) and fatal at runtime, when the entrypoint's seed runs after the
# mount is in place: FileNotFoundError, no seed, and the demo surfaces empty.
#
# A directory outside the mount is reachable in every environment: the seed
# data is static, part of the image, and never user data.
COPY data/ ./seed-data/

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
