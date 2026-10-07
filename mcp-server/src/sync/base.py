"""Base class for CRM sync adapters."""
import os
from typing import ClassVar


class BaseSyncAdapter:
    """Base class for CRM sync adapters.

    Provides common functionality for checking configuration and
    building not-configured responses.
    """

    crm_name: ClassVar[str] = ""
    required_env_vars: ClassVar[list[str]] = []

    def _is_configured(self) -> bool:
        """Check if all required environment variables are set."""
        return all(os.environ.get(var) for var in self.required_env_vars)

    def not_configured_response(self) -> dict:
        """Return the standard not-configured response."""
        return {
            "status": "not_configured",
            "record_id": None,
            "provenance": "none",
            "error": f"{self.crm_name} not configured",
        }

    @classmethod
    def get_adapter(cls, target: str):
        """Return the adapter instance for the given target CRM."""
        from sync import SalesforceSync, HubSpotSync, PipedriveSync

        adapters = {
            "salesforce": SalesforceSync,
            "hubspot": HubSpotSync,
            "pipedrive": PipedriveSync,
        }
        adapter_cls = adapters.get(target)
        if adapter_cls is None:
            return None
        return adapter_cls()
