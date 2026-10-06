import { useState, useRef, useCallback, useEffect } from 'react'

interface VoiceInputProps {
  onTranscript: (text: string) => void
  isListening: boolean
  onListeningChange: (listening: boolean) => void
}

// Web Speech API types
interface SpeechRecognitionEvent {
  results: SpeechRecognitionResultList
  resultIndex: number
}

interface SpeechRecognitionInstance {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: ((event: { error: string }) => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance
    webkitSpeechRecognition: new () => SpeechRecognitionInstance
  }
}

const SAMPLE_TRANSCRIPTS = [
  "Hi Sarah, this is John from Sage. I wanted to follow up on our conversation last week about the enterprise license. We've got 20 seats ready to go and the budget was approved. Can we schedule a demo for next Tuesday?",
  "Hey Mike, John here from Sage. I know you're evaluating competitors right now. I wanted to share our new pricing structure — we can offer a 15% discount on the platform deal if we close by end of month. What do you think?",
  "Hi Jennifer, this is John calling from Sage. I understand your team just started evaluating solutions. I'd love to set up a quick call to walk you through our team features. Are you available Thursday afternoon?",
  "David, John from Sage. Congrats on the signed contract! I wanted to confirm the rollout starts next month and make sure we have everything in place. Do you need any additional seats or features added before we kick off?",
  "Hi Lisa, John from Sage. David Stark referred me — he had great things to say about your team. I'd love to learn more about what Wayne Enterprises is looking for and see if we can help. Do you have 15 minutes this week?",
]

export default function VoiceInput({ onTranscript, isListening, onListeningChange }: VoiceInputProps) {
  const [liveTranscript, setLiveTranscript] = useState('')
  const [fallbackText, setFallbackText] = useState('')
  const [useFallback, setUseFallback] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)
  const transcriptRef = useRef('')

  const hasSpeechRecognition = typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)

  useEffect(() => {
    if (!hasSpeechRecognition) {
      setUseFallback(true)
    }
  }, [hasSpeechRecognition])

  const startListening = useCallback(() => {
    if (!hasSpeechRecognition) {
      setUseFallback(true)
      return
    }

    setMicError(null)
    setLiveTranscript('')
    transcriptRef.current = ''

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'en-US'

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = ''
      let interimTranscript = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          finalTranscript += result[0].transcript
        } else {
          interimTranscript += result[0].transcript
        }
      }

      const fullTranscript = transcriptRef.current + finalTranscript
      transcriptRef.current = fullTranscript
      setLiveTranscript(fullTranscript + interimTranscript)
    }

    recognition.onerror = (event: { error: string }) => {
      if (event.error === 'not-allowed') {
        setMicError('Microphone access denied. Please allow microphone access or use text input.')
      } else if (event.error === 'no-speech') {
        setMicError('No speech detected. Try again or use text input.')
      } else {
        setMicError(`Speech recognition error: ${event.error}. Using text input.`)
      }
      setUseFallback(true)
      onListeningChange(false)
    }

    recognition.onend = () => {
      onListeningChange(false)
      if (transcriptRef.current) {
        onTranscript(transcriptRef.current)
      }
    }

    recognitionRef.current = recognition
    recognition.start()
    onListeningChange(true)
  }, [hasSpeechRecognition, onListeningChange, onTranscript])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
    onListeningChange(false)
  }, [onListeningChange])

  const toggleListening = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  const handleFallbackSubmit = () => {
    if (fallbackText.trim()) {
      onTranscript(fallbackText.trim())
      setFallbackText('')
    }
  }

  const loadSampleTranscript = (index: number) => {
    const text = SAMPLE_TRANSCRIPTS[index]
    setFallbackText(text)
    onTranscript(text)
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
          </svg>
          Voice Input
        </h3>
        {isListening && (
          <span className="flex items-center gap-1.5 text-xs text-red-400 animate-pulse">
            <span className="w-2 h-2 bg-red-500 rounded-full"></span>
            REC
          </span>
        )}
      </div>

      {!useFallback ? (
        <div className="space-y-4">
          {/* Microphone Button */}
          <div className="flex flex-col items-center gap-3">
            <button
              onClick={toggleListening}
              className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
                isListening
                  ? 'bg-red-500/20 border-2 border-red-500 shadow-lg shadow-red-500/20'
                  : 'bg-alexa-blue/10 border-2 border-alexa-blue/50 hover:border-alexa-blue hover:bg-alexa-blue/20'
              }`}
            >
              {isListening && (
                <span className="absolute inset-0 rounded-full bg-red-500/10 animate-ping"></span>
              )}
              <svg
                className={`w-8 h-8 transition-colors ${isListening ? 'text-red-400' : 'text-alexa-blue'}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>
            <p className="text-sm text-gray-400">
              {isListening ? 'Listening... Click to stop' : 'Click to start voice input'}
            </p>
          </div>

          {/* Live Transcript */}
          {liveTranscript && (
            <div className="bg-alexa-dark/50 rounded-lg p-3 border border-alexa-accent/20">
              <p className="text-xs text-gray-500 mb-1">Live Transcript</p>
              <p className="text-sm text-gray-300 leading-relaxed">{liveTranscript}</p>
            </div>
          )}

          {/* Error */}
          {micError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm text-red-400">{micError}</p>
            </div>
          )}

          {/* Sample transcripts */}
          <div className="border-t border-alexa-accent/20 pt-3">
            <p className="text-xs text-gray-500 mb-2">Or load a sample transcript:</p>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_TRANSCRIPTS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => loadSampleTranscript(i)}
                  className="px-3 py-1.5 text-xs bg-alexa-accent/20 text-alexa-blue rounded-full hover:bg-alexa-accent/40 transition-colors"
                >
                  Sample {i + 1}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Fallback text input */
        <div className="space-y-3">
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
            <p className="text-sm text-yellow-400">
              Speech recognition not available. Use text input below.
            </p>
          </div>
          <textarea
            value={fallbackText}
            onChange={(e) => setFallbackText(e.target.value)}
            placeholder="Type or paste a call transcript here..."
            className="w-full h-32 bg-alexa-dark/50 border border-alexa-accent/30 rounded-lg p-3 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-alexa-blue resize-none"
          />
          <div className="flex gap-2">
            <button
              onClick={handleFallbackSubmit}
              disabled={!fallbackText.trim()}
              className="px-4 py-2 bg-alexa-blue text-alexa-dark font-medium rounded-lg hover:bg-alexa-blue/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-sm"
            >
              Submit Transcript
            </button>
            <button
              onClick={() => setUseFallback(false)}
              className="px-4 py-2 bg-alexa-accent/30 text-gray-300 rounded-lg hover:bg-alexa-accent/50 transition-colors text-sm"
            >
              Try Voice
            </button>
          </div>
          <div className="border-t border-alexa-accent/20 pt-3">
            <p className="text-xs text-gray-500 mb-2">Load a sample:</p>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_TRANSCRIPTS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => loadSampleTranscript(i)}
                  className="px-3 py-1.5 text-xs bg-alexa-accent/20 text-alexa-blue rounded-full hover:bg-alexa-accent/40 transition-colors"
                >
                  Sample {i + 1}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
