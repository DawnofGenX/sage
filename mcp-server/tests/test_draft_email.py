"""Tests for draft_followup_email.

The tool previously called the LLM with extraction_type="full" — a
call-transcript extraction task — and then discarded the response, building the
email from a template regardless of what the model said. These tests pin the
fixed behaviour: the model's own words reach the caller, and a templated email
is labelled as one.
"""

import asyncio
import json

import pytest

import tools.crud as crud
from llm.provider import LLMProvider

TEMPLATE_SENTINEL = "I wanted to follow up on our recent conversation"


class StubProvider(LLMProvider):
    """A provider that reports real provenance and returns a known email."""

    def __init__(self, email: dict, provenance: str = "openai"):
        super().__init__(api_key="stub-key", api_url="https://api.openai.com/v1/chat/completions")
        self._email = email
        self.last_provenance = provenance
        self.requested_type = None

    async def extract(self, transcript, extraction_type):
        self.requested_type = extraction_type
        return self._email


@pytest.fixture
def stub_provider(monkeypatch):
    """Install a stub provider into crud's module-level accessor."""
    def _install(email, provenance="openai"):
        provider = StubProvider(email, provenance)
        monkeypatch.setattr(crud, "_get_provider", lambda: provider)
        return provider

    return _install


# ==================================================================
# The model writes the email
# ==================================================================


def test_real_provider_subject_and_body_come_from_the_model(stub_provider):
    """With a real provider, the returned text is the model's, not a template."""
    written = {
        "subject": "Acme enterprise licence — next steps",
        "body": "Hi Sarah,\n\nGreat speaking today about the enterprise tier.\n\nBest,\nPriyansh",
        "tone_used": "formal",
    }
    provider = stub_provider(written)

    result = asyncio.run(
        crud.draft_followup_email(
            contact="Sarah Chen", context="the enterprise licence", tone="formal"
        )
    )

    assert result["subject"] == written["subject"]
    assert result["body"] == written["body"]
    assert result["tone_used"] == "formal"
    assert result["provenance"] == "openai"
    assert result["templated"] is False
    # The template text must not appear anywhere in a written email.
    assert TEMPLATE_SENTINEL not in result["body"]


def test_uses_the_email_extraction_type_not_full(stub_provider):
    """The prompt must be an email prompt, not a transcript-extraction prompt.

    The old code sent extraction_type="full", asking the model to extract CRM
    records from a call transcript — the wrong task entirely.
    """
    provider = stub_provider({"subject": "s", "body": "b"})
    asyncio.run(crud.draft_followup_email(contact="Sarah", context="ctx"))

    assert provider.requested_type == "email"


def test_passes_contact_context_and_tone_through(stub_provider):
    """The provider receives the real fields, not a pre-baked string."""
    captured = {}

    class CapturingProvider(StubProvider):
        async def extract(self, transcript, extraction_type):
            captured.update(json.loads(transcript))
            return {"subject": "s", "body": "b"}

    provider = CapturingProvider({"subject": "s", "body": "b"})
    import tools.crud as crud_mod

    original = crud_mod._get_provider
    crud_mod._get_provider = lambda: provider
    try:
        asyncio.run(
            crud_mod.draft_followup_email(
                contact="Mike Johnson", context="competitor pricing", tone="urgent"
            )
        )
    finally:
        crud_mod._get_provider = original

    assert captured["contact"] == "Mike Johnson"
    assert captured["context"] == "competitor pricing"
    assert captured["tone"] == "urgent"


# ==================================================================
# Mock mode is honest about being a template
# ==================================================================


def test_mock_provenance_is_labelled_templated(monkeypatch):
    """A mock-mode email must not claim to be model-written."""
    provider = LLMProvider()  # no api key, no bedrock -> mock mode
    monkeypatch.setattr(crud, "_get_provider", lambda: provider)
    assert provider.is_mock

    result = asyncio.run(
        crud.draft_followup_email(contact="Sarah", context="the proposal")
    )

    assert result["provenance"] == "mock"
    assert result["templated"] is True
    assert result["subject"]
    assert result["body"]


def test_mock_mode_still_produces_a_usable_email(monkeypatch):
    """Mock mode is a fallback, not a failure — it must still return text."""
    provider = LLMProvider()
    monkeypatch.setattr(crud, "_get_provider", lambda: provider)

    result = asyncio.run(
        crud.draft_followup_email(contact="Sarah Chen", context="Acme proposal")
    )
    assert result["subject"]
    assert "Sarah Chen" in result["body"]


# ==================================================================
# A real provider that misbehaves must not produce an empty email
# ==================================================================


def test_real_provider_returning_nothing_falls_back_and_says_so(stub_provider):
    """An empty model response must not ship as an empty email."""
    stub_provider({"subject": "", "body": ""}, provenance="anthropic")

    result = asyncio.run(
        crud.draft_followup_email(contact="Sarah", context="the proposal")
    )
    assert result["subject"], "subject must never be empty"
    assert result["body"], "body must never be empty"
    assert result["templated"] is True


def test_real_provider_returning_non_dict_falls_back(stub_provider):
    stub_provider(None, provenance="openai")

    result = asyncio.run(
        crud.draft_followup_email(contact="Sarah", context="the proposal")
    )
    assert result["subject"]
    assert result["body"]
    assert result["templated"] is True


# ==================================================================
# Prompt routing
# ==================================================================


def test_email_prompt_renders_the_fields():
    """EMAIL_PROMPT must actually substitute contact, context, and tone."""
    from llm.provider import LLMProvider as P

    p = P(api_key="k", api_url="https://api.openai.com/v1/chat/completions")
    rendered = p._build_prompt(
        json.dumps({"contact": "Sarah", "context": "renewal", "tone": "casual"}),
        "email",
    )
    assert "Sarah" in rendered
    assert "renewal" in rendered
    assert "casual" in rendered
    assert "{contact}" not in rendered
    assert "{tone}" not in rendered
    # Must not ask for CRM extraction.
    assert "contacts" not in rendered


def test_mock_email_dispatch_returns_email_shape():
    p = LLMProvider()
    out = p._mock_extract(
        json.dumps({"contact": "Sarah", "context": "ctx", "tone": "formal"}), "email"
    )
    assert set(out) >= {"subject", "body"}


def test_email_prompt_survives_unparseable_input():
    """A malformed payload must not raise out of the prompt builder."""
    from llm.provider import LLMProvider as P

    p = P(api_key="k", api_url="https://api.openai.com/v1/chat/completions")
    rendered = p._build_prompt("not json at all", "email")
    assert "there" in rendered  # falls back to a default salutation