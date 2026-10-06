"""CRM sync adapters for Sage."""
from sync.salesforce import SalesforceSync
from sync.hubspot import HubSpotSync
from sync.pipedrive import PipedriveSync
from sync.local import LocalCRMSync

__all__ = ["SalesforceSync", "HubSpotSync", "PipedriveSync", "LocalCRMSync"]