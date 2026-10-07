"""Reference implementation of the frontend's SSE parser, in Python.

`web-simulator/src/lib/api.ts` runAgenticLoop parses SSE frames by hand
because EventSource cannot POST. This mirrors its logic so the backend's
output can be checked against the real parser before the two ever run
together.

THE MIRROR IS ITSELF CODE AND WAS ONCE WRONG. An earlier version appended
each chunk to `buffer` and then called a helper that re-split `buffer`
itself, so every chunk was counted twice and frame state was mangled across
boundaries. It reported zero frames from a perfectly valid payload, which
looked like a frontend bug and was not. The parser below consumes each chunk
exactly once and carries frame state across calls, and
`test_sse_reference_parser.py` pins its behaviour so it cannot manufacture a
phantom finding again.

Framing rules mirrored from api.ts:
  - accumulate decoded chunks into a buffer
  - split on newlines; keep the last element as the new buffer
  - `event: X` sets the current event type
  - `data: Y` appends to the current data lines
  - an EMPTY line dispatches the frame and resets
  - after the stream ends, flush when the buffer has content
"""

from __future__ import annotations

import json


def parse_sse_like_frontend(payload: str, chunk_size: int = 4096) -> dict:
    """Mirror of the frontend parser. Returns what the UI would actually see.

    Args:
        payload: the raw response body, as text.
        chunk_size: simulated network chunk size. The result must not depend on
            this, since the frontend relies on that.

    Returns:
        {"steps", "complete", "error", "dropped"}
    """
    buffer = ""
    event_type = ""
    data_lines: list[str] = []
    steps: list[dict] = []
    complete: dict | None = None
    error: dict | None = None
    dropped: list[dict] = []

    def dispatch() -> None:
        nonlocal event_type, data_lines, steps, complete, error, dropped
        et, dl = event_type, data_lines
        event_type, data_lines = "", []
        if not et or not dl:
            if et and not dl:
                dropped.append({"event": et, "why": "no data lines"})
            return
        try:
            parsed = json.loads("\n".join(dl))
        except json.JSONDecodeError:
            dropped.append({"event": et, "why": "malformed JSON"})
            return
        if et == "step":
            steps.append(parsed)
        elif et == "complete":
            complete = parsed
        elif et == "error":
            error = parsed
        else:
            dropped.append({"event": et, "why": "unhandled event type"})

    def consume(text: str, is_final: bool) -> None:
        """Feed one chunk. Appends to buffer exactly once.

        `buffer`, `event_type`, AND `data_lines` must all be declared
        nonlocal. Without the latter two, assigning them here creates
        function-locals that shadow the enclosing scope, so every frame's
        type and payload are discarded when consume() returns and nothing is
        ever dispatched.
        """
        nonlocal buffer, event_type, data_lines
        lines = (buffer + text).split("\n")
        buffer = "" if is_final else (lines.pop() or "")
        for line in lines:
            if line.startswith("event: "):
                event_type = line[7:].strip()
            elif line.startswith("data: "):
                data_lines.append(line[6:])
            elif line == "":
                dispatch()
            # Any other line (a ": keep-alive" comment) is ignored,
            # exactly as the frontend does.

    for i in range(0, len(payload), chunk_size):
        consume(payload[i : i + chunk_size], is_final=False)

    if buffer.strip():
        consume("", is_final=True)
    # A frame whose data arrived but whose terminating blank line did not is
    # still dispatched: dropping it would hide a completed run. This must run
    # BEFORE any reset, and it reads the live frame state, not a copy.
    if event_type and data_lines:
        dispatch()

    return {
        "steps": steps,
        "complete": complete,
        "error": error,
        "dropped": dropped,
    }


def frame(event: str, data: dict) -> str:
    """Build one correctly-framed SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"