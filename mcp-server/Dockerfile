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

# Seed so the container is demo-ready on first boot. The API creates the schema
# on demand when this is skipped, but without seed data every demo surface is
# empty.
#
# SAGE_DB_PATH matters more than it looks. Database() defaults to the relative
# path "sage.db", which resolves against the WORKDIR (/app) — that is inside the
# container's ephemeral filesystem, NOT the sage-data volume mounted at
# /app/data. Every write was lost on recreate while the volume held only a
# 0-byte .gitkeep, and `docker compose down -v` reset nothing.
#
# The seed below, and the server at runtime, must both point at the volume.
ENV SAGE_DB_PATH=/app/data/sage.db
RUN python -m src.data.seed || true

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.rest:app", "--host", "0.0.0.0", "--port", "8000"]
