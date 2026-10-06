# Sage — The Alexa+ Sales Intelligence Layer

Your CRM that listens.

## What is Sage?

Sage is a passive sales intelligence layer that sits on top of your existing CRM. It listens to your sales calls, extracts insights using Amazon Nova, proactively surfaces what you're forgetting, and syncs to your existing CRM via MCP.

## Features

- **Passive Listening** — No wake words, no commands. Just have the conversation.
- **Auto-Extraction** — Contacts, deals, follow-ups, sentiment, buying signals extracted automatically.
- **Proactive Insights** — "You haven't followed up with Acme in 20 days."
- **CRM Sync** — Bidirectional sync with Salesforce, HubSpot, Pipedrive via MCP.
- **Visual Pipeline** — Deal boards, stuck-deal alerts, sentiment trends on Echo Show.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/yourusername/sage.git
cd sage

# Start with Docker
docker compose up

# Or run locally
cd mcp-server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .          # required: installs src/ as a package
.venv/bin/python -m src.data.seed
.venv/bin/python -m uvicorn src.api.rest:app --port 8000
cd web-simulator && npm install && npm run dev
```

### Running the tests

```bash
cd mcp-server
.venv/bin/python -m pytest tests/ -q     # expect: 163 passed
```

The `pip install -e .` step is not optional. The suite imports `from tools.crud
import ...`, so `src/` must be installed as a package; with dependencies alone
you get 13 collection errors (`No module named 'tools'`) and zero tests run.

## MCP Tools

| Tool | Description |
|------|-------------|
| `extract_from_call` | Process call transcript → structured CRM data |
| `get_contact_context` | Full contact history, deals, interactions |
| `get_pipeline_health` | Deal stages, stuck deals, sentiment trends |
| `create_contact` | Add new contact |
| `update_contact` | Update existing contact |
| `create_deal` | Add new deal |
| `update_deal_stage` | Move deal to new stage |
| `schedule_followup` | Create follow-up reminder |
| `draft_followup_email` | Generate follow-up email draft |
| `log_call` | Log a call record |
| `get_deal_insights` | Sentiment, risks, buying signals |
| `get_daily_briefing` | Morning summary |
| `get_todays_followups` | Prioritized action items |
| `get_weekly_review` | Weekly performance summary |
| `search_contacts` | Fuzzy search |
| `sync_to_crm` | Sync to external CRM |

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
