"""Prompt templates for Sage LLM extraction."""

EXTRACTION_PROMPT = """You are a sales call analysis AI. Extract all CRM-relevant data from the following sales call transcript.

Return a JSON object with this exact structure:
{
  "contacts": [{"name": "...", "company": "...", "email": "...", "phone": "...", "title": "..."}],
  "deals": [{"title": "...", "value": 0, "stage": "lead|proposal|negotiation|closed_won|closed_lost", "notes": "..."}],
  "followups": [{"title": "...", "due_date": "YYYY-MM-DD or null"}],
  "sentiment": "positive|neutral|negative",
  "buying_signals": ["..."],
  "risks": ["..."],
  "competitor_mentions": ["..."],
  "intent": "new_lead|follow_up|deal_update|general"
}

Transcript:
{transcript}
"""

INSIGHTS_PROMPT = """You are a sales intelligence AI. Based on the following pipeline context, generate proactive insights.

Pipeline context:
{context}

Return a JSON object with:
{
  "insights": ["insight 1", "insight 2", ...],
  "urgency": "high|medium|low",
  "recommended_actions": ["action 1", "action 2", ...]
}
"""
