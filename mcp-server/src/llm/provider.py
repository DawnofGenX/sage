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
import re
from typing import Any

import httpx

from llm.formats import LLMAPIFormat, detect_format, parse_json_response
from llm.prompts import EXTRACTION_PROMPT, INSIGHTS_PROMPT

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


class LLMProvider:
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
        if self._use_mock:
            return self._mock_extract(transcript, extraction_type)
        if self._use_bedrock:
            bedrock = self._get_bedrock()
            return await bedrock.extract(transcript, extraction_type)
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

        # Track token usage and cost
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        tokens = prompt_tokens + completion_tokens
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
        return EXTRACTION_PROMPT.replace("{transcript}", transcript)

    # ------------------------------------------------------------------
    # Mock mode
    # ------------------------------------------------------------------

    def _mock_extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Return realistic mock data based on transcript content."""
        dispatch = {
            "entities": self._mock_entities,
            "intent": self._mock_intent,
            "sentiment": self._mock_sentiment,
            "full": self._mock_full,
            "insights": self._mock_insights,
        }
        handler = dispatch.get(extraction_type, self._mock_full)
        return handler(transcript)

    def _mock_entities(self, transcript: str) -> dict[str, Any]:
        """Extract entities using regex patterns."""
        # People: capitalized first + last name pairs
        people = []
        for match in re.finditer(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", transcript):
            name = match.group(1)
            if name not in people:
                people.append(name)

        # Companies: look for common company suffixes or "at <Company>"
        companies = []
        for match in re.finditer(
            r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+(?:Inc|Corp|LLC|Ltd|Company|Co|Group|Technologies|Systems|Solutions))\b",
            transcript,
        ):
            companies.append(match.group(1))
        # Also catch "at <Company>" patterns
        for match in re.finditer(r"\bat\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*)\b", transcript):
            name = match.group(1)
            if name not in companies and name not in ("I", "We", "The", "A", "An"):
                companies.append(name)

        # Amounts: dollar figures
        amounts = []
        for match in re.finditer(r"\$[\d,]+(?:\.\d{2})?", transcript):
            amounts.append(match.group(0))

        # Dates: MM/DD/YYYY or Month DD patterns
        dates = []
        for match in re.finditer(
            r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?)\b",
            transcript,
        ):
            dates.append(match.group(0))

        return {
            "people": people,
            "companies": companies,
            "amounts": amounts,
            "dates": dates,
        }

    def _mock_intent(self, transcript: str) -> dict[str, Any]:
        """Classify intent using keyword matching."""
        text = transcript.lower()

        new_lead_keywords = ["new", "interested", "just started", "looking for", "evaluate", "demo", "trial"]
        follow_up_keywords = ["follow up", "follow-up", "check in", "touch base", "circle back", "reconnect"]
        deal_update_keywords = ["update", "progress", "stage", "negotiate", "contract", "proposal", "signed", "closed"]

        scores = {
            "new_lead": sum(1 for kw in new_lead_keywords if kw in text),
            "follow_up": sum(1 for kw in follow_up_keywords if kw in text),
            "deal_update": sum(1 for kw in deal_update_keywords if kw in text),
        }

        best = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[best] / total if total > 0 else 0.5

        if scores[best] == 0:
            best = "general"
            confidence = 0.6

        return {"intent": best, "confidence": round(confidence, 2)}

    def _mock_sentiment(self, transcript: str) -> dict[str, Any]:
        """Analyze sentiment using keyword matching."""
        text = transcript.lower()

        positive_keywords = ["great", "excited", "love", "excellent", "amazing", "perfect", "happy", "pleased", "awesome", "fantastic"]
        negative_keywords = ["concerned", "worried", "problem", "issue", "unhappy", "disappointed", "frustrated", "angry", "upset", "bad"]

        pos_count = sum(1 for kw in positive_keywords if kw in text)
        neg_count = sum(1 for kw in negative_keywords if kw in text)

        if pos_count > neg_count:
            sentiment = "positive"
            confidence = min(0.5 + (pos_count - neg_count) * 0.15, 0.95)
        elif neg_count > pos_count:
            sentiment = "negative"
            confidence = min(0.5 + (neg_count - pos_count) * 0.15, 0.95)
        else:
            sentiment = "neutral"
            confidence = 0.6

        return {"sentiment": sentiment, "confidence": round(confidence, 2)}

    def _mock_full(self, transcript: str) -> dict[str, Any]:
        """Combine all mock extractions into a full CRM record."""
        entities = self._mock_entities(transcript)
        intent = self._mock_intent(transcript)
        sentiment = self._mock_sentiment(transcript)

        # Build contacts with name and company
        contacts = []
        for i, name in enumerate(entities["people"]):
            company = entities["companies"][i] if i < len(entities["companies"]) else ""
            contacts.append({"name": name, "company": company})

        deals = []
        if entities["amounts"]:
            deals.append({
                "title": f"Potential deal with {entities['companies'][0] if entities['companies'] else 'prospect'}",
                "value": entities["amounts"][0].replace("$", "").replace(",", ""),
                "stage": "lead",
            })

        followups = []
        if intent["intent"] == "follow_up":
            followups.append({"title": "Follow up with prospect", "due_date": entities["dates"][0] if entities["dates"] else None})
        elif entities["dates"]:
            followups.append({"title": "Follow up on mentioned date", "due_date": entities["dates"][0]})

        buying_signals = []
        text_lower = transcript.lower()
        signal_keywords = ["budget", "ready to buy", "decision", "approve", "sign", "contract", "timeline"]
        for kw in signal_keywords:
            if kw in text_lower:
                buying_signals.append(kw)

        risks = []
        risk_keywords = ["competitor", "delay", "budget cut", "concern", "hesitation", "stall"]
        for kw in risk_keywords:
            if kw in text_lower:
                risks.append(kw)

        return {
            "contacts": contacts,
            "deals": deals,
            "followups": followups,
            "sentiment": sentiment["sentiment"],
            "buying_signals": buying_signals,
            "risks": risks,
            "intent": intent["intent"],
        }

    def _mock_insights(self, transcript: str) -> dict[str, Any]:
        """Generate proactive insights based on keywords."""
        text = transcript.lower()
        insights = []

        if "budget" in text:
            insights.append("Prospect mentioned budget — prioritize pricing discussion")
        if "competitor" in text:
            insights.append("Competitor mentioned — prepare competitive positioning")
        if "timeline" in text or "urgent" in text:
            insights.append("Time-sensitive opportunity — accelerate follow-up")
        if "demo" in text or "trial" in text:
            insights.append("Demo/trial interest — schedule product walkthrough")
        if "decision" in text or "approve" in text:
            insights.append("Decision-maker engaged — prepare proposal")
        if "concern" in text or "worried" in text:
            insights.append("Concerns raised — address objections proactively")

        if not insights:
            insights.append("General follow-up recommended to maintain engagement")

        priority = "high" if len(insights) >= 3 else "medium" if len(insights) >= 2 else "low"

        return {"insights": insights, "priority": priority}
