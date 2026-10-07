"""LLM provider abstraction with mock mode fallback.

Supports real LLM API calls via httpx when LLM_API_KEY is set,
and falls back to regex/keyword-based mock responses for demo use.

Real API calls support both OpenAI-compatible (chat/completions) and
Anthropic (messages) endpoints, auto-detected from the API URL. Calls
use exponential-backoff retries (3 attempts), a 30-second timeout, and
JSON response validation. See :mod:`llm.formats` for the wire formats.

When AWS credentials are available (AWS_ACCESS_KEY_ID env var), the
provider automatically uses Amazon Bedrock (Nova/Claude models) instead
of the OpenAI/Anthropic API path.
"""

import asyncio
import json
import os
from typing import Any

import httpx

from llm.formats import LLMAPIFormat, detect_format, parse_json_response
from llm.mock_extraction import MockExtractionMixin
from llm.prompts import (
    EMAIL_PROMPT,
    ENTITIES_PROMPT,
    EXTRACTION_PROMPT,
    INSIGHTS_PROMPT,
    INTENT_PROMPT,
)

DEFAULT_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0

# Approximate cost per 1K tokens (input + output combined) for common models.
# Used for cost estimation only — actual billing varies by provider.
MODEL_COST_PER_1K = {
    "gpt-4o-mini": 0.0006,
    "gpt-4o": 0.01,
    "gpt-4-turbo": 0.02,
    "gpt-3.5-turbo": 0.002,
    "claude-sonnet-4-20250514": 0.009,
    "claude-3-5-sonnet-20241022": 0.009,
    "claude-3-haiku-20240307": 0.0015,
}
DEFAULT_COST_PER_1K = 0.001


class LLMAPIError(RuntimeError):
    """Raised when a real LLM API call fails after all retries."""


class LLMProvider(MockExtractionMixin):
    """Configurable LLM provider for sales intelligence extraction."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        model: str | None = None,
        *,
        timeout: float = REQUEST_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_base_delay: float = RETRY_BASE_DELAY,
        transport: httpx.AsyncBaseTransport | None = None,
        use_bedrock: bool | None = None,
    ):
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        self.api_url = api_url or os.environ.get("LLM_API_URL", DEFAULT_API_URL)
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)

        # Bedrock integration: use when AWS credentials are available
        if use_bedrock is None:
            use_bedrock = bool(os.environ.get("AWS_ACCESS_KEY_ID"))
        self._use_bedrock = use_bedrock

        self._use_mock = not self.api_key and not self._use_bedrock

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._transport = transport

        self._format: LLMAPIFormat = detect_format(self.api_url)

        # Token and cost tracking
        self.total_tokens: int = 0
        self.total_cost: float = 0.0

        # Lazy Bedrock provider
        self._bedrock_provider = None

        # Provenance of the most recent extract() call, and a call counter.
        # Added 2026-06 for the truth-discipline work: consumers must be able
        # to tell whether a value came from a real provider or a mock, without
        # inferring it from the absence of an error.
        self.last_provenance: str = "none"
        self.call_count: int = 0

    @property
    def is_mock(self) -> bool:
        """Return True if running in mock mode (no API key and no Bedrock)."""
        return self._use_mock

    @property
    def use_bedrock(self) -> bool:
        """Return True if Bedrock is enabled (AWS credentials available)."""
        return self._use_bedrock

    @property
    def api_format(self) -> str:
        """Name of the detected API wire format ('openai' or 'anthropic')."""
        return self._format.name

    def _get_bedrock(self):
        """Lazy-initialize the Bedrock provider."""
        if self._bedrock_provider is None:
            from aws.bedrock import BedrockProvider
            self._bedrock_provider = BedrockProvider()
        return self._bedrock_provider

    async def extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Extract structured data from a transcript.

        Args:
            transcript: The call transcript text.
            extraction_type: One of 'entities', 'intent', 'sentiment', 'full', 'insights'.

        Returns:
            A dictionary with the extracted data.

        Raises:
            LLMAPIError: If the real API call fails after all retries.
        """
        self.call_count += 1

        if self._use_mock:
            self.last_provenance = "mock"
            return self._mock_extract(transcript, extraction_type)

        if self._use_bedrock:
            self.last_provenance = "bedrock"
            bedrock = self._get_bedrock()
            return await bedrock.extract(transcript, extraction_type)

        self.last_provenance = self._format.name
        return await self._api_extract(transcript, extraction_type)

    # ------------------------------------------------------------------
    # Real API path
    # ------------------------------------------------------------------

    async def _api_extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Call the real LLM API and parse the JSON response.

        Retries up to ``max_retries`` times with exponential backoff on
        network errors, HTTP 429/5xx responses, and invalid JSON.
        """
        prompt = self._build_prompt(transcript, extraction_type)
        payload = self._format.build_payload(self.model, prompt)
        headers = self._format.build_headers(self.api_key or "")

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return await self._single_request(payload, headers)
            except (httpx.HTTPError, LLMAPIError, ValueError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                delay = self.retry_base_delay * (2 ** (attempt - 1))
                await asyncio.sleep(delay)

        raise LLMAPIError(
            f"LLM API call failed after {self.max_retries} attempts: {last_error}"
        ) from last_error

    async def _single_request(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        """Perform one API request and validate the parsed response."""
        client_kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)

        if response.status_code == 429 or response.status_code >= 500:
            # Retryable — surfaced to the retry loop in _api_extract.
            raise httpx.HTTPStatusError(
                f"retryable HTTP {response.status_code}: {response.text[:200]}",
                request=response.request,
                response=response,
            )
        response.raise_for_status()

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise LLMAPIError(f"API response was not valid JSON: {exc}") from exc

        self._format.validate_response(data)
        content = self._format.extract_content(data)
        result = parse_json_response(content)

        # Track token usage and cost.
        #
        # Some providers report only `total_tokens` (and some, notably OpenAI's
        # newer responses, split it differently). Previously this read only
        # prompt_tokens + completion_tokens and fell back to 0 when absent, so
        # a response carrying just total_tokens was counted as zero cost —
        # silently under-reporting spend. Prefer the provider's own total when
        # present, and only sum the split fields as a fallback.
        usage = data.get("usage") or {}
        total = usage.get("total_tokens")
        if total is None:
            prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
            completion_tokens = usage.get(
                "completion_tokens", usage.get("output_tokens", 0)
            )
            total = prompt_tokens + completion_tokens
        tokens = int(total or 0)
        self.total_tokens += tokens
        self.total_cost += self._calculate_cost(tokens)

        return result

    def _calculate_cost(self, tokens: int) -> float:
        """Estimate cost based on model and token count.

        Args:
            tokens: Total tokens (prompt + completion).

        Returns:
            Estimated cost in USD.
        """
        cost_per_1k = MODEL_COST_PER_1K.get(self.model, DEFAULT_COST_PER_1K)
        return (tokens / 1000) * cost_per_1k

    def _build_prompt(self, transcript: str, extraction_type: str) -> str:
        """Build the LLM prompt for a given extraction type."""
        if extraction_type == "insights":
            return INSIGHTS_PROMPT.replace("{context}", transcript)
        if extraction_type == "entities":
            return ENTITIES_PROMPT.replace("{transcript}", transcript)
        if extraction_type == "intent":
            return INTENT_PROMPT.replace("{transcript}", transcript)
        if extraction_type == "email":
            # The caller passes a JSON blob of {contact, context, tone} in the
            # transcript slot, since this prompt is not transcript-shaped.
            # Malformed input falls back to neutral defaults rather than
            # raising: a malformed payload should still yield a usable prompt.
            import json

            try:
                fields = json.loads(transcript)
            except (TypeError, ValueError):
                fields = {}
            if not isinstance(fields, dict):
                fields = {}
            return (
                EMAIL_PROMPT.replace("{tone}", str(fields.get("tone", "formal")))
                .replace("{contact}", str(fields.get("contact", "there")))
                .replace("{context}", str(fields.get("context", "our conversation")))
            )
        return EXTRACTION_PROMPT.replace("{transcript}", transcript)

    # ------------------------------------------------------------------
    # Mock mode
    # ------------------------------------------------------------------

    def _mock_email(self, transcript: str) -> dict[str, Any]:
        """Produce a template email for mock mode.

        Callers must treat an email from mock provenance as templated, not
        written. draft_followup_email sets provenance="mock" when this runs so
        the UI can label it.
        """
        import json

        try:
            fields = json.loads(transcript)
        except (TypeError, ValueError):
            fields = {}
        contact = fields.get("contact", "there")
        context = fields.get("context", "our recent conversation")
        tone = fields.get("tone", "formal")
        subject = f"Following up: {context[:50]}"
        body = (
            f"Dear {contact},\n\n"
            f"I wanted to follow up on {context}.\n\n"
            f"Looking forward to hearing from you.\n\n"
            f"Best regards"
        )
        return {"subject": subject, "body": body, "tone_used": tone}
