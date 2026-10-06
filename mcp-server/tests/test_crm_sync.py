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
    # Test that invalid target returns error
    result = await sync_to_crm(
        record={"name": "Test"},
        target="invalid_crm",
        idempotency_key="test-key",
    )
    assert result["status"] == "error"
    assert "Invalid target" in result["error"]

    # Test that unconfigured salesforce returns graceful fallback (mock success)
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target="salesforce",
        idempotency_key="test-key",
    )
    assert result["status"] == "success"
    assert result["target"] == "salesforce"
    assert result["record_id"] is not None

    # Test that unconfigured hubspot returns graceful fallback
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target="hubspot",
        idempotency_key="test-key",
    )
    assert result["status"] == "success"
    assert result["target"] == "hubspot"
    assert result["record_id"] is not None

    # Test that unconfigured pipedrive returns graceful fallback
    result = await sync_to_crm(
        record={"name": "Test", "email": "test@test.com"},
        target="pipedrive",
        idempotency_key="test-key",
    )
    assert result["status"] == "success"
    assert result["target"] == "pipedrive"
    assert result["record_id"] is not None
