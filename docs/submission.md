# Sage — Hackster.io Submission

## Project Name
Sage — The Alexa+ Sales Intelligence Layer

## Elevator Pitch
Sage listens to your sales calls, auto-extracts insights with Amazon Nova, and proactively tells you what you're forgetting — synced to your CRM via MCP.

## About the Project

### Inspiration

I've spent years watching salespeople — including myself — struggle with the same problem: CRM systems are graveyards of good intentions. We have calls, we have meetings, we have insights — but by the time we sit down to log everything, half of it is forgotten. The CRM becomes a chore, not a tool.

When Amazon launched Alexa+ with agentic capabilities, I saw an opportunity. Not another voice-command CRM (those exist — Pact, PipeCrush, SymbiozAI all ship them), but something fundamentally different: a system that listens passively and just knows what happened. No wake words. No commands. No data entry.

### What I Built

Sage is a passive sales intelligence layer built as an MCP server (spec 2025-11-25, Streamable HTTP) that:

- **Listens** to sales calls via Echo device (office) or phone app (field)
- **Extracts** contacts, deals, follow-ups, sentiment, buying signals, and competitor mentions using Amazon Nova via AWS Bedrock (two LLM passes: entities + intent concurrent, then record generation grounded in pass-1 findings)
- **Surfaces** proactive insights: "You haven't followed up with Acme in 20 days. Their Q4 budget deadline is Friday."
- **Syncs** to Salesforce, HubSpot, Pipedrive, or a local SQLite-backed CRM via MCP — never fabricates success when credentials are missing
- **Visualizes** pipeline health on Echo Show with deal boards, stuck-deal alerts, and sentiment trends

The MCP server exposes 22 tools with typed output schemas, including `extract_from_call`, `get_pipeline_health`, `get_contact_context`, `draft_followup_email`, and `sync_to_crm`. A web simulator demonstrates the full experience for judges who don't have Alexa+ hardware.

### How I Built It

- **MCP Server**: Python, Streamable HTTP transport, spec 2025-11-25
- **LLM**: Amazon Nova via AWS Bedrock for extraction and reasoning
- **Data**: DynamoDB for CRM records, S3 for call recordings
- **Proactive triggers**: EventBridge for scheduled insights
- **Alexa+ integration**: Voice ID for speaker identification, Echo Show for visual rendering, proactive suggestions
- **Web simulator**: React frontend with Web Speech API for voice input, Alexa+-style card rendering
- **Open source**: MIT license, public repo

### Challenges Faced

1. **MCP spec friction**: The 2025-11-25 spec is still evolving. Streamable HTTP session management required careful handling of reconnection logic and idempotency keys for write operations.

2. **Latency budget**: Voice interactions demand sub-second responses. I implemented per-tool timeouts, pre-warming of likely-needed data at session start, and filler speech ("Let me pull that up") during tool calls to stay invisible.

3. **Extraction accuracy**: Sales conversations are messy — interruptions, jargon, multiple languages. Fine-tuning the Nova prompt with few-shot examples and structured output schemas was critical.

4. **No Alexa+ hardware access**: The MCP toolkit is gated preview. I built a web simulator that demonstrates the full MCP server + Alexa+ experience without requiring physical hardware — positioning it as a "client-agnostic MCP server" feature, not a workaround.

5. **Scope discipline**: Matching Pact's 180 tools was impossible in 7 weeks. I focused on 16 high-impact tools that demonstrate the full agentic loop: listen → extract → reason → act → sync.

### What I Learned

- MCP is the right protocol for agentic tool use — but the spec is still maturing, and friction logs earn judging bonuses
- Passive listening is a fundamentally different UX paradigm than voice commands — it requires rethinking the entire interaction model
- AWS Bedrock + Nova is genuinely capable for structured extraction from noisy audio transcripts
- The best hackathon submissions are specific, surprising, and polished — not broad and generic
