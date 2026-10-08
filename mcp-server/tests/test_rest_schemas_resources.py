"""Regression tests for the REST tool-discovery surface and MCP resources.

Both defects here were invisible to the suite until they were raised by hand:

1. `GET /api/tools` returned `input_schema: null` for all 23 tools. FastMCP's
   `list_tools()` yields `FunctionTool` objects carrying `parameters` and
   `output_schema` — there is no `input_schema` field, so the old
   `getattr(t, "input_schema", None)` defaulted every value to None. The MCP
   protocol surface converts to the wire `Tool` type (which does have
   `input_schema`), which is why the protocol client reported schemas present
   while the REST layer reported them absent.
2. Both MCP resources returned `str(dict)` — a Python repr (single quotes,
   `None`) that no JSON parser accepts. The tools returned proper JSON; the
   resources did not.
"""
import json

import pytest
from fastapi.testclient import TestClient

from api.rest import app


@pytest.fixture
def client():
    return TestClient(app)


GET_TOOLS = "/api/tools"


def test_api_tools_reports_input_schema_for_every_tool(client):
    """A discovery surface that publishes null schemas is worse than none."""
    response = client.get(GET_TOOLS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == len(payload["tools"]), "count must match the list"

    missing_in = [t["name"] for t in payload["tools"] if not t.get("input_schema")]
    assert not missing_in, f"input_schema null for {len(missing_in)} tools: {missing_in[:5]}"

    missing_out = [t["name"] for t in payload["tools"] if not t.get("output_schema")]
    assert not missing_out, f"output_schema null for {len(missing_out)} tools: {missing_out[:5]}"


def test_api_tools_input_schema_is_valid_json_schema(client):
    """Not merely present — shaped like a JSON Schema object."""
    payload = client.get(GET_TOOLS).json()
    tool = next(t for t in payload["tools"] if t["name"] == "extract_from_call")

    schema = tool["input_schema"]
    assert isinstance(schema, dict), schema
    assert schema.get("type") == "object", schema
    assert "transcript" in schema.get("properties", {}), schema


def test_api_tools_never_returns_camelcase_shadowing(client):
    """Guards the failure mode directly: the value must not be re-derived as None.

    `parameters` is the field FastMCP actually uses; if a future version moves
    it, this test fails loudly rather than silently publishing nulls again.
    """
    payload = client.get(GET_TOOLS).json()
    for t in payload["tools"]:
        assert t["input_schema"] is not None, t["name"]


# --- MCP resources: must return JSON, not a Python repr -------------------

@pytest.mark.asyncio
async def test_pipeline_status_resource_is_json():
    from server import mcp

    body = await _read_resource(mcp, "sage://pipeline/status")

    parsed = json.loads(body)  # str(dict) would raise here
    assert isinstance(parsed, dict)
    assert "deals_by_stage" in parsed
    assert "total_deals" in parsed


@pytest.mark.asyncio
async def test_pipeline_status_resource_has_no_python_repr_markers():
    """Single quotes and bare `None` are the tells of str(dict)."""
    from server import mcp

    body = await _read_resource(mcp, "sage://pipeline/status")
    assert "'" not in body, f"looks like a Python repr, not JSON: {body[:120]}"


@pytest.mark.asyncio
async def test_contacts_resource_returns_json_for_real_id():
    from server import mcp

    body = await _read_resource(mcp, "sage://contacts/1")
    parsed = json.loads(body)
    assert parsed.get("id") == 1, parsed


@pytest.mark.asyncio
async def test_contacts_resource_is_json_for_missing_id():
    """The not-found path must also be JSON — it used to be bare text."""
    from server import mcp

    body = await _read_resource(mcp, "sage://contacts/999999")
    parsed = json.loads(body)
    assert parsed.get("error"), parsed


@pytest.mark.asyncio
async def test_contacts_resource_is_json_for_non_integer_id():
    """A malformed id must not surface as a ValueError over the protocol."""
    from server import mcp

    body = await _read_resource(mcp, "sage://contacts/not-an-int")
    parsed = json.loads(body)
    assert "error" in parsed, parsed


async def _read_resource(mcp, uri: str) -> str:
    """Read a resource through FastMCP, returning its text body.

    Uses `read_resource` where available rather than reaching into private
    handler state, so the assertion is about what a client actually gets.
    """
    reader = getattr(mcp, "read_resource", None)
    if reader is None:
        pytest.skip("FastMCP version exposes no read_resource()")

    result = await reader(uri) if _takes_one_arg(reader) else await reader(uri, None)
    if isinstance(result, str):
        return result

    contents = getattr(result, "contents", None)
    if contents:
        first = contents[0]
        # FastMCP's ResourceContent stores the payload on `.content`; the wire
        # `TextResourceContents` type calls it `.text`. Try both.
        return (
            getattr(first, "content", None)
            or getattr(first, "text", None)
            or str(first)
        )
    return str(result)


def _takes_one_arg(fn) -> bool:
    try:
        import inspect

        params = [
            p
            for p in inspect.signature(fn).parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        return len(params) == 1
    except (TypeError, ValueError):  # pragma: no cover
        return True
