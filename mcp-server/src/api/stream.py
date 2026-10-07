"""SSE streaming for the chained agentic loop.

The web simulator cannot use EventSource because it needs POST, so it parses
SSE frames by hand (`web-simulator/src/lib/api.ts` runAgenticLoop). This
module emits exactly the frames that parser reads:

    event: step     data: {index, tool, duration_ms, provenance, summary}
    event: complete data: {status, steps, synced_record_id, reason}
    event: error    data: {error}

Frames are separated by a blank line, which is what triggers dispatch.

On provenance of `steps`: the `complete` frame carries the step COUNT, not an
array, matching what the frontend's AgenticComplete type declares after the
contract fix in docs/sse-contract-bugs.md. The per-step detail already
arrived in the individual `step` frames, so repeating it would be redundant.

On timing: run_agentic_loop returns its full result rather than yielding, so
frames are emitted after the chain completes. The contract is the frame
SEQUENCE, not real-time interleaving — the frontend renders each step as it
arrives, which still gives the progressive reveal a demo wants.
"""

import json
import os
from typing import Any, AsyncGenerator

from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from client.demo_flow import run_agentic_loop


DEFAULT_SERVER_URL = "http://localhost:8000/mcp"


class AgenticLoopRequest(BaseModel):
    """Request body for POST /api/stream/agentic_loop."""

    transcript: str = Field(
        ..., description="The sales call transcript to process."
    )
    target: str = Field(
        default="local",
        description="CRM sync target: local, salesforce, hubspot, or pipedrive.",
    )


def _server_url() -> str:
    """MCP endpoint the chain should call.

    Configurable so tests can point at an ephemeral port; defaults to the
    address the app is served on in development.
    """
    return os.environ.get("SAGE_MCP_SERVER_URL", DEFAULT_SERVER_URL)


def _step_summary(step: dict[str, Any]) -> str:
    """A one-line, human-readable description of what a step did.

    Prefer something drawn from the result over echoing the tool name, so the
    demo shows a progression rather than five identical-looking rows.
    """
    name = step.get("name", "step")
    result = step.get("result")
    if not isinstance(result, dict):
        return name

    if name == "extract_from_call":
        record = result.get("step3_record", {})
        contacts = len(record.get("contacts", []) or [])
        deals = len(record.get("deals", []) or [])
        if contacts or deals:
            return f"Extracted {contacts} contact(s), {deals} deal(s)"
    elif name == "create_contact":
        who = result.get("name")
        return f"Created contact {who}" if who else "Created contact"
    elif name == "create_deal":
        title = result.get("title")
        return f"Created deal {title}" if title else "Created deal"
    elif name == "schedule_followup":
        title = result.get("title")
        return f"Scheduled follow-up: {title}" if title else "Scheduled follow-up"
    elif name == "sync_to_crm":
        rid = result.get("record_id")
        target = result.get("target", "")
        return f"Synced to {target}: {rid}" if rid else "Synced"

    return name


def _format_step(index: int, step: dict[str, Any]) -> dict[str, Any]:
    """Map an internal recorded step onto the frontend's AgenticStep shape."""
    return {
        "index": index,
        "tool": step.get("name", "unknown"),
        "duration_ms": step.get("duration_ms", 0),
        "provenance": step.get("provenance"),
        "summary": _step_summary(step),
    }


def _frame(event: str, data: dict[str, Any]) -> str:
    """Render one SSE frame with its terminating blank line."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _generate_sse(transcript: str, target: str) -> AsyncGenerator[str, None]:
    """Yield SSE frames for one agentic-loop run."""
    try:
        result = await run_agentic_loop(transcript, server=_server_url(), target=target)
    except Exception as exc:
        # A failure here must surface as a frame, never as a silently closed
        # stream: a truncated stream leaves the frontend waiting forever with
        # no indication anything went wrong.
        yield _frame("error", {"error": str(exc) or exc.__class__.__name__})
        return

    for index, step in enumerate(result.steps):
        yield _frame("step", _format_step(index, step))

    yield _frame(
        "complete",
        {
            "status": result.status,
            # A COUNT, not an array. The frontend's AgenticComplete declares
            # `steps: number`; sending a list here is a type-level lie that
            # TypeScript cannot catch at runtime.
            "steps": result.completed_steps,
            "synced_record_id": result.synced_record_id,
            "reason": result.reason,
        },
    )


def create_agentic_loop_response(transcript: str, target: str = "local") -> StreamingResponse:
    """Build the StreamingResponse for one agentic-loop run."""
    return StreamingResponse(
        _generate_sse(transcript, target),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Disables proxy buffering (nginx and similar), which would
            # otherwise hold frames back and defeat the point of streaming.
            "X-Accel-Buffering": "no",
        },
    )