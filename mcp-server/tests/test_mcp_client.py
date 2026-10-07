"""Tests for Sage MCP client against a real server."""
import os
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import pytest
import pytest_asyncio

# Set up temp DB before importing anything
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SAGE_DB_PATH"] = _tmp_db.name

from src.client.chained import SageMCPClient


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server_url():
    """Start a real uvicorn server on an ephemeral port."""
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(__file__), "..", "src")
    env["SAGE_DB_PATH"] = _tmp_db.name

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "api.rest:app",
            "--host", "127.0.0.1",
            "--port", str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    url = f"http://127.0.0.1:{port}/mcp"
    for _ in range(50):
        try:
            resp = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=1)
            if resp.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("Server failed to start")

    yield url

    proc.terminate()
    proc.wait(timeout=5)


@pytest.mark.asyncio
async def test_list_tools_returns_22_tools(server_url):
    """list_tools returns all 22 tools from the real server."""
    async with SageMCPClient(server_url) as client:
        tools = await client.list_tools()
    assert len(tools) == 22
    names = {t["name"] for t in tools}
    assert "get_pipeline_health" in names
    assert "create_contact" in names
    assert "extract_from_call" in names


@pytest.mark.asyncio
async def test_call_returns_structured_content(server_url):
    """call returns populated structured content from a real tool."""
    async with SageMCPClient(server_url) as client:
        result = await client.call("get_pipeline_health", {})
    assert "deals_by_stage" in result
    assert "total_deals" in result
    assert "total_value" in result


@pytest.mark.asyncio
async def test_call_recorded_captures_duration_and_provenance(server_url):
    """call_recorded returns timing and provenance metadata."""
    async with SageMCPClient(server_url) as client:
        recorded = await client.call_recorded("get_pipeline_health", {})
    assert recorded["name"] == "get_pipeline_health"
    assert recorded["arguments"] == {}
    assert recorded["duration_ms"] > 0
    assert "result" in recorded
    assert "provenance" in recorded
    assert "deals_by_stage" in recorded["result"]


def test_input_required_result_narrowing():
    """InputRequiredResult-shaped response is narrowed safely (no AttributeError)."""
    from mcp.types import InputRequiredResult

    result = InputRequiredResult(
        result_type="input_required",
        input_requests=None,
        request_state="state",
    )

    # This must NOT raise AttributeError
    extracted = SageMCPClient._extract_structured(result)
    assert extracted["result_type"] == "input_required"
    assert extracted["request_state"] == "state"


def test_call_tool_result_narrowing():
    """CallToolResult with structured_content is extracted correctly."""
    from mcp.types import CallToolResult

    result = CallToolResult(
        content=[],
        result_type="complete",
        structured_content={"key": "value"},
    )

    extracted = SageMCPClient._extract_structured(result)
    assert extracted == {"key": "value"}


def test_call_tool_result_error_narrowing():
    """CallToolResult with is_error=True returns error info."""
    from mcp.types import CallToolResult, TextContent

    result = CallToolResult(
        content=[TextContent(type="text", text="something went wrong")],
        result_type="complete",
        is_error=True,
    )

    extracted = SageMCPClient._extract_structured(result)
    assert extracted["result_type"] == "error"
    assert extracted["is_error"] is True
    assert "something went wrong" in extracted["content"]


def teardown_module():
    """Clean up temporary database."""
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass
