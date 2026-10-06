"""Amazon Bedrock LLM provider with mock fallback.

Wraps the Amazon Bedrock API for LLM calls, supporting Nova and Claude models.
Falls back to mock mode when AWS credentials are not available.

Integration Pattern:
    1. Set AWS credentials via environment variables or IAM role
    2. Instantiate BedrockProvider with optional region/model overrides
    3. Call invoke_model() for raw LLM calls or extract() for structured extraction
    4. If credentials are missing, falls back to keyword-based mock responses

Environment Variables:
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-1)
    BEDROCK_MODEL_ID: Override model ID
"""

import json
import os
import re
from typing import Any


class BedrockProvider:
    """Amazon Bedrock provider for LLM-powered sales intelligence.

    Supports Nova and Claude model families. Falls back to mock mode
    when AWS credentials are not configured.
    """

    # Supported model families
    DEFAULT_MODEL = "amazon.nova-lite-v1:0"
    SUPPORTED_MODELS = {
        "nova-lite": "amazon.nova-lite-v1:0",
        "nova-pro": "amazon.nova-pro-v1:0",
        "nova-micro": "amazon.nova-micro-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    }

    def __init__(
        self,
        region: str | None = None,
        model_id: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
    ):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", self.DEFAULT_MODEL)
        self.aws_access_key = aws_access_key or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = aws_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY")
        self._use_mock = not (self.aws_access_key and self.aws_secret_key)
        self._client = None

    @property
    def is_mock(self) -> bool:
        """Return True if running in mock mode (no AWS credentials)."""
        return self._use_mock

    def _get_client(self):
        """Lazy-initialize the Bedrock runtime client."""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                )
            except ImportError:
                raise RuntimeError(
                    "boto3 is required for Bedrock integration. "
                    "Install with: pip install boto3"
                )
        return self._client

    async def invoke_model(self, prompt: str, model_id: str | None = None) -> str:
        """Invoke a Bedrock model with the given prompt.

        Args:
            prompt: The text prompt to send to the model.
            model_id: Optional model override. Uses instance default if not set.

        Returns:
            The model's text response.
        """
        model = model_id or self.model_id

        if self._use_mock:
            return self._mock_invoke(prompt)

        client = self._get_client()

        # Determine model family and format request accordingly
        if model.startswith("amazon.nova"):
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxNewTokens": 1024, "temperature": 0.2},
            })
        elif model.startswith("anthropic.claude"):
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.2,
                "messages": [{"role": "user", "content": prompt}],
            })
        else:
            # Generic Nova-style format
            body = json.dumps({
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxNewTokens": 1024, "temperature": 0.2},
            })

        response = client.invoke_model(
            modelId=model,
            body=body,
            accept="application/json",
            contentType="application/json",
        )

        response_body = json.loads(response["body"].read())

        # Parse response based on model family
        if "output" in response_body:
            # Nova response format
            return response_body["output"]["message"]["content"][0]["text"]
        elif "content" in response_body:
            # Claude response format
            return response_body["content"][0]["text"]
        else:
            return str(response_body)

    async def extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Extract structured data from a sales transcript using Bedrock.

        Args:
            transcript: The call transcript text.
            extraction_type: One of 'entities', 'intent', 'sentiment', 'full', 'insights'.

        Returns:
            A dictionary with the extracted data.
        """
        if self._use_mock:
            return self._mock_extract(transcript, extraction_type)

        prompt = self._build_prompt(transcript, extraction_type)
        response_text = await self.invoke_model(prompt)

        try:
            return json.loads(response_text)
        except (json.JSONDecodeError, TypeError):
            return {"raw": response_text}

    def _build_prompt(self, transcript: str, extraction_type: str) -> str:
        """Build the extraction prompt for a given type."""
        prompts = {
            "entities": (
                "Extract all people names, company names, dollar amounts, and dates "
                "from this sales call transcript. Return JSON with keys: people, "
                "companies, amounts, dates.\n\nTranscript:\n"
            ),
            "intent": (
                "Classify the sales intent from this transcript. Return JSON with "
                "keys: intent (one of: follow_up, demo_request, pricing_inquiry, "
                "support, closing, general), confidence (0-1).\n\nTranscript:\n"
            ),
            "sentiment": (
                "Analyze the sentiment of this sales call. Return JSON with keys: "
                "sentiment (positive/negative/neutral), confidence (0-1).\n\nTranscript:\n"
            ),
            "full": (
                "Extract all CRM-relevant data from this sales call transcript. "
                "Return JSON with keys: contacts, deals, followups, sentiment, "
                "buying_signals, risks.\n\nTranscript:\n"
            ),
            "insights": (
                "Generate proactive sales insights from this transcript. Return JSON "
                "with keys: insights (list of strings), priority (high/medium/low)."
                "\n\nTranscript:\n"
            ),
        }
        base = prompts.get(extraction_type, prompts["full"])
        return base + transcript

    # ------------------------------------------------------------------
    # Mock mode (fallback when no AWS credentials)
    # ------------------------------------------------------------------

    def _mock_invoke(self, prompt: str) -> str:
        """Return a mock response based on prompt content."""
        prompt_lower = prompt.lower()

        if "sentiment" in prompt_lower:
            return json.dumps({"sentiment": "positive", "confidence": 0.85})
        elif "intent" in prompt_lower:
            return json.dumps({"intent": "follow_up", "confidence": 0.75})
        elif "entities" in prompt_lower:
            return json.dumps({
                "people": ["John Smith", "Sarah Johnson"],
                "companies": ["Acme Corp", "Globex Inc"],
                "amounts": ["$50,000"],
                "dates": ["January 15th"],
            })
        elif "insights" in prompt_lower:
            return json.dumps({
                "insights": ["Follow up on budget discussion"],
                "priority": "medium",
            })
        else:
            return json.dumps({
                "contacts": [{"name": "Prospect"}],
                "deals": [],
                "followups": [],
                "sentiment": {"sentiment": "neutral", "confidence": 0.6},
                "buying_signals": [],
                "risks": [],
            })

    def _mock_extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Keyword-based mock extraction (same pattern as LLMProvider)."""
        if extraction_type == "entities":
            return self._mock_entities(transcript)
        elif extraction_type == "intent":
            return self._mock_intent(transcript)
        elif extraction_type == "sentiment":
            return self._mock_sentiment(transcript)
        elif extraction_type == "insights":
            return self._mock_insights(transcript)
        else:
            return self._mock_full(transcript)

    def _mock_entities(self, transcript: str) -> dict[str, Any]:
        """Extract entities using regex/keyword matching."""
        people = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", transcript)
        companies = re.findall(r"\b([A-Z][a-z]+ (?:Corp|Inc|Ltd|LLC|Company))\b", transcript)
        amounts = re.findall(r"\$[\d,]+(?:\.\d{2})?", transcript)
        dates = re.findall(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\b", transcript)

        return {
            "people": list(set(people)),
            "companies": list(set(companies)),
            "amounts": amounts,
            "dates": dates,
        }

    def _mock_intent(self, transcript: str) -> dict[str, Any]:
        """Classify intent using keyword matching."""
        text = transcript.lower()
        intents = {
            "follow_up": ["follow up", "follow-up", "check back", "reconnect"],
            "demo_request": ["demo", "walkthrough", "show me", "trial"],
            "pricing_inquiry": ["price", "pricing", "cost", "budget", "quote"],
            "support": ["issue", "problem", "help", "support", "broken"],
            "closing": ["sign", "contract", "approve", "buy", "purchase"],
        }

        best_intent = "general"
        best_score = 0
        for intent, keywords in intents.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_intent = intent

        confidence = min(0.5 + best_score * 0.15, 0.95)
        return {"intent": best_intent, "confidence": round(confidence, 2)}

    def _mock_sentiment(self, transcript: str) -> dict[str, Any]:
        """Analyze sentiment using keyword counting."""
        text = transcript.lower()
        positive_keywords = ["excited", "interested", "ready", "great", "love", "happy", "excellent"]
        negative_keywords = ["concerned", "worried", "problem", "issue", "delay", "cut", "expensive"]

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

        contacts = [{"name": name} for name in entities["people"]]
        deals = []
        if entities["amounts"]:
            deals.append({
                "title": f"Potential deal with {entities['companies'][0] if entities['companies'] else 'prospect'}",
                "value": entities["amounts"][0].replace("$", "").replace(",", ""),
                "stage": "lead",
            })

        followups = []
        if intent["intent"] == "follow_up":
            followups.append({
                "title": "Follow up with prospect",
                "due_date": entities["dates"][0] if entities["dates"] else None,
            })

        buying_signals = []
        signal_keywords = ["budget", "ready to buy", "decision", "approve", "sign", "contract", "timeline"]
        for kw in signal_keywords:
            if kw in transcript.lower():
                buying_signals.append(kw)

        risks = []
        risk_keywords = ["competitor", "delay", "budget cut", "concern", "hesitation", "stall"]
        for kw in risk_keywords:
            if kw in transcript.lower():
                risks.append(kw)

        return {
            "contacts": contacts,
            "deals": deals,
            "followups": followups,
            "sentiment": sentiment,
            "buying_signals": buying_signals,
            "risks": risks,
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
