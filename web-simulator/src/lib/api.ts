const API_BASE = '/api'

async function callTool(toolName: string, args: Record<string, unknown>) {
  const response = await fetch(`${API_BASE}/tools/${toolName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(args)
  })
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }
  return response.json()
}

export const api = {
  extractFromCall: (transcript: string) =>
    callTool('extract_from_call', { transcript }),

  getContactContext: (name: string) =>
    callTool('get_contact_context', { name }),

  getPipelineHealth: () =>
    callTool('get_pipeline_health', {}),

  getDailyBriefing: () =>
    callTool('get_daily_briefing', {}),

  getTodaysFollowups: () =>
    callTool('get_todays_followups', {}),

  getWeeklyReview: () =>
    callTool('get_weekly_review', {}),

  searchContacts: (query: string) =>
    callTool('search_contacts', { query }),

  createContact: (data: Record<string, unknown>) =>
    callTool('create_contact', data),

  createDeal: (data: Record<string, unknown>) =>
    callTool('create_deal', data),

  updateDealStage: (dealId: number, stage: string) =>
    callTool('update_deal_stage', { deal_id: dealId, stage }),

  scheduleFollowup: (data: Record<string, unknown>) =>
    callTool('schedule_followup', data),

  draftFollowupEmail: (contact: string, context: string, tone?: string) =>
    callTool('draft_followup_email', { contact, context, tone }),

  logCall: (data: Record<string, unknown>) =>
    callTool('log_call', data),

  getDealInsights: (dealId: number) =>
    callTool('get_deal_insights', { deal_id: dealId }),

  syncToCrm: (record: Record<string, unknown>, target: string, idempotencyKey: string) =>
    callTool('sync_to_crm', { record, target, idempotency_key: idempotencyKey }),
}
