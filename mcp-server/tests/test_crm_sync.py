"""Tests for CRM sync adapters."""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure no CRM credentials are set for not_configured tests
for key in [
    "SALESFORCE_CLIENT_ID",
    "SALESFORCE_CLIENT_SECRET",
    "SALESFORCE_USERNAME",
    "SALESFORCE_PASSWORD",
    "SALESFORCE_SECURITY_TOKEN",
    "HUBSPOT_ACCESS_TOKEN",
    "PIPEDRIVE_API_TOKEN",
]:
    os.environ.pop(key, None)

from sync import SalesforceSync, HubSpotSync, PipedriveSync
from tools.sync import sync_to_crm


# ==================================================================
# Not configured tests
# ==================================================================


@pytest.mark.asyncio
async def test_salesforce_not_configured():
    """Verify graceful handling when Salesforce credentials are missing."""
    sf = SalesforceSync()
    result = await sf.create_contact({"name": "Test", "email": "test@test.com"})
    assert "error" in result
    assert "not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_hubspot_not_configured():
    """Verify graceful handling when HubSpot token is missing."""
    hs = HubSpotSync()
    result = await hs.create_contact({"name": "Test", "email": "test@test.com"})
    assert "error" in result
    assert "not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_pipedrive_not_configured():
    """Verify graceful handling when Pipedrive token is missing."""
    pd = PipedriveSync()
    result = await pd.create_contact({"name": "Test", "email": "test@test.com"})
    assert "error" in result
    assert "not configured" in result["error"].lower()


# ==================================================================
# Mock transport tests
# ==================================================================


@pytest.mark.asyncio
async def test_salesforce_mock():
    """Verify Salesforce adapter with mock transport."""
    with patch.dict(os.environ, {
        "SALESFORCE_CLIENT_ID": "test_client_id",
        "SALESFORCE_CLIENT_SECRET": "test_client_secret",
        "SALESFORCE_USERNAME": "test@example.com",
        "SALESFORCE_PASSWORD": "testpass",
        "SALESFORCE_SECURITY_TOKEN": "testtoken",
    }):
        sf = SalesforceSync()

        # Mock the auth response
        mock_auth_response = MagicMock()
        mock_auth_response.status_code = 200
        mock_auth_response.json.return_value = {
            "access_token": "mock_access_token_123",
            "instance_url": "https://mock.salesforce.com",
        }

        # Mock the create_contact response
        mock_contact_response = MagicMock()
        mock_contact_response.status_code = 201
        mock_contact_response.json.return_value = {
            "id": "003XXXXXXXXXXXXXXX",
            "success": True,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=[mock_auth_response, mock_contact_response])
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await sf.create_contact({
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "title": "VP Sales",
            })

        assert result["id"] == "003XXXXXXXXXXXXXXX"
        assert result["status"] == "created"


@pytest.mark.asyncio
async def test_hubspot_mock():
    """Verify HubSpot adapter with mock transport."""
    with patch.dict(os.environ, {
        "HUBSPOT_ACCESS_TOKEN": "mock_hubspot_token_123",
    }):
        hs = HubSpotSync()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "12345",
            "properties": {"email": "test@example.com"},
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await hs.create_contact({
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane@example.com",
            })

        assert result["id"] == "12345"
        assert result["status"] == "created"


@pytest.mark.asyncio
async def test_pipedrive_mock():
    """Verify Pipedrive adapter with mock transport."""
    with patch.dict(os.environ, {
        "PIPEDRIVE_API_TOKEN": "mock_pipedrive_token_123",
    }):
        pd = PipedriveSync()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "data": {"id": 67890},
            "success": True,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await pd.create_contact({
                "name": "Bob Wilson",
                "email": "bob@example.com",
            })

        assert result["id"] == 67890
        assert result["status"] == "created"


# ==================================================================
# Dispatch test
# ==================================================================


@pytest.mark.asyncio
async def test_sync_to_crm_dispatch():
    """Verify sync_to_crm dispatches to correct adapter."""
    # Invalid target is rejected before any adapter is constructed.
    result = await sync_to_crm(
        record={"name": "Test"},
        target="invalid_crm",
        idempotency_key="test-key",
    )
    assert result["status"] == "error"
    assert "Invalid target" in result["error"]


# ==================================================================
# Unconfigured CRMs must NOT report success
# ==================================================================
#
# These three assertions replace ones that previously asserted
# status == "success" for unconfigured CRMs. That behaviour was the
# defect fixed in this task: sync_to_crm used to synthesise a record ID
# (f"{target[:3]}_{idempotency_key[:8]}") and report success for a CRM
# it had never contacted. Do not restore it.


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["salesforce", "hubspot", "pipedrive"])
async def test_unconfigured_crm_reports_not_configured(target):
    """An unconfigured CRM yields not_configured, never a fake success."""
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target=target,
        idempotency_key="test-key",
    )
    assert result["status"] == "not_configured"
    assert result["target"] == target
    # No record was created anywhere, so there must be no record ID.
    assert result["record_id"] is None
    assert result["synced_at"] is None
    assert result["provenance"] == "none"
    assert result["error"]


@pytest.mark.asyncio
async def test_unconfigured_sync_error_is_actionable():
    """The error must say what is missing, not merely that it failed.

    NOTE: as of this commit the Salesforce adapter returns the generic
    "Salesforce not configured". Making it name the exact env vars is
    follow-up work; this test pins the weaker contract so the improvement
    is a visible, deliberate change rather than an accident.
    """
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target="salesforce",
        idempotency_key="test-key",
    )
    assert "not configured" in result["error"].lower()
    assert "salesforce" in result["error"].lower()


@pytest.mark.asyncio
async def test_no_fabricated_record_id_anywhere_in_source():
    """Guard against the synthesised-ID pattern being reintroduced.

    The old bug was f"{target[:3]}_{idempotency_key[:8]}". If any *executable*
    line builds a record ID from the idempotency key rather than from a real
    provider response, fail here.

    Comments and docstrings are excluded: the fix's explanatory comment quotes
    the old expression verbatim, so a naive text scan would make this guard
    permanently unsatisfiable.
    """
    import ast
    import pathlib

    sync_src = pathlib.Path(__file__).resolve().parent.parent / "src" / "tools" / "sync.py"
    tree = ast.parse(sync_src.read_text())

    # Collect identifiers named `idempotency_key` that are the base of a
    # slice expression. Comments and docstrings are not in the AST at all, so
    # this cannot match prose.
    offenders = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Slice)
        and isinstance(node.value, ast.Name)
        and node.value.id == "idempotency_key"
    ]
    assert not offenders, (
        "sync.py slices `idempotency_key` — that was how the fabricated "
        f"record ID was built ({len(offenders)} occurrence(s)). A record ID "
        "must come from a provider response, never be synthesised locally."
    )


@pytest.mark.asyncio
async def test_successful_sync_reports_real_provenance(monkeypatch):
    """When an adapter really succeeds, provenance names the real CRM."""
    class StubAdapter:
        async def create_contact(self, contact):
            return {"id": "003A000001ABC", "status": "created"}

    # Patch the name as bound in tools/sync.py's globals, so the stub is the
    # adapter the tool actually constructs. (Pyright cannot resolve "tools.*"
    # because src/ is not on its analysis path; the runtime import works
    # because the project is pip-installed. Verified by this test passing.)
    monkeypatch.setattr("tools.sync.SalesforceSync", StubAdapter)
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target="salesforce",
        idempotency_key="test-key",
    )
    assert result["status"] == "success"
    assert result["record_id"] == "003A000001ABC"
    assert result["provenance"] == "salesforce"
