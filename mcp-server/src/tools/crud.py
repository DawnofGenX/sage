"""CRUD tools for Sage MCP server."""

from llm.provider import LLMProvider
from tools.common import _get_db
from tools.schemas import CreatedRecord, EmailDraft, UpdatedRecord

_provider = None


def _get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider


async def create_contact(
    name: str,
    company: str = None,
    email: str = None,
    phone: str = None,
    title: str = None,
    notes: str = None,
) -> CreatedRecord:
    """Create a new contact.

    Args:
        name: Contact name (required).
        company: Company name.
        email: Email address.
        phone: Phone number.
        title: Job title.
        notes: Additional notes.

    Returns:
        A dictionary with id, name, and created flag.
    """
    db = _get_db()
    data = {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "title": title,
        "notes": notes,
    }
    contact_id = db.create_contact(data)
    return {"id": contact_id, "name": name, "created": True}


async def update_contact(
    contact_id: int,
    name: str = None,
    company: str = None,
    email: str = None,
    phone: str = None,
    title: str = None,
    notes: str = None,
) -> UpdatedRecord:
    """Update an existing contact.

    Args:
        contact_id: The contact ID to update.
        name: Updated name.
        company: Updated company.
        email: Updated email.
        phone: Updated phone.
        title: Updated title.
        notes: Updated notes.

    Returns:
        The updated contact.
    """
    db = _get_db()
    updates = {k: v for k, v in {
        "name": name,
        "company": company,
        "email": email,
        "phone": phone,
        "title": title,
        "notes": notes,
    }.items() if v is not None}
    db.update_contact(contact_id, updates)
    contact = db.get_contact(contact_id)
    return contact


async def create_deal(
    contact_id: int,
    title: str,
    value: float = None,
    stage: str = "lead",
    notes: str = None,
) -> CreatedRecord:
    """Create a new deal.

    Args:
        contact_id: Associated contact ID.
        title: Deal title.
        value: Deal value in dollars.
        stage: Deal stage (lead, qualified, proposal, negotiation, won, lost).
        notes: Additional notes.

    Returns:
        A dictionary with id, title, and created flag.
    """
    db = _get_db()
    data = {
        "contact_id": contact_id,
        "title": title,
        "value": value,
        "stage": stage,
        "notes": notes,
    }
    deal_id = db.create_deal(data)
    return {"id": deal_id, "title": title, "created": True}


async def update_deal_stage(deal_id: int, stage: str) -> UpdatedRecord:
    """Update a deal's stage.

    Args:
        deal_id: The deal ID to update.
        stage: New stage value.

    Returns:
        The updated deal.
    """
    db = _get_db()
    db.update_deal_stage(deal_id, stage)
    deal = db.get_deal(deal_id)
    return deal


async def schedule_followup(
    contact_id: int,
    title: str,
    due_date: str | None = None,
    deal_id: int = None,
    notes: str = None,
) -> CreatedRecord:
    """Schedule a follow-up task.

    Args:
        contact_id: Associated contact ID.
        title: Follow-up title.
        due_date: Optional due date (ISO format string). A follow-up with no
            agreed date is normal -- many calls end without one -- so this is
            optional rather than required. It was previously a required str,
            which made the tool unusable for exactly the common case.
        deal_id: Optional associated deal ID.
        notes: Additional notes.

    Returns:
        A dictionary with id, title, and created flag.
    """
    db = _get_db()
    data = {
        "contact_id": contact_id,
        "deal_id": deal_id,
        "title": title,
        "due_date": due_date,
        "notes": notes,
    }
    followup_id = db.create_followup(data)
    return {"id": followup_id, "title": title, "created": True}


async def draft_followup_email(
    contact: str,
    context: str,
    tone: str = "formal",
) -> EmailDraft:
    """Draft a follow-up email using the LLM provider.

    The email body and subject come from the model. The template path exists
    only for mock mode, and the response says so via provenance.

    Args:
        contact: Contact name and context.
        context: Context for the email (deal info, previous conversations).
        tone: Email tone ('formal', 'friendly', 'casual').

    Returns:
        A dictionary with subject, body, tone_used, and provenance.
    """
    import json

    provider = _get_provider()

    # EMAIL_PROMPT is not transcript-shaped, so the fields travel as JSON in
    # the provider's transcript slot.
    request = json.dumps({"contact": contact, "context": context, "tone": tone})
    result = await provider.extract(request, "email")

    provenance = getattr(provider, "last_provenance", "mock")

    # Only accept a model-written email when the model actually produced one.
    # A real provider can still return something unexpected; fall back rather
    # than ship an empty subject.
    subject = result.get("subject") if isinstance(result, dict) else None
    body = result.get("body") if isinstance(result, dict) else None

    if provenance == "mock" or not subject or not body:
        subject = subject or f"Following up: {context[:50]}"
        body = body or (
            f"Dear {contact},\n\n"
            f"I wanted to follow up on our recent conversation. {context}\n\n"
            f"Looking forward to hearing from you.\n\n"
            f"Best regards"
        )
        return {
            "subject": subject,
            "body": body,
            "tone_used": tone,
            "provenance": provenance if provenance != "mock" else "mock",
            "templated": True,
        }

    return {
        "subject": subject,
        "body": body,
        "tone_used": result.get("tone_used", tone),
        "provenance": provenance,
        "templated": False,
    }


async def log_call(
    contact_id: int,
    transcript: str,
    summary: str = None,
    duration_seconds: int = None,
    deal_id: int = None,
) -> CreatedRecord:
    """Log a call record.

    Args:
        contact_id: Associated contact ID.
        transcript: Call transcript text.
        summary: Optional call summary.
        duration_seconds: Call duration in seconds.
        deal_id: Optional associated deal ID.

    Returns:
        A dictionary with id and created flag.
    """
    db = _get_db()
    data = {
        "contact_id": contact_id,
        "deal_id": deal_id,
        "transcript": transcript,
        "summary": summary,
        "duration_seconds": duration_seconds,
    }
    call_id = db.log_call(data)
    return {"id": call_id, "created": True}
