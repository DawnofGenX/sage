import { useState } from 'react'

export type TraceStatus = 'pending' | 'running' | 'complete' | 'error'

export interface TraceStep {
  id: number
  title: string
  description: string
  status: TraceStatus
  details?: string
  duration?: number
}

interface ReasoningTraceProps {
  steps: TraceStep[]
  isVisible: boolean
}

function StatusIcon({ status }: { status: TraceStatus }) {
  switch (status) {
    case 'running':
      return (
        <div className="w-4 h-4 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
      )
    case 'complete':
      return (
        <div className="w-4 h-4 bg-green-500/20 rounded-full flex items-center justify-center">
          <svg className="w-2.5 h-2.5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )
    case 'error':
      return (
        <div className="w-4 h-4 bg-red-500/20 rounded-full flex items-center justify-center">
          <svg className="w-2.5 h-2.5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      )
    default:
      return (
        <div className="w-4 h-4 bg-gray-600/30 rounded-full flex items-center justify-center">
          <div className="w-1.5 h-1.5 bg-gray-500 rounded-full"></div>
        </div>
      )
  }
}

export default function ReasoningTrace({ steps, isVisible }: ReasoningTraceProps) {
  const [expandedStep, setExpandedStep] = useState<number | null>(null)
  const [showTerminal, setShowTerminal] = useState(false)

  if (!isVisible) return null

  const completedSteps = steps.filter(s => s.status === 'complete').length
  const totalDuration = steps.reduce((sum, s) => sum + (s.duration || 0), 0)

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          Reasoning Trace
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500">
            {completedSteps}/{steps.length} steps
          </span>
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className={`px-2 py-1 text-xs rounded transition-colors ${
              showTerminal ? 'bg-alexa-blue/20 text-alexa-blue' : 'bg-alexa-accent/20 text-gray-400 hover:text-gray-300'
            }`}
          >
            Terminal
          </button>
        </div>
      </div>

      {showTerminal ? (
        /* Terminal View */
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs max-h-64 overflow-y-auto">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-700">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="ml-2 text-gray-500">sage-pipeline</span>
          </div>
          <div className="space-y-1">
            <p className="text-gray-500">$ sage extract --pipeline</p>
            {steps.map((step) => (
              <div key={step.id} className="flex items-start gap-2">
                <span className="text-gray-600">[{String(step.id).padStart(2, '0')}]</span>
                <span className={
                  step.status === 'complete' ? 'text-green-400' :
                  step.status === 'running' ? 'text-alexa-blue' :
                  step.status === 'error' ? 'text-red-400' : 'text-gray-500'
                }>
                  {step.status === 'complete' ? '✓' : step.status === 'running' ? '⟳' : step.status === 'error' ? '✗' : '○'}
                </span>
                <span className="text-gray-300">{step.title}</span>
                {step.duration && (
                  <span className="text-gray-600 ml-auto">{step.duration}ms</span>
                )}
              </div>
            ))}
            {completedSteps === steps.length && (
              <>
                <p className="text-gray-500 mt-2">─────────────────────────</p>
                <p className="text-green-400">Pipeline complete in {totalDuration}ms</p>
                <p className="text-gray-500">$ <span className="animate-pulse">▊</span></p>
              </>
            )}
          </div>
        </div>
      ) : (
        /* Step View */
        <div className="space-y-2">
          {steps.map((step) => (
            <div
              key={step.id}
              className={`bg-alexa-dark/30 rounded-lg border transition-all ${
                step.status === 'running' ? 'border-alexa-blue/50' :
                step.status === 'complete' ? 'border-green-500/20' :
                'border-alexa-accent/10'
              }`}
            >
              <button
                onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                className="w-full flex items-center gap-3 p-3 text-left"
              >
                <StatusIcon status={step.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium">{step.title}</p>
                  <p className="text-xs text-gray-500 truncate">{step.description}</p>
                </div>
                {step.duration && (
                  <span className="text-xs text-gray-600 font-mono">{step.duration}ms</span>
                )}
                <svg
                  className={`w-4 h-4 text-gray-500 transition-transform ${expandedStep === step.id ? 'rotate-180' : ''}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {expandedStep === step.id && step.details && (
                <div className="px-3 pb-3 pt-1 border-t border-alexa-accent/10">
                  <pre className="text-xs text-gray-400 font-mono whitespace-pre-wrap bg-alexa-dark/50 rounded p-2">
                    {step.details}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
