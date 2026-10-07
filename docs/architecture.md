# Sage Architecture

## System Overview

Sage is a passive sales intelligence layer that listens to sales conversations, extracts structured CRM data using LLMs, and proactively surfaces insights — all without requiring manual data entry.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Sage System Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Alexa/Echo  │    │  Web         │    │  External CRM        │  │
│  │  Device      │    │  Simulator   │    │  (Salesforce, etc.)  │  │
│  │  (Voice UI)  │    │  (React UI)  │    │                      │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │              │
│         │  Voice Input      │  REST/WebSocket       │  Sync API    │
│         ▼                   ▼                       ▼              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server (FastMCP)                       │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │  │
│  │  │  LLM       │  │  Extraction│  │  Proactive             │  │  │
│  │  │  Provider  │  │  Pipeline  │  │  Engine                │  │  │
│  │  │  (Nova/    │  │  (2-pass)  │  │  (Rules + LLM)         │  │  │
│  │  │   Mock)    │  │            │  │                        │  │  │
│  │  └─────┬──────┘  └─────┬──────┘  └───────────┬────────────┘  │  │
│  │        │               │                      │               │  │
│  │        └───────────────┼──────────────────────┘               │  │
│  │                        ▼                                      │  │
│  │              ┌─────────────────┐                              │  │
│  │              │  SQLite DB      │                              │  │
│  │              │  (sage.db)      │                              │  │
│  │              └─────────────────┘                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### 1. MCP Server (`mcp-server/`)

The core backend, built with FastMCP. Exposes tools over Streamable HTTP for LLM-powered sales intelligence.

| Module | Path | Purpose |
|--------|------|---------|
| Server | `src/server.py` | FastMCP server entry point, tool registration |
| LLM Provider | `src/llm/provider.py` | Pluggable LLM API client (OpenAI / Anthropic, auto-detected) with mock fallback |
| LLM Formats | `src/llm/formats.py` | Wire-format handlers: OpenAI chat/completions + Anthropic messages |
| Extraction Pipeline | `src/extraction/pipeline.py` | 2-pass transcript processing: entities + intent (concurrent) → record → local validation |
| Proactive Engine | `src/proactive/engine.py` | Rule-based + LLM insight generation from CRM data |
| Database | `src/data/db.py` | SQLite CRUD operations for contacts, deals, followups, call logs |
| Tools | `src/tools/` | MCP tool definitions (CRUD, extraction, intelligence, sync) |

### 2. Web Simulator (`web-simulator/`)

React + TypeScript + Vite + Tailwind CSS frontend that simulates the Alexa+ experience.

| Component | Purpose |
|-----------|---------|
| `VoiceInput` | Web Speech API integration with fallback text input |
| `TranscriptView` | Live transcript display with sample call loading |
| `ExtractionPipeline` | Visual 4-stage pipeline progress (2 LLM passes + local validation) with animated transitions |
| `ProactiveInsights` | Urgency-coded insight cards (overdue/stuck/info) |
| `PipelineBoard` | Kanban-style deal pipeline with sync button |
| `ReasoningTrace` | Detailed 7-step LLM reasoning trace visualization |
| `ContactCard` / `DealCard` | CRM record display components |

### 3. Data Layer

SQLite database with 5 tables:

- **contacts** — Sales contacts with company, email, phone, title
- **deals** — Sales deals with value, stage, sentiment, notes
- **followups** — Scheduled follow-up tasks with due dates
- **call_logs** — Recorded call transcripts with extracted metadata
- **activities** — Contact activity timeline

## Data Flow

```
┌─────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────┐
│  Call   │────▶│  Transcript  │────▶│  Extraction     │────▶│  SQLite  │
│  Audio  │     │  (Text)      │     │  Pipeline       │     │  DB      │
└─────────┘     └──────────────┘     └─────────────────┘     └──────────┘
                                              │                    │
                                              ▼                    ▼
                                       ┌──────────────┐     ┌──────────────┐
                                       │  Structured  │     │  Proactive   │
                                       │  CRM Record  │     │  Engine      │
                                       └──────────────┘     └──────────────┘
                                              │                    │
                                              ▼                    ▼
                                       ┌──────────────┐     ┌──────────────┐
                                       │  CRM Sync    │     │  Insights    │
                                       │  (Salesforce)│     │  (Echo Show) │
                                       └──────────────┘     └──────────────┘
```

### Extraction Pipeline (2 Passes, 4 Stages)

**Pass 1** (concurrent):
1. **Entity Extraction** — Identify people, companies, amounts, dates
2. **Intent Classification** — Classify as `new_lead`, `follow_up`, `deal_update`, or `general`

**Pass 2** (grounded in pass-1 findings):
3. **Record Generation** — Produce contacts, deals, followups, sentiment, buying signals, risks

**Local** (no LLM):
4. **Schema Validation** — Validate required fields, normalize types, ensure data integrity

### Proactive Insight Generation

1. **Rule-based triggers** — Overdue follow-ups, stuck deals (14+ days inactive), budget deadlines
2. **LLM-based insights** — Pipeline context analysis for pattern detection
3. **Urgency scoring** — Overdue (3) > Stuck (2) = Budget (2) > General (1)

## MCP Tool Catalog

### CRUD Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_contact` | Create a new contact | `name`, `company?`, `email?`, `phone?`, `title?`, `notes?` |
| `update_contact` | Update an existing contact | `contact_id`, `**kwargs` |
| `create_deal` | Create a new deal | `contact_id`, `title`, `value?`, `stage?`, `notes?` |
| `update_deal_stage` | Update deal stage | `deal_id`, `stage` |
| `schedule_followup` | Schedule a follow-up task | `contact_id`, `title`, `due_date`, `deal_id?`, `notes?` |
| `draft_followup_email` | Draft follow-up email using LLM output (template fallback only on mock provenance) | `contact`, `context`, `tone?` |
| `log_call` | Log a call record | `contact_id`, `transcript`, `summary?`, `duration_seconds?`, `deal_id?` |

### Extraction Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `extract_from_call` | Run full 2-pass extraction pipeline | `transcript` |
| `get_contact_context` | Get contact with deals and history | `name`, `include_history?`, `include_deals?` |
| `get_pipeline_health` | Get pipeline metrics | `timeframe?`, `include_sentiment?` |

### Intelligence Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_deal_insights` | AI-powered deal analysis | `deal_id` |
| `get_daily_briefing` | Daily metrics and action items | — |
| `get_todays_followups` | Prioritized follow-ups for today | — |
| `get_weekly_review` | Weekly sales activity review | — |
| `search_contacts` | Search contacts by name/company/email | `query` |

### Sync Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `sync_to_crm` | Sync record to CRM (returns `not_configured` when credentials missing, `already_synced` on repeated key) | `record`, `target`, `idempotency_key` |

### System Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `health_check` | Server health check | — |

## API Endpoint Reference

The MCP server exposes tools via Streamable HTTP at `http://localhost:8000`.

### Web Simulator API Proxy

The web simulator proxies MCP tool calls through `/api/tools/{toolName}`:

```
POST /api/tools/{toolName}
Content-Type: application/json

{
  "arg1": "value1",
  "arg2": "value2"
}
```

### Supported Targets for CRM Sync

- `salesforce`
- `hubspot`
- `pipedrive`
- `local` — SQLite-backed CRM with Salesforce-shaped field names (for demo without external credentials)

## Deployment Architecture

### Local Development

```
┌─────────────┐     ┌─────────────┐
│  MCP Server │◀───▶│  Web Sim    │
│  :8000      │     │  :3000      │
└─────────────┘     └─────────────┘
```

### Docker Compose

```
┌─────────────────────────────────────┐
│           Docker Network            │
│  ┌──────────┐    ┌──────────────┐  │
│  │  MCP     │◀──▶│  Web Sim     │  │
│  │  :8000   │    │  :3000→:80   │  │
│  └──────────┘    └──────────────┘  │
│       │                             │
│  ┌────▼────┐                        │
│  │  Volume │                        │
│  │  sage-  │                        │
│  │  data   │                        │
│  └─────────┘                        │
└─────────────────────────────────────┘
```

### Production

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Vercel/    │     │  Railway/   │     │  External   │
│  Netlify    │◀───▶│  Render     │◀───▶│  CRM        │
│  (Frontend) │     │  (Backend)  │     │  (Salesforce)│
└─────────────┘     └─────────────┘     └─────────────┘
```

## AWS Integration

Sage supports AWS-native infrastructure for production deployments. Each AWS adapter falls back to a local alternative when AWS credentials are not configured, enabling seamless local development.

### AWS Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Sage AWS Architecture                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐      │
│  │  Alexa/Echo  │    │  Web         │    │  External CRM        │      │
│  │  Device      │    │  Simulator   │    │  (Salesforce, etc.)  │      │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘      │
│         │                   │                       │                  │
│         ▼                   ▼                       ▼                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    MCP Server (FastMCP)                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐     │  │
│  │  │  Bedrock   │  │  Extraction│  │  Proactive             │     │  │
│  │  │  Provider  │  │  Pipeline  │  │  Engine                │     │  │
│  │  │  (Nova/    │  │  (2-pass)  │  │  (Rules + LLM)         │     │  │
│  │  │   Claude)  │  │            │  │                        │     │  │
│  │  └─────┬──────┘  └─────┬──────┘  └───────────┬────────────┘     │  │
│  │        │               │                      │                   │  │
│  │        └───────────────┼──────────────────────┘                   │  │
│  │                        ▼                                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐     │  │
│  │  │  DynamoDB  │  │  S3        │  │  EventBridge           │     │  │
│  │  │  (CRM Data)│  │  (Recordings)│  │  (Scheduled Triggers) │     │  │
│  │  └────────────┘  └────────────┘  └────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Bedrock (LLM Provider)

Replaces the default LLM provider with Amazon Bedrock, supporting Nova and Claude model families.

| Model Family | Model ID | Use Case |
|-------------|----------|----------|
| Nova Lite | `amazon.nova-lite-v1:0` | Fast, cost-effective extraction |
| Nova Pro | `amazon.nova-pro-v1:0` | Higher quality analysis |
| Nova Micro | `amazon.nova-micro-v1:0` | Ultra-low-latency classification |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | Balanced performance |
| Claude 3 Sonnet | `anthropic.claude-3-sonnet-20240229-v1:0` | Complex reasoning |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | Maximum intelligence |

**Fallback:** When `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are not set, uses keyword-based mock extraction.

### LLM API Integration (OpenAI / Anthropic)

The LLM provider (`src/llm/provider.py`) calls real LLM APIs when `LLM_API_KEY` is set, and falls back to regex/keyword mock extraction when it is not (demo mode, no network calls).

**Configuration** (see `.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_API_KEY` | API key. If unset, provider runs in mock mode. | — |
| `LLM_API_URL` | Endpoint URL. Format is auto-detected from the URL. | `https://api.openai.com/v1/chat/completions` |
| `LLM_MODEL` | Model name sent to the API. | `gpt-4o-mini` |

**Supported formats** (`src/llm/formats.py`):

| Format | Detection | Endpoint | Auth header |
|--------|-----------|----------|-------------|
| OpenAI-compatible | URL does not contain `anthropic` | `POST {LLM_API_URL}` with `{model, messages, temperature}` | `Authorization: Bearer <key>` |
| Anthropic | URL contains `anthropic` | `POST {LLM_API_URL}` with `{model, max_tokens, messages, temperature}` | `x-api-key: <key>` + `anthropic-version` |

The OpenAI-compatible format also works with OpenRouter, Together, local Ollama, and any other chat/completions-compatible endpoint.

**Reliability:**

- **Retries** — up to 3 attempts with exponential backoff (1s, 2s, 4s) on network errors, HTTP 429/5xx, and invalid JSON responses.
- **Timeout** — 30 seconds per request; timeouts are retried like other transient failures.
- **Response validation** — the response payload is validated against the detected format (e.g. `choices[0].message.content` for OpenAI, `content[0].text` for Anthropic), then parsed as a JSON object. Markdown code fences (```` ```json ````) are stripped before parsing. Non-object or unparseable responses raise `LLMAPIError` after retries are exhausted.

**Example:**

```bash
# OpenAI
LLM_API_KEY=sk-... LLM_API_URL=https://api.openai.com/v1/chat/completions LLM_MODEL=gpt-4o-mini

# Anthropic
LLM_API_KEY=sk-ant-... LLM_API_URL=https://api.anthropic.com/v1/messages LLM_MODEL=claude-sonnet-4-20250514
```

### DynamoDB (CRM Data Store)

Replaces SQLite with DynamoDB for serverless, scalable CRM data storage.

| Table | Primary Key | Attributes |
|-------|-------------|------------|
| `sage-contacts` | `contact_id` (String) | name, company, email, phone, title, notes |
| `sage-deals` | `deal_id` (String), `contact_id` (SK) | title, value, stage, notes, sentiment |
| `sage-followups` | `followup_id` (String), `contact_id` (SK) | title, due_date, completed, notes |
| `sage-call-logs` | `log_id` (String) | contact_id, transcript, summary, sentiment, buying_signals, risks |

**Fallback:** When AWS credentials are not set, uses SQLite in a temporary directory.

### S3 (Call Recording Storage)

Replaces local file storage with S3 for durable, scalable call recording archival.

```
sage-recordings/
├── recordings/
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── call_<id>.mp3
│   │   │   └── call_<id>.json (metadata)
│   │   └── 02/
│   └── ...
└── transcripts/
    ├── call_<id>.txt
    └── call_<id>.json (extracted data)
```

**Fallback:** When AWS credentials are not set, uses local filesystem in a temporary directory.

### EventBridge (Proactive Triggers)

Replaces in-process scheduling with EventBridge for serverless, cron-based insight generation.

| Rule Name | Schedule | Purpose |
|-----------|----------|---------|
| `sage-daily-insights` | `cron(0 9 * * ? *)` | Daily sales insight generation |
| `sage-overdue-followups` | `cron(0 */4 * * ? *)` | Check for overdue follow-ups every 4 hours |
| `sage-stale-deal-alert` | `cron(0 12 ? * MON *)` | Weekly stale deal identification |
| `sage-call-summary` | Event-driven | Generate summaries after call processing |

**Fallback:** When AWS credentials are not set, uses in-process rule tracking.

### AWS Credentials Configuration

All AWS adapters use the same credential detection:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_REGION=us-east-1
```

Optional overrides:
```bash
export BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
export DYNAMODB_TABLE_PREFIX=sage-prod
export S3_BUCKET_NAME=sage-recordings-prod
export EVENTBRIDGE_BUS=sage-events
```
