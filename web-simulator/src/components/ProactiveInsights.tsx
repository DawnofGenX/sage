export interface Insight {
  id: string
  text: string
  urgency: 'overdue' | 'stuck' | 'info'
  timestamp?: string
}

interface ProactiveInsightsProps {
  insights: Insight[]
  isGenerating: boolean
  onGenerate: () => void
}

const URGENCY_CONFIG = {
  overdue: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    badge: 'bg-red-500/20 text-red-400',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    label: 'Overdue',
  },
  stuck: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/30',
    text: 'text-yellow-400',
    badge: 'bg-yellow-500/20 text-yellow-400',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    ),
    label: 'Stuck',
  },
  info: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    badge: 'bg-blue-500/20 text-blue-400',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    label: 'Info',
  },
}

export default function ProactiveInsights({ insights, isGenerating, onGenerate }: ProactiveInsightsProps) {
  return (
    <div className="bg-alexa-card rounded-xl p-5 border border-alexa-accent/30">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <svg className="w-5 h-5 text-alexa-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          Proactive Insights
        </h3>
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className="flex items-center gap-2 px-3 py-1.5 bg-alexa-blue/10 border border-alexa-blue/30 text-alexa-blue text-xs font-medium rounded-lg hover:bg-alexa-blue/20 transition-colors disabled:opacity-50"
        >
          {isGenerating ? (
            <>
              <div className="w-3 h-3 border-2 border-alexa-blue border-t-transparent rounded-full animate-spin"></div>
              Generating...
            </>
          ) : (
            <>
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Generate Insights
            </>
          )}
        </button>
      </div>

      {insights.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-16 h-16 bg-alexa-accent/20 rounded-full flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm font-medium">No insights yet</p>
          <p className="text-gray-500 text-xs mt-1">Click "Generate Insights" to analyze your pipeline</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {insights.map((insight) => {
            const config = URGENCY_CONFIG[insight.urgency]
            return (
              <div
                key={insight.id}
                className={`${config.bg} border ${config.border} rounded-lg p-3 transition-all hover:scale-[1.01]`}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex-shrink-0 mt-0.5 ${config.text}`}>
                    {config.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${config.badge}`}>
                        {config.label}
                      </span>
                      {insight.timestamp && (
                        <span className="text-xs text-gray-500">{insight.timestamp}</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-300 leading-relaxed">{insight.text}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
