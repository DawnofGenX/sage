# Sage — Hackster.io "About the Project" Draft

## Title
Sage — The Alexa+ Sales Intelligence Layer

## Elevator Pitch
Sage listens to your sales calls, auto-extracts insights with a two-pass LLM pipeline, and proactively tells you what you're forgetting — synced to your CRM via MCP.

## About the Project

### The Problem
Salespeople spend over two hours a day on CRM data entry. Deals fall through the cracks. Follow-ups get forgotten. The CRM becomes a chore, not a tool.

### The Solution
Sage is a passive sales intelligence layer built as an MCP server. It listens to your sales calls, extracts structured CRM data using a two-pass LLM pipeline, and proactively surfaces insights — all without requiring manual data entry.

### Key Features
- **Passive listening** — no wake words, no commands. Just have the conversation.
- **Two-pass LLM extraction** — entities + intent classified concurrently, then record generation grounded in pass-1 findings. LLM provider is pluggable (Amazon Nova via AWS Bedrock, or deterministic fallback).
- **Proactive insights** — "You haven't followed up with Acme in 20 days. Their Q4 budget deadline is Friday."
- **Multi-CRM sync** — Salesforce, HubSpot, Pipedrive, or local SQLite-backed CRM. Never fabricates success when credentials are missing.
- **23 MCP tools** with typed output schemas, including `extract_from_call`, `get_pipeline_health`, `draft_followup_email`, and `sync_to_crm`.
- **Agentic chaining** — a real MCP client that performs a 5-step chained tool sequence, inspectable in the UI and readable in the source.
- **Web simulator** — React frontend with Web Speech API for voice input, Alexa+-style card rendering, and a DemoFlow panel that streams each step of the agentic chain.

### How It Works
1. **Call** — Echo device or phone app captures the conversation.
2. **Extract** — `extract_from_call` runs a two-pass LLM pipeline: entities + intent concurrently, then record generation grounded in pass-1 findings.
3. **Reason** — proactive insight engine correlates CRM data, follow-up dates, and deal stages.
4. **Act** — insights are spoken back via Alexa+ or shown on Echo Show.
5. **Sync** — records sync to your CRM via MCP. No credentials? The sync returns `not_configured` with a reason — never a fabricated success.

### Tech Stack
- **MCP Server**: Python, FastMCP, Streamable HTTP transport
- **LLM**: Amazon Nova via AWS Bedrock (with deterministic fallback)
- **Data**: SQLite (DynamoDB-ready schema)
- **Frontend**: React, Vite, Tailwind CSS, Web Speech API
- **AWS**: DynamoDB, S3, EventBridge, Bedrock (adapters ready)

### What Makes It Different
- **Honest by design** — every tool response carries provenance. No fabricated success, no mock data in the demo path.
- **Real agentic chaining** — a genuine MCP client performing a real chained sequence, not a UI animation.
- **Measured accuracy** — extraction precision and recall reported in `docs/extraction-eval.md`, not asserted.
- **Client-agnostic** — the MCP server works with any MCP-compliant client, not just the web simulator.

### Challenges
1. **MCP spec friction** — the 2025-11-25 spec is still evolving. Streamable HTTP session management required careful handling.
2. **Latency budget** — voice interactions demand sub-second responses. Per-tool timeouts and pre-warming of likely-needed data.
3. **No Alexa+ hardware** — the MCP toolkit is gated preview. Built a web simulator that demonstrates the full experience without physical hardware.

### Links
- **GitHub**: [github.com/DawnofGenX/sage](https://github.com/DawnofGenX/sage)
- **Live Demo**: [sage-mcp-server.onrender.com](https://sage-mcp-server.onrender.com)
- **Video**: [YouTube demo](https://youtube.com)
