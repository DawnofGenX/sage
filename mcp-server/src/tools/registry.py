"""Central tool registry for Sage MCP server."""
from client.demo_flow import run_agentic_loop
from tools.extraction import extract_from_call, get_contact_context, get_pipeline_health
from tools.crud import (
    create_contact, update_contact, create_deal, update_deal_stage,
    schedule_followup, draft_followup_email, log_call,
)
from tools.intelligence import (
    get_deal_insights, get_daily_briefing, get_todays_followups,
    get_weekly_review, search_contacts,
)
from tools.sync import sync_to_crm
from tools.expansion import (
    get_company_context, get_activities, get_deal_history,
    create_task, enrich_contact, get_forecast,
)

ALL_TOOLS = [
    extract_from_call, get_contact_context, get_pipeline_health,
    create_contact, update_contact, create_deal, update_deal_stage,
    schedule_followup, draft_followup_email, log_call,
    get_deal_insights, get_daily_briefing, get_todays_followups,
    get_weekly_review, search_contacts,
    sync_to_crm,
    get_company_context, get_activities, get_deal_history,
    create_task, enrich_contact, get_forecast,
    run_agentic_loop,
]
