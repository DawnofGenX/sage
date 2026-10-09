import { useState, useCallback, useEffect, useRef } from 'react'
import VoiceInput from './components/VoiceInput'
import TranscriptView, { SAMPLE_CALLS } from './components/TranscriptView'
import ExtractionPipeline, { PipelineStep, StepStatus } from './components/ExtractionPipeline'
import ProactiveInsights, { Insight } from './components/ProactiveInsights'
import PipelineBoard, { BoardDeal } from './components/PipelineBoard'
import ContactCard from './components/ContactCard'
import DealCard from './components/DealCard'
import ReasoningTrace, { TraceStep } from './components/ReasoningTrace'
import CallSimulator from './components/CallSimulator'
import ContactDetail from './components/ContactDetail'
import DealDetail from './components/DealDetail'
import ForecastChart from './components/ForecastChart'
import ActivityFeed from './components/ActivityFeed'
import AlexaView from './components/AlexaView'
import DemoMode from './components/DemoMode'
import Hero from './components/Hero'
import { api, runAgenticLoop, getStats, AgenticStep } from './lib/api'
import type { Contact, Deal, Activity } from './lib/types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface ExtractionResult {
  step1_entities: {
    people: string[]
    companies: string[]
    amounts: number[]
    dates: string[]
  }
  step2_intent: string
  step3_record: {
    contacts: Array<{ name: string; company?: string; email?: string }>
    deals: Array<{ title: string; value?: number; stage?: string }>
    followups: Array<{ title: string; due_date?: string }>
    sentiment: string
    buying_signals: string[]
    risks: string[]
  }
  step4_derived: boolean
}

type TabId = 'dashboard' | 'calls' | 'contacts' | 'deals' | 'forecast' | 'activity' | 'scenarios' | 'alexa'

interface Scenario {
  id: number
  title: string
  description: string
  steps: string[]
  icon: string
}

// ─── Initial Data ────────────────────────────────────────────────────────────

const INITIAL_PIPELINE_STEPS: PipelineStep[] = [
  { id: 1, title: 'Entity Extraction', description: 'Extract people, companies, amounts, dates', status: 'pending' },
  { id: 2, title: 'Intent Classification', description: 'Classify call intent and purpose', status: 'pending' },
  { id: 3, title: 'Structured Record', description: 'Generate CRM records from transcript', status: 'pending' },
  { id: 4, title: 'Schema Validation', description: 'Validate and normalize extracted data', status: 'pending' },
]

const INITIAL_TRACE_STEPS: TraceStep[] = [
  { id: 1, title: 'Tokenize transcript', description: 'Split into sentences and tokens', status: 'pending' },
  { id: 2, title: 'NER extraction', description: 'Identify people, companies, amounts, dates', status: 'pending' },
  { id: 3, title: 'Intent classification', description: 'Determine call purpose and next actions', status: 'pending' },
  { id: 4, title: 'Record generation', description: 'Create structured CRM records', status: 'pending' },
  { id: 5, title: 'Schema validation', description: 'Validate against CRM schema', status: 'pending' },
  { id: 6, title: 'Deduplication', description: 'Check for existing records', status: 'pending' },
  { id: 7, title: 'Write to database', description: 'Persist extracted records', status: 'pending' },
]

const SAMPLE_CONTACTS: Contact[] = [
  { id: 1, name: 'Sarah Chen', company: 'Acme Corp', email: 'sarah@acme.com', phone: '+1-555-0100', title: 'VP of Engineering', notes: '', created_at: '2024-01-15' },
  { id: 2, name: 'Mike Johnson', company: 'Globex', email: 'mike@globex.com', phone: '+1-555-0101', title: 'CTO', notes: '', created_at: '2024-01-20' },
  { id: 3, name: 'Jennifer Williams', company: 'Initech', email: 'jennifer@initech.com', phone: '+1-555-0102', title: 'Head of Product', notes: '', created_at: '2024-02-01' },
  { id: 4, name: 'David Stark', company: 'Stark Industries', email: 'david@stark.com', phone: '+1-555-0103', title: 'CEO', notes: '', created_at: '2024-02-10' },
  { id: 5, name: 'Lisa Wayne', company: 'Wayne Enterprises', email: 'lisa@wayne.com', phone: '+1-555-0104', title: 'CFO', notes: '', created_at: '2024-02-15' },
]

const SAMPLE_ACTIVITIES: Activity[] = [
  { id: 1, contact_id: 1, deal_id: 1, type: 'call', description: 'Follow-up call about enterprise license', created_at: '2024-03-01T10:30:00Z' },
  { id: 2, contact_id: 1, deal_id: 1, type: 'email', description: 'Sent demo calendar invite', created_at: '2024-03-01T11:00:00Z' },
  { id: 3, contact_id: 2, deal_id: 2, type: 'meeting', description: 'Product demo with Globex team', created_at: '2024-02-28T14:00:00Z' },
  { id: 4, contact_id: 3, deal_id: 3, type: 'task', description: 'Prepare team features one-pager', created_at: '2024-02-27T09:00:00Z' },
  { id: 5, contact_id: 4, deal_id: 4, type: 'call', description: 'Kickoff call for Stark deployment', created_at: '2024-02-26T15:00:00Z' },
  { id: 6, contact_id: 5, deal_id: 5, type: 'email', description: 'Sent pricing information', created_at: '2024-02-25T16:00:00Z' },
  { id: 7, contact_id: 2, deal_id: 2, type: 'call', description: 'Negotiation call — 15% discount offered', created_at: '2024-02-24T11:00:00Z' },
  { id: 8, contact_id: 1, deal_id: 1, type: 'meeting', description: 'Executive demo with Sarah Chen', created_at: '2024-02-23T10:00:00Z' },
]

const DEMO_SCENARIOS: Scenario[] = [
  {
    id: 1,
    title: 'New Lead Call',
    description: 'Extract → Create Contact → Create Deal',
    steps: ['Start call simulation', 'End call & extract insights', 'Create contact from extraction', 'Create deal from extraction'],
    icon: 'M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z',
  },
  {
    id: 2,
    title: 'Follow-up Call',
    description: 'Extract → Update Deal Stage → Schedule Follow-up',
    steps: ['Start follow-up call', 'End call & extract', 'Update deal stage', 'Schedule follow-up task'],
    icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15',
  },
  {
    id: 3,
    title: 'Deal Update',
    description: 'Extract → Get Insights → Sync to CRM',
    steps: ['Start deal update call', 'End call & extract', 'Get deal insights', 'Sync to CRM'],
    icon: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    id: 4,
    title: 'Morning Briefing',
    description: 'Review Pipeline → Prioritize Follow-ups',
    steps: ['Review pipeline board', 'Check proactive insights', 'Review activity feed', 'Prioritize follow-ups'],
    icon: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  },
  {
    id: 5,
    title: 'Weekly Review',
    description: 'Analyze Performance → Forecast',
    steps: ['Review forecast chart', 'Analyze pipeline health', 'Review activity trends', 'Generate weekly report'],
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  },
]

// ─── Tab Configuration ──────────────────────────────────────────────────────

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
  { id: 'calls', label: 'Call Sim', icon: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z' },
  { id: 'contacts', label: 'Contacts', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' },
  { id: 'deals', label: 'Deals', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
  { id: 'forecast', label: 'Forecast', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  { id: 'activity', label: 'Activity', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
  { id: 'scenarios', label: 'Scenarios', icon: 'M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z' },
  { id: 'alexa', label: 'Alexa+', icon: 'M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z' },
]

// ─── App Component ───────────────────────────────────────────────────────────

export default function App() {
  // Navigation state
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')

  // Voice & transcript state
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [callStartTime, setCallStartTime] = useState<Date | null>(null)

  // Pipeline state
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(INITIAL_PIPELINE_STEPS)
  const [extractionResult, setExtractionResult] = useState<ExtractionResult | null>(null)

  // Trace state
  const [traceSteps, setTraceSteps] = useState<TraceStep[]>(INITIAL_TRACE_STEPS)
  const [showTrace, setShowTrace] = useState(false)

  // Insights state
  const [insights, setInsights] = useState<Insight[]>([])
  const [isGeneratingInsights, setIsGeneratingInsights] = useState(false)

  // Pipeline board state
  const [deals, setDeals] = useState<BoardDeal[]>([])
  const [dealsError, setDealsError] = useState<string | null>(null)
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncComplete, setSyncComplete] = useState(false)

  // Contacts state
  const [contacts, setContacts] = useState<Contact[]>(SAMPLE_CONTACTS)
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null)

  // Deals state
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null)

  // Activity state
  const [activities, setActivities] = useState<Activity[]>(SAMPLE_ACTIVITIES)

  // Scenario state
  const [activeScenario, setActiveScenario] = useState<Scenario | null>(null)
  const [scenarioStep, setScenarioStep] = useState(0)

  // Pipeline health & pre-populated data
  const [isLoadingHealth, setIsLoadingHealth] = useState(true)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [isLoadingInsights, setIsLoadingInsights] = useState(true)
  const [insightsError, setInsightsError] = useState<string | null>(null)

  // Hero stats — computed from the tool-call log, not hardcoded
  const [hoursSaved, setHoursSaved] = useState(0)
  const [manualEntries, setManualEntries] = useState(0)

  // Demo mode state
  const [showDemoMode, setShowDemoMode] = useState(false)
  const [demoToast, setDemoToast] = useState(false)

  // Sample dropdown
  const [showSampleDropdown, setShowSampleDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowSampleDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Listen for sample transcript events from TranscriptView
  useEffect(() => {
    function handleLoadSample(event: Event) {
      const customEvent = event as CustomEvent<{ index: number }>
      const index = customEvent.detail.index
      if (SAMPLE_CALLS[index]) {
        setTranscript(SAMPLE_CALLS[index].transcript)
        setCallStartTime(new Date())
      }
    }
    window.addEventListener('loadSampleTranscript', handleLoadSample)
    return () => window.removeEventListener('loadSampleTranscript', handleLoadSample)
  }, [])

  // Pre-populate dashboard on first load
  useEffect(() => {
    let cancelled = false

    async function loadDashboard() {
      // Load the real pipeline. The board used to seed from hardcoded
      // SAMPLE_DEALS and never call the API, so it showed five invented deals
      // while the CRM sat behind the same server. Start empty and fill from
      // get_deals; on failure the board shows the error rather than fake data.
      try {
        // Fetch stats in parallel with deals
        const [dealsResp, stats] = await Promise.all([
          api.getDeals(),
          getStats().catch(() => null),
        ])
        if (!cancelled && stats) {
          setHoursSaved(stats.hoursSaved)
          setManualEntries(stats.manualEntries)
        }
        if (!cancelled) {
          const live = (dealsResp.deals || []).map((d: Record<string, unknown>) => ({
            id: Number(d.id),
            title: String(d.title ?? ''),
            value: Number(d.value ?? 0),
            stage: String(d.stage ?? 'lead'),
            contactName: String(d.contact_name ?? ''),
            sentiment: (d.sentiment as string | null) ?? undefined,
            isStuck: Boolean(d.is_stuck),
            daysInactive: d.days_inactive == null ? undefined : Number(d.days_inactive),
          }))
          setDeals(live)
          setDealsError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setDealsError(
            err instanceof Error ? err.message : 'Failed to load deals from the API'
          )
        }
      }

      // Load pipeline health
      try {
        await api.getPipelineHealth()
        if (!cancelled) {
          setHealthError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setHealthError(err instanceof Error ? err.message : 'Failed to load pipeline health')
        }
      } finally {
        if (!cancelled) setIsLoadingHealth(false)
      }

      // Load daily briefing insights
      try {
        const briefing = await api.getDailyBriefing()
        if (!cancelled && briefing && Array.isArray(briefing.insights) && briefing.insights.length > 0) {
          setInsights(briefing.insights.map((ins: { text: string; urgency: string; timestamp?: string }, i: number) => ({
            id: `briefing-${i}`,
            text: ins.text,
            urgency: (ins.urgency as 'overdue' | 'stuck' | 'info') || 'info',
            timestamp: ins.timestamp,
          })))
          setInsightsError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setInsightsError(err instanceof Error ? err.message : 'Failed to load daily briefing')
        }
      } finally {
        if (!cancelled) setIsLoadingInsights(false)
      }
    }

    loadDashboard()
    return () => { cancelled = true }
  }, [])

  // ─── Handlers ─────────────────────────────────────────────────────────────

  const handleTranscript = useCallback((text: string) => {
    setTranscript(text)
    if (!callStartTime) {
      setCallStartTime(new Date())
    }
  }, [callStartTime])

  const handleListeningChange = useCallback((listening: boolean) => {
    setIsListening(listening)
    if (listening) {
      setCallStartTime(new Date())
    }
  }, [])

  const updatePipelineStep = useCallback((stepId: number, status: StepStatus, data?: Record<string, unknown>) => {
    setPipelineSteps(prev => prev.map(s =>
      s.id === stepId ? { ...s, status, data: data || s.data } : s
    ))
  }, [])

  const updateTraceStep = useCallback((stepId: number, status: TraceStep['status'], duration?: number) => {
    setTraceSteps(prev => prev.map(s =>
      s.id === stepId ? { ...s, status, duration: duration || s.duration } : s
    ))
  }, [])

  const runPipeline = useCallback(async () => {
    if (!transcript || isProcessing) return

    setIsProcessing(true)
    setShowTrace(true)
    setExtractionResult(null)
    setPipelineSteps(INITIAL_PIPELINE_STEPS)
    setTraceSteps(INITIAL_TRACE_STEPS)

    const accumulatedSteps: AgenticStep[] = []

    runAgenticLoop(transcript, {
      onStep: (step) => {
        accumulatedSteps.push(step)
        const pipelineStepId = Math.min(step.index + 1, 4)
        const traceStepId = Math.min(step.index + 1, 7)

        updatePipelineStep(pipelineStepId, 'complete', {
          tool: step.tool,
          summary: step.summary,
          duration_ms: step.duration_ms,
          provenance: step.provenance,
        })
        updateTraceStep(traceStepId, 'complete', step.duration_ms)
        setCurrentStep(pipelineStepId)
      },
      onComplete: (result) => {
        const extractionResult: ExtractionResult = {
          step1_entities: { people: [], companies: [], amounts: [], dates: [] },
          step2_intent: 'general',
          step3_record: { contacts: [], deals: [], followups: [], sentiment: 'neutral', buying_signals: [], risks: [] },
          step4_derived: result.status === 'success',
        }
        setExtractionResult(extractionResult)
        setCurrentStep(0)
        setIsProcessing(false)
      },
      onError: (err) => {
        setCurrentStep(0)
        setIsProcessing(false)
        setHealthError(err.message)
      },
    })
  }, [transcript, isProcessing, updatePipelineStep, updateTraceStep])

  const handleGenerateInsights = useCallback(async () => {
    setIsGeneratingInsights(true)
    try {
      const briefing = await api.getDailyBriefing()
      if (briefing && Array.isArray(briefing.insights) && briefing.insights.length > 0) {
        setInsights(briefing.insights.map((ins: { text: string; urgency: string; timestamp?: string }, i: number) => ({
          id: `briefing-${i}`,
          text: ins.text,
          urgency: (ins.urgency as 'overdue' | 'stuck' | 'info') || 'info',
          timestamp: ins.timestamp,
        })))
      }
    } catch (err) {
      setInsightsError(err instanceof Error ? err.message : 'Failed to load insights')
    } finally {
      setIsGeneratingInsights(false)
    }
  }, [])

  const handleSync = useCallback(async () => {
    setIsSyncing(true)
    setSyncComplete(false)
    await delay(2000)
    setIsSyncing(false)
    setSyncComplete(true)
    setTimeout(() => setSyncComplete(false), 3000)
  }, [])

  const handleLoadSample = useCallback((index: number) => {
    if (SAMPLE_CALLS[index]) {
      setTranscript(SAMPLE_CALLS[index].transcript)
      setCallStartTime(new Date())
      setShowSampleDropdown(false)
    }
  }, [])

  // Call simulator handler
  const handleCallEnd = useCallback((callTranscript: string, duration: number) => {
    setTranscript(callTranscript)
    setCallStartTime(new Date())
    // Add activity
    const newActivity: Activity = {
      id: activities.length + 1,
      contact_id: 1,
      deal_id: 1,
      type: 'call',
      description: `Call ended (${Math.floor(duration / 60)}m ${duration % 60}s) — transcript ready for extraction`,
      created_at: new Date().toISOString(),
    }
    setActivities(prev => [newActivity, ...prev])
  }, [activities.length])

  // Contact handlers
  const handleSelectContact = useCallback((contact: Contact) => {
    setSelectedContact(contact)
  }, [])

  const handleEnrichContact = useCallback((contactId: number) => {
    setContacts(prev => prev.map(c =>
      c.id === contactId ? { ...c, notes: (c.notes || '') + ' [Enriched]' } : c
    ))
  }, [])

  const handleCreateTask = useCallback((contactId: number, task: { title: string; due_date: string }) => {
    const newActivity: Activity = {
      id: activities.length + 1,
      contact_id: contactId,
      type: 'task',
      description: task.title,
      created_at: new Date().toISOString(),
    }
    setActivities(prev => [newActivity, ...prev])
  }, [activities.length])

  // Deal handlers
  const handleSelectDeal = useCallback((deal: Deal) => {
    setSelectedDeal(deal)
  }, [])

  const handleUpdateDealStage = useCallback((dealId: number, stage: string) => {
    setDeals(prev => prev.map(d =>
      d.id === dealId ? { ...d, stage } : d
    ))
    if (selectedDeal && selectedDeal.id === dealId) {
      setSelectedDeal(prev => prev ? { ...prev, stage } : null)
    }
  }, [selectedDeal])

  const handleGetDealInsights = useCallback((_dealId: number) => {
    // Insights are shown in DealDetail component
  }, [])

  // Scenario handlers
  const handleStartScenario = useCallback((scenario: Scenario) => {
    setActiveScenario(scenario)
    setScenarioStep(0)
    setActiveTab('scenarios')
  }, [])

  const handleNextScenarioStep = useCallback(() => {
    if (activeScenario && scenarioStep < activeScenario.steps.length - 1) {
      setScenarioStep(prev => prev + 1)
    }
  }, [activeScenario, scenarioStep])

  const handlePrevScenarioStep = useCallback(() => {
    if (scenarioStep > 0) {
      setScenarioStep(prev => prev - 1)
    }
  }, [scenarioStep])

  const handleEndScenario = useCallback(() => {
    setActiveScenario(null)
    setScenarioStep(0)
  }, [])

  const handleDemoComplete = useCallback(() => {
    setDemoToast(true)
    setTimeout(() => setDemoToast(false), 4000)
  }, [])

  // ─── Render Helpers ───────────────────────────────────────────────────────

  const renderTabButton = (tab: typeof TABS[0]) => (
    <button
      key={tab.id}
      onClick={() => setActiveTab(tab.id)}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
        activeTab === tab.id
          ? 'bg-alexa-blue/20 text-alexa-blue border border-alexa-blue/30'
          : 'text-gray-400 hover:text-white hover:bg-alexa-accent/30'
      }`}
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={tab.icon} />
      </svg>
      <span className="hidden sm:inline">{tab.label}</span>
    </button>
  )

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-alexa-dark text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-alexa-dark/95 backdrop-blur-sm border-b border-alexa-accent/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-alexa-blue/20 flex items-center justify-center">
                <svg className="w-6 h-6 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Sage</h1>
                <p className="text-xs text-gray-500">Your CRM that listens</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
              {/* Sample Call Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setShowSampleDropdown(!showSampleDropdown)}
                  className="flex items-center gap-2 px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 transition-colors text-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  Load Sample Call
                  <svg className={`w-3 h-3 transition-transform ${showSampleDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {showSampleDropdown && (
                  <div className="absolute right-0 mt-2 w-72 bg-alexa-card border border-alexa-accent/30 rounded-lg shadow-xl shadow-black/20 overflow-hidden">
                    {SAMPLE_CALLS.map((call, i) => (
                      <button
                        key={i}
                        onClick={() => handleLoadSample(i)}
                        className="w-full text-left px-4 py-3 text-sm text-gray-300 hover:bg-alexa-accent/30 transition-colors border-b border-alexa-accent/10 last:border-0"
                      >
                        <span className="font-medium text-white">{call.label}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Demo Mode Button */}
              <button
                onClick={() => setShowDemoMode(true)}
                className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 border border-purple-500/30 text-purple-400 font-medium rounded-lg hover:bg-purple-500/30 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Demo Mode
              </button>

              {/* Extract Insights Button */}
              <button
                onClick={runPipeline}
                disabled={!transcript || isProcessing}
                className="flex items-center gap-2 px-4 py-2 bg-alexa-blue text-alexa-dark font-semibold rounded-lg hover:bg-alexa-blue/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
              >
                {isProcessing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-alexa-dark border-t-transparent rounded-full animate-spin"></div>
                    Processing...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    Extract Insights
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="sticky top-16 z-40 bg-alexa-dark/95 backdrop-blur-sm border-b border-alexa-accent/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-1 py-2 overflow-x-auto">
            {TABS.map(renderTabButton)}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Hero Section */}
            <Hero hoursSaved={hoursSaved} manualEntries={manualEntries} />

            {/* Loading State */}
            {(isLoadingHealth || isLoadingInsights) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-6">
                  <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30 animate-pulse-slow">
                    <div className="h-4 bg-alexa-accent/30 rounded w-1/3 mb-4" />
                    <div className="space-y-3">
                      <div className="h-3 bg-alexa-accent/20 rounded w-full" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-5/6" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-4/6" />
                    </div>
                  </div>
                  <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30 animate-pulse-slow" style={{ animationDelay: '0.2s' }}>
                    <div className="h-4 bg-alexa-accent/30 rounded w-1/4 mb-4" />
                    <div className="space-y-3">
                      <div className="h-3 bg-alexa-accent/20 rounded w-full" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-3/4" />
                    </div>
                  </div>
                </div>
                <div className="space-y-6">
                  <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30 animate-pulse-slow" style={{ animationDelay: '0.1s' }}>
                    <div className="h-4 bg-alexa-accent/30 rounded w-1/3 mb-4" />
                    <div className="space-y-3">
                      <div className="h-3 bg-alexa-accent/20 rounded w-full" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-5/6" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-2/3" />
                    </div>
                  </div>
                  <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30 animate-pulse-slow" style={{ animationDelay: '0.3s' }}>
                    <div className="h-4 bg-alexa-accent/30 rounded w-1/4 mb-4" />
                    <div className="space-y-3">
                      <div className="h-3 bg-alexa-accent/20 rounded w-full" />
                      <div className="h-3 bg-alexa-accent/20 rounded w-4/6" />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Error State */}
            {(healthError || insightsError) && !isLoadingHealth && !isLoadingInsights && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-red-400">Some data failed to load</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {healthError && <span>Pipeline health: {healthError}</span>}
                      {healthError && insightsError && <span> · </span>}
                      {insightsError && <span>Insights: {insightsError}</span>}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Main Dashboard Content */}
            {!isLoadingHealth && !isLoadingInsights && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column */}
            <div className="space-y-6">
              <VoiceInput
                onTranscript={handleTranscript}
                isListening={isListening}
                onListeningChange={handleListeningChange}
              />
              <TranscriptView
                transcript={transcript}
                isListening={isListening}
                callStartTime={callStartTime}
              />
              <ExtractionPipeline
                isProcessing={isProcessing}
                currentStep={currentStep}
                steps={pipelineSteps}
                extractionResult={extractionResult}
              />
              <ReasoningTrace
                steps={traceSteps}
                isVisible={showTrace}
              />
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <ProactiveInsights
                insights={insights}
                isGenerating={isGeneratingInsights}
                onGenerate={handleGenerateInsights}
              />
              <PipelineBoard
                deals={deals}
                isSyncing={isSyncing}
                onSync={handleSync}
                loadError={dealsError}
              />

              {/* Sync Complete Toast */}
              {syncComplete && (
                <div className="fixed bottom-6 right-6 bg-green-500/20 border border-green-500/30 rounded-lg p-4 shadow-lg shadow-green-500/10 animate-slide-up">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center">
                      <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-green-400">Sync Complete</p>
                      <p className="text-xs text-gray-400">All records updated in CRM</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Contacts Section */}
              <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                  <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Recent Contacts
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {contacts.slice(0, 4).map((contact) => (
                    <div key={contact.id} onClick={() => handleSelectContact(contact)} className="cursor-pointer">
                      <ContactCard
                        contact={contact}
                        dealCount={Math.floor(Math.random() * 3) + 1}
                        recentActivity="Call 2h ago"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Deals Section */}
              <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
                  <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Active Deals
                </h3>
                <div className="space-y-3">
                  {deals.filter(d => !d.stage.startsWith('closed')).map((deal) => (
                    <div key={deal.id} onClick={() => handleSelectDeal({
                      id: deal.id,
                      contact_id: 0,
                      title: deal.title,
                      value: deal.value,
                      stage: deal.stage,
                      sentiment: deal.sentiment,
                      created_at: '2024-02-01',
                    })} className="cursor-pointer">
                      <DealCard
                        deal={{
                          id: deal.id,
                          contact_id: 0,
                          title: deal.title,
                          value: deal.value,
                          stage: deal.stage,
                          sentiment: deal.sentiment,
                          created_at: '2024-02-01',
                        }}
                        contactName={deal.contactName}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
        )}

        {/* Call Simulator Tab */}
        {activeTab === 'calls' && (
          <div className="max-w-3xl mx-auto">
            <CallSimulator onCallEnd={handleCallEnd} />
          </div>
        )}

        {/* Contacts Tab */}
        {activeTab === 'contacts' && (
          <div className="max-w-3xl mx-auto">
            {selectedContact ? (
              <ContactDetail
                contact={selectedContact}
                deals={deals.filter(d => d.contactName === selectedContact.name).map(d => ({
                  id: d.id,
                  contact_id: 0,
                  title: d.title,
                  value: d.value,
                  stage: d.stage,
                  sentiment: d.sentiment,
                  created_at: '2024-02-01',
                }))}
                activities={activities.filter(a => a.contact_id === selectedContact.id)}
                onEnrich={handleEnrichContact}
                onCreateTask={handleCreateTask}
                onBack={() => setSelectedContact(null)}
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {contacts.map(contact => (
                  <div key={contact.id} onClick={() => handleSelectContact(contact)} className="cursor-pointer">
                    <ContactCard
                      contact={contact}
                      dealCount={deals.filter(d => d.contactName === contact.name).length}
                      recentActivity="Recent activity"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Deals Tab */}
        {activeTab === 'deals' && (
          <div className="max-w-3xl mx-auto">
            {selectedDeal ? (
              <DealDetail
                deal={selectedDeal}
                activities={activities.filter(a => a.deal_id === selectedDeal.id)}
                onUpdateStage={handleUpdateDealStage}
                onGetInsights={handleGetDealInsights}
                onBack={() => setSelectedDeal(null)}
              />
            ) : (
              <div className="space-y-4">
                {deals.map(deal => (
                  <div key={deal.id} onClick={() => handleSelectDeal({
                    id: deal.id,
                    contact_id: 0,
                    title: deal.title,
                    value: deal.value,
                    stage: deal.stage,
                    sentiment: deal.sentiment,
                    created_at: '2024-02-01',
                  })} className="cursor-pointer">
                    <DealCard
                      deal={{
                        id: deal.id,
                        contact_id: 0,
                        title: deal.title,
                        value: deal.value,
                        stage: deal.stage,
                        sentiment: deal.sentiment,
                        created_at: '2024-02-01',
                      }}
                      contactName={deal.contactName}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Forecast Tab */}
        {activeTab === 'forecast' && (
          <div className="max-w-4xl mx-auto">
            <ForecastChart deals={deals.map(d => ({ stage: d.stage, value: d.value }))} />
          </div>
        )}

        {/* Activity Tab */}
        {activeTab === 'activity' && (
          <div className="max-w-3xl mx-auto">
            <ActivityFeed activities={activities} contacts={contacts} />
          </div>
        )}

        {/* Scenarios Tab */}
        {activeTab === 'scenarios' && (
          <div className="max-w-4xl mx-auto">
            {!activeScenario ? (
              <div>
                <h3 className="text-xl font-semibold text-white mb-6">Demo Scenarios</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {DEMO_SCENARIOS.map(scenario => (
                    <div
                      key={scenario.id}
                      className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30 hover:border-alexa-blue/30 transition-all cursor-pointer"
                      onClick={() => handleStartScenario(scenario)}
                    >
                      <div className="w-12 h-12 rounded-lg bg-alexa-blue/10 flex items-center justify-center mb-4">
                        <svg className="w-6 h-6 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={scenario.icon} />
                        </svg>
                      </div>
                      <h4 className="text-sm font-semibold text-white mb-1">{scenario.title}</h4>
                      <p className="text-xs text-gray-400 mb-3">{scenario.description}</p>
                      <div className="flex items-center gap-1">
                        {scenario.steps.map((_, i) => (
                          <div key={i} className="w-2 h-2 rounded-full bg-alexa-accent/50"></div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                {/* Scenario Header */}
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleEndScenario}
                      className="p-1.5 rounded-lg bg-alexa-accent/30 text-gray-400 hover:text-white hover:bg-alexa-accent/50 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                    <div>
                      <h3 className="text-xl font-semibold text-white">{activeScenario.title}</h3>
                      <p className="text-sm text-gray-400">{activeScenario.description}</p>
                    </div>
                  </div>
                  <span className="text-sm text-gray-500">
                    Step {scenarioStep + 1} of {activeScenario.steps.length}
                  </span>
                </div>

                {/* Progress Bar */}
                <div className="w-full h-2 bg-alexa-dark rounded-full overflow-hidden mb-6">
                  <div
                    className="h-full bg-alexa-blue rounded-full transition-all duration-300"
                    style={{ width: `${((scenarioStep + 1) / activeScenario.steps.length) * 100}%` }}
                  ></div>
                </div>

                {/* Steps */}
                <div className="space-y-3 mb-6">
                  {activeScenario.steps.map((step, i) => (
                    <div
                      key={i}
                      className={`flex items-center gap-3 p-4 rounded-lg border transition-all ${
                        i === scenarioStep
                          ? 'bg-alexa-blue/10 border-alexa-blue/30'
                          : i < scenarioStep
                          ? 'bg-green-500/5 border-green-500/20'
                          : 'bg-alexa-dark/30 border-alexa-accent/20'
                      }`}
                    >
                      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                        i === scenarioStep
                          ? 'bg-alexa-blue/20 text-alexa-blue'
                          : i < scenarioStep
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-600/20 text-gray-500'
                      }`}>
                        {i < scenarioStep ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <span className="text-sm font-medium">{i + 1}</span>
                        )}
                      </div>
                      <span className={`text-sm ${
                        i === scenarioStep ? 'text-white font-medium' :
                        i < scenarioStep ? 'text-gray-400' : 'text-gray-500'
                      }`}>
                        {step}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Navigation */}
                <div className="flex items-center justify-between">
                  <button
                    onClick={handlePrevScenarioStep}
                    disabled={scenarioStep === 0}
                    className="flex items-center gap-2 px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 transition-colors text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Previous
                  </button>
                  {scenarioStep < activeScenario.steps.length - 1 ? (
                    <button
                      onClick={handleNextScenarioStep}
                      className="flex items-center gap-2 px-4 py-2 bg-alexa-blue text-alexa-dark font-medium rounded-lg hover:bg-alexa-blue/80 transition-colors text-sm"
                    >
                      Next Step
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  ) : (
                    <button
                      onClick={handleEndScenario}
                      className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500/30 text-green-400 font-medium rounded-lg hover:bg-green-500/30 transition-colors text-sm"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Complete Scenario
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Alexa+ Tab */}
        {activeTab === 'alexa' && (
          <AlexaView />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-alexa-accent/20 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-600">Sage — Passive Sales Intelligence</p>
            <p className="text-xs text-gray-600">Simulator v1.1</p>
          </div>
        </div>
      </footer>

      {/* Demo Mode Modal */}
      <DemoMode
        isOpen={showDemoMode}
        onClose={() => setShowDemoMode(false)}
        onComplete={handleDemoComplete}
      />

      {/* Demo Complete Toast */}
      {demoToast && (
        <div className="fixed bottom-6 right-6 bg-purple-500/20 border border-purple-500/30 rounded-lg p-4 shadow-lg shadow-purple-500/10 animate-slide-up z-[200]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-purple-400">Demo Complete</p>
              <p className="text-xs text-gray-400">Full sales intelligence flow finished</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Utilities ───────────────────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}
