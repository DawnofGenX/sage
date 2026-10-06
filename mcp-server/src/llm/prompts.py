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

# Added 2026-06 for the two-pass pipeline.
#
# Before this, "entities" and "intent" both fell through to EXTRACTION_PROMPT,
# so pass 1 asked the model for a full CRM record twice — while the caller
# expected a small entity list and a bare intent label respectively. The two
# prompts below are the shapes the pipeline actually consumes.
ENTITIES_PROMPT = """You are a sales call analysis AI. From the following call transcript, extract ONLY the entities. Do not build a CRM record.

Return a JSON object with exactly these keys:
{{
  "people": ["full names of people mentioned"],
  "companies": ["company names mentioned"],
  "amounts": ["monetary amounts, as written in the transcript"],
  "dates": ["dates and deadlines mentioned, as written"]
}}

Transcript:
{transcript}
"""

INTENT_PROMPT = """You are a sales call analysis AI. Classify the intent of the following call transcript.

Choose exactly one of:
  new_lead     — a new prospect is being qualified for the first time
  follow_up    — an existing contact is being followed up on
  deal_update  — an existing deal's status is changing
  general      — none of the above

Return a JSON object with exactly these keys:
{{
  "intent": "one of new_lead | follow_up | deal_update | general",
  "confidence": 0.0
}}

Transcript:
{transcript}
"""

# Added 2026-06. draft_followup_email previously reused EXTRACTION_PROMPT with
# extraction_type="full", which asks the model to pull CRM records out of a
# call transcript — the wrong task entirely — and then discarded the response.
EMAIL_PROMPT = """You are a sales assistant writing a follow-up email.

Write a {tone} follow-up email to {contact} about: {context}

Return a JSON object with exactly these keys:
{{
  "subject": "a short subject line",
  "body": "the email body, as a plain string with line breaks",
  "tone_used": "{tone}"
}}

Write the email itself. Do not extract CRM records. Do not return commentary.
"""
