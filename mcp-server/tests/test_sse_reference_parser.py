"""Pin the reference SSE parser's own behaviour.

This parser exists to validate the backend's output against what the
frontend will actually parse. An earlier version of it was itself buggy and
reported zero frames for a valid payload — which looked like a frontend bug.
These tests ensure the mirror is trustworthy before anything relies on it.
"""

import json

from sse_reference_parser import frame, parse_sse_like_frontend

CHUNK_SIZES = [4096, 500, 137, 37, 11, 3, 1]


def test_two_frame_payload_parses():
    payload = frame("step", {"index": 1, "tool": "a"}) + frame(
        "complete", {"status": "success"}
    )
    r = parse_sse_like_frontend(payload)
    assert len(r["steps"]) == 1
    assert r["complete"] == {"status": "success"}
    assert r["dropped"] == []


def test_result_is_independent_of_chunk_size():
    """The property the frontend actually relies on.

    A frame split across a network chunk boundary must still parse. An
    earlier mirror reset its frame state per chunk and failed this, so it is
    pinned explicitly.
    """
    payload = "".join(
        frame("step", {"index": i, "tool": f"t{i}", "duration_ms": i,
                       "provenance": "local", "summary": "s"})
        for i in range(1, 6)
    ) + frame("complete", {"status": "success", "steps": 5,
                           "synced_record_id": "loc_d_1"})

    baseline = None
    for size in CHUNK_SIZES:
        r = parse_sse_like_frontend(payload, chunk_size=size)
        assert len(r["steps"]) == 5, f"chunk_size={size} lost frames"
        assert r["complete"]["synced_record_id"] == "loc_d_1"
        assert r["dropped"] == []
        if baseline is None:
            baseline = r
        else:
            assert r["steps"] == baseline["steps"]


def test_incomplete_frame_is_read():
    payload = frame("complete", {"status": "incomplete", "steps": 1,
                                 "reason": "no contacts extracted"})
    r = parse_sse_like_frontend(payload)
    assert r["complete"]["status"] == "incomplete"
    assert "no contacts" in r["complete"]["reason"]


def test_error_frame_is_read():
    payload = frame("error", {"error": "backend exploded"})
    r = parse_sse_like_frontend(payload)
    assert r["error"] == {"error": "backend exploded"}


def test_malformed_json_is_dropped_not_raised():
    payload = "event: step\ndata: {not json}\n\n" + frame("complete", {"status": "success"})
    r = parse_sse_like_frontend(payload)
    assert r["steps"] == []
    assert r["complete"] is not None
    assert any("malformed" in d["why"] for d in r["dropped"])


def test_unknown_event_type_is_dropped_not_raised():
    payload = frame("heartbeat", {"n": 1}) + frame("complete", {"status": "success"})
    r = parse_sse_like_frontend(payload)
    assert any("unhandled" in d["why"] for d in r["dropped"])
    assert r["complete"] is not None


def test_keepalive_comment_lines_are_ignored():
    """SSE servers commonly emit `: keep-alive` comments. They must not
    break frame parsing — the frontend ignores any line it does not match."""
    payload = ": keep-alive\n\n" + frame("complete", {"status": "success"})
    r = parse_sse_like_frontend(payload)
    assert r["complete"] == {"status": "success"}


def test_multiline_data_is_joined():
    """A data payload split across several `data:` lines must reassemble."""
    payload = (
        "event: complete\n"
        "data: {\"status\":\n"
        "data: \"success\"}\n\n"
    )
    r = parse_sse_like_frontend(payload)
    assert r["complete"] == {"status": "success"}


def test_frame_without_terminating_blank_line_still_dispatches():
    """A truncated final frame must not silently swallow the completion."""
    payload = frame("step", {"index": 1}) + 'event: complete\ndata: {"status":"success"}'
    r = parse_sse_like_frontend(payload)
    assert r["complete"] == {"status": "success"}


def test_empty_payload_yields_nothing():
    r = parse_sse_like_frontend("")
    assert r["steps"] == [] and r["complete"] is None and r["error"] is None


def test_frame_helper_produces_spec_shaped_output():
    out = frame("step", {"a": 1})
    assert out == 'event: step\ndata: {"a": 1}\n\n'
    assert json.loads(out.split("data: ")[1].strip()) == {"a": 1}