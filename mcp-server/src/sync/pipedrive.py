"""Pipedrive CRM sync adapter."""
import os

import httpx

from sync.base import BaseSyncAdapter


class PipedriveSync(BaseSyncAdapter):
    """Sync contacts and deals to Pipedrive via REST API."""

    crm_name = "Pipedrive"
    required_env_vars = ["PIPEDRIVE_API_TOKEN"]

    def __init__(self):
        self.api_token = os.environ.get("PIPEDRIVE_API_TOKEN")

    async def create_contact(self, contact: dict) -> dict:
        """Create a person in Pipedrive."""
        if not self._is_configured():
            return self.not_configured_response()

        url = "https://api.pipedrive.com/v1/persons"
        params = {"api_token": self.api_token}
        payload = {
            "name": contact.get("name", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "org_name": contact.get("company", ""),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, params=params)
            if resp.status_code not in (200, 201):
                return {"error": f"Pipedrive create_contact failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["data"]["id"], "status": "created"}

    async def create_deal(self, deal: dict) -> dict:
        """Create a deal in Pipedrive."""
        if not self._is_configured():
            return self.not_configured_response()

        url = "https://api.pipedrive.com/v1/deals"
        params = {"api_token": self.api_token}
        payload = {
            "title": deal.get("name", deal.get("title", "")),
            "value": deal.get("amount", deal.get("value", 0)),
            "status": deal.get("status", "open"),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, params=params)
            if resp.status_code not in (200, 201):
                return {"error": f"Pipedrive create_deal failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["data"]["id"], "status": "created"}
