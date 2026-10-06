"""Token accounting across the provider's usage shapes.

Found while verifying the draft_followup_email fix: the accounting read only
prompt_tokens + completion_tokens, so a response carrying just total_tokens was
recorded as zero cost. That silently under-reports spend, which matters for a
project that reports its own LLM cost.
"""

import asyncio
import json

import httpx
import pytest

from llm.provider import LLMProvider

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


def _provider_with_usage(usage: dict) -> LLMProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"ok": True})}}],
                "usage": usage,
            },
        )

    return LLMProvider(
        api_key="k",
        api_url=OPENAI_URL,
        model="gpt-4o-mini",
        transport=httpx.MockTransport(handler),
    )


def _call(provider: LLMProvider):
    return asyncio.run(provider.extract("transcript text", "full"))


def test_split_token_fields_are_summed():
    p = _provider_with_usage({"prompt_tokens": 30, "completion_tokens": 12})
    _call(p)
    assert p.total_tokens == 42


def test_total_token_field_is_used_when_present():
    """A provider that reports only a total must not be counted as zero."""
    p = _provider_with_usage({"total_tokens": 55})
    _call(p)
    assert p.total_tokens == 55
    assert p.total_cost > 0


def test_total_wins_over_a_disagreeing_split():
    """When both are present, the provider's own total is authoritative.

    Providers sometimes report a total that includes reasoning tokens absent
    from the two split fields; trusting the split undercounts.
    """
    p = _provider_with_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 90}
    )
    _call(p)
    assert p.total_tokens == 90


def test_anthropic_style_input_output_fields():
    p = _provider_with_usage({"input_tokens": 20, "output_tokens": 8})
    _call(p)
    assert p.total_tokens == 28


def test_missing_usage_block_does_not_raise():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]}
        )

    p = LLMProvider(
        api_key="k",
        api_url=OPENAI_URL,
        transport=httpx.MockTransport(handler),
    )
    _call(p)
    assert p.total_tokens == 0


def test_null_usage_does_not_raise():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"ok": True})}}],
                "usage": None,
            },
        )

    p = LLMProvider(
        api_key="k",
        api_url=OPENAI_URL,
        transport=httpx.MockTransport(handler),
    )
    _call(p)
    assert p.total_tokens == 0


def test_tokens_accumulate_across_calls():
    p = _provider_with_usage({"total_tokens": 10})
    _call(p)
    _call(p)
    _call(p)
    assert p.total_tokens == 30


def test_unknown_model_falls_back_to_default_cost():
    p = _provider_with_usage({"total_tokens": 1000})
    p.model = "some-model-nobody-has-priced"
    _call(p)
    assert p.total_cost > 0, "an unpriced model must still yield a non-zero estimate"