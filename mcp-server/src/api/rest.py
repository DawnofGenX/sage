"""REST API wrapper for Sage MCP server tools."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any

from server import mcp

from tools.registry import ALL_TOOLS

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

# Derived from ALL_TOOLS, NEVER hand-maintained.
#
# This used to be a literal dict of 22 imports, and it silently drifted: the
# registry gained tools the dict never heard about, so /api/tools/{name} 404'd
# for them while the MCP surface served them fine. run_agentic_loop,
# get_deal_timeline_events and get_deals were all unreachable over REST that way
# — which is exactly how the pipeline board ended up showing hardcoded sample
# deals: it could not ask for the real ones.
#
# Deriving the map from the single registry makes drift impossible. A tool added
# to ALL_TOOLS is callable over REST and MCP alike, or it fails a test.
TOOLS = {fn.__name__: fn for fn in ALL_TOOLS}


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
    rows = []
    for t in tools:
        # FastMCP's list_tools() yields FunctionTool objects, which expose
        # `parameters` and `output_schema` — there is no `input_schema` field.
        # Reading it with getattr(t, "input_schema", None) silently yields None
        # for every tool, so /api/tools published null schemas while the MCP
        # protocol surface (which converts to the wire Tool type) showed them.
        input_schema = getattr(t, "parameters", None)
        if input_schema is None:
            input_schema = getattr(t, "input_schema", None)
        rows.append(
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": input_schema,
                "output_schema": getattr(t, "output_schema", None),
            }
        )
    return {"count": len(tools), "tools": rows}


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
        # Serialize through the model's own dump, not FastAPI's model encoder.
        # FastAPI emits every declared field — including optional `error` as an
        # explicit null — whereas the model omits fields it was never given.
        # SyncResult declares `error` optional precisely so the success path
        # carries no error key at all (friction log entry 10: it was once
        # declared required and that broke every successful sync).
        if hasattr(result, "model_dump"):
            # exclude_unset, NOT exclude_none. `record_id` is explicitly None on
            # the not_configured path and must stay present (test_api asserts it
            # is None); `error` is simply never provided on success and so is
            # dropped. exclude_none would strip both and lose a field a caller
            # is entitled to see as null.
            return result.model_dump(exclude_unset=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/", mcp_app)
