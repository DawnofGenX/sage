"""Shared mock extraction logic for LLM providers.

Provides regex/keyword-based mock responses used when no real LLM API
credentials are configured. Both LLMProvider and BedrockProvider inherit
from MockExtractionMixin to avoid duplicating this logic.
"""

import re
from typing import Any


class MockExtractionMixin:
    """Mixin providing mock extraction methods for LLM providers.

    Subclasses must implement ``_mock_email`` if they support email
    extraction; the default raises ``NotImplementedError``.
    """

    def _mock_extract(self, transcript: str, extraction_type: str) -> dict[str, Any]:
        """Return realistic mock data based on transcript content."""
        dispatch = {
            "entities": self._mock_entities,
            "intent": self._mock_intent,
            "sentiment": self._mock_sentiment,
            "full": self._mock_full,
            "insights": self._mock_insights,
            "email": self._mock_email,
        }
        handler = dispatch.get(extraction_type, self._mock_full)
        return handler(transcript)

    def _mock_email(self, transcript: str) -> dict[str, Any]:
        """Produce a template email for mock mode.

        Subclasses that support email extraction must override this method.
        """
        raise NotImplementedError("Email extraction not supported by this provider")

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
