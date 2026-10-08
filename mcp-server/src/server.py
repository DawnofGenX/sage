import json

from fastmcp import FastMCP
from tools.registry import ALL_TOOLS

mcp = FastMCP(
    "sage",
    version="1.0.0",
    instructions="Sage — passive sales intelligence layer for Alexa+",
)

for tool in ALL_TOOLS:
    mcp.tool()(tool)

@mcp.resource("sage://pipeline/status")
async def pipeline_status() -> str:
    from tools.extraction import get_pipeline_health
    result = await get_pipeline_health()
    # json.dumps, NOT str(result): a resource body is read by clients as data,
    # and str(dict) emits a Python repr (single quotes, None) that no JSON
    # parser accepts.
    #
    # Tolerant of the return type: get_pipeline_health is annotated
    # `-> PipelineHealth` (a Pydantic model) but returns a plain dict at
    # runtime, so a bare .model_dump() would raise and the resource would 500.
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    return json.dumps(result, default=str)

@mcp.resource("sage://contacts/{contact_id}")
async def contact_resource(contact_id: str) -> str:
    from data.db import Database
    db = Database()
    try:
        cid = int(contact_id)
    except ValueError:
        # FastMCP surfaces a ValueError as a protocol error, which loses the
        # "your URI was malformed" signal; a JSON body keeps it machine-readable.
        return json.dumps({"error": f"contact_id must be an integer, got {contact_id!r}"})
    contact = db.get_contact(cid)
    return json.dumps(contact, default=str) if contact else json.dumps({"error": "Contact not found"})

@mcp.prompt()
def analyze_call(transcript: str) -> str:
    return f"Analyze this sales call and extract all CRM-relevant data: {transcript}"

@mcp.prompt()
def generate_followup(contact: str, context: str) -> str:
    return f"Write a follow-up email to {contact} about {context}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
