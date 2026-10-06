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
    return str(result)

@mcp.resource("sage://contacts/{contact_id}")
async def contact_resource(contact_id: str) -> str:
    from data.db import Database
    db = Database()
    contact = db.get_contact(int(contact_id))
    return str(contact) if contact else "Contact not found"

@mcp.prompt()
def analyze_call(transcript: str) -> str:
    return f"Analyze this sales call and extract all CRM-relevant data: {transcript}"

@mcp.prompt()
def generate_followup(contact: str, context: str) -> str:
    return f"Write a follow-up email to {contact} about {context}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
