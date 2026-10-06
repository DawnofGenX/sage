import { useState, useEffect, useRef, useCallback } from 'react'

interface TranscriptLine {
  speaker: 'rep' | 'prospect'
  text: string
  timestamp: number
}

interface CallSimulatorProps {
  onCallEnd?: (transcript: string, duration: number) => void
}

const SAMPLE_CALL_TRANSCRIPT: TranscriptLine[] = [
  { speaker: 'rep', text: "Hi Sarah, this is John from Sage. How are you doing today?", timestamp: 0 },
  { speaker: 'prospect', text: "Hi John, I'm doing well! Thanks for calling. I've been meaning to reach out about the enterprise license.", timestamp: 3000 },
  { speaker: 'rep', text: "That's great to hear! I wanted to follow up on our conversation last week. We've got 20 seats ready to go and the budget was approved. Can we schedule a demo for next Tuesday?", timestamp: 7000 },
  { speaker: 'prospect', text: "Yes, I remember our conversation. The team is really excited about the enterprise features. Tuesday works great for us. How about 2 PM?", timestamp: 12000 },
  { speaker: 'rep', text: "2 PM works perfectly. I'll send over a calendar invite with the demo link. Is there anything specific you'd like me to prepare?", timestamp: 16000 },
  { speaker: 'prospect', text: "Yes, could you include details about the API integrations? We're particularly interested in the Salesforce and Slack integrations.", timestamp: 20000 },
  { speaker: 'rep', text: "Absolutely, I'll have that ready for you. Looking forward to Tuesday!", timestamp: 24000 },
]

export default function CallSimulator({ onCallEnd }: CallSimulatorProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isCallActive, setIsCallActive] = useState(false)
  const [visibleLines, setVisibleLines] = useState<TranscriptLine[]>([])
  const [currentLineIndex, setCurrentLineIndex] = useState(0)
  const [callDuration, setCallDuration] = useState(0)
  const [callEnded, setCallEnded] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const lineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [visibleLines])

  // Call duration timer
  useEffect(() => {
    if (isCallActive && isPlaying) {
      timerRef.current = setInterval(() => {
        setCallDuration(prev => prev + 1)
      }, 1000)
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isCallActive, isPlaying])

  // Line-by-line transcript display
  useEffect(() => {
    if (!isPlaying || currentLineIndex >= SAMPLE_CALL_TRANSCRIPT.length) {
      return
    }

    const nextLine = SAMPLE_CALL_TRANSCRIPT[currentLineIndex]
    const delay = currentLineIndex === 0 ? 500 : nextLine.timestamp - (SAMPLE_CALL_TRANSCRIPT[currentLineIndex - 1]?.timestamp || 0)

    lineTimerRef.current = setTimeout(() => {
      setVisibleLines(prev => [...prev, nextLine])
      setCurrentLineIndex(prev => prev + 1)
    }, Math.min(delay, 3000)) // Cap delay at 3s for demo

    return () => {
      if (lineTimerRef.current) clearTimeout(lineTimerRef.current)
    }
  }, [isPlaying, currentLineIndex])

  const startCall = useCallback(() => {
    setIsCallActive(true)
    setIsPlaying(true)
    setCallEnded(false)
    setVisibleLines([])
    setCurrentLineIndex(0)
    setCallDuration(0)
  }, [])

  const togglePlayPause = useCallback(() => {
    setIsPlaying(prev => !prev)
  }, [])

  const endCall = useCallback(() => {
    setIsPlaying(false)
    setIsCallActive(false)
    setCallEnded(true)
    if (timerRef.current) clearInterval(timerRef.current)
    if (lineTimerRef.current) clearTimeout(lineTimerRef.current)

    const transcript = visibleLines
      .map(l => `${l.speaker === 'rep' ? 'John' : 'Sarah'}: ${l.text}`)
      .join('\n')
    onCallEnd?.(transcript, callDuration)
  }, [visibleLines, callDuration, onCallEnd])

  const resetCall = useCallback(() => {
    setIsCallActive(false)
    setIsPlaying(false)
    setCallEnded(false)
    setVisibleLines([])
    setCurrentLineIndex(0)
    setCallDuration(0)
  }, [])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const speakerLabel = (speaker: 'rep' | 'prospect') => {
    return speaker === 'rep' ? 'John (Sales Rep)' : 'Sarah (Prospect)'
  }

  const speakerColor = (speaker: 'rep' | 'prospect') => {
    return speaker === 'rep' ? 'text-alexa-blue' : 'text-purple-400'
  }

  const speakerBg = (speaker: 'rep' | 'prospect') => {
    return speaker === 'rep' ? 'bg-alexa-blue/10 border-alexa-blue/30' : 'bg-purple-500/10 border-purple-500/30'
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
          Call Simulator
        </h3>
        <div className="flex items-center gap-3">
          {isCallActive && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/30 rounded-full">
              <span className={`w-2 h-2 rounded-full ${isPlaying ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></span>
              <span className="text-xs text-green-400 font-medium">
                {isPlaying ? 'Live' : 'Paused'}
              </span>
            </span>
          )}
          {callEnded && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-500/10 border border-gray-500/30 rounded-full">
              <span className="text-xs text-gray-400 font-medium">Ended</span>
            </span>
          )}
        </div>
      </div>

      {/* Call Controls */}
      <div className="flex items-center gap-3 mb-4">
        {!isCallActive && !callEnded && (
          <button
            onClick={startCall}
            className="flex items-center gap-2 px-4 py-2 bg-green-500/20 border border-green-500/30 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            Start Call
          </button>
        )}
        {isCallActive && (
          <>
            <button
              onClick={togglePlayPause}
              className="flex items-center gap-2 px-4 py-2 bg-alexa-blue/20 border border-alexa-blue/30 text-alexa-blue rounded-lg hover:bg-alexa-blue/30 transition-colors text-sm font-medium"
            >
              {isPlaying ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Pause
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                  Play
                </>
              )}
            </button>
            <button
              onClick={endCall}
              className="flex items-center gap-2 px-4 py-2 bg-red-500/20 border border-red-500/30 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors text-sm font-medium"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 8l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.516l2.257-1.13a1 1 0 00.502-1.21L9.228 3.684A1 1 0 008.28 3H5z" />
              </svg>
              End Call
            </button>
          </>
        )}
        {callEnded && (
          <button
            onClick={resetCall}
            className="flex items-center gap-2 px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            New Call
          </button>
        )}
        {isCallActive && (
          <span className="text-sm font-mono text-gray-400 ml-auto">
            {formatDuration(callDuration)}
          </span>
        )}
      </div>

      {/* Transcript Display */}
      <div
        ref={scrollRef}
        className="bg-alexa-dark/50 rounded-lg p-4 border border-alexa-accent/20 h-72 overflow-y-auto scroll-smooth"
      >
        {visibleLines.length === 0 && !callEnded ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg className="w-12 h-12 text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-gray-500 text-sm">No call in progress</p>
            <p className="text-gray-600 text-xs mt-1">Click "Start Call" to begin simulation</p>
          </div>
        ) : (
          <div className="space-y-3">
            {visibleLines.map((line, i) => (
              <div key={i} className={`flex gap-3 ${line.speaker === 'rep' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[80%] rounded-lg p-3 border ${speakerBg(line.speaker)}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-semibold ${speakerColor(line.speaker)}`}>
                      {speakerLabel(line.speaker)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-200 leading-relaxed">{line.text}</p>
                </div>
              </div>
            ))}
            {isPlaying && currentLineIndex < SAMPLE_CALL_TRANSCRIPT.length && (
              <div className="flex items-center gap-2 text-gray-500">
                <span className="w-2 h-2 bg-alexa-blue rounded-full animate-pulse"></span>
                <span className="text-xs italic">Speaking...</span>
              </div>
            )}
            {callEnded && (
              <div className="flex items-center justify-center gap-2 text-gray-500 pt-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-sm">Call ended — ready for extraction</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Call Summary */}
      {callEnded && visibleLines.length > 0 && (
        <div className="mt-4 p-3 bg-alexa-dark/30 rounded-lg border border-alexa-accent/20">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Duration: <span className="text-white font-mono">{formatDuration(callDuration)}</span></span>
            <span className="text-gray-400">Lines: <span className="text-white">{visibleLines.length}</span></span>
            <span className="text-gray-400">Speakers: <span className="text-white">2</span></span>
          </div>
        </div>
      )}
    </div>
  )
}
