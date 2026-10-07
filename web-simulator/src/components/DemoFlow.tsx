import { useState, useEffect, useCallback, useRef } from 'react'
import { api, runAgenticLoop, AgenticStep, AgenticComplete } from '../lib/api'

interface DemoFlowProps {
  onComplete: () => void
}

const SAMPLE_TRANSCRIPT = `John: Hi Sarah, this is John from Sage. How are you doing today?
Sarah: Hi John, I'm doing well! Thanks for calling. I've been meaning to reach out about the enterprise license.
John: That's great to hear! I wanted to follow up on our conversation last week. We've got 20 seats ready to go and the budget was approved. Can we schedule a demo for next Tuesday?
Sarah: Yes, I remember our conversation. The team is really excited about the enterprise features. Tuesday works great for us. How about 2 PM?
John: 2 PM works perfectly. I'll send over a calendar invite with the demo link. Is there anything specific you'd like me to prepare?
Sarah: Yes, could you include details about the API integrations? We're particularly interested in the Salesforce and Slack integrations.
John: Absolutely, I'll have that ready for you. Looking forward to Tuesday!
Sarah: Great, talk to you then.`

type DemoState = 'loading' | 'ready' | 'running' | 'complete' | 'error'

export default function DemoFlow({ onComplete }: DemoFlowProps) {
  const [state, setState] = useState<DemoState>('loading')
  const [toolCount, setToolCount] = useState(0)
  const [steps, setSteps] = useState<AgenticStep[]>([])
  const [complete, setComplete] = useState<AgenticComplete | null>(null)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.listTools()
      .then((result) => {
        const count = Array.isArray(result) ? result.length : (result.tools?.length ?? 0)
        setToolCount(count)
        setState('ready')
      })
      .catch(() => {
        setState('error')
        setError('Failed to load tools')
      })
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [steps, complete])

  const startDemo = useCallback(() => {
    setState('running')
    setSteps([])
    setComplete(null)
    setError(null)

    runAgenticLoop(SAMPLE_TRANSCRIPT, {
      onStep: (step) => {
        setSteps(prev => [...prev, step])
      },
      onComplete: (result) => {
        setComplete(result)
        setState('complete')
        onComplete()
      },
      onError: (err) => {
        setError(err.message)
        setState('error')
      },
    })
  }, [onComplete])

  const reset = useCallback(() => {
    setState('ready')
    setSteps([])
    setComplete(null)
    setError(null)
  }, [])

  if (state === 'loading') {
    return (
      <div className="px-6 py-8 text-center">
        <div className="w-6 h-6 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
        <p className="text-gray-400 text-sm">Loading tools...</p>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className="px-6 py-5">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
          <svg className="w-8 h-8 text-red-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <p className="text-red-400 font-medium text-sm">Backend unreachable — start the MCP server</p>
          {error && <p className="text-gray-400 text-xs mt-1">{error}</p>}
        </div>
        <button
          onClick={reset}
          className="w-full mt-4 px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          Try Again
        </button>
      </div>
    )
  }

  if (state === 'ready') {
    return (
      <div className="px-6 py-5">
        <div className="text-center py-6">
          <div className="w-16 h-16 rounded-xl bg-alexa-blue/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl font-bold text-alexa-blue">{toolCount}</span>
          </div>
          <p className="text-white font-semibold text-lg">tools available</p>
          <p className="text-gray-400 text-sm mt-1">Ready to run the agentic extraction chain</p>
        </div>
        <button
          onClick={startDemo}
          className="w-full flex items-center justify-center gap-2 px-5 py-2.5 bg-alexa-blue text-alexa-dark font-semibold rounded-lg hover:bg-alexa-blue/80 transition-colors text-sm"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Start Agentic Chain
        </button>
      </div>
    )
  }

  return (
    <div className="px-6 py-5">
      <div ref={scrollRef} className="space-y-2 max-h-80 overflow-y-auto scroll-smooth">
        {steps.map((step, i) => (
          <div key={i} className="bg-alexa-dark/30 rounded-lg p-3 border border-alexa-accent/20">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-white">{step.tool}</span>
              <span className="text-xs text-gray-500">{step.duration_ms}ms</span>
            </div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-block px-2 py-0.5 text-xs bg-alexa-blue/10 text-alexa-blue rounded">
                {step.provenance}
              </span>
            </div>
            <p className="text-xs text-gray-400">{step.summary}</p>
          </div>
        ))}
        {state === 'running' && (
          <div className="flex items-center gap-2 text-gray-500 py-2">
            <div className="w-4 h-4 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs">Running...</span>
          </div>
        )}
      </div>
      {complete && (
        <div className="mt-4 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm font-medium text-green-400">Complete</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Status: {complete.status}
            {complete.synced_record_id && ` · Record: ${complete.synced_record_id}`}
          </p>
        </div>
      )}
      {state === 'complete' && (
        <button
          onClick={reset}
          className="w-full mt-4 px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          Run Again
        </button>
      )}
    </div>
  )
}
