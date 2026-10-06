import { useRef, useEffect } from 'react'

interface TranscriptViewProps {
  transcript: string
  isListening: boolean
  callStartTime: Date | null
}

const SAMPLE_CALLS = [
  {
    label: "Sarah Chen — Enterprise License",
    transcript: "Hi Sarah, this is John from Sage. I wanted to follow up on our conversation last week about the enterprise license. We've got 20 seats ready to go and the budget was approved. Can we schedule a demo for next Tuesday?\n\nSarah: Hi John, yes I remember our conversation. The team is really excited about the enterprise features. Tuesday works great for us. How about 2 PM?\n\nJohn: 2 PM works perfectly. I'll send over a calendar invite with the demo link. Is there anything specific you'd like me to prepare?\n\nSarah: Yes, could you include details about the API integrations? We're particularly interested in the Salesforce and Slack integrations.\n\nJohn: Absolutely, I'll have that ready for you. Looking forward to Tuesday!"
  },
  {
    label: "Mike Johnson — Platform Deal",
    transcript: "Hey Mike, John here from Sage. I know you're evaluating competitors right now. I wanted to share our new pricing structure — we can offer a 15% discount on the platform deal if we close by end of month. What do you think?\n\nMike: Hey John, appreciate the call. We are looking at a couple of other options. The discount helps, but I need to discuss with my team. Can you send over the revised proposal?\n\nJohn: Of course, I'll have it in your inbox within the hour. The 15% discount is locked in through the end of the month, so you have some time. Is there anything else I can address?\n\nMike: The main concern is implementation time. We need to be up and running within 6 weeks.\n\nJohn: That's totally doable. Our implementation team can have you live in 4 weeks. I'll include that timeline in the proposal."
  },
  {
    label: "Jennifer Williams — Team Plan",
    transcript: "Hi Jennifer, this is John calling from Sage. I understand your team just started evaluating solutions. I'd love to set up a quick call to walk you through our team features. Are you available Thursday afternoon?\n\nJennifer: Hi John, thanks for reaching out. Yes, we're in the early stages of evaluation. Thursday at 3 PM works for me.\n\nJohn: Perfect, I'll send a calendar invite. I'll also include a one-pager about our team features so you can share it with your team beforehand.\n\nJennifer: That would be great. We're particularly interested in collaboration features and reporting dashboards.\n\nJohn: You'll love what we've built. I'll make sure to highlight those areas in the demo."
  },
  {
    label: "David Stark — Closed Won",
    transcript: "David, John from Sage. Congrats on the signed contract! I wanted to confirm the rollout starts next month and make sure we have everything in place. Do you need any additional seats or features added before we kick off?\n\nDavid: Thanks John! Yes, we're excited to get started. Actually, we might need 5 more seats — the marketing team wants in too.\n\nJohn: No problem at all. I'll update the contract to 25 seats total. The pricing stays the same per seat. I'll also set up a kickoff call with your team for early next month.\n\nDavid: Perfect. Let's do the first Tuesday of the month at 10 AM.\n\nJohn: Done. I'll send over the updated paperwork and calendar invite today."
  },
  {
    label: "Lisa Wayne — New Lead",
    transcript: "Hi Lisa, John from Sage. David Stark referred me — he had great things to say about your team. I'd love to learn more about what Wayne Enterprises is looking for and see if we can help. Do you have 15 minutes this week?\n\nLisa: Hi John, David mentioned you. Sure, I can spare some time. We're looking for a CRM solution for our sales team of about 30 people. What makes Sage different?\n\nJohn: Great question. Sage is built specifically for sales teams — it's passive, meaning it listens to your calls and automatically updates your CRM. No manual data entry. Can I show you a quick demo?\n\nLisa: That sounds interesting. How does it handle existing data? We're currently using Salesforce.\n\nJohn: We integrate directly with Salesforce. Your existing contacts and deals sync over automatically. Would Friday at 11 AM work for a demo?\n\nLisa: Friday at 11 works. Send me an invite."
  }
]

export default function TranscriptView({ transcript, isListening, callStartTime }: TranscriptViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [transcript])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const loadSample = (index: number) => {
    // This will be handled by parent via a custom event or callback
    const event = new CustomEvent('loadSampleTranscript', { detail: { index } })
    window.dispatchEvent(event)
  }

  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Call Transcript
        </h3>
        <div className="flex items-center gap-3">
          {callStartTime && (
            <span className="text-xs text-gray-500 font-mono">
              {formatTime(callStartTime)}
            </span>
          )}
          {isListening && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/30 rounded-full">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="text-xs text-green-400 font-medium">Call in progress</span>
            </span>
          )}
        </div>
      </div>

      {/* Transcript Display */}
      <div
        ref={scrollRef}
        className="bg-alexa-dark/50 rounded-lg p-4 border border-alexa-accent/20 h-64 overflow-y-auto scroll-smooth"
      >
        {transcript ? (
          <div className="space-y-3">
            {transcript.split('\n').map((line, i) => (
              <p key={i} className={`text-sm leading-relaxed ${
                line.startsWith('John:') ? 'text-alexa-blue' :
                line.startsWith('Sarah:') || line.startsWith('Mike:') || line.startsWith('Jennifer:') ||
                line.startsWith('David:') || line.startsWith('Lisa:') ? 'text-gray-300' :
                'text-gray-400'
              }`}>
                {line}
              </p>
            ))}
            {isListening && (
              <div className="flex items-center gap-2 text-alexa-blue">
                <span className="w-2 h-2 bg-alexa-blue rounded-full animate-pulse"></span>
                <span className="text-sm italic">Listening...</span>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg className="w-12 h-12 text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-gray-500 text-sm">No transcript yet</p>
            <p className="text-gray-600 text-xs mt-1">Start voice input or load a sample call</p>
          </div>
        )}
      </div>

      {/* Sample Call Buttons */}
      <div className="mt-4">
        <p className="text-xs text-gray-500 mb-2">Load a sample call:</p>
        <div className="flex flex-wrap gap-2">
          {SAMPLE_CALLS.map((call, i) => (
            <button
              key={i}
              onClick={() => loadSample(i)}
              className="px-3 py-1.5 text-xs bg-alexa-accent/20 text-alexa-blue rounded-full hover:bg-alexa-accent/40 transition-colors"
              title={call.label}
            >
              {call.label.split(' — ')[0]}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export { SAMPLE_CALLS }
