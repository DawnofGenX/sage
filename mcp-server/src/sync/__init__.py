"""CRM sync adapters for Sage."""
from sync.salesforce import SalesforceSync
from sync.hubspot import HubSpotSync
from sync.pipedrive import PipedriveSync

__all__ = ["SalesforceSync", "HubSpotSync", "PipedriveSync"]
