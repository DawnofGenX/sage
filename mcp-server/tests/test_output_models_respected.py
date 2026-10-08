"""Guards: tool returns match their declared output schema, with no warnings.

Why this file exists
--------------------
Every tool declares a Pydantic return type, and FastMCP publishes it as an
output_schema. The annotations were not being honoured: the tools returned
plain dicts, and Pydantic does not coerce a function's return value. FastMCP
then serialized those dicts against the *declared* type
(fastmcp/tools/base.py:88 -> TypeAdapter(annotation).dump_python), which
dumps a dict against a model schema successfully but emits a
``PydanticSerializationUnexpectedValue`` warning for every call. The suite ran
green with 57 of them, because no test asserted on warnings.

The wire output was always right, which is exactly what made this insidious:
only the mechanism announcing the schema was lying.

These tests fail if a tool stops returning its declared model (which is what
brings the warnings back), and assert the two output-shape invariants that
callers depend on:

* ``SyncResult`` must not carry an ``error`` key on the success path — it was
  once declared required and that rejected every successful sync (friction log
  entry 10).
* ``record_id`` must be present-and-None on the ``not_configured`` path, not
  omitted — a caller is entitled to distinguish "no id" from "no field".
"""
import asyncio
import json
import os
import tempfile
import warnings
from typing import get_type_hints

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from api.rest import TOOLS, app  # noqa: E402  (must follow the env setup below)
from fastapi.testclient import TestClient  # noqa: E402
from tools.schemas import (  # noqa: E402
    ContactContext,
    CreatedRecord,
    ExtractionResult,
    PipelineHealth,
    SyncResult,
)


# Isolated database so these tests never touch a real one.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAGE_DB_PATH"] = _tmp.name


@pytest.fixture
def client():
    return TestClient(app)


# --- the core invariant -----------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", sorted(TOOLS))
async def test_tool_return_matches_declared_schema(tool_name):
    """Each tool must serialise cleanly through FastMCP's own converter.

    This goes through ``mcp.call_tool`` rather than calling the function
    directly, because that is where the failure lived: FastMCP's
    ``convert_result`` dumps the return against the *declared* type
    (fastmcp/tools/base.py:88). A bare dict dumped against a model schema
    succeeds but warns; the model return is silent. Either way the bytes are
    identical, so the warning is the only observable — and it was invisible to
    the suite for a whole cycle.

    Arguments are built from the published input schema's `required` list, so
    a new tool is covered automatically without a hand-maintained table.
    """
    import inspect

    from server import mcp

    fn = TOOLS[tool_name]
    resolved = get_type_hints(fn)
    declared = resolved["return"]
    models = [
        a
        for a in _unwrap(declared)
        if isinstance(a, type) and hasattr(a, "model_fields")
    ]
    if not models:
        pytest.skip(f"{tool_name} returns a non-model type ({declared})")

    listed = await mcp.list_tools()
    # FastMCP 4.x returns the list directly; older versions wrap it.
    tool_meta = {
        t.name: t for t in (listed if isinstance(listed, list) else listed.tools)
    }
    params = tool_meta[tool_name].parameters or {}
    args = {k: _placeholder(k, v) for k, v in params.get("properties", {}).items()
            if k in params.get("required", [])}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        await mcp.call_tool(tool_name, args)

    serialization_warnings = [
        w for w in caught if "PydanticSerialization" in str(w.message)
    ]
    assert not serialization_warnings, (
        f"{tool_name} produced {len(serialization_warnings)} serializer "
        f"warning(s) — it is returning a bare dict against its declared "
        f"model {models[0].__name__}"
    )


def _unwrap(declared):
    """Flatten a return annotation to its candidate types."""
    origin = getattr(declared, "__origin__", None)
    if origin is not None and hasattr(declared, "__args__"):
        out = []
        for a in declared.__args__:
            out.extend(_unwrap(a))
        return out
    return [declared]


def _placeholder(name: str, spec: dict):
    """A minimal valid value for a JSON-Schema property."""
    t = (spec or {}).get("type")
    if t == "string":
        return "guard-probe"
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    if t == "array":
        return []
    if t == "object":
        return {}
    return None


# --- the two output-shape invariants callers rely on -------------------------


def test_sync_success_carries_no_error_key(client):
    """The success path must omit `error`, not emit it as null.

    Friction log entry 10: `error` was once declared required on SyncResult,
    which made FastMCP reject every successful sync. It is optional now; this
    asserts the field is genuinely absent so a future serialization change
    cannot quietly reintroduce an explicit null.
    """
    import uuid

    response = client.post(
        "/api/tools/sync_to_crm",
        json={
            "record": {"name": "Guard Success"},
            "target": "local",
            "idempotency_key": f"guard-success-{uuid.uuid4().hex[:8]}",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "success", body
    assert body["record_id"], body
    assert "error" not in body, (
        "successful sync must not carry an error key; the REST boundary is "
        "serializing with exclude_unset for exactly this reason"
    )


def test_sync_not_configured_keeps_null_record_id(client):
    """`record_id: null` must survive serialization on the honest failure path.

    Pairs with the test above: exclude_unset (not exclude_none) is what keeps
    an explicitly-null field present while dropping never-provided ones.
    """
    response = client.post(
        "/api/tools/sync_to_crm",
        json={
            "record": {"name": "Guard Unconfigured"},
            "target": "salesforce",
            "idempotency_key": "guard-unconfigured",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "not_configured", body
    assert body["provenance"] == "none", body
    assert "record_id" in body, "field must be present"
    assert body["record_id"] is None, "value must be null"
    assert body["error"], "the failure path must say why"


def test_created_record_is_dict_readable():
    """Tool results are consumed as dicts across the codebase.

    result["id"] and result.get("id") must keep working now that tools return
    models — otherwise every call site breaks and the first person to touch a
    tool sees 33 failures.
    """
    rec = CreatedRecord.model_validate({"id": 7, "name": "X", "created": True})
    assert rec["id"] == 7
    assert rec.get("created") is True
    assert rec.get("nope", "dflt") == "dflt"
    assert "name" in rec
    assert "absent" not in rec
    with pytest.raises(KeyError):
        rec["missing"]


def test_serializing_model_emits_no_warning():
    """The regression in its purest form: model return = zero warnings.

    A dict return against a declared model is what FastMCP serializes with a
    PydanticSerializationUnexpectedValue warning; a model return is silent.
    The JSON is byte-identical either way, so nothing downstream can tell the
    difference except the warning.
    """
    from fastmcp.tools.base import _serialize_to_jsonable

    payload = {"id": 3, "name": "Y", "created": True}

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from_dict = _serialize_to_jsonable(payload, CreatedRecord)
        n_dict = sum(
            1 for x in w if "PydanticSerialization" in str(x.message)
        )

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from_model = _serialize_to_jsonable(
            CreatedRecord.model_validate(payload), CreatedRecord
        )
        n_model = sum(
            1 for x in w if "PydanticSerialization" in str(x.message)
        )

    assert n_dict == 1, "expected the dict return to warn — the premise changed"
    assert n_model == 0, "returning the model must be silent"
    assert from_dict == from_model, "output must be byte-identical"


def test_suite_emits_no_pydantic_serialization_warnings():
    """The loud version: the warning count must be zero.

    Deliberately NOT a recursive pytest run — that made the suite quadratic
    and timed out. Instead it asserts the property parametrically: every tool
    that declares a model must serialise silently through FastMCP, which is the
    only place the original 57 warnings came from
    (fastmcp/tools/base.py:88, convert_result). The per-tool test above does
    exactly that; this one is the human-readable summary that fails with a
    pointer to it.

    If a future tool starts warning, the parametrized test names it.
    """
    from server import mcp

    warned = []

    async def probe_all():
        listed = await mcp.list_tools()
        tools = listed if isinstance(listed, list) else listed.tools
        for t in tools:
            params = t.parameters or {}
            args = {
                k: _placeholder(k, v)
                for k, v in params.get("properties", {}).items()
                if k in params.get("required", [])
            }
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                await mcp.call_tool(t.name, args)
            if any("PydanticSerialization" in str(w.message) for w in caught):
                warned.append(t.name)

    asyncio.run(probe_all())
    assert not warned, (
        f"{len(warned)} tool(s) emitted serializer warnings: {warned}. Each is "
        "returning a bare dict against its declared model — see "
        "test_tool_return_matches_declared_schema."
    )
