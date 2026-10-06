export interface Contact {
  id: number
  name: string
  company?: string
  email?: string
  phone?: string
  title?: string
  notes?: string
  created_at: string
}

export interface Deal {
  id: number
  contact_id: number
  title: string
  value?: number
  stage: string
  notes?: string
  sentiment?: string
  created_at: string
}

export interface Followup {
  id: number
  contact_id: number
  deal_id?: number
  title: string
  due_date?: string
  completed: boolean
  notes?: string
}

export interface CallLog {
  id: number
  contact_id: number
  deal_id?: number
  transcript: string
  summary?: string
  duration_seconds?: number
  sentiment?: string
  buying_signals?: string
  risks?: string
}

export interface ExtractionResult {
  step1_entities: {
    people: string[]
    companies: string[]
    amounts: number[]
    dates: string[]
  }
  step2_intent: string
  step3_record: {
    contacts: Partial<Contact>[]
    deals: Partial<Deal>[]
    followups: Partial<Followup>[]
    sentiment: string
    buying_signals: string[]
    risks: string[]
  }
  step4_validated: boolean
}

export interface PipelineHealth {
  deals_by_stage: Record<string, number>
  stuck_deals: Deal[]
  total_deals: number
  total_value: number
}

export interface DailyBriefing {
  followups_due: Followup[]
  total_deals: number
  pipeline_value: number
  stuck_deals: Deal[]
  insights: string[]
}

export interface DealInsights {
  deal: Deal
  sentiment_trend: string[]
  risks: string[]
  buying_signals: string[]
  recommendation: string
}

export interface ContactContext {
  contact: Contact
  deals: Deal[]
  history: Activity[]
}

export interface Activity {
  id: number
  contact_id: number
  deal_id?: number
  type: string
  description: string
  created_at: string
}
