"""HubSpot CRM sync adapter."""
import os

import httpx

from sync.base import BaseSyncAdapter


class HubSpotSync(BaseSyncAdapter):
    """Sync contacts and deals to HubSpot via REST API."""

    crm_name = "HubSpot"
    required_env_vars = ["HUBSPOT_ACCESS_TOKEN"]

    def __init__(self):
        self.access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN")

    async def create_contact(self, contact: dict) -> dict:
        """Create a contact in HubSpot."""
        if not self._is_configured():
            return self.not_configured_response()

        url = "https://api.hubapi.com/crm/v3/objects/contacts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "properties": {
                "email": contact.get("email", ""),
                "firstname": contact.get("first_name", ""),
                "lastname": contact.get("last_name", contact.get("name", "")),
                "jobtitle": contact.get("title", ""),
                "company": contact.get("company", ""),
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                return {"error": f"HubSpot create_contact failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["id"], "status": "created"}

    async def create_deal(self, deal: dict) -> dict:
        """Create a deal in HubSpot."""
        if not self._is_configured():
            return self.not_configured_response()

        url = "https://api.hubapi.com/crm/v3/objects/deals"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "properties": {
                "dealname": deal.get("name", deal.get("title", "")),
                "amount": str(deal.get("amount", deal.get("value", 0))),
                "dealstage": deal.get("stage", "lead"),
                "closedate": deal.get("close_date", ""),
            }
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                return {"error": f"HubSpot create_deal failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["id"], "status": "created"}
