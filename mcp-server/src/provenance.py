"""Provenance vocabulary for Sage tool responses.

Every mutating tool response carries a `provenance` field so a consumer can
tell exactly what produced the value. The distinction that matters: `mock`
means a deterministic fallback produced this, `none` means nothing happened
and here is why. Nothing may report `success` without a provenance that
earned it.

Added 2026-10-06 to fix a defect where sync_to_crm returned
`status: "success"` with a synthesised record ID when the target CRM was
unconfigured.
"""

from typing import Literal

Provenance = Literal[
    # Real, external systems
    "local",        # Sage's own SQLite store
    "salesforce",   # real Salesforce API response
    "hubspot",      # real HubSpot API response
    "pipedrive",    # real Pipedrive API response
    # Real LLM providers
    "bedrock",      # AWS Bedrock
    "openai",       # OpenAI-compatible endpoint
    "anthropic",    # Anthropic messages endpoint
    # Explicitly not real
    "mock",         # no credentials; deterministic fallback produced this
    "replay",       # a recorded response, labelled as such
    "none",         # nothing happened; see the error field
]

MOCK_NOTE = (
    "No credentials configured; a deterministic fallback produced this value. "
    "It is not a real external record."
)

#: Provenance values that represent a genuine external system or local store.
REAL_PROVENANCE = frozenset(
    {"local", "salesforce", "hubspot", "pipedrive", "bedrock", "openai", "anthropic"}
)

#: Provenance values that must never accompany status="success".
NOT_REAL_PROVENANCE = frozenset({"mock", "none"})


def is_real(provenance: str) -> bool:
    """Return True only if the provenance represents a genuine record."""
    return provenance in REAL_PROVENANCE