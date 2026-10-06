import { useState, useEffect, useCallback, useRef } from 'react'

export type DemoStepStatus = 'pending' | 'running' | 'complete'

export interface DemoStep {
  id: number
  title: string
  description: string
  duration: number // milliseconds
  status: DemoStepStatus
}

interface DemoModeProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

const INITIAL_DEMO_STEPS: DemoStep[] = [
  { id: 1, title: 'Call in progress...', description: 'Simulating a sales call with a prospect', duration: 5000, status: 'pending' },
  { id: 2, title: 'Extracting insights...', description: 'Running NLP pipeline on transcript', duration: 3000, status: 'pending' },
  { id: 3, title: 'Generating proactive insights...', description: 'Analyzing patterns and generating recommendations', duration: 2000, status: 'pending' },
  { id: 4, title: 'Syncing to CRM...', description: 'Pushing records to Salesforce', duration: 2000, status: 'pending' },
  { id: 5, title: 'Demo complete!', description: 'All systems operational', duration: 1000, status: 'pending' },
]

function DemoStatusIndicator({ status }: { status: DemoStepStatus }) {
  if (status === 'running') {
    return (
      <div className="flex items-center gap-2">
        <div className="w-5 h-5 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs text-alexa-blue font-medium">Running...</span>
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
        <span className="text-xs text-green-400 font-medium">Done</span>
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

export default function DemoMode({ isOpen, onClose, onComplete }: DemoModeProps) {
  const [steps, setSteps] = useState<DemoStep[]>(INITIAL_DEMO_STEPS)
  const [isRunning, setIsRunning] = useState(false)
  const [currentStepIndex, setCurrentStepIndex] = useState(-1)
  const [hasStarted, setHasStarted] = useState(false)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearAllTimers = useCallback(() => {
    timersRef.current.forEach(timer => clearTimeout(timer))
    timersRef.current = []
  }, [])

  const resetDemo = useCallback(() => {
    clearAllTimers()
    setSteps(INITIAL_DEMO_STEPS.map(s => ({ ...s, status: 'pending' as DemoStepStatus })))
    setIsRunning(false)
    setCurrentStepIndex(-1)
    setHasStarted(false)
  }, [clearAllTimers])

  const startDemo = useCallback(() => {
    setHasStarted(true)
    setIsRunning(true)
    setCurrentStepIndex(0)
    setSteps(prev => prev.map((s, i) => ({
      ...s,
      status: i === 0 ? 'running' : 'pending',
    })))

    let cumulativeDelay = 0
    INITIAL_DEMO_STEPS.forEach((step, index) => {
      // Start this step
      const startTimer = setTimeout(() => {
        setSteps(prev => prev.map((s, i) => ({
          ...s,
          status: i === index ? 'running' : s.status,
        })))
        setCurrentStepIndex(index)
      }, cumulativeDelay)
      timersRef.current.push(startTimer)

      cumulativeDelay += step.duration

      // Complete this step
      const completeTimer = setTimeout(() => {
        setSteps(prev => prev.map((s, i) => ({
          ...s,
          status: i === index ? 'complete' : s.status,
        })))
      }, cumulativeDelay)
      timersRef.current.push(completeTimer)
    })

    // Finish
    const finishTimer = setTimeout(() => {
      setIsRunning(false)
      onComplete()
    }, cumulativeDelay)
    timersRef.current.push(finishTimer)
  }, [onComplete])

  // Cleanup on unmount
  useEffect(() => {
    return () => clearAllTimers()
  }, [clearAllTimers])

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isRunning) {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, isRunning])

  const handleClose = () => {
    resetDemo()
    onClose()
  }

  if (!isOpen) return null

  const totalDuration = INITIAL_DEMO_STEPS.reduce((sum, s) => sum + s.duration, 0)
  const completedDuration = steps
    .filter(s => s.status === 'complete')
    .reduce((sum, s) => sum + s.duration, 0)
  const progress = hasStarted ? (completedDuration / totalDuration) * 100 : 0

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={() => !isRunning && handleClose()}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-alexa-card border border-alexa-accent/30 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-alexa-accent/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-alexa-blue/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Auto Demo</h2>
              <p className="text-xs text-gray-500">Full 60-second sales intelligence flow</p>
            </div>
          </div>
          {!isRunning && (
            <button
              onClick={handleClose}
              className="p-1.5 rounded-lg bg-alexa-accent/30 text-gray-400 hover:text-white hover:bg-alexa-accent/50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-alexa-dark">
          <div
            className="h-full bg-alexa-blue transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Steps */}
        <div className="px-6 py-5 space-y-3">
          {steps.map((step) => (
            <div
              key={step.id}
              className={`flex items-start gap-3 p-3 rounded-lg border transition-all duration-300 ${
                step.status === 'running'
                  ? 'bg-alexa-blue/10 border-alexa-blue/30 shadow-lg shadow-alexa-blue/5'
                  : step.status === 'complete'
                  ? 'bg-green-500/5 border-green-500/20'
                  : 'bg-alexa-dark/30 border-alexa-accent/20'
              }`}
            >
              {/* Step number / status icon */}
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${
                step.status === 'running'
                  ? 'bg-alexa-blue/20 text-alexa-blue'
                  : step.status === 'complete'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-600/20 text-gray-500'
              }`}>
                {step.status === 'complete' ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : step.status === 'running' ? (
                  <div className="w-4 h-4 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <span className="text-xs font-medium">{step.id}</span>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className={`text-sm font-medium ${
                    step.status === 'running' ? 'text-white' :
                    step.status === 'complete' ? 'text-gray-300' : 'text-gray-500'
                  }`}>
                    {step.title}
                  </p>
                  <DemoStatusIndicator status={step.status} />
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-alexa-accent/20 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {isRunning
              ? `Step ${currentStepIndex + 1} of ${steps.length}`
              : hasStarted
              ? 'Demo finished'
              : 'Ready to start'}
          </span>
          <div className="flex items-center gap-2">
            {hasStarted && !isRunning && (
              <button
                onClick={resetDemo}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                Reset
              </button>
            )}
            {!hasStarted && (
              <button
                onClick={startDemo}
                className="flex items-center gap-2 px-5 py-2 bg-alexa-blue text-alexa-dark font-semibold rounded-lg hover:bg-alexa-blue/80 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Start Demo
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
