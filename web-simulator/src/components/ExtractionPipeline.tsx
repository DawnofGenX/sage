import { useEffect, useState } from 'react'

export type StepStatus = 'pending' | 'running' | 'complete'

export interface PipelineStep {
  id: number
  title: string
  description: string
  status: StepStatus
  data?: Record<string, unknown>
}

interface ExtractionPipelineProps {
  isProcessing: boolean
  currentStep: number
  steps: PipelineStep[]
  extractionResult: {
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
    step4_validated: boolean
  } | null
}

const STEP_ICONS = [
  // Entity extraction
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
  </svg>,
  // Intent classification
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>,
  // Structured record
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
  </svg>,
  // Schema validation
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>,
]

function StatusIndicator({ status }: { status: StepStatus }) {
  if (status === 'running') {
    return (
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs text-alexa-blue font-medium">Processing...</span>
      </div>
    )
  }
  if (status === 'complete') {
    return (
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 bg-green-500/20 rounded-full flex items-center justify-center">
          <svg className="w-3 h-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <span className="text-xs text-green-400 font-medium">Complete</span>
      </div>
    )
  }
  return (
    <div className="flex items-center gap-2">
      <div className="w-5 h-5 bg-gray-600/30 rounded-full flex items-center justify-center">
        <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
      </div>
      <span className="text-xs text-gray-500 font-medium">Pending</span>
    </div>
  )
}

function StepData({ step, extractionResult }: { step: PipelineStep; extractionResult: ExtractionPipelineProps['extractionResult'] }) {
  if (step.status !== 'complete' || !extractionResult) return null

  if (step.id === 1) {
    const entities = extractionResult.step1_entities
    return (
      <div className="mt-3 grid grid-cols-2 gap-2">
        {entities.people.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">People</p>
            {entities.people.map((p, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-alexa-blue/10 text-alexa-blue rounded mr-1 mb-1">{p}</span>
            ))}
          </div>
        )}
        {entities.companies.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Companies</p>
            {entities.companies.map((c, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-purple-500/10 text-purple-400 rounded mr-1 mb-1">{c}</span>
            ))}
          </div>
        )}
        {entities.amounts.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Amounts</p>
            {entities.amounts.map((a, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded mr-1 mb-1">${a.toLocaleString()}</span>
            ))}
          </div>
        )}
        {entities.dates.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Dates</p>
            {entities.dates.map((d, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-yellow-500/10 text-yellow-400 rounded mr-1 mb-1">{d}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (step.id === 2) {
    const intent = extractionResult.step2_intent
    const intentColors: Record<string, string> = {
      new_lead: 'bg-green-500/10 text-green-400',
      follow_up: 'bg-blue-500/10 text-blue-400',
      deal_update: 'bg-purple-500/10 text-purple-400',
      general: 'bg-gray-500/10 text-gray-400',
    }
    return (
      <div className="mt-3">
        <span className={`inline-block px-3 py-1 text-xs font-medium rounded-full ${intentColors[intent] || intentColors.general}`}>
          {intent.replace('_', ' ').toUpperCase()}
        </span>
      </div>
    )
  }

  if (step.id === 3) {
    const record = extractionResult.step3_record
    return (
      <div className="mt-3 space-y-2">
        {record.contacts.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Contacts ({record.contacts.length})</p>
            {record.contacts.map((c, i) => (
              <p key={i} className="text-xs text-gray-300">{c.name}{c.company ? ` — ${c.company}` : ''}</p>
            ))}
          </div>
        )}
        {record.deals.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Deals ({record.deals.length})</p>
            {record.deals.map((d, i) => (
              <p key={i} className="text-xs text-gray-300">{d.title}{d.value ? ` — $${d.value.toLocaleString()}` : ''}</p>
            ))}
          </div>
        )}
        {record.followups.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Follow-ups ({record.followups.length})</p>
            {record.followups.map((f, i) => (
              <p key={i} className="text-xs text-gray-300">{f.title}{f.due_date ? ` — ${f.due_date}` : ''}</p>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sentiment:</span>
          <span className={`text-xs font-medium ${
            record.sentiment === 'positive' ? 'text-green-400' :
            record.sentiment === 'negative' ? 'text-red-400' : 'text-gray-400'
          }`}>
            {record.sentiment}
          </span>
        </div>
        {record.buying_signals.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Buying Signals</p>
            {record.buying_signals.map((s, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-green-500/10 text-green-400 rounded mr-1 mb-1">{s}</span>
            ))}
          </div>
        )}
        {record.risks.length > 0 && (
          <div className="bg-alexa-dark/30 rounded p-2">
            <p className="text-xs text-gray-500 mb-1">Risks</p>
            {record.risks.map((r, i) => (
              <span key={i} className="inline-block px-2 py-0.5 text-xs bg-red-500/10 text-red-400 rounded mr-1 mb-1">{r}</span>
            ))}
          </div>
        )}
      </div>
    )
  }

  if (step.id === 4) {
    return (
      <div className="mt-3">
        <div className={`flex items-center gap-2 p-2 rounded ${extractionResult.step4_validated ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
          <svg className={`w-4 h-4 ${extractionResult.step4_validated ? 'text-green-400' : 'text-red-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {extractionResult.step4_validated ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            )}
          </svg>
          <span className={`text-xs font-medium ${extractionResult.step4_validated ? 'text-green-400' : 'text-red-400'}`}>
            {extractionResult.step4_validated ? 'Schema Valid' : 'Validation Failed'}
          </span>
        </div>
      </div>
    )
  }

  return null
}

export default function ExtractionPipeline({ isProcessing, currentStep, steps, extractionResult }: ExtractionPipelineProps) {
  const [animatingStep, setAnimatingStep] = useState<number | null>(null)

  useEffect(() => {
    if (isProcessing && currentStep > 0) {
      setAnimatingStep(currentStep)
      const timer = setTimeout(() => setAnimatingStep(null), 600)
      return () => clearTimeout(timer)
    }
  }, [currentStep, isProcessing])

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Extraction Pipeline
        </h3>
        {isProcessing && (
          <span className="text-xs text-alexa-blue animate-pulse">Processing...</span>
        )}
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div
            key={step.id}
            className={`relative bg-alexa-dark/30 rounded-lg p-4 border transition-all duration-500 ${
              step.status === 'running'
                ? 'border-alexa-blue/50 shadow-lg shadow-alexa-blue/10'
                : step.status === 'complete'
                ? 'border-green-500/30'
                : 'border-alexa-accent/20'
            } ${animatingStep === step.id ? 'scale-[1.02]' : ''}`}
          >
            {/* Connector line */}
            {index < steps.length - 1 && (
              <div className="absolute left-7 top-full w-0.5 h-3 bg-alexa-accent/20"></div>
            )}

            <div className="flex items-start gap-3">
              {/* Step icon */}
              <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                step.status === 'running'
                  ? 'bg-alexa-blue/20 text-alexa-blue'
                  : step.status === 'complete'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-600/20 text-gray-500'
              }`}>
                {STEP_ICONS[index]}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">
                      Step {step.id}: {step.title}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
                  </div>
                  <StatusIndicator status={step.status} />
                </div>

                {/* Step data */}
                <StepData step={step} extractionResult={extractionResult} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
