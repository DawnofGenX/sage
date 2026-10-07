"""REST API wrapper for Sage MCP server tools."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from server import mcp

from tools.extraction import extract_from_call, get_contact_context, get_pipeline_health
from tools.crud import (
    create_contact,
    update_contact,
    create_deal,
    update_deal_stage,
    schedule_followup,
    draft_followup_email,
    log_call,
)
from tools.intelligence import (
    get_deal_insights,
    get_daily_briefing,
    get_todays_followups,
    get_weekly_review,
    search_contacts,
)
from tools.sync import sync_to_crm
from tools.expansion import (
    get_company_context,
    get_activities,
    get_deal_history,
    create_task,
    enrich_contact,
    get_forecast,
)

mcp_app = mcp.http_app()
app = FastAPI(
    title="Sage API",
    version="1.0.0",
    lifespan=mcp_app.lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOOLS = {
    "extract_from_call": extract_from_call,
    "get_contact_context": get_contact_context,
    "get_pipeline_health": get_pipeline_health,
    "create_contact": create_contact,
    "update_contact": update_contact,
    "create_deal": create_deal,
    "update_deal_stage": update_deal_stage,
    "schedule_followup": schedule_followup,
    "draft_followup_email": draft_followup_email,
    "log_call": log_call,
    "get_deal_insights": get_deal_insights,
    "get_daily_briefing": get_daily_briefing,
    "get_todays_followups": get_todays_followups,
    "get_weekly_review": get_weekly_review,
    "search_contacts": search_contacts,
    "sync_to_crm": sync_to_crm,
    "get_company_context": get_company_context,
    "get_activities": get_activities,
    "get_deal_history": get_deal_history,
    "create_task": create_task,
    "enrich_contact": enrich_contact,
    "get_forecast": get_forecast,
}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "server": "sage", "version": "1.0.0"}


@app.get("/api/tools")
async def list_tools():
    """List every registered MCP tool with its schema.

    Tool discovery is an MCP protocol operation (tools/list), not a Sage tool,
    so it needs its own route. The web simulator calls this to show the tool
    count before running the agentic chain; without it the client requested
    /api/tools/list_tools, which 404s and put the demo into a permanent error
    state. See docs/sse-contract-bugs.md.
    """
    tools = await mcp.list_tools()
    return {
        "count": len(tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": getattr(t, "input_schema", None),
                "output_schema": getattr(t, "output_schema", None),
            }
            for t in tools
        ],
    }


from api.stream import AgenticLoopRequest, create_agentic_loop_response


@app.post("/api/stream/agentic_loop")
async def stream_agentic_loop(request: AgenticLoopRequest):
    """Stream the chained agentic loop as Server-Sent Events.

    POST rather than GET because the transcript is a request body, and the
    frontend cannot use EventSource (which is GET-only). It parses the frames
    by hand instead; see web-simulator/src/lib/api.ts.
    """
    return create_agentic_loop_response(request.transcript, request.target)


@app.post("/api/tools/{tool_name}")
async def call_tool(tool_name: str, request: dict[str, Any]):
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    tool_fn = TOOLS[tool_name]
    try:
        result = await tool_fn(**request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", mcp_app)
