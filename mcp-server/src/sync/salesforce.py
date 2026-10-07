"""Salesforce CRM sync adapter using OAuth 2.0 username-password flow."""
import os
from typing import Optional

import httpx

from sync.base import BaseSyncAdapter


class SalesforceSync(BaseSyncAdapter):
    """Sync contacts and deals to Salesforce via REST API."""

    crm_name = "Salesforce"
    required_env_vars = [
        "SALESFORCE_CLIENT_ID",
        "SALESFORCE_CLIENT_SECRET",
        "SALESFORCE_USERNAME",
        "SALESFORCE_PASSWORD",
        "SALESFORCE_SECURITY_TOKEN",
    ]

    def __init__(self):
        self.client_id = os.environ.get("SALESFORCE_CLIENT_ID")
        self.client_secret = os.environ.get("SALESFORCE_CLIENT_SECRET")
        self.username = os.environ.get("SALESFORCE_USERNAME")
        self.password = os.environ.get("SALESFORCE_PASSWORD")
        self.security_token = os.environ.get("SALESFORCE_SECURITY_TOKEN")
        self.access_token: Optional[str] = None
        self.instance_url: Optional[str] = None

    async def authenticate(self) -> dict:
        """OAuth 2.0 username-password flow to Salesforce."""
        if not self._is_configured():
            return self.not_configured_response()

        auth_url = "https://login.salesforce.com/services/oauth2/token"
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": f"{self.password}{self.security_token}",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(auth_url, data=payload)
            if resp.status_code != 200:
                return {"error": f"Salesforce auth failed: {resp.status_code}"}
            data = resp.json()
            self.access_token = data["access_token"]
            self.instance_url = data["instance_url"]
            return {"access_token": self.access_token, "instance_url": self.instance_url}

    async def create_contact(self, contact: dict) -> dict:
        """Create a Contact in Salesforce."""
        if not self._is_configured():
            return self.not_configured_response()

        if not self.access_token:
            auth_result = await self.authenticate()
            if "error" in auth_result:
                return auth_result

        url = f"{self.instance_url}/services/data/v58.0/sobjects/Contact"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "FirstName": contact.get("first_name", ""),
            "LastName": contact.get("last_name", contact.get("name", "")),
            "Email": contact.get("email", ""),
            "Title": contact.get("title", ""),
            "AccountId": contact.get("account_id", ""),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                return {"error": f"Salesforce create_contact failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["id"], "status": "created"}

    async def create_deal(self, deal: dict) -> dict:
        """Create an Opportunity in Salesforce."""
        if not self._is_configured():
            return self.not_configured_response()

        if not self.access_token:
            auth_result = await self.authenticate()
            if "error" in auth_result:
                return auth_result

        url = f"{self.instance_url}/services/data/v58.0/sobjects/Opportunity"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "Name": deal.get("name", deal.get("title", "")),
            "Amount": deal.get("amount", deal.get("value", 0)),
            "StageName": self._map_stage(deal.get("stage", "lead")),
            "CloseDate": deal.get("close_date", ""),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                return {"error": f"Salesforce create_deal failed: {resp.status_code}"}
            data = resp.json()
            return {"id": data["id"], "status": "created"}

    @staticmethod
    def _map_stage(stage: str) -> str:
        """Map internal stage names to Salesforce stage names."""
        mapping = {
            "lead": "Prospecting",
            "proposal": "Proposal/Price Quote",
            "negotiation": "Negotiation/Review",
            "closed_won": "Closed Won",
            "closed_lost": "Closed Lost",
        }
        return mapping.get(stage, "Prospecting")
