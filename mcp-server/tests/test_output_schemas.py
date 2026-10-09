"""Every MCP tool must publish a TYPED output schema.

This exists because a weaker check gave a false pass. Testing only
`output_schema is not None` reported 22/22 "OK" while six expansion tools
published `{"type": "object", "additionalProperties": true}` — the same
schema an unannotated `-> dict` produces. That bare object carries no
information about the response shape, which is the whole point of declaring
a schema.

A schema counts as typed only if it declares `properties`.
"""

import pytest


@pytest.mark.asyncio
async def test_all_tools_are_registered():
    from server import mcp
    from tools.registry import ALL_TOOLS

    tools = await mcp.list_tools()
    assert len(tools) == len(ALL_TOOLS) == 24


@pytest.mark.asyncio
async def test_every_tool_publishes_a_typed_output_schema():
    """The real check: a schema must declare properties, not merely exist."""
    from server import mcp

    tools = {t.name: t for t in await mcp.list_tools()}
    untyped = [
        name for name, tool in tools.items()
        if not (tool.output_schema or {}).get("properties")
    ]
    assert not untyped, (
        f"{len(untyped)} tool(s) publish an untyped schema, which tells a "
        f"client nothing about the response: {untyped}"
    )


@pytest.mark.asyncio
async def test_no_tool_falls_back_to_a_bare_object_schema():
    """Guard the specific regression: extra='allow' with no fields.

    A Pydantic model with only `model_config = ConfigDict(extra="allow")`
    and no declared fields generates no `properties`, so it is
    indistinguishable from an unannotated tool.
    """
    from server import mcp

    for tool in await mcp.list_tools():
        schema = tool.output_schema or {}
        assert schema.get("type") == "object", f"{tool.name}: unexpected type"
        assert schema.get("properties"), f"{tool.name}: no properties declared"


@pytest.mark.asyncio
async def test_expansion_tools_declare_their_own_fields():
    """The six tools that were previously untyped must be specific.

    GenericRecord (an empty model) produced a bare object schema; each now
    has a dedicated model naming the fields it returns.
    """
    from server import mcp

    expected = {
        "get_company_context": {"company", "contacts", "deals"},
        "get_activities": {"activities", "total"},
        "get_deal_history": {"deal", "stage_history"},
        "enrich_contact": {"contact", "data", "enriched"},
        "get_forecast": {"forecast", "total_pipeline", "weighted_forecast"},
    }
    tools = {t.name: t for t in await mcp.list_tools()}
    for name, required in expected.items():
        props = set((tools[name].output_schema or {}).get("properties", {}))
        missing = required - props
        assert not missing, f"{name} missing expected properties: {missing}"


@pytest.mark.asyncio
async def test_mutating_tools_expose_provenance_in_their_schema():
    """Provenance is the honesty contract; it must be visible to clients.

    A client reading structuredContent should be able to tell a real record
    from a fallback without inspecting prose.
    """
    from server import mcp

    tools = {t.name: t for t in await mcp.list_tools()}
    for name in ("sync_to_crm", "extract_from_call"):
        props = (tools[name].output_schema or {}).get("properties", {})
        assert "provenance" in props, f"{name} schema does not expose provenance"


@pytest.mark.asyncio
async def test_structured_content_populates_on_a_real_call():
    """A declared schema that is never emitted is indistinguishable from none."""
    from server import mcp

    result = await mcp.call_tool("get_pipeline_health", {})
    assert result.structured_content is not None
    assert isinstance(result.structured_content, dict)
    assert result.structured_content, "structuredContent was empty"