# Sage Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose 2+
- Node.js 20+ (for local frontend development)
- Python 3.12+ (for local backend development)
- An Amazon Nova or OpenAI-compatible API key (optional — mock mode works without it)

---

## Local Development Setup

### Option A: Docker Compose (Recommended)

```bash
git clone https://github.com/DawnofGenX/sage.git
cd sage
docker compose up --build
```

- MCP Server: http://localhost:8000
- Web Simulator: http://localhost:3000

### Option B: Manual Setup

#### Backend (MCP Server)

```bash
cd mcp-server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .          # required — src/ is the import root
python -m uvicorn src.api.rest:app --port 8000
```

The server starts on `http://localhost:8000` with Streamable HTTP transport.
`pip install -e .` is not optional: without it the process dies with
`ModuleNotFoundError: No module named 'server'` at `src/api/rest.py:7`.

#### Frontend (Web Simulator)

```bash
cd web-simulator
npm install
npm run dev
```

The dev server starts on `http://localhost:3000` with Vite proxying `/api` to `:8000`.

---

## Docker Deployment

**Verified 2026-10-08:** `docker compose build` then `docker compose up -d` produces both
containers Up, `/api/health` → `{"status":"ok",...}`, `tools: 23`, MCP `initialize` → 200, and
the SSE agentic loop streaming 5 steps + `status:success` through nginx to the SPA.

The Python base image is **3.12** while the dev venv is 3.14. Annotations are therefore kept
portable: self-referential return types are quoted (see `src/client/chained.py`) so the code
imports under both interpreters.

### Build and Run

```bash
docker compose up --build -d
```

- Web simulator (what you open): http://localhost:3000 — nginx serves the SPA **and**
  reverse-proxies `/api` and the SSE `/api/stream/` endpoint to the backend service.
- MCP server: http://localhost:8000 (REST surface + Streamable HTTP mounted at `/mcp`)

### View Logs

```bash
docker compose logs -f mcp-server
docker compose logs -f web-simulator
```

### Stop

```bash
docker compose down
```

### Persistent Data

The SQLite database lives on the `sage-data` volume, mounted at `/app/data`.

The container seeds itself on first boot instead of at image build. Build-time
seeding cannot reach a volume that already exists — Docker only copies image
contents into a named volume the first time it is created, so an existing
volume's `/app/data` masks the image's copy and the built-in seed silently does
nothing. `entrypoint.sh` therefore calls `ensure_seeded()` before uvicorn,
against the database the container actually sees, and seeds only when that
database is empty — an existing volume with real data is never overwritten.

Because of this, upgrading an existing deployment no longer needs a manual
`docker compose down -v`: the next `up` seeds the database if it is empty and
leaves it alone otherwise.

**`SAGE_DB_PATH=/app/data/sage.db` is set in the Dockerfile and is
load-bearing.** `Database()` resolves it as its default path. Without it the
path falls back to the relative `"sage.db"`, which resolves against the
container WORKDIR (`/app`) — ephemeral filesystem, not the volume. Every write
was silently lost on recreate while `docker compose down -v` appeared to work,
because the volume only ever held a 0-byte `.gitkeep`.

To reset:

```bash
docker compose down -v      # removes the volume, so the next up re-seeds
docker compose up --build
```

---

## Production Deployment

### Backend: Railway

1. **Create a new project** on [Railway](https://railway.app)
2. **Add a new service** from the `mcp-server/` directory
3. **Set environment variables:**

   | Variable | Required | Default | Description |
   |----------|----------|---------|-------------|
   | `LLM_API_KEY` | No | — | Amazon Nova or OpenAI API key |
   | `LLM_API_URL` | No | `https://api.openai.com/v1/chat/completions` | LLM API endpoint |
   | `LLM_MODEL` | No | `gpt-4o-mini` | Model identifier |
   | `SAGE_DB_PATH` | No | `/app/data/sage.db` | SQLite database path |

4. **Deploy** — Railway auto-detects Python and runs `python -m src.server`
5. **Add a volume** mounted at `/app/data` for persistent SQLite storage
6. **Expose port 8000** via Railway's networking settings

### Backend: Render

1. **Create a new Web Service** on [Render](https://render.com)
2. **Set build command:** `pip install -r mcp-server/requirements.txt`
3. **Set start command:** `python -m mcp-server.src.server`
4. **Add environment variables** (same as Railway above)
5. **Add a disk** mounted at `/app/data` for persistent storage

### Frontend: Vercel

1. **Install Vercel CLI:** `npm i -g vercel`
2. **Deploy from `web-simulator/`:**

   ```bash
   cd web-simulator
   vercel --prod
   ```

3. **Set environment variable:**

   | Variable | Description |
   |----------|-------------|
   | `VITE_API_BASE_URL` | URL of your deployed MCP server (e.g., `https://sage-backend.up.railway.app`) |

4. **Update `vite.config.ts`** to use the production API URL instead of the proxy

### Frontend: Netlify

1. **Create a new site** on [Netlify](https://netlify.com)
2. **Set build command:** `npm run build`
3. **Set publish directory:** `dist`
4. **Add environment variable:**

   | Variable | Description |
   |----------|-------------|
   | `VITE_API_BASE_URL` | URL of your deployed MCP server |

5. **Add a `_redirects` file** in `public/` for SPA routing:

   ```
   /*    /index.html   200
   ```

---

## Environment Variables

### MCP Server

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_API_KEY` | No | — | API key for LLM provider. If not set, runs in mock mode. |
| `LLM_API_URL` | No | `https://api.openai.com/v1/chat/completions` | LLM API endpoint URL |
| `LLM_MODEL` | No | `gpt-4o-mini` | Model to use for extraction |
| `SAGE_DB_PATH` | No | `sage.db` | Path to SQLite database file |

### Web Simulator

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | — | Base URL for MCP server API. If unset, uses Vite proxy. |

---

## Troubleshooting

### MCP server won't start

```bash
# Check if port 8000 is in use
lsof -i :8000

# Check Docker logs
docker compose logs mcp-server

# Verify Python version
python --version  # Must be 3.12+
```

### Web simulator can't connect to MCP server

```bash
# Verify MCP server is running
curl http://localhost:8000/health

# Check Vite proxy config
cat web-simulator/vite.config.ts

# Check browser console for CORS errors
```

### LLM extraction returns errors

```bash
# Check if API key is set
echo $LLM_API_KEY

# Test LLM provider directly
cd mcp-server
python -c "from src.llm.provider import LLMProvider; p = LLMProvider(); print(p.is_mock)"

# If is_mock is True, the server is in mock mode (no API key)
# If is_mock is False, check API key validity and endpoint URL
```

### Database locked errors

```bash
# Check for stale lock files
ls -la mcp-server/sage.db*

# Remove WAL/SHM files if present
rm -f mcp-server/sage.db-wal mcp-server/sage.db-shm

# Restart the server
docker compose restart mcp-server
```

### Docker build fails

```bash
# Clean build cache
docker compose build --no-cache

# Check Docker version
docker --version  # Must be 24+
docker compose version  # Must be 2+
```

### Production deployment issues

```bash
# Railway: Check service logs
railway logs

# Render: Check service logs in dashboard

# Vercel: Check build logs in deployment details

# Netlify: Check build logs in deploy details
```

---

## Verification Checklist

After deployment, verify:

- [ ] `GET /health` returns `{"status": "ok", "server": "sage", "version": "1.0.0"}`
- [ ] Web simulator loads at the frontend URL
- [ ] Voice input or sample transcript loads correctly
- [ ] "Extract Insights" button runs the 2-pass extraction pipeline
- [ ] Proactive insights generate successfully
- [ ] Pipeline board displays deals
- [ ] CRM sync button shows success toast
- [ ] Database persists across restarts (check volume/disk)
