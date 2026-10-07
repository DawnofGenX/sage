import { useState, useEffect, useCallback } from 'react'
import DemoFlow from './DemoFlow'

interface DemoModeProps {
  isOpen: boolean
  onClose: () => void
  onComplete: () => void
}

export default function DemoMode({ isOpen, onClose, onComplete }: DemoModeProps) {
  const [demoKey, setDemoKey] = useState(0)

  const handleComplete = useCallback(() => {
    onComplete()
  }, [onComplete])

  const handleClose = useCallback(() => {
    setDemoKey(prev => prev + 1)
    onClose()
  }, [onClose])

  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        handleClose()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [isOpen, handleClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />
      <div className="relative w-full max-w-lg mx-4 bg-alexa-card border border-alexa-accent/30 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-alexa-accent/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-alexa-blue/20 flex items-center justify-center">
              <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Agentic Chain Demo</h2>
              <p className="text-xs text-gray-500">Real MCP tool chain</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg bg-alexa-accent/30 text-gray-400 hover:text-white hover:bg-alexa-accent/50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <DemoFlow key={demoKey} onComplete={handleComplete} />
      </div>
    </div>
  )
}
