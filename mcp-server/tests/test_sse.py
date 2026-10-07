"""Tests for the SSE agentic-loop endpoint.

The contract that matters is not "it returns 200" but "the frontend's hand-
written parser reads it correctly". So these tests parse real endpoint output
through `sse_reference_parser`, a mirror of `web-simulator/src/lib/api.ts`
runAgenticLoop, at several simulated chunk sizes. A response that is valid
SSE but unreadable by the actual client is still broken.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import tempfile
import threading
from typing import Iterator

import pytest
import uvicorn
from fastapi.testclient import TestClient

from sse_reference_parser import parse_sse_like_frontend

FULL_TRANSCRIPT = (
    "Hi, I'm calling about the project. John Smith from Acme Corp is interested "
    "in our solution. The budget is around $50,000. Let's follow up on 12/15/2026."
)

NO_CONTACTS_TRANSCRIPT = (
    "Hello, I'm calling about the project. The budget is around $50,000."
)

CHUNK_SIZES = [4096, 512, 97, 31, 7]


@pytest.fixture(scope="module")
def server_url(tmp_path_factory, monkeypatch_module) -> Iterator[str]:
    """Run a real uvicorn server on an ephemeral port for the chain to call."""
    db = tmp_path_factory.mktemp("sse") / "sse.db"
    from src.api.rest import app

    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    waited = 0.0
    while not server.started and waited < 30:
        asyncio.run(asyncio.sleep(0.05))
        waited += 0.05
    if not server.started:
        pytest.fail("SSE test server failed to start")

    port = server.servers[0].sockets[0].getsockname()[1]
    # Set, never popped. Several test modules set SAGE_DB_PATH at import time
    # for their own isolation; popping it here handed the next module the
    # developer's real sage.db, and the chain wrote deals into it. A test that
    # removes another module's isolation is the bug, not the module after it.
    monkeypatch_module.setenv("SAGE_DB_PATH", str(db))
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped env restoration, so teardown cannot leak into other modules."""
    original = os.environ.get("SAGE_DB_PATH")
    yield _ModuleEnv()
    if original is None:
        os.environ.pop("SAGE_DB_PATH", None)
    else:
        os.environ["SAGE_DB_PATH"] = original


class _ModuleEnv:
    """Minimal setenv that participates in module-scoped teardown above."""

    def __init__(self) -> None:
        self._saved: dict[str, str | None] = {}

    def setenv(self, key: str, value: str) -> None:
        self._saved.setdefault(key, os.environ.get(key))
        os.environ[key] = value


@pytest.fixture
def client(server_url, monkeypatch):
    """TestClient pointed at the live server, with the chain able to reach it."""
    monkeypatch.setenv("SAGE_MCP_SERVER_URL", f"{server_url}/mcp")
    from src.api.rest import app

    with TestClient(app) as c:
        yield c


def _post(client, transcript, target="local"):
    return client.post(
        "/api/stream/agentic_loop",
        json={"transcript": transcript, "target": target},
    )


# ==================================================================
# Response shape
# ==================================================================


def test_endpoint_is_declared_as_event_stream(client):
    r = _post(client, FULL_TRANSCRIPT)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    # Proxy buffering would defeat streaming entirely.
    assert r.headers.get("x-accel-buffering") == "no"
    assert "no-cache" in r.headers.get("cache-control", "")


def test_request_body_is_validated(client):
    r = client.post("/api/stream/agentic_loop", json={})
    assert r.status_code == 422, "a missing transcript must be rejected"


# ==================================================================
# The contract the frontend actually reads
# ==================================================================


def test_frontend_parser_reads_every_frame(client):
    """The whole point: real output, parsed by the real parser's logic."""
    body = _post(client, FULL_TRANSCRIPT).text
    r = parse_sse_like_frontend(body, chunk_size=31)

    assert r["dropped"] == [], f"frames the frontend would drop: {r['dropped']}"
    assert len(r["steps"]) == 5, f"expected 5 steps, got {len(r['steps'])}"
    assert r["complete"] is not None
    assert r["complete"]["status"] == "success"
    assert r["error"] is None


@pytest.mark.parametrize("chunk_size", CHUNK_SIZES)
def test_frames_survive_any_chunk_size(client, chunk_size):
    """A frame split across a network boundary must still parse.

    The frontend reads a stream, so chunk boundaries land mid-frame in
    practice. This is the property that would silently break the demo.
    """
    r = parse_sse_like_frontend(_post(client, FULL_TRANSCRIPT).text, chunk_size=chunk_size)
    assert len(r["steps"]) == 5, f"chunk_size={chunk_size} lost frames"
    assert r["complete"]["status"] == "success"


def test_step_frames_carry_the_fields_the_ui_renders(client):
    r = parse_sse_like_frontend(_post(client, FULL_TRANSCRIPT).text)
    for i, step in enumerate(r["steps"]):
        assert set(step) >= {
            "index", "tool", "duration_ms", "provenance", "summary",
        }, f"step {i} missing fields the UI reads: {sorted(step)}"
        assert step["index"] == i
        assert step["tool"], "a step must name its tool"
        assert isinstance(step["duration_ms"], (int, float))
        assert step["summary"], "a step must have a human-readable summary"


def test_complete_frame_steps_is_a_count_not_an_array(client):
    """AgenticComplete.steps is typed `number`.

    Sending a list here is a type-level lie TypeScript cannot catch, because
    the value arrives as untyped JSON. See docs/sse-contract-bugs.md.
    """
    r = parse_sse_like_frontend(_post(client, FULL_TRANSCRIPT).text)
    steps = r["complete"]["steps"]
    assert isinstance(steps, int), f"steps must be a count, got {type(steps)}"
    assert steps == 5


def test_summaries_are_informative_not_just_tool_names(client):
    """The demo reads as a progression; identical rows look like a stub."""
    r = parse_sse_like_frontend(_post(client, FULL_TRANSCRIPT).text)
    summaries = [s["summary"] for s in r["steps"]]
    assert len(set(summaries)) == len(summaries), f"summaries repeat: {summaries}"


def test_incomplete_chain_emits_complete_not_error(client):
    """No contacts is a legitimate outcome, not an error."""
    r = parse_sse_like_frontend(_post(client, NO_CONTACTS_TRANSCRIPT).text)
    assert r["error"] is None, "a halted chain is not an error"
    assert r["complete"] is not None
    assert r["complete"]["status"] == "incomplete"
    assert "no contacts" in (r["complete"]["reason"] or "").lower()
    assert len(r["steps"]) == 1, "it should halt after the extraction step"


def test_failure_emits_an_error_frame_rather_than_truncating(monkeypatch):
    """A broken backend must produce a readable error, not a dead stream.

    The failure path is exercised by patching run_agentic_loop to raise,
    rather than by pointing at a dead port. A real connection failure inside
    the anyio-based MCP client cancels the surrounding task scope, so the
    generator never gets as far as emitting anything — a property of the
    transport, not of this code. The behaviour under test is: whatever goes
    wrong, an `error` frame is emitted and the stream closes cleanly.
    """
    import api.stream as stream_mod

    async def boom(*args, **kwargs):
        raise RuntimeError("backend unreachable")

    monkeypatch.setattr(stream_mod, "run_agentic_loop", boom)

    async def collect():
        return [chunk async for chunk in stream_mod._generate_sse(FULL_TRANSCRIPT, "local")]

    body = "".join(asyncio.run(collect()))
    r = parse_sse_like_frontend(body)

    assert r["error"] is not None, "a failed chain must emit an error frame"
    assert r["error"].get("error"), "the error frame must carry a message"
    assert r["complete"] is None, "a failed chain must not claim completion"
    assert r["steps"] == [], "no steps completed, so no step frames"
    assert r["dropped"] == [], f"the frontend must be able to read it: {r['dropped']}"
    # And it must still be a well-formed, terminating frame.
    assert body.endswith("\n\n")


def test_frames_are_newline_terminated(client):
    """Each frame ends with a blank line; that is what triggers dispatch."""
    body = _post(client, FULL_TRANSCRIPT).text
    assert body.endswith("\n\n"), "the last frame needs its blank-line terminator"
    # No stray carriage returns: the parser splits on \n only.
    assert "\r" not in body