const API_BASE = import.meta.env.VITE_API_URL || '/api'

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

// ─── SSE types ───────────────────────────────────────────────────────────────

export interface AgenticStep {
  index: number
  tool: string
  duration_ms: number
  provenance: string
  summary: string
}

export interface AgenticComplete {
  status: string
  /** Number of steps that completed. NOT an array — the backend sends a count. */
  steps: number
  synced_record_id?: string
  reason?: string
}

export interface AgenticLoopHandlers {
  onStep: (step: AgenticStep) => void
  onComplete: (result: AgenticComplete) => void
  onError: (error: Error) => void
}

// ─── SSE client ─────────────────────────────────────────────────────────────

export async function runAgenticLoop(
  transcript: string,
  handlers: AgenticLoopHandlers,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}/stream/agentic_loop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript, target: 'local' }),
    })
  } catch (err) {
    handlers.onError(err instanceof Error ? err : new Error('Network error'))
    return
  }

  if (!response.ok) {
    handlers.onError(new Error(`API error: ${response.status} ${response.statusText}`))
    return
  }

  if (!response.body) {
    handlers.onError(new Error('No response body'))
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatchFrame = (eventType: string, dataLines: string[]) => {
    if (!eventType || dataLines.length === 0) return
    const data = dataLines.join('\n')
    try {
      const parsed = JSON.parse(data)
      if (eventType === 'step') {
        handlers.onStep(parsed)
      } else if (eventType === 'complete') {
        handlers.onComplete(parsed)
      } else if (eventType === 'error') {
        // The backend emits this when the chain fails mid-run. It used to be
        // dropped here — parsed, matched no branch, discarded — so the demo
        // just stopped with no message. See docs/sse-contract-bugs.md.
        handlers.onError(new Error(parsed.error ?? 'Agentic loop failed'))
      }
    } catch {
      // Ignore malformed JSON
    }
  }

  const processBuffer = (isFinal: boolean) => {
    const lines = buffer.split('\n')
    if (!isFinal) {
      buffer = lines.pop() || ''
    } else {
      buffer = ''
    }

    let eventType = ''
    let dataLines: string[] = []

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        dataLines.push(line.slice(6))
      } else if (line === '') {
        dispatchFrame(eventType, dataLines)
        eventType = ''
        dataLines = []
      }
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    processBuffer(false)
  }

  // Process any remaining buffer
  if (buffer.trim()) {
    processBuffer(true)
  }
}

// ─── API ─────────────────────────────────────────────────────────────────────

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

  listTools: () =>
    fetch(`${API_BASE}/tools`).then((r) => {
      if (!r.ok) throw new Error(`API error: ${r.statusText}`)
      return r.json()
    }),
}
