FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
COPY pyproject.toml ./
# The src/ layout means `from server import mcp`, `from tools... import ...` only
# resolve once the project itself is installed — the same constraint the test
# suite has (see the comment block in requirements.txt and the README). src/ is
# copied BEFORE the editable install because egg_info inspects it at build time.
COPY src/ ./src/
COPY data/ ./data/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -e . --no-deps

# Seed so the container is demo-ready on first boot. The API creates the schema
# on demand when this is skipped, but without seed data every demo surface is
# empty.
RUN python -m src.data.seed || true

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.api.rest:app", "--host", "0.0.0.0", "--port", "8000"]
